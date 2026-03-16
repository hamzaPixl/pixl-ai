/**
 * PdfTemplate domain entity
 *
 * Domain layer - pure TypeScript, NO external dependencies
 */

export type TemplateStatus = 'active' | 'inactive' | 'archived';
export type PageSize = 'A4' | 'A3' | 'Letter' | 'Legal' | 'Tabloid';
export type Orientation = 'portrait' | 'landscape';

export interface PageMargins {
  top: string;
  right: string;
  bottom: string;
  left: string;
}

export interface TemplateVariable {
  name: string;
  description?: string;
  required: boolean;
  defaultValue?: string;
}

export interface PdfTemplateProps {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  htmlContent: string;
  cssStyles: string | null;
  variables: TemplateVariable[] | null;
  pageSize: PageSize;
  orientation: Orientation;
  margins: PageMargins | null;
  header: string | null;
  footer: string | null;
  status: TemplateStatus;
  version: number;
  createdBy: string | null;
  updatedBy: string | null;
  createdAt: Date;
  updatedAt: Date;
  deletedAt: Date | null;
}

export interface CreatePdfTemplateInput {
  tenantId: string;
  name: string;
  description?: string;
  htmlContent: string;
  cssStyles?: string;
  variables?: TemplateVariable[];
  pageSize?: PageSize;
  orientation?: Orientation;
  margins?: PageMargins;
  header?: string;
  footer?: string;
  createdBy?: string;
}

export interface UpdatePdfTemplateInput {
  name?: string;
  description?: string;
  htmlContent?: string;
  cssStyles?: string;
  variables?: TemplateVariable[];
  pageSize?: PageSize;
  orientation?: Orientation;
  margins?: PageMargins;
  header?: string;
  footer?: string;
  status?: TemplateStatus;
  updatedBy?: string;
}

export class PdfTemplate {
  private constructor(private readonly props: PdfTemplateProps) {}

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

  get htmlContent(): string {
    return this.props.htmlContent;
  }

  get cssStyles(): string | null {
    return this.props.cssStyles;
  }

  get variables(): TemplateVariable[] | null {
    return this.props.variables;
  }

  get pageSize(): PageSize {
    return this.props.pageSize;
  }

  get orientation(): Orientation {
    return this.props.orientation;
  }

  get margins(): PageMargins | null {
    return this.props.margins;
  }

  get header(): string | null {
    return this.props.header;
  }

  get footer(): string | null {
    return this.props.footer;
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

  static create(input: CreatePdfTemplateInput): PdfTemplate {
    if (!input.name || input.name.trim().length === 0) {
      throw new Error('Template name is required');
    }

    if (!input.htmlContent || input.htmlContent.trim().length === 0) {
      throw new Error('HTML content is required');
    }

    const now = new Date();

    return new PdfTemplate({
      id: crypto.randomUUID(),
      tenantId: input.tenantId,
      name: input.name.trim(),
      description: input.description?.trim() ?? null,
      htmlContent: input.htmlContent,
      cssStyles: input.cssStyles ?? null,
      variables: input.variables ?? null,
      pageSize: input.pageSize ?? 'A4',
      orientation: input.orientation ?? 'portrait',
      margins: input.margins ?? null,
      header: input.header ?? null,
      footer: input.footer ?? null,
      status: 'active',
      version: 0,
      createdBy: input.createdBy ?? null,
      updatedBy: null,
      createdAt: now,
      updatedAt: now,
      deletedAt: null,
    });
  }

  static fromPersistence(props: PdfTemplateProps): PdfTemplate {
    return new PdfTemplate(props);
  }

  update(input: UpdatePdfTemplateInput): PdfTemplate {
    if (this.isDeleted) {
      throw new Error('Cannot update deleted template');
    }

    return new PdfTemplate({
      ...this.props,
      name: input.name?.trim() ?? this.props.name,
      description:
        input.description !== undefined
          ? (input.description?.trim() ?? null)
          : this.props.description,
      htmlContent: input.htmlContent ?? this.props.htmlContent,
      cssStyles: input.cssStyles !== undefined ? (input.cssStyles ?? null) : this.props.cssStyles,
      variables: input.variables ?? this.props.variables,
      pageSize: input.pageSize ?? this.props.pageSize,
      orientation: input.orientation ?? this.props.orientation,
      margins: input.margins ?? this.props.margins,
      header: input.header !== undefined ? (input.header ?? null) : this.props.header,
      footer: input.footer !== undefined ? (input.footer ?? null) : this.props.footer,
      status: input.status ?? this.props.status,
      updatedBy: input.updatedBy ?? this.props.updatedBy,
      updatedAt: new Date(),
      version: this.props.version + 1,
    });
  }

  render(data: Record<string, unknown>): string {
    let html = this.props.htmlContent;

    for (const [key, value] of Object.entries(data)) {
      const placeholder = `{{${key}}}`;
      const stringValue = String(value ?? '');
      html = html.replaceAll(placeholder, stringValue);
    }

    if (this.props.cssStyles) {
      html = `<style>${this.props.cssStyles}</style>${html}`;
    }

    return html;
  }

  delete(deletedBy?: string): PdfTemplate {
    if (this.isDeleted) {
      throw new Error('Template is already deleted');
    }

    return new PdfTemplate({
      ...this.props,
      status: 'archived',
      deletedAt: new Date(),
      updatedBy: deletedBy ?? this.props.updatedBy,
      updatedAt: new Date(),
      version: this.props.version + 1,
    });
  }

  toPersistence(): PdfTemplateProps {
    return { ...this.props };
  }
}
