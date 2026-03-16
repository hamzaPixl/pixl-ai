import type { DomainEvent, IDomainEventDispatcher } from '@saas-studio/domain';
import type { IEventBus } from '../bus';
import type { ILogger } from '@saas-studio/logger';

export interface IntegrationEvent {
  eventId: string;
  eventType: string;
  occurredAt: Date;
  payload: unknown;
  metadata: {
    tenantId?: string;
    correlationId?: string;
    source: string;
    version: number;
  };
}

export class DomainToIntegrationAdapter {
  constructor(
    private readonly source: string,
    private readonly version: number = 1,
  ) {}

  convert(domainEvent: DomainEvent): IntegrationEvent {
    return {
      eventId: domainEvent.eventId,
      eventType: domainEvent.eventType,
      occurredAt: domainEvent.occurredAt,
      payload: domainEvent.payload,
      metadata: {
        tenantId: (domainEvent as DomainEvent & { metadata?: { tenantId?: string } }).metadata
          ?.tenantId,
        correlationId: (domainEvent as DomainEvent & { metadata?: { correlationId?: string } })
          .metadata?.correlationId,
        source: this.source,
        version: this.version,
      },
    };
  }
}

export class EventBusDispatcher implements IDomainEventDispatcher {
  private handlers = new Map<string, ((event: DomainEvent) => Promise<void>)[]>();

  constructor(
    private readonly eventBus: IEventBus,
    private readonly logger?: ILogger,
  ) {}

  async dispatch(event: DomainEvent): Promise<void> {
    this.logger?.debug('Dispatching domain event', {
      eventType: event.eventType,
      eventId: event.eventId,
    });

    await this.eventBus.publish(event);

    const handlers = this.handlers.get(event.eventType) ?? [];
    await Promise.all(handlers.map((handler) => handler(event)));
  }

  async dispatchAll(events: DomainEvent[]): Promise<void> {
    for (const event of events) {
      await this.dispatch(event);
    }
  }

  register<T extends DomainEvent>(eventType: string, handler: (event: T) => Promise<void>): void {
    const existing = this.handlers.get(eventType) ?? [];
    existing.push(handler as (event: DomainEvent) => Promise<void>);
    this.handlers.set(eventType, existing);
  }
}

export interface ReplayOptions {
  fromTimestamp?: Date;
  toTimestamp?: Date;
  eventTypes?: string[];
  limit?: number;
}

export interface IEventStore {
  append(aggregateId: string, events: DomainEvent[], expectedVersion: number): Promise<void>;
  load(aggregateId: string): Promise<DomainEvent[]>;
  loadFromVersion(aggregateId: string, fromVersion: number): Promise<DomainEvent[]>;
  getLastVersion(aggregateId: string): Promise<number>;
}

export class InMemoryEventStore implements IEventStore {
  private events = new Map<string, DomainEvent[]>();

  async append(aggregateId: string, events: DomainEvent[], expectedVersion: number): Promise<void> {
    const existing = this.events.get(aggregateId) ?? [];
    const currentVersion = existing.length;

    if (currentVersion !== expectedVersion) {
      throw new Error(
        `Concurrency conflict: expected version ${expectedVersion}, got ${currentVersion}`,
      );
    }

    this.events.set(aggregateId, [...existing, ...events]);
  }

  async load(aggregateId: string): Promise<DomainEvent[]> {
    return this.events.get(aggregateId) ?? [];
  }

  async loadFromVersion(aggregateId: string, fromVersion: number): Promise<DomainEvent[]> {
    const all = this.events.get(aggregateId) ?? [];
    return all.slice(fromVersion);
  }

  async getLastVersion(aggregateId: string): Promise<number> {
    const events = this.events.get(aggregateId) ?? [];
    return events.length;
  }
}
