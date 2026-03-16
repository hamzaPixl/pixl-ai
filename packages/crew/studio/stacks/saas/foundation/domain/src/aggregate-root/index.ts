import { Entity, TenantEntity, type BaseEntityProps, type TenantEntityProps } from '../entity';
import type { DomainEvent } from '../domain-event';

export abstract class AggregateRoot<TProps extends BaseEntityProps> extends Entity<TProps> {
  private _domainEvents: DomainEvent[] = [];
  private _version: number = 0;

  protected constructor(props: TProps) {
    super(props);
  }

  get domainEvents(): ReadonlyArray<DomainEvent> {
    return [...this._domainEvents];
  }

  get version(): number {
    return this._version;
  }

  protected setVersion(version: number): void {
    this._version = version;
  }

  protected addDomainEvent(event: DomainEvent): void {
    this._domainEvents.push(event);
  }

  clearDomainEvents(): DomainEvent[] {
    const events = [...this._domainEvents];
    this._domainEvents = [];
    return events;
  }

  protected incrementVersion(): void {
    this._version++;
  }
}

export abstract class TenantAggregateRoot<TProps extends TenantEntityProps> extends TenantEntity<TProps> {
  private _domainEvents: DomainEvent[] = [];
  private _version: number = 0;

  protected constructor(props: TProps) {
    super(props);
  }

  get domainEvents(): ReadonlyArray<DomainEvent> {
    return [...this._domainEvents];
  }

  get version(): number {
    return this._version;
  }

  protected setVersion(version: number): void {
    this._version = version;
  }

  protected addDomainEvent(event: DomainEvent): void {
    this._domainEvents.push(event);
  }

  clearDomainEvents(): DomainEvent[] {
    const events = [...this._domainEvents];
    this._domainEvents = [];
    return events;
  }

  protected incrementVersion(): void {
    this._version++;
  }
}
