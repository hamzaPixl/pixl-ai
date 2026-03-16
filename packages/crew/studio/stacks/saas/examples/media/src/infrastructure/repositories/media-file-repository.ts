/**
 * Media file repository - Infrastructure layer
 *
 * Prisma-based repository implementation
 */

import {
  Prisma,
  type PrismaClient,
  type MediaFile as PrismaMediaFile,
} from '../../../prisma/generated/client';
import { MediaFile, type MediaFileProps } from '../../domain/entities/media-file';

export interface IMediaFileRepository {
  findById(id: string): Promise<MediaFile | null>;
  findByTenant(
    tenantId: string,
    options?: { status?: string; limit?: number; offset?: number },
  ): Promise<MediaFile[]>;
  save(mediaFile: MediaFile, tx?: unknown): Promise<MediaFile>;
  delete(id: string): Promise<void>;
}

function toDomain(record: PrismaMediaFile): MediaFile {
  return MediaFile.fromPersistence({
    id: record.id,
    tenantId: record.tenantId,
    name: record.name,
    originalName: record.originalName,
    mimeType: record.mimeType,
    size: record.size,
    path: record.path,
    bucket: record.bucket,
    url: record.url,
    thumbnailUrl: record.thumbnailUrl,
    metadata: record.metadata as Record<string, unknown> | null,
    status: record.status as MediaFileProps['status'],
    version: record.version,
    createdBy: record.createdBy,
    updatedBy: record.updatedBy,
    createdAt: record.createdAt,
    updatedAt: record.updatedAt,
    deletedAt: record.deletedAt,
  });
}

export class PrismaMediaFileRepository implements IMediaFileRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async findById(id: string): Promise<MediaFile | null> {
    const record = await this.prisma.mediaFile.findUnique({
      where: { id },
    });

    return record ? toDomain(record) : null;
  }

  async findByTenant(
    tenantId: string,
    options: { status?: string; limit?: number; offset?: number } = {},
  ): Promise<MediaFile[]> {
    const records = await this.prisma.mediaFile.findMany({
      where: {
        tenantId,
        ...(options.status && { status: options.status }),
        deletedAt: null,
      },
      take: options.limit ?? 100,
      skip: options.offset ?? 0,
      orderBy: { createdAt: 'desc' },
    });

    return records.map(toDomain);
  }

  async save(mediaFile: MediaFile, tx?: unknown): Promise<MediaFile> {
    const client = (tx as PrismaClient) ?? this.prisma;
    const data = mediaFile.toPersistence();
    const metadata =
      data.metadata === null ? Prisma.DbNull : (data.metadata as unknown as Prisma.InputJsonValue);

    const record = await client.mediaFile.upsert({
      where: { id: data.id },
      create: {
        id: data.id,
        tenantId: data.tenantId,
        name: data.name,
        originalName: data.originalName,
        mimeType: data.mimeType,
        size: data.size,
        path: data.path,
        bucket: data.bucket,
        url: data.url,
        thumbnailUrl: data.thumbnailUrl,
        metadata,
        status: data.status,
        version: data.version,
        createdBy: data.createdBy,
        updatedBy: data.updatedBy,
        createdAt: data.createdAt,
        updatedAt: data.updatedAt,
        deletedAt: data.deletedAt,
      },
      update: {
        name: data.name,
        url: data.url,
        thumbnailUrl: data.thumbnailUrl,
        metadata,
        status: data.status,
        version: data.version,
        updatedBy: data.updatedBy,
        updatedAt: data.updatedAt,
        deletedAt: data.deletedAt,
      },
    });

    return toDomain(record);
  }

  async delete(id: string): Promise<void> {
    await this.prisma.mediaFile.delete({
      where: { id },
    });
  }
}
