import {
  connect,
  type NatsConnection,
  StringCodec,
  type JetStreamClient,
  type JetStreamManager,
  RetentionPolicy,
  StorageType,
} from 'nats';
import type { ILogger } from '@saas-studio/logger';
import type { OutboxEntry } from '../schema';

export interface EventPublisher {
  publish(entry: OutboxEntry): Promise<void>;
  connect(): Promise<void>;
  disconnect(): Promise<void>;
}

export interface NatsPublisherConfig {
  url: string;
  streamName?: string;
  subjectPrefix?: string;
  logger?: ILogger;
}

export class NatsPublisher implements EventPublisher {
  private connection: NatsConnection | null = null;
  private jetstream: JetStreamClient | null = null;
  private readonly codec = StringCodec();
  private readonly config: Required<Omit<NatsPublisherConfig, 'logger'>> & { logger?: ILogger };

  constructor(config: NatsPublisherConfig) {
    this.config = {
      url: config.url,
      streamName: config.streamName ?? 'EVENTS',
      subjectPrefix: config.subjectPrefix ?? 'events',
      logger: config.logger,
    };
  }

  async connect(): Promise<void> {
    this.connection = await connect({
      servers: this.config.url,
      maxReconnectAttempts: 10,
      reconnectTimeWait: 2000,
    });

    this.jetstream = this.connection.jetstream();

    const jsm = await this.connection.jetstreamManager();
    await this.ensureStream(jsm);

    this.config.logger?.info('Connected to NATS', { url: this.config.url });
  }

  private async ensureStream(jsm: JetStreamManager): Promise<void> {
    try {
      await jsm.streams.info(this.config.streamName);
    } catch {
      await jsm.streams.add({
        name: this.config.streamName,
        subjects: [`${this.config.subjectPrefix}.>`],
        retention: RetentionPolicy.Limits,
        max_msgs: 1000000,
        max_bytes: 1024 * 1024 * 1024, // 1GB
        max_age: 7 * 24 * 60 * 60 * 1000000000, // 7 days in nanoseconds
        storage: StorageType.File,
        num_replicas: 1,
      });

      this.config.logger?.info('Created NATS stream', {
        stream: this.config.streamName,
      });
    }
  }

  async publish(entry: OutboxEntry): Promise<void> {
    if (!this.jetstream) {
      throw new Error('NATS not connected');
    }

    const subject = `${this.config.subjectPrefix}.${entry.aggregateType}.${entry.eventType}`;

    const message = JSON.stringify({
      id: entry.id,
      tenantId: entry.tenantId,
      eventType: entry.eventType,
      aggregateType: entry.aggregateType,
      aggregateId: entry.aggregateId,
      payload: entry.payload,
      metadata: entry.metadata,
      occurredAt: entry.createdAt,
    });

    await this.jetstream.publish(subject, this.codec.encode(message), {
      msgID: entry.id,
    });

    this.config.logger?.debug('Published event to NATS', {
      subject,
      eventId: entry.id,
      eventType: entry.eventType,
    });
  }

  async disconnect(): Promise<void> {
    if (this.connection) {
      await this.connection.drain();
      await this.connection.close();
      this.connection = null;
      this.jetstream = null;
      this.config.logger?.info('Disconnected from NATS');
    }
  }
}

export class InMemoryPublisher implements EventPublisher {
  public readonly events: OutboxEntry[] = [];

  async publish(entry: OutboxEntry): Promise<void> {
    this.events.push(entry);
  }

  async connect(): Promise<void> {}
  async disconnect(): Promise<void> {}

  clear(): void {
    this.events.length = 0;
  }
}

export function createNatsPublisher(config: NatsPublisherConfig): NatsPublisher {
  return new NatsPublisher(config);
}

export function createInMemoryPublisher(): InMemoryPublisher {
  return new InMemoryPublisher();
}
