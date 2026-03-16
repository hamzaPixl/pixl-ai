/**
 * PdfDocument domain entity
 *
 * Domain layer - pure TypeScript, NO external dependencies
 */

export type DocumentStatus = 'pending' | 'generating' | 'ready' | 'failed' | 'expired';

export interface PdfDocumentProps {
  id: string;
  tenantId: string;
  templateId: string | null;
  name: string;
  data: Record<string, unknown> | null;
  filePath: string | null;
  fileSize: bigint | null;
  pageCount: number | null;
  status: DocumentStatus;
  generatedAt: Date | null;
  expiresAt: Date | null;
  metadata: Record<string, unknown> | null;
  createdBy: string | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface CreatePdfDocumentInput {
  tenantId: string;
  templateId?: string;
  name: string;
  data?: Record<string, unknown>;
  expiresAt?: Date;
  metadata?: Record<string, unknown>;
  createdBy?: string;
}

export class PdfDocument {
  private constructor(private readonly props: PdfDocumentProps) {}

  get id(): string {
    return this.props.id;
  }

  get tenantId(): string {
    return this.props.tenantId;
  }

  get templateId(): string | null {
    return this.props.templateId;
  }

  get name(): string {
    return this.props.name;
  }

  get data(): Record<string, unknown> | null {
    return this.props.data;
  }

  get filePath(): string | null {
    return this.props.filePath;
  }

  get fileSize(): bigint | null {
    return this.props.fileSize;
  }

  get pageCount(): number | null {
    return this.props.pageCount;
  }

  get status(): DocumentStatus {
    return this.props.status;
  }

  get generatedAt(): Date | null {
    return this.props.generatedAt;
  }

  get expiresAt(): Date | null {
    return this.props.expiresAt;
  }

  get metadata(): Record<string, unknown> | null {
    return this.props.metadata;
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

  get isReady(): boolean {
    return this.props.status === 'ready' && !this.isExpired;
  }

  get isExpired(): boolean {
    if (!this.props.expiresAt) return false;
    return new Date() > this.props.expiresAt;
  }

  static create(input: CreatePdfDocumentInput): PdfDocument {
    if (!input.name || input.name.trim().length === 0) {
      throw new Error('Document name is required');
    }

    const now = new Date();

    return new PdfDocument({
      id: crypto.randomUUID(),
      tenantId: input.tenantId,
      templateId: input.templateId ?? null,
      name: input.name.trim(),
      data: input.data ?? null,
      filePath: null,
      fileSize: null,
      pageCount: null,
      status: 'pending',
      generatedAt: null,
      expiresAt: input.expiresAt ?? null,
      metadata: input.metadata ?? null,
      createdBy: input.createdBy ?? null,
      createdAt: now,
      updatedAt: now,
    });
  }

  static fromPersistence(props: PdfDocumentProps): PdfDocument {
    return new PdfDocument(props);
  }

  markGenerating(): PdfDocument {
    return new PdfDocument({
      ...this.props,
      status: 'generating',
      updatedAt: new Date(),
    });
  }

  markReady(filePath: string, fileSize: bigint, pageCount: number): PdfDocument {
    return new PdfDocument({
      ...this.props,
      filePath,
      fileSize,
      pageCount,
      status: 'ready',
      generatedAt: new Date(),
      updatedAt: new Date(),
    });
  }

  markFailed(): PdfDocument {
    return new PdfDocument({
      ...this.props,
      status: 'failed',
      updatedAt: new Date(),
    });
  }

  markExpired(): PdfDocument {
    return new PdfDocument({
      ...this.props,
      status: 'expired',
      updatedAt: new Date(),
    });
  }

  toPersistence(): PdfDocumentProps {
    return { ...this.props };
  }
}
