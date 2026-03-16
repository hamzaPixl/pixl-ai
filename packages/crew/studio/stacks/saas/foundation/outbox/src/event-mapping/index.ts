import type { DomainEvent, DomainEventMetadata } from '@saas-studio/domain';
import type { CreateOutboxEntry } from '../schema';
import type { CreateAuditEntry } from '@saas-studio/audit';

/**
 * Converts a domain event class name to an outbox event type.
 * Example: TaskCreatedEvent -> task.created
 */
export function getOutboxEventType(event: DomainEvent): string {
  const className = event.constructor.name;
  const eventName = className
    .replace(/Event$/, '')
    .replace(/([A-Z])/g, '_$1')
    .toLowerCase()
    .replace(/^_/, '');

  const parts = eventName.split('_');
  if (parts.length >= 2) {
    const aggregate = parts[0];
    const action = parts.slice(1).join('_');
    return `${aggregate}.${action}`;
  }

  return `${event.aggregateType.toLowerCase()}.${eventName}`;
}

/**
 * Derives an audit action from a domain event class name.
 * Example: TaskCreatedEvent -> CREATE, TaskUpdatedEvent -> UPDATE
 */
export function getAuditAction(event: DomainEvent): string {
  const className = event.constructor.name;

  if (className.includes('Created')) return 'CREATE';
  if (className.includes('Updated')) return 'UPDATE';
  if (className.includes('Deleted')) return 'DELETE';
  if (className.includes('Completed')) return 'COMPLETE';
  if (className.includes('Cancelled')) return 'CANCEL';
  if (className.includes('Archived')) return 'ARCHIVE';
  if (className.includes('Started')) return 'START';
  if (className.includes('Assigned')) return 'ASSIGN';
  if (className.includes('Restored')) return 'RESTORE';
  if (className.includes('Approved')) return 'APPROVE';
  if (className.includes('Rejected')) return 'REJECT';
  if (className.includes('Submitted')) return 'SUBMIT';

  return className.replace(/Event$/, '').toUpperCase();
}

/**
 * Converts a domain event to an outbox entry for persistence.
 */
export function domainEventToOutboxEntry(
  event: DomainEvent,
  tenantId: string,
): CreateOutboxEntry {
  const eventWithMeta = event as DomainEvent & { metadata?: DomainEventMetadata };

  return {
    tenantId: tenantId as CreateOutboxEntry['tenantId'],
    eventType: getOutboxEventType(event),
    aggregateType: event.aggregateType,
    aggregateId: event.aggregateId,
    payload: event.payload,
    correlationId: (eventWithMeta.metadata?.correlationId as CreateOutboxEntry['correlationId']) ?? undefined,
    causationId: eventWithMeta.metadata?.causationId,
  };
}

/**
 * Converts a domain event to an audit entry for persistence.
 */
export function domainEventToAuditEntry(
  event: DomainEvent,
  tenantId: string,
  actorId?: string | null,
): CreateAuditEntry {
  const action = getAuditAction(event);
  const payload = event.payload as Record<string, unknown>;
  const eventWithMeta = event as DomainEvent & { metadata?: DomainEventMetadata };

  return {
    tenantId: tenantId as CreateAuditEntry['tenantId'],
    aggregateType: event.aggregateType,
    aggregateId: event.aggregateId,
    action,
    actorType: actorId ? 'user' : 'system',
    actorId: actorId ?? null,
    before: payload?.before ?? null,
    after: payload?.after ?? payload ?? null,
    correlationId: eventWithMeta.metadata?.correlationId,
  };
}

/**
 * Maps an array of domain events to both outbox and audit entries.
 */
export function mapDomainEvents(
  events: readonly DomainEvent[],
  tenantId: string,
  actorId?: string | null,
): {
  outboxEntries: CreateOutboxEntry[];
  auditEntries: CreateAuditEntry[];
} {
  const outboxEntries = events.map((e) => domainEventToOutboxEntry(e, tenantId));
  const auditEntries = events.map((e) => domainEventToAuditEntry(e, tenantId, actorId));

  return { outboxEntries, auditEntries };
}
