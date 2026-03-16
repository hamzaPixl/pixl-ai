import { randomUUID } from 'node:crypto';
import { CorrelationIdSchema, TenantIdSchema, type CorrelationId } from '@saas-studio/contracts';

interface TransactionClient {
  $executeRawUnsafe: (query: string, ...values: unknown[]) => Promise<number>;
}
import { getCorrelationId, getContext, getActor } from '@saas-studio/identity';
import { CreateOutboxEntrySchema, OutboxStatus } from '../schema';
import type { CreateOutboxEntry, OutboxEntry } from '../schema';

function parseCorrelationId(value: string | undefined): CorrelationId | undefined {
  if (!value) return undefined;
  const result = CorrelationIdSchema.safeParse(value);
  return result.success ? result.data : undefined;
}

export interface OutboxWriterConfig {
  tableName?: string;
}

export class OutboxWriter {
  private readonly tableName: string;

  constructor(config: OutboxWriterConfig = {}) {
    this.tableName = config.tableName ?? 'outbox';
  }

  async write(tx: TransactionClient, entry: CreateOutboxEntry): Promise<OutboxEntry> {
    const id = randomUUID();
    const now = new Date().toISOString();
    const context = getContext();
    const actor = getActor();
    const correlationId = entry.correlationId ?? parseCorrelationId(getCorrelationId());

    const outboxEntry: OutboxEntry = {
      id,
      tenantId: entry.tenantId,
      eventType: entry.eventType,
      aggregateType: entry.aggregateType,
      aggregateId: entry.aggregateId,
      payload: entry.payload,
      correlationId,
      causationId: entry.causationId,
      metadata: {
        eventId: id,
        eventType: entry.eventType,
        aggregateType: entry.aggregateType,
        aggregateId: entry.aggregateId,
        version: 1,
        occurredAt: now,
        correlationId,
        actor: {
          type: actor?.type ?? 'system',
          id: actor?.id,
          tenantId: entry.tenantId,
          email: actor?.email,
          name: actor?.name,
        },
      },
      status: OutboxStatus.PENDING,
      attempts: 0,
      lastError: null,
      publishedAt: null,
      createdAt: now,
      processedAt: null,
    };

    await tx.$executeRawUnsafe(
      `INSERT INTO ${this.tableName} (
        id, tenant_id, event_type, aggregate_type, aggregate_id,
        payload, metadata, correlation_id, causation_id,
        status, attempts, last_error, published_at, created_at, processed_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)`,
      outboxEntry.id,
      outboxEntry.tenantId,
      outboxEntry.eventType,
      outboxEntry.aggregateType,
      outboxEntry.aggregateId,
      JSON.stringify(outboxEntry.payload),
      JSON.stringify(outboxEntry.metadata),
      outboxEntry.correlationId,
      outboxEntry.causationId,
      outboxEntry.status,
      outboxEntry.attempts,
      outboxEntry.lastError,
      outboxEntry.publishedAt,
      outboxEntry.createdAt,
      outboxEntry.processedAt,
    );

    return outboxEntry;
  }

  async writeBulk(tx: TransactionClient, entries: CreateOutboxEntry[]): Promise<OutboxEntry[]> {
    const results: OutboxEntry[] = [];

    for (const entry of entries) {
      const result = await this.write(tx, entry);
      results.push(result);
    }

    return results;
  }
}

export class OutboxEntryBuilder {
  private entry: Partial<CreateOutboxEntry> = {};

  tenant(tenantId: string): this {
    this.entry.tenantId = TenantIdSchema.parse(tenantId);
    return this;
  }

  event(type: string): this {
    this.entry.eventType = type;
    return this;
  }

  aggregate(type: string, id: string): this {
    this.entry.aggregateType = type;
    this.entry.aggregateId = id;
    return this;
  }

  payload<T>(data: T): this {
    this.entry.payload = data;
    return this;
  }

  correlationId(id: string): this {
    this.entry.correlationId = CorrelationIdSchema.parse(id);
    return this;
  }

  causationId(id: string): this {
    this.entry.causationId = id;
    return this;
  }

  build(): CreateOutboxEntry {
    if (!this.entry.tenantId) {
      throw new Error('Outbox entry requires tenantId');
    }
    if (!this.entry.eventType) {
      throw new Error('Outbox entry requires eventType');
    }
    if (!this.entry.aggregateType || !this.entry.aggregateId) {
      throw new Error('Outbox entry requires aggregate type and id');
    }

    return CreateOutboxEntrySchema.parse(this.entry);
  }
}

export function outboxEntry(): OutboxEntryBuilder {
  return new OutboxEntryBuilder();
}

export function createOutboxWriter(config?: OutboxWriterConfig): OutboxWriter {
  return new OutboxWriter(config);
}
