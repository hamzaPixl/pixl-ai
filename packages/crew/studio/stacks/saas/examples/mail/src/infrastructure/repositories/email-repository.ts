/**
 * Email repository - Infrastructure layer
 *
 * Prisma-based repository implementation
 */

import {
  Prisma,
  type PrismaClient,
  type Email as PrismaEmail,
} from '../../../prisma/generated/client';
import { Email, type EmailProps, type EmailAttachment } from '../../domain/entities/email';

export interface IEmailRepository {
  findById(id: string): Promise<Email | null>;
  findByTenant(
    tenantId: string,
    options?: { status?: string; limit?: number; offset?: number },
  ): Promise<Email[]>;
  findPending(limit?: number): Promise<Email[]>;
  save(email: Email, tx?: unknown): Promise<Email>;
}

function toDomain(record: PrismaEmail): Email {
  return Email.fromPersistence({
    id: record.id,
    tenantId: record.tenantId,
    templateId: record.templateId,
    fromAddress: record.fromAddress,
    fromName: record.fromName,
    toAddresses: record.toAddresses as string[],
    ccAddresses: record.ccAddresses as string[] | null,
    bccAddresses: record.bccAddresses as string[] | null,
    subject: record.subject,
    htmlBody: record.htmlBody,
    textBody: record.textBody,
    attachments: record.attachments as EmailAttachment[] | null,
    metadata: record.metadata as Record<string, unknown> | null,
    status: record.status as EmailProps['status'],
    priority: record.priority,
    scheduledFor: record.scheduledFor,
    sentAt: record.sentAt,
    failedAt: record.failedAt,
    failureReason: record.failureReason,
    retryCount: record.retryCount,
    maxRetries: record.maxRetries,
    createdBy: record.createdBy,
    createdAt: record.createdAt,
    updatedAt: record.updatedAt,
  });
}

export class PrismaEmailRepository implements IEmailRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async findById(id: string): Promise<Email | null> {
    const record = await this.prisma.email.findUnique({
      where: { id },
    });

    return record ? toDomain(record) : null;
  }

  async findByTenant(
    tenantId: string,
    options: { status?: string; limit?: number; offset?: number } = {},
  ): Promise<Email[]> {
    const records = await this.prisma.email.findMany({
      where: {
        tenantId,
        ...(options.status && { status: options.status }),
      },
      take: options.limit ?? 100,
      skip: options.offset ?? 0,
      orderBy: { createdAt: 'desc' },
    });

    return records.map(toDomain);
  }

  async findPending(limit = 100): Promise<Email[]> {
    const now = new Date();
    const records = await this.prisma.email.findMany({
      where: {
        status: 'pending',
        OR: [{ scheduledFor: null }, { scheduledFor: { lte: now } }],
      },
      take: limit,
      orderBy: [{ priority: 'desc' }, { createdAt: 'asc' }],
    });

    return records.map(toDomain);
  }

  async save(email: Email, tx?: unknown): Promise<Email> {
    const client = (tx as PrismaClient) ?? this.prisma;
    const data = email.toPersistence();
    const attachments =
      data.attachments === null
        ? Prisma.DbNull
        : (data.attachments as unknown as Prisma.InputJsonValue);
    const metadata =
      data.metadata === null ? Prisma.DbNull : (data.metadata as unknown as Prisma.InputJsonValue);
    const ccAddresses =
      data.ccAddresses === null
        ? Prisma.DbNull
        : (data.ccAddresses as unknown as Prisma.InputJsonValue);
    const bccAddresses =
      data.bccAddresses === null
        ? Prisma.DbNull
        : (data.bccAddresses as unknown as Prisma.InputJsonValue);

    const record = await client.email.upsert({
      where: { id: data.id },
      create: {
        id: data.id,
        tenantId: data.tenantId,
        templateId: data.templateId,
        fromAddress: data.fromAddress,
        fromName: data.fromName,
        toAddresses: data.toAddresses as unknown as Prisma.InputJsonValue,
        ccAddresses,
        bccAddresses,
        subject: data.subject,
        htmlBody: data.htmlBody,
        textBody: data.textBody,
        attachments,
        metadata,
        status: data.status,
        priority: data.priority,
        scheduledFor: data.scheduledFor,
        sentAt: data.sentAt,
        failedAt: data.failedAt,
        failureReason: data.failureReason,
        retryCount: data.retryCount,
        maxRetries: data.maxRetries,
        createdBy: data.createdBy,
        createdAt: data.createdAt,
        updatedAt: data.updatedAt,
      },
      update: {
        status: data.status,
        sentAt: data.sentAt,
        failedAt: data.failedAt,
        failureReason: data.failureReason,
        retryCount: data.retryCount,
        updatedAt: data.updatedAt,
      },
    });

    return toDomain(record);
  }
}
