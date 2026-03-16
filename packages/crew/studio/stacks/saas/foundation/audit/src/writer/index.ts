import { randomUUID } from 'node:crypto';
import { TenantIdSchema } from '@saas-studio/contracts';

interface TransactionClient {
  $executeRawUnsafe: (query: string, ...values: unknown[]) => Promise<number>;
}
import { getActor, getCorrelationId, getContext } from '@saas-studio/identity';
import { CreateAuditEntrySchema } from '../schema';
import type { CreateAuditEntry, AuditEntry, AuditQueryParams } from '../schema';
import type { AuditActionType } from '../types';

export interface AuditWriterConfig {
  tableName?: string;
  captureIpAddress?: boolean;
  captureUserAgent?: boolean;
}

export class AuditWriter {
  private readonly config: Required<AuditWriterConfig>;

  constructor(config: AuditWriterConfig = {}) {
    this.config = {
      tableName: config.tableName ?? 'audit_log',
      captureIpAddress: config.captureIpAddress ?? true,
      captureUserAgent: config.captureUserAgent ?? true,
    };
  }

  async write(tx: TransactionClient, entry: CreateAuditEntry): Promise<AuditEntry> {
    const id = randomUUID();
    const occurredAt = new Date().toISOString();

    const context = getContext();
    const actor = getActor();

    const auditEntry: AuditEntry = {
      id,
      tenantId: entry.tenantId,
      aggregateType: entry.aggregateType,
      aggregateId: entry.aggregateId,
      action: entry.action,
      actorType: entry.actorType ?? actor?.type ?? 'system',
      actorId: entry.actorId ?? actor?.id ?? null,
      actorEmail: entry.actorEmail ?? actor?.email ?? null,
      actorName: entry.actorName ?? actor?.name ?? null,
      before: entry.before ?? null,
      after: entry.after ?? null,
      metadata: entry.metadata ?? null,
      correlationId: entry.correlationId ?? getCorrelationId() ?? null,
      requestId: entry.requestId ?? context?.requestId ?? null,
      ipAddress: entry.ipAddress ?? null,
      userAgent: entry.userAgent ?? null,
      occurredAt,
    };

    await tx.$executeRawUnsafe(
      `INSERT INTO ${this.config.tableName} (
        id, tenant_id, aggregate_type, aggregate_id, action,
        actor_type, actor_id, actor_email, actor_name,
        before, after, metadata, correlation_id, request_id,
        ip_address, user_agent, occurred_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)`,
      auditEntry.id,
      auditEntry.tenantId,
      auditEntry.aggregateType,
      auditEntry.aggregateId,
      auditEntry.action,
      auditEntry.actorType,
      auditEntry.actorId,
      auditEntry.actorEmail,
      auditEntry.actorName,
      auditEntry.before ? JSON.stringify(auditEntry.before) : null,
      auditEntry.after ? JSON.stringify(auditEntry.after) : null,
      auditEntry.metadata ? JSON.stringify(auditEntry.metadata) : null,
      auditEntry.correlationId,
      auditEntry.requestId,
      auditEntry.ipAddress,
      auditEntry.userAgent,
      auditEntry.occurredAt,
    );

    return auditEntry;
  }

  async writeBulk(tx: TransactionClient, entries: CreateAuditEntry[]): Promise<AuditEntry[]> {
    const results: AuditEntry[] = [];

    for (const entry of entries) {
      const result = await this.write(tx, entry);
      results.push(result);
    }

    return results;
  }
}

export class AuditEntryBuilder {
  private entry: Partial<CreateAuditEntry> = {};

  tenant(tenantId: string): this {
    this.entry.tenantId = TenantIdSchema.parse(tenantId);
    return this;
  }

  aggregate(type: string, id: string): this {
    this.entry.aggregateType = type;
    this.entry.aggregateId = id;
    return this;
  }

  action(action: AuditActionType | string): this {
    this.entry.action = action;
    return this;
  }

  actor(type: CreateAuditEntry['actorType'], id?: string): this {
    this.entry.actorType = type;
    this.entry.actorId = id ?? null;
    return this;
  }

  before<T>(data: T): this {
    this.entry.before = data;
    return this;
  }

  after<T>(data: T): this {
    this.entry.after = data;
    return this;
  }

  metadata(data: Record<string, unknown>): this {
    this.entry.metadata = data;
    return this;
  }

  correlationId(id: string): this {
    this.entry.correlationId = id;
    return this;
  }

  build(): CreateAuditEntry {
    if (!this.entry.tenantId) {
      throw new Error('Audit entry requires tenantId');
    }
    if (!this.entry.aggregateType || !this.entry.aggregateId) {
      throw new Error('Audit entry requires aggregate type and id');
    }
    if (!this.entry.action) {
      throw new Error('Audit entry requires action');
    }
    if (!this.entry.actorType) {
      this.entry.actorType = 'system';
    }

    return CreateAuditEntrySchema.parse(this.entry);
  }
}

export function auditEntry(): AuditEntryBuilder {
  return new AuditEntryBuilder();
}

export function createAuditWriter(config?: AuditWriterConfig): AuditWriter {
  return new AuditWriter(config);
}
