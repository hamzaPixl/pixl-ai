/**
 * FormSubmission domain entity
 *
 * Domain layer - pure TypeScript, NO external dependencies
 */

export type SubmissionStatus = 'pending' | 'processed' | 'rejected' | 'spam';

export interface FormSubmissionProps {
  id: string;
  tenantId: string;
  formId: string;
  data: Record<string, unknown>;
  metadata: Record<string, unknown> | null;
  status: SubmissionStatus;
  submittedBy: string | null;
  submittedAt: Date;
  processedAt: Date | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface CreateSubmissionInput {
  tenantId: string;
  formId: string;
  data: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  submittedBy?: string;
}

export class FormSubmission {
  private constructor(private readonly props: FormSubmissionProps) {}

  get id(): string {
    return this.props.id;
  }

  get tenantId(): string {
    return this.props.tenantId;
  }

  get formId(): string {
    return this.props.formId;
  }

  get data(): Record<string, unknown> {
    return this.props.data;
  }

  get metadata(): Record<string, unknown> | null {
    return this.props.metadata;
  }

  get status(): SubmissionStatus {
    return this.props.status;
  }

  get submittedBy(): string | null {
    return this.props.submittedBy;
  }

  get submittedAt(): Date {
    return this.props.submittedAt;
  }

  get processedAt(): Date | null {
    return this.props.processedAt;
  }

  get createdAt(): Date {
    return this.props.createdAt;
  }

  get updatedAt(): Date {
    return this.props.updatedAt;
  }

  get isProcessed(): boolean {
    return this.props.status === 'processed';
  }

  static create(input: CreateSubmissionInput): FormSubmission {
    if (!input.formId) {
      throw new Error('Form ID is required');
    }

    if (!input.data || Object.keys(input.data).length === 0) {
      throw new Error('Submission data is required');
    }

    const now = new Date();

    return new FormSubmission({
      id: crypto.randomUUID(),
      tenantId: input.tenantId,
      formId: input.formId,
      data: input.data,
      metadata: input.metadata ?? null,
      status: 'pending',
      submittedBy: input.submittedBy ?? null,
      submittedAt: now,
      processedAt: null,
      createdAt: now,
      updatedAt: now,
    });
  }

  static fromPersistence(props: FormSubmissionProps): FormSubmission {
    return new FormSubmission(props);
  }

  markProcessed(): FormSubmission {
    return new FormSubmission({
      ...this.props,
      status: 'processed',
      processedAt: new Date(),
      updatedAt: new Date(),
    });
  }

  markRejected(): FormSubmission {
    return new FormSubmission({
      ...this.props,
      status: 'rejected',
      processedAt: new Date(),
      updatedAt: new Date(),
    });
  }

  markSpam(): FormSubmission {
    return new FormSubmission({
      ...this.props,
      status: 'spam',
      processedAt: new Date(),
      updatedAt: new Date(),
    });
  }

  toPersistence(): FormSubmissionProps {
    return { ...this.props };
  }
}
