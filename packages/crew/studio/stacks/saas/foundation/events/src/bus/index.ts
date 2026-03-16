import type { DomainEvent } from '@saas-studio/domain';
import type { ILogger } from '@saas-studio/logger';

export type EventHandler<T = unknown> = (event: T) => Promise<void>;

export interface EventSubscription {
  unsubscribe(): Promise<void>;
}

export interface EventBusOptions {
  logger?: ILogger;
}

export interface IEventBus {
  publish<T extends DomainEvent>(event: T): Promise<void>;
  publishAll<T extends DomainEvent>(events: T[]): Promise<void>;
  subscribe<T extends DomainEvent>(
    eventType: string,
    handler: EventHandler<T>,
  ): Promise<EventSubscription>;
  subscribeToPattern(pattern: string, handler: EventHandler): Promise<EventSubscription>;
  close(): Promise<void>;
}

export class InMemoryEventBus implements IEventBus {
  private handlers = new Map<string, EventHandler[]>();
  private patternHandlers = new Map<string, EventHandler[]>();
  private readonly logger?: ILogger;

  constructor(options: EventBusOptions = {}) {
    this.logger = options.logger;
  }

  async publish<T extends DomainEvent>(event: T): Promise<void> {
    this.logger?.debug('Publishing event', { eventType: event.eventType, eventId: event.eventId });

    const handlers = this.handlers.get(event.eventType) ?? [];
    await Promise.all(handlers.map((handler) => this.safeHandle(handler, event)));

    for (const [pattern, patternHandlers] of this.patternHandlers) {
      if (this.matchesPattern(event.eventType, pattern)) {
        await Promise.all(patternHandlers.map((handler) => this.safeHandle(handler, event)));
      }
    }
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
    const existing = this.handlers.get(eventType) ?? [];
    existing.push(handler as EventHandler);
    this.handlers.set(eventType, existing);

    return {
      unsubscribe: async () => {
        const handlers = this.handlers.get(eventType) ?? [];
        const index = handlers.indexOf(handler as EventHandler);
        if (index > -1) {
          handlers.splice(index, 1);
        }
      },
    };
  }

  async subscribeToPattern(pattern: string, handler: EventHandler): Promise<EventSubscription> {
    const existing = this.patternHandlers.get(pattern) ?? [];
    existing.push(handler);
    this.patternHandlers.set(pattern, existing);

    return {
      unsubscribe: async () => {
        const handlers = this.patternHandlers.get(pattern) ?? [];
        const index = handlers.indexOf(handler);
        if (index > -1) {
          handlers.splice(index, 1);
        }
      },
    };
  }

  async close(): Promise<void> {
    this.handlers.clear();
    this.patternHandlers.clear();
  }

  private async safeHandle<T>(handler: EventHandler<T>, event: T): Promise<void> {
    try {
      await handler(event);
    } catch (error) {
      this.logger?.error('Event handler failed', {
        error: error instanceof Error ? error.message : 'Unknown',
      });
    }
  }

  private matchesPattern(eventType: string, pattern: string): boolean {
    // SECURITY: Escape regex special characters to prevent ReDoS
    const escaped = pattern.replace(/[.+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp('^' + escaped.replace(/\*/g, '.*') + '$');
    return regex.test(eventType);
  }
}
