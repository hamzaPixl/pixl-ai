/**
 * Form domain entity
 *
 * Domain layer - pure TypeScript, NO external dependencies
 */

export type FormStatus = 'draft' | 'published' | 'archived';

export type FieldType =
  | 'text'
  | 'textarea'
  | 'number'
  | 'email'
  | 'phone'
  | 'date'
  | 'time'
  | 'datetime'
  | 'select'
  | 'multiselect'
  | 'checkbox'
  | 'radio'
  | 'file'
  | 'hidden';

export interface FormField {
  id: string;
  name: string;
  label: string;
  type: FieldType;
  placeholder?: string;
  defaultValue?: unknown;
  required: boolean;
  validation?: {
    minLength?: number;
    maxLength?: number;
    min?: number;
    max?: number;
    pattern?: string;
    message?: string;
  };
  options?: Array<{ value: string; label: string }>;
  conditionalLogic?: {
    show: boolean;
    rules: Array<{
      field: string;
      operator: 'equals' | 'not_equals' | 'contains' | 'greater_than' | 'less_than';
      value: unknown;
    }>;
  };
}

export interface FormSchema {
  fields: FormField[];
  sections?: Array<{
    id: string;
    title: string;
    description?: string;
    fields: string[];
  }>;
}

export interface FormSettings {
  submitButtonText?: string;
  successMessage?: string;
  redirectUrl?: string;
  notifyOnSubmission?: boolean;
  notificationEmails?: string[];
  allowMultipleSubmissions?: boolean;
  requireAuthentication?: boolean;
}

export interface FormProps {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  schema: FormSchema;
  settings: FormSettings | null;
  status: FormStatus;
  version: number;
  publishedAt: Date | null;
  createdBy: string | null;
  updatedBy: string | null;
  createdAt: Date;
  updatedAt: Date;
  deletedAt: Date | null;
}

export interface CreateFormInput {
  tenantId: string;
  name: string;
  description?: string;
  schema: FormSchema;
  settings?: FormSettings;
  createdBy?: string;
}

export interface UpdateFormInput {
  name?: string;
  description?: string;
  schema?: FormSchema;
  settings?: FormSettings;
  updatedBy?: string;
}

export class Form {
  private constructor(private readonly props: FormProps) {}

  get id(): string {
    return this.props.id;
  }

  get tenantId(): string {
    return this.props.tenantId;
  }

  get name(): string {
    return this.props.name;
  }

  get description(): string | null {
    return this.props.description;
  }

  get schema(): FormSchema {
    return this.props.schema;
  }

  get settings(): FormSettings | null {
    return this.props.settings;
  }

  get status(): FormStatus {
    return this.props.status;
  }

  get version(): number {
    return this.props.version;
  }

  get publishedAt(): Date | null {
    return this.props.publishedAt;
  }

  get createdBy(): string | null {
    return this.props.createdBy;
  }

  get updatedBy(): string | null {
    return this.props.updatedBy;
  }

  get createdAt(): Date {
    return this.props.createdAt;
  }

  get updatedAt(): Date {
    return this.props.updatedAt;
  }

  get deletedAt(): Date | null {
    return this.props.deletedAt;
  }

  get isDeleted(): boolean {
    return this.props.deletedAt !== null;
  }

  get isPublished(): boolean {
    return this.props.status === 'published' && !this.isDeleted;
  }

  get fields(): FormField[] {
    return this.props.schema.fields;
  }

  static create(input: CreateFormInput): Form {
    if (!input.name || input.name.trim().length === 0) {
      throw new Error('Form name is required');
    }

    if (!input.schema.fields || input.schema.fields.length === 0) {
      throw new Error('Form must have at least one field');
    }

    const now = new Date();

    return new Form({
      id: crypto.randomUUID(),
      tenantId: input.tenantId,
      name: input.name.trim(),
      description: input.description?.trim() ?? null,
      schema: input.schema,
      settings: input.settings ?? null,
      status: 'draft',
      version: 0,
      publishedAt: null,
      createdBy: input.createdBy ?? null,
      updatedBy: null,
      createdAt: now,
      updatedAt: now,
      deletedAt: null,
    });
  }

  static fromPersistence(props: FormProps): Form {
    return new Form(props);
  }

  update(input: UpdateFormInput): Form {
    if (this.isDeleted) {
      throw new Error('Cannot update deleted form');
    }

    return new Form({
      ...this.props,
      name: input.name?.trim() ?? this.props.name,
      description:
        input.description !== undefined
          ? (input.description?.trim() ?? null)
          : this.props.description,
      schema: input.schema ?? this.props.schema,
      settings: input.settings ?? this.props.settings,
      updatedBy: input.updatedBy ?? this.props.updatedBy,
      updatedAt: new Date(),
      version: this.props.version + 1,
    });
  }

  publish(publishedBy?: string): Form {
    if (this.isDeleted) {
      throw new Error('Cannot publish deleted form');
    }

    if (this.isPublished) {
      throw new Error('Form is already published');
    }

    return new Form({
      ...this.props,
      status: 'published',
      publishedAt: new Date(),
      updatedBy: publishedBy ?? this.props.updatedBy,
      updatedAt: new Date(),
      version: this.props.version + 1,
    });
  }

  unpublish(updatedBy?: string): Form {
    if (!this.isPublished) {
      throw new Error('Form is not published');
    }

    return new Form({
      ...this.props,
      status: 'draft',
      updatedBy: updatedBy ?? this.props.updatedBy,
      updatedAt: new Date(),
      version: this.props.version + 1,
    });
  }

  delete(deletedBy?: string): Form {
    if (this.isDeleted) {
      throw new Error('Form is already deleted');
    }

    return new Form({
      ...this.props,
      status: 'archived',
      deletedAt: new Date(),
      updatedBy: deletedBy ?? this.props.updatedBy,
      updatedAt: new Date(),
      version: this.props.version + 1,
    });
  }

  toPersistence(): FormProps {
    return { ...this.props };
  }
}
