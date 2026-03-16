/**
 * Email template repository - Infrastructure layer
 *
 * Prisma-based repository implementation
 */

import {
  EmailTemplate,
  type EmailTemplateProps,
  type TemplateVariable,
} from '../../domain/entities/email-template';
import {
  Prisma,
  type PrismaClient,
  type EmailTemplate as PrismaEmailTemplate,
} from '../../../prisma/generated/client';

export interface IEmailTemplateRepository {
  findById(id: string): Promise<EmailTemplate | null>;
  findByName(tenantId: string, name: string): Promise<EmailTemplate | null>;
  findByTenant(
    tenantId: string,
    options?: {
      category?: string;
      status?: string;
      limit?: number;
      offset?: number;
    },
  ): Promise<EmailTemplate[]>;
  save(template: EmailTemplate, tx?: unknown): Promise<EmailTemplate>;
  delete(id: string): Promise<void>;
}

function toDomain(record: PrismaEmailTemplate): EmailTemplate {
  return EmailTemplate.fromPersistence({
    id: record.id,
    tenantId: record.tenantId,
    name: record.name,
    subject: record.subject,
    htmlBody: record.htmlBody,
    textBody: record.textBody,
    variables: record.variables as TemplateVariable[] | null,
    category: record.category,
    status: record.status as EmailTemplateProps['status'],
    version: record.version,
    createdBy: record.createdBy,
    updatedBy: record.updatedBy,
    createdAt: record.createdAt,
    updatedAt: record.updatedAt,
    deletedAt: record.deletedAt,
  });
}

export class PrismaEmailTemplateRepository implements IEmailTemplateRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async findById(id: string): Promise<EmailTemplate | null> {
    const record = await this.prisma.emailTemplate.findUnique({
      where: { id },
    });

    return record ? toDomain(record) : null;
  }

  async findByName(tenantId: string, name: string): Promise<EmailTemplate | null> {
    const record = await this.prisma.emailTemplate.findUnique({
      where: { tenantId_name: { tenantId, name } },
    });

    return record ? toDomain(record) : null;
  }

  async findByTenant(
    tenantId: string,
    options: {
      category?: string;
      status?: string;
      limit?: number;
      offset?: number;
    } = {},
  ): Promise<EmailTemplate[]> {
    const records = await this.prisma.emailTemplate.findMany({
      where: {
        tenantId,
        ...(options.category && { category: options.category }),
        ...(options.status && { status: options.status }),
        deletedAt: null,
      },
      take: options.limit ?? 100,
      skip: options.offset ?? 0,
      orderBy: { createdAt: 'desc' },
    });

    return records.map(toDomain);
  }

  async save(template: EmailTemplate, tx?: unknown): Promise<EmailTemplate> {
    const client = (tx as PrismaClient) ?? this.prisma;
    const data = template.toPersistence();
    const variables =
      data.variables === null
        ? Prisma.DbNull
        : (data.variables as unknown as Prisma.InputJsonValue);

    const record = await client.emailTemplate.upsert({
      where: { id: data.id },
      create: {
        id: data.id,
        tenantId: data.tenantId,
        name: data.name,
        subject: data.subject,
        htmlBody: data.htmlBody,
        textBody: data.textBody,
        variables,
        category: data.category,
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
        subject: data.subject,
        htmlBody: data.htmlBody,
        textBody: data.textBody,
        variables,
        category: data.category,
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
    await this.prisma.emailTemplate.delete({
      where: { id },
    });
  }
}
