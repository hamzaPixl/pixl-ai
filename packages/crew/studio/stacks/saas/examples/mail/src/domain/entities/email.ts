/**
 * Email domain entity
 *
 * Domain layer - pure TypeScript, NO external dependencies
 */

export type EmailStatus = 'pending' | 'queued' | 'sending' | 'sent' | 'failed' | 'bounced';

export interface EmailAttachment {
  filename: string;
  content: string;
  contentType: string;
  encoding?: 'base64' | 'utf-8';
}

export interface EmailProps {
  id: string;
  tenantId: string;
  templateId: string | null;
  fromAddress: string;
  fromName: string | null;
  toAddresses: string[];
  ccAddresses: string[] | null;
  bccAddresses: string[] | null;
  subject: string;
  htmlBody: string | null;
  textBody: string | null;
  attachments: EmailAttachment[] | null;
  metadata: Record<string, unknown> | null;
  status: EmailStatus;
  priority: number;
  scheduledFor: Date | null;
  sentAt: Date | null;
  failedAt: Date | null;
  failureReason: string | null;
  retryCount: number;
  maxRetries: number;
  createdBy: string | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface CreateEmailInput {
  tenantId: string;
  templateId?: string;
  fromAddress: string;
  fromName?: string;
  toAddresses: string[];
  ccAddresses?: string[];
  bccAddresses?: string[];
  subject: string;
  htmlBody?: string;
  textBody?: string;
  attachments?: EmailAttachment[];
  metadata?: Record<string, unknown>;
  priority?: number;
  scheduledFor?: Date;
  createdBy?: string;
}

export class Email {
  private constructor(private readonly props: EmailProps) {}

  get id(): string {
    return this.props.id;
  }

  get tenantId(): string {
    return this.props.tenantId;
  }

  get templateId(): string | null {
    return this.props.templateId;
  }

  get fromAddress(): string {
    return this.props.fromAddress;
  }

  get fromName(): string | null {
    return this.props.fromName;
  }

  get toAddresses(): string[] {
    return this.props.toAddresses;
  }

  get ccAddresses(): string[] | null {
    return this.props.ccAddresses;
  }

  get bccAddresses(): string[] | null {
    return this.props.bccAddresses;
  }

  get subject(): string {
    return this.props.subject;
  }

  get htmlBody(): string | null {
    return this.props.htmlBody;
  }

  get textBody(): string | null {
    return this.props.textBody;
  }

  get attachments(): EmailAttachment[] | null {
    return this.props.attachments;
  }

  get metadata(): Record<string, unknown> | null {
    return this.props.metadata;
  }

  get status(): EmailStatus {
    return this.props.status;
  }

  get priority(): number {
    return this.props.priority;
  }

  get scheduledFor(): Date | null {
    return this.props.scheduledFor;
  }

  get sentAt(): Date | null {
    return this.props.sentAt;
  }

  get failedAt(): Date | null {
    return this.props.failedAt;
  }

  get failureReason(): string | null {
    return this.props.failureReason;
  }

  get retryCount(): number {
    return this.props.retryCount;
  }

  get maxRetries(): number {
    return this.props.maxRetries;
  }

  get createdBy(): string | null {
    return this.props.createdBy;
  }

  get createdAt(): Date {
    return this.props.createdAt;
  }

  get updatedAt(): Date {
    return this.props.updatedAt;
  }

  get isSent(): boolean {
    return this.props.status === 'sent';
  }

  get canRetry(): boolean {
    return this.props.status === 'failed' && this.props.retryCount < this.props.maxRetries;
  }

  static create(input: CreateEmailInput): Email {
    if (!input.fromAddress) {
      throw new Error('From address is required');
    }

    if (!input.toAddresses || input.toAddresses.length === 0) {
      throw new Error('At least one recipient is required');
    }

    if (!input.subject) {
      throw new Error('Email subject is required');
    }

    if (!input.htmlBody && !input.textBody) {
      throw new Error('Email body (HTML or text) is required');
    }

    const now = new Date();

    return new Email({
      id: crypto.randomUUID(),
      tenantId: input.tenantId,
      templateId: input.templateId ?? null,
      fromAddress: input.fromAddress,
      fromName: input.fromName ?? null,
      toAddresses: input.toAddresses,
      ccAddresses: input.ccAddresses ?? null,
      bccAddresses: input.bccAddresses ?? null,
      subject: input.subject,
      htmlBody: input.htmlBody ?? null,
      textBody: input.textBody ?? null,
      attachments: input.attachments ?? null,
      metadata: input.metadata ?? null,
      status: 'pending',
      priority: input.priority ?? 0,
      scheduledFor: input.scheduledFor ?? null,
      sentAt: null,
      failedAt: null,
      failureReason: null,
      retryCount: 0,
      maxRetries: 3,
      createdBy: input.createdBy ?? null,
      createdAt: now,
      updatedAt: now,
    });
  }

  static fromPersistence(props: EmailProps): Email {
    return new Email(props);
  }

  markQueued(): Email {
    return new Email({
      ...this.props,
      status: 'queued',
      updatedAt: new Date(),
    });
  }

  markSending(): Email {
    return new Email({
      ...this.props,
      status: 'sending',
      updatedAt: new Date(),
    });
  }

  markSent(): Email {
    return new Email({
      ...this.props,
      status: 'sent',
      sentAt: new Date(),
      updatedAt: new Date(),
    });
  }

  markFailed(reason: string): Email {
    return new Email({
      ...this.props,
      status: 'failed',
      failedAt: new Date(),
      failureReason: reason,
      retryCount: this.props.retryCount + 1,
      updatedAt: new Date(),
    });
  }

  markBounced(): Email {
    return new Email({
      ...this.props,
      status: 'bounced',
      failedAt: new Date(),
      updatedAt: new Date(),
    });
  }

  retry(): Email {
    if (!this.canRetry) {
      throw new Error('Cannot retry email: max retries exceeded');
    }

    return new Email({
      ...this.props,
      status: 'pending',
      failedAt: null,
      failureReason: null,
      updatedAt: new Date(),
    });
  }

  toPersistence(): EmailProps {
    return { ...this.props };
  }
}
