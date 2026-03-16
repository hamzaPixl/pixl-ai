/**
 * PDF template repository - Infrastructure layer
 *
 * Prisma-based repository implementation
 */

import {
  Prisma,
  type PrismaClient,
  type PdfTemplate as PrismaPdfTemplate,
} from '../../../prisma/generated/client';
import {
  PdfTemplate,
  type PdfTemplateProps,
  type TemplateVariable,
  type PageMargins,
} from '../../domain/entities/pdf-template';

export interface IPdfTemplateRepository {
  findById(id: string): Promise<PdfTemplate | null>;
  findByName(tenantId: string, name: string): Promise<PdfTemplate | null>;
  findByTenant(
    tenantId: string,
    options?: { status?: string; limit?: number; offset?: number },
  ): Promise<PdfTemplate[]>;
  save(template: PdfTemplate, tx?: unknown): Promise<PdfTemplate>;
  delete(id: string): Promise<void>;
}

function toDomain(record: PrismaPdfTemplate): PdfTemplate {
  return PdfTemplate.fromPersistence({
    id: record.id,
    tenantId: record.tenantId,
    name: record.name,
    description: record.description,
    htmlContent: record.htmlContent,
    cssStyles: record.cssStyles,
    variables: record.variables as TemplateVariable[] | null,
    pageSize: record.pageSize as PdfTemplateProps['pageSize'],
    orientation: record.orientation as PdfTemplateProps['orientation'],
    margins: record.margins as PageMargins | null,
    header: record.header,
    footer: record.footer,
    status: record.status as PdfTemplateProps['status'],
    version: record.version,
    createdBy: record.createdBy,
    updatedBy: record.updatedBy,
    createdAt: record.createdAt,
    updatedAt: record.updatedAt,
    deletedAt: record.deletedAt,
  });
}

export class PrismaPdfTemplateRepository implements IPdfTemplateRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async findById(id: string): Promise<PdfTemplate | null> {
    const record = await this.prisma.pdfTemplate.findUnique({
      where: { id },
    });

    return record ? toDomain(record) : null;
  }

  async findByName(tenantId: string, name: string): Promise<PdfTemplate | null> {
    const record = await this.prisma.pdfTemplate.findUnique({
      where: { tenantId_name: { tenantId, name } },
    });

    return record ? toDomain(record) : null;
  }

  async findByTenant(
    tenantId: string,
    options: { status?: string; limit?: number; offset?: number } = {},
  ): Promise<PdfTemplate[]> {
    const records = await this.prisma.pdfTemplate.findMany({
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

  async save(template: PdfTemplate, tx?: unknown): Promise<PdfTemplate> {
    const client = (tx as PrismaClient) ?? this.prisma;
    const data = template.toPersistence();
    const variables =
      data.variables === null
        ? Prisma.DbNull
        : (data.variables as unknown as Prisma.InputJsonValue);
    const margins =
      data.margins === null ? Prisma.DbNull : (data.margins as unknown as Prisma.InputJsonValue);

    const record = await client.pdfTemplate.upsert({
      where: { id: data.id },
      create: {
        id: data.id,
        tenantId: data.tenantId,
        name: data.name,
        description: data.description,
        htmlContent: data.htmlContent,
        cssStyles: data.cssStyles,
        variables,
        pageSize: data.pageSize,
        orientation: data.orientation,
        margins,
        header: data.header,
        footer: data.footer,
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
        description: data.description,
        htmlContent: data.htmlContent,
        cssStyles: data.cssStyles,
        variables,
        pageSize: data.pageSize,
        orientation: data.orientation,
        margins,
        header: data.header,
        footer: data.footer,
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
    await this.prisma.pdfTemplate.delete({
      where: { id },
    });
  }
}
