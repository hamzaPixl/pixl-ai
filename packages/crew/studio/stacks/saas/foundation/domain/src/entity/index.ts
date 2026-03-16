import { v4 as uuidv4 } from 'uuid';

export interface BaseEntityProps {
  id: string;
  createdBy: string | null;
  updatedBy: string | null;
  createdAt: Date;
  updatedAt: Date;
  deletedAt?: Date | null;
}

export interface TenantEntityProps extends BaseEntityProps {
  tenantId: string;
}

export abstract class Entity<TProps extends BaseEntityProps> {
  protected readonly props: TProps;

  protected constructor(props: TProps) {
    this.props = props;
  }

  static generateId(): string {
    return uuidv4();
  }

  get id(): string {
    return this.props.id;
  }

  get createdAt(): Date {
    return this.props.createdAt;
  }

  get updatedAt(): Date {
    return this.props.updatedAt;
  }

  get createdBy(): string | null {
    return this.props.createdBy;
  }

  get updatedBy(): string | null {
    return this.props.updatedBy;
  }

  get deletedAt(): Date | null | undefined {
    return this.props.deletedAt;
  }

  get isDeleted(): boolean {
    return this.props.deletedAt != null;
  }

  equals(other: Entity<TProps>): boolean {
    if (other === null || other === undefined) {
      return false;
    }
    if (!(other instanceof Entity)) {
      return false;
    }
    return this.props.id === other.props.id;
  }
}

export abstract class TenantEntity<TProps extends TenantEntityProps> extends Entity<TProps> {
  protected constructor(props: TProps) {
    super(props);
  }

  get tenantId(): string {
    return this.props.tenantId;
  }
}
