import { randomUUID } from 'crypto';

export interface DomainEvent {
  readonly eventId: string;
  readonly eventType: string;
  readonly aggregateType: string;
  readonly aggregateId: string;
  readonly occurredAt: Date;
  readonly version: number;
  readonly payload: unknown;
}

export interface DomainEventMetadata {
  correlationId?: string;
  causationId?: string;
  tenantId?: string;
  actorId?: string;
  actorType?: 'user' | 'system' | 'service';
}

export abstract class BaseDomainEvent<TPayload = unknown> implements DomainEvent {
  readonly eventId: string;
  readonly eventType: string;
  readonly aggregateType: string;
  readonly aggregateId: string;
  readonly occurredAt: Date;
  readonly version: number;
  readonly payload: TPayload;
  readonly metadata: DomainEventMetadata;

  constructor(
    aggregateType: string,
    aggregateId: string,
    payload: TPayload,
    version: number = 1,
    metadata: DomainEventMetadata = {},
  ) {
    this.eventId = randomUUID();
    this.eventType = this.constructor.name;
    this.aggregateType = aggregateType;
    this.aggregateId = aggregateId;
    this.occurredAt = new Date();
    this.version = version;
    this.payload = payload;
    this.metadata = metadata;
  }
}

export type DomainEventHandler<T extends DomainEvent = DomainEvent> = (event: T) => Promise<void>;

export interface EventDispatcherLogger {
  error(message: string, context?: Record<string, unknown>): void;
  warn(message: string, context?: Record<string, unknown>): void;
}

export interface EventDispatcherOptions {
  logger?: EventDispatcherLogger;
  /** Whether to continue dispatching to remaining handlers if one fails (default: true) */
  continueOnError?: boolean;
}

export interface EventDispatchError {
  event: DomainEvent;
  handler: string;
  error: Error;
}

export interface IDomainEventDispatcher {
  dispatch(event: DomainEvent): Promise<void>;
  dispatchAll(events: DomainEvent[]): Promise<void>;
  register<T extends DomainEvent>(eventType: string, handler: DomainEventHandler<T>): void;
}

export class InMemoryDomainEventDispatcher implements IDomainEventDispatcher {
  private handlers = new Map<string, DomainEventHandler[]>();
  private readonly logger?: EventDispatcherLogger;
  private readonly continueOnError: boolean;

  constructor(options: EventDispatcherOptions = {}) {
    this.logger = options.logger;
    this.continueOnError = options.continueOnError ?? true;
  }

  register<T extends DomainEvent>(eventType: string, handler: DomainEventHandler<T>): void {
    const existing = this.handlers.get(eventType) ?? [];
    existing.push(handler as DomainEventHandler);
    this.handlers.set(eventType, existing);
  }

  async dispatch(event: DomainEvent): Promise<void> {
    const handlers = this.handlers.get(event.eventType) ?? [];
    const errors: EventDispatchError[] = [];

    for (const handler of handlers) {
      try {
        await handler(event);
      } catch (error) {
        const dispatchError: EventDispatchError = {
          event,
          handler: handler.name || 'anonymous',
          error: error instanceof Error ? error : new Error(String(error)),
        };

        errors.push(dispatchError);

        this.logger?.error('Event handler failed', {
          eventId: event.eventId,
          eventType: event.eventType,
          aggregateId: event.aggregateId,
          handler: dispatchError.handler,
          error: dispatchError.error.message,
        });

        if (!this.continueOnError) {
          throw dispatchError.error;
        }
      }
    }

    if (errors.length > 0 && this.continueOnError) {
      this.logger?.warn('Some event handlers failed', {
        eventId: event.eventId,
        eventType: event.eventType,
        failedCount: errors.length,
        totalHandlers: handlers.length,
      });
    }
  }

  async dispatchAll(events: DomainEvent[]): Promise<void> {
    for (const event of events) {
      await this.dispatch(event);
    }
  }
}
