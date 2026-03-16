/**
 * MediaFile domain entity
 *
 * Domain layer - pure TypeScript, NO external dependencies
 */

export type MediaFileStatus = 'pending' | 'processing' | 'ready' | 'failed' | 'archived';

export interface MediaFileProps {
  id: string;
  tenantId: string;
  name: string;
  originalName: string;
  mimeType: string;
  size: bigint;
  path: string;
  bucket: string;
  url: string | null;
  thumbnailUrl: string | null;
  metadata: Record<string, unknown> | null;
  status: MediaFileStatus;
  version: number;
  createdBy: string | null;
  updatedBy: string | null;
  createdAt: Date;
  updatedAt: Date;
  deletedAt: Date | null;
}

export interface CreateMediaFileInput {
  tenantId: string;
  name: string;
  originalName: string;
  mimeType: string;
  size: bigint;
  path: string;
  bucket: string;
  createdBy?: string;
}

export interface UpdateMediaFileInput {
  name?: string;
  url?: string;
  thumbnailUrl?: string;
  metadata?: Record<string, unknown>;
  status?: MediaFileStatus;
  updatedBy?: string;
}

export class MediaFile {
  private constructor(private readonly props: MediaFileProps) {}

  get id(): string {
    return this.props.id;
  }

  get tenantId(): string {
    return this.props.tenantId;
  }

  get name(): string {
    return this.props.name;
  }

  get originalName(): string {
    return this.props.originalName;
  }

  get mimeType(): string {
    return this.props.mimeType;
  }

  get size(): bigint {
    return this.props.size;
  }

  get path(): string {
    return this.props.path;
  }

  get bucket(): string {
    return this.props.bucket;
  }

  get url(): string | null {
    return this.props.url;
  }

  get thumbnailUrl(): string | null {
    return this.props.thumbnailUrl;
  }

  get metadata(): Record<string, unknown> | null {
    return this.props.metadata;
  }

  get status(): MediaFileStatus {
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

  get isReady(): boolean {
    return this.props.status === 'ready' && !this.isDeleted;
  }

  get isImage(): boolean {
    return this.props.mimeType.startsWith('image/');
  }

  static create(input: CreateMediaFileInput): MediaFile {
    if (!input.name || input.name.trim().length === 0) {
      throw new Error('File name is required');
    }

    if (input.size <= 0) {
      throw new Error('File size must be positive');
    }

    const now = new Date();

    return new MediaFile({
      id: crypto.randomUUID(),
      tenantId: input.tenantId,
      name: input.name.trim(),
      originalName: input.originalName,
      mimeType: input.mimeType,
      size: input.size,
      path: input.path,
      bucket: input.bucket,
      url: null,
      thumbnailUrl: null,
      metadata: null,
      status: 'pending',
      version: 0,
      createdBy: input.createdBy ?? null,
      updatedBy: null,
      createdAt: now,
      updatedAt: now,
      deletedAt: null,
    });
  }

  static fromPersistence(props: MediaFileProps): MediaFile {
    return new MediaFile(props);
  }

  update(input: UpdateMediaFileInput): MediaFile {
    if (this.isDeleted) {
      throw new Error('Cannot update deleted file');
    }

    return new MediaFile({
      ...this.props,
      name: input.name?.trim() ?? this.props.name,
      url: input.url ?? this.props.url,
      thumbnailUrl: input.thumbnailUrl ?? this.props.thumbnailUrl,
      metadata: input.metadata ?? this.props.metadata,
      status: input.status ?? this.props.status,
      updatedBy: input.updatedBy ?? this.props.updatedBy,
      updatedAt: new Date(),
      version: this.props.version + 1,
    });
  }

  markReady(url: string, thumbnailUrl?: string): MediaFile {
    return this.update({
      url,
      thumbnailUrl,
      status: 'ready',
    });
  }

  markFailed(): MediaFile {
    return this.update({ status: 'failed' });
  }

  delete(deletedBy?: string): MediaFile {
    if (this.isDeleted) {
      throw new Error('File is already deleted');
    }

    return new MediaFile({
      ...this.props,
      status: 'archived',
      deletedAt: new Date(),
      updatedBy: deletedBy ?? this.props.updatedBy,
      updatedAt: new Date(),
      version: this.props.version + 1,
    });
  }

  toPersistence(): MediaFileProps {
    return { ...this.props };
  }
}
