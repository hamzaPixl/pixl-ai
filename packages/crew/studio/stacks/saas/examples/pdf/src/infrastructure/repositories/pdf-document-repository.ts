/**
 * PDF document repository - Infrastructure layer
 *
 * Prisma-based repository implementation
 */

import {
  Prisma,
  type PrismaClient,
  type PdfDocument as PrismaPdfDocument,
} from '../../../prisma/generated/client';
import { PdfDocument, type PdfDocumentProps } from '../../domain/entities/pdf-document';

export interface IPdfDocumentRepository {
  findById(id: string): Promise<PdfDocument | null>;
  findByTenant(
    tenantId: string,
    options?: {
      templateId?: string;
      status?: string;
      limit?: number;
      offset?: number;
    },
  ): Promise<PdfDocument[]>;
  findPending(limit?: number): Promise<PdfDocument[]>;
  save(document: PdfDocument, tx?: unknown): Promise<PdfDocument>;
  delete(id: string): Promise<void>;
}

function toDomain(record: PrismaPdfDocument): PdfDocument {
  return PdfDocument.fromPersistence({
    id: record.id,
    tenantId: record.tenantId,
    templateId: record.templateId,
    name: record.name,
    data: record.data as Record<string, unknown> | null,
    filePath: record.filePath,
    fileSize: record.fileSize,
    pageCount: record.pageCount,
    status: record.status as PdfDocumentProps['status'],
    generatedAt: record.generatedAt,
    expiresAt: record.expiresAt,
    metadata: record.metadata as Record<string, unknown> | null,
    createdBy: record.createdBy,
    createdAt: record.createdAt,
    updatedAt: record.updatedAt,
  });
}

export class PrismaPdfDocumentRepository implements IPdfDocumentRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async findById(id: string): Promise<PdfDocument | null> {
    const record = await this.prisma.pdfDocument.findUnique({
      where: { id },
    });

    return record ? toDomain(record) : null;
  }

  async findByTenant(
    tenantId: string,
    options: {
      templateId?: string;
      status?: string;
      limit?: number;
      offset?: number;
    } = {},
  ): Promise<PdfDocument[]> {
    const records = await this.prisma.pdfDocument.findMany({
      where: {
        tenantId,
        ...(options.templateId && { templateId: options.templateId }),
        ...(options.status && { status: options.status }),
      },
      take: options.limit ?? 100,
      skip: options.offset ?? 0,
      orderBy: { createdAt: 'desc' },
    });

    return records.map(toDomain);
  }

  async findPending(limit = 100): Promise<PdfDocument[]> {
    const records = await this.prisma.pdfDocument.findMany({
      where: { status: 'pending' },
      take: limit,
      orderBy: { createdAt: 'asc' },
    });

    return records.map(toDomain);
  }

  async save(document: PdfDocument, tx?: unknown): Promise<PdfDocument> {
    const client = (tx as PrismaClient) ?? this.prisma;
    const data = document.toPersistence();
    const documentData =
      data.data === null ? Prisma.DbNull : (data.data as unknown as Prisma.InputJsonValue);
    const metadata =
      data.metadata === null ? Prisma.DbNull : (data.metadata as unknown as Prisma.InputJsonValue);

    const record = await client.pdfDocument.upsert({
      where: { id: data.id },
      create: {
        id: data.id,
        tenantId: data.tenantId,
        templateId: data.templateId,
        name: data.name,
        data: documentData,
        filePath: data.filePath,
        fileSize: data.fileSize,
        pageCount: data.pageCount,
        status: data.status,
        generatedAt: data.generatedAt,
        expiresAt: data.expiresAt,
        metadata,
        createdBy: data.createdBy,
        createdAt: data.createdAt,
        updatedAt: data.updatedAt,
      },
      update: {
        filePath: data.filePath,
        fileSize: data.fileSize,
        pageCount: data.pageCount,
        status: data.status,
        generatedAt: data.generatedAt,
        updatedAt: data.updatedAt,
      },
    });

    return toDomain(record);
  }

  async delete(id: string): Promise<void> {
    await this.prisma.pdfDocument.delete({
      where: { id },
    });
  }
}
