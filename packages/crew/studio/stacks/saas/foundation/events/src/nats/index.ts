import {
  connect,
  StringCodec,
  type NatsConnection,
  type Subscription,
  type JetStreamClient,
  type JetStreamManager,
} from 'nats';
import type { DomainEvent } from '@saas-studio/domain';
import type { ILogger } from '@saas-studio/logger';
import type { IEventBus, EventHandler, EventSubscription, EventBusOptions } from '../bus';

export interface NatsEventBusOptions extends EventBusOptions {
  servers: string[];
  name?: string;
  token?: string;
  user?: string;
  pass?: string;
  maxReconnectAttempts?: number;
  reconnectTimeWait?: number;
}

export class NatsEventBus implements IEventBus {
  private connection: NatsConnection | null = null;
  private jetstream: JetStreamClient | null = null;
  private jsm: JetStreamManager | null = null;
  private subscriptions: Subscription[] = [];
  private readonly options: NatsEventBusOptions;
  private readonly logger?: ILogger;
  private readonly codec = StringCodec();

  constructor(options: NatsEventBusOptions) {
    this.options = options;
    this.logger = options.logger;
  }

  async connect(): Promise<void> {
    this.logger?.info('Connecting to NATS', { servers: this.options.servers });

    this.connection = await connect({
      servers: this.options.servers,
      name: this.options.name,
      token: this.options.token,
      user: this.options.user,
      pass: this.options.pass,
      maxReconnectAttempts: this.options.maxReconnectAttempts ?? 10,
      reconnectTimeWait: this.options.reconnectTimeWait ?? 1000,
    });

    this.logger?.info('Connected to NATS');

    this.jetstream = this.connection.jetstream();
    this.jsm = await this.connection.jetstreamManager();

    this.handleConnectionEvents();
  }

  async publish<T extends DomainEvent>(event: T): Promise<void> {
    if (!this.connection) {
      throw new Error('NATS not connected');
    }

    const subject = this.eventTypeToSubject(event.eventType);
    const data = this.codec.encode(JSON.stringify(event));

    this.logger?.debug('Publishing event to NATS', {
      eventType: event.eventType,
      subject,
    });

    this.connection.publish(subject, data);
  }

  async publishAll<T extends DomainEvent>(events: T[]): Promise<void> {
    for (const event of events) {
      await this.publish(event);
    }
  }

  async subscribe<T extends DomainEvent>(
    eventType: string,
    handler: EventHandler<T>,
  ): Promise<EventSubscription> {
    if (!this.connection) {
      throw new Error('NATS not connected');
    }

    const subject = this.eventTypeToSubject(eventType);
    const subscription = this.connection.subscribe(subject);
    this.subscriptions.push(subscription);

    this.processSubscription(subscription, handler);

    return {
      unsubscribe: async () => {
        subscription.unsubscribe();
        const index = this.subscriptions.indexOf(subscription);
        if (index > -1) {
          this.subscriptions.splice(index, 1);
        }
      },
    };
  }

  async subscribeToPattern(pattern: string, handler: EventHandler): Promise<EventSubscription> {
    if (!this.connection) {
      throw new Error('NATS not connected');
    }

    const subject = pattern.replace(/\./g, '.').replace(/\*/g, '*');
    const subscription = this.connection.subscribe(subject);
    this.subscriptions.push(subscription);

    this.processSubscription(subscription, handler);

    return {
      unsubscribe: async () => {
        subscription.unsubscribe();
        const index = this.subscriptions.indexOf(subscription);
        if (index > -1) {
          this.subscriptions.splice(index, 1);
        }
      },
    };
  }

  async close(): Promise<void> {
    this.logger?.info('Closing NATS connection');

    for (const subscription of this.subscriptions) {
      subscription.unsubscribe();
    }
    this.subscriptions = [];

    if (this.connection) {
      await this.connection.drain();
      this.connection = null;
    }

    this.jetstream = null;
    this.jsm = null;
  }

  private async processSubscription<T>(
    subscription: Subscription,
    handler: EventHandler<T>,
  ): Promise<void> {
    for await (const msg of subscription) {
      try {
        const data = this.codec.decode(msg.data);
        const event = JSON.parse(data) as T;
        await handler(event);
      } catch (error) {
        this.logger?.error('Failed to process NATS message', {
          error: error instanceof Error ? error.message : 'Unknown',
        });
      }
    }
  }

  private handleConnectionEvents(): void {
    if (!this.connection) return;

    (async () => {
      for await (const status of this.connection!.status()) {
        this.logger?.debug('NATS status', { type: status.type, data: status.data });
      }
    })();
  }

  private eventTypeToSubject(eventType: string): string {
    return `events.${eventType
      .replace(/([A-Z])/g, '.$1')
      .toLowerCase()
      .replace(/^\./, '')}`;
  }
}

export async function createNatsEventBus(options: NatsEventBusOptions): Promise<NatsEventBus> {
  const bus = new NatsEventBus(options);
  await bus.connect();
  return bus;
}
