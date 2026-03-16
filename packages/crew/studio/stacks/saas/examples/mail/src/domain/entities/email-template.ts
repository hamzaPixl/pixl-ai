/**
 * EmailTemplate domain entity
 *
 * Domain layer - pure TypeScript, NO external dependencies
 */

export type TemplateStatus = 'active' | 'inactive' | 'archived';

export interface TemplateVariable {
  name: string;
  description?: string;
  required: boolean;
  defaultValue?: string;
}

export interface EmailTemplateProps {
  id: string;
  tenantId: string;
  name: string;
  subject: string;
  htmlBody: string;
  textBody: string | null;
  variables: TemplateVariable[] | null;
  category: string | null;
  status: TemplateStatus;
  version: number;
  createdBy: string | null;
  updatedBy: string | null;
  createdAt: Date;
  updatedAt: Date;
  deletedAt: Date | null;
}

export interface CreateEmailTemplateInput {
  tenantId: string;
  name: string;
  subject: string;
  htmlBody: string;
  textBody?: string;
  variables?: TemplateVariable[];
  category?: string;
  createdBy?: string;
}

export interface UpdateEmailTemplateInput {
  name?: string;
  subject?: string;
  htmlBody?: string;
  textBody?: string;
  variables?: TemplateVariable[];
  category?: string;
  status?: TemplateStatus;
  updatedBy?: string;
}

export class EmailTemplate {
  private constructor(private readonly props: EmailTemplateProps) {}

  get id(): string {
    return this.props.id;
  }

  get tenantId(): string {
    return this.props.tenantId;
  }

  get name(): string {
    return this.props.name;
  }

  get subject(): string {
    return this.props.subject;
  }

  get htmlBody(): string {
    return this.props.htmlBody;
  }

  get textBody(): string | null {
    return this.props.textBody;
  }

  get variables(): TemplateVariable[] | null {
    return this.props.variables;
  }

  get category(): string | null {
    return this.props.category;
  }

  get status(): TemplateStatus {
    return this.props.status;
  }

  get version(): number {
    return this.props.version;
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

  get isActive(): boolean {
    return this.props.status === 'active' && !this.isDeleted;
  }

  static create(input: CreateEmailTemplateInput): EmailTemplate {
    if (!input.name || input.name.trim().length === 0) {
      throw new Error('Template name is required');
    }

    if (!input.subject || input.subject.trim().length === 0) {
      throw new Error('Email subject is required');
    }

    if (!input.htmlBody || input.htmlBody.trim().length === 0) {
      throw new Error('HTML body is required');
    }

    const now = new Date();

    return new EmailTemplate({
      id: crypto.randomUUID(),
      tenantId: input.tenantId,
      name: input.name.trim(),
      subject: input.subject.trim(),
      htmlBody: input.htmlBody,
      textBody: input.textBody?.trim() ?? null,
      variables: input.variables ?? null,
      category: input.category?.trim() ?? null,
      status: 'active',
      version: 0,
      createdBy: input.createdBy ?? null,
      updatedBy: null,
      createdAt: now,
      updatedAt: now,
      deletedAt: null,
    });
  }

  static fromPersistence(props: EmailTemplateProps): EmailTemplate {
    return new EmailTemplate(props);
  }

  update(input: UpdateEmailTemplateInput): EmailTemplate {
    if (this.isDeleted) {
      throw new Error('Cannot update deleted template');
    }

    return new EmailTemplate({
      ...this.props,
      name: input.name?.trim() ?? this.props.name,
      subject: input.subject?.trim() ?? this.props.subject,
      htmlBody: input.htmlBody ?? this.props.htmlBody,
      textBody:
        input.textBody !== undefined ? (input.textBody?.trim() ?? null) : this.props.textBody,
      variables: input.variables ?? this.props.variables,
      category:
        input.category !== undefined ? (input.category?.trim() ?? null) : this.props.category,
      status: input.status ?? this.props.status,
      updatedBy: input.updatedBy ?? this.props.updatedBy,
      updatedAt: new Date(),
      version: this.props.version + 1,
    });
  }

  render(data: Record<string, unknown>): { subject: string; html: string; text: string | null } {
    let subject = this.props.subject;
    let html = this.props.htmlBody;
    let text = this.props.textBody;

    for (const [key, value] of Object.entries(data)) {
      const placeholder = `{{${key}}}`;
      const stringValue = String(value ?? '');
      subject = subject.replaceAll(placeholder, stringValue);
      html = html.replaceAll(placeholder, stringValue);
      if (text) {
        text = text.replaceAll(placeholder, stringValue);
      }
    }

    return { subject, html, text };
  }

  delete(deletedBy?: string): EmailTemplate {
    if (this.isDeleted) {
      throw new Error('Template is already deleted');
    }

    return new EmailTemplate({
      ...this.props,
      status: 'archived',
      deletedAt: new Date(),
      updatedBy: deletedBy ?? this.props.updatedBy,
      updatedAt: new Date(),
      version: this.props.version + 1,
    });
  }

  toPersistence(): EmailTemplateProps {
    return { ...this.props };
  }
}
