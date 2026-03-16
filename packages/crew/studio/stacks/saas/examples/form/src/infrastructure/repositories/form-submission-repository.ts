/**
 * Form submission repository - Infrastructure layer
 *
 * Prisma-based repository implementation
 */

import {
  Prisma,
  type PrismaClient,
  type FormSubmission as PrismaFormSubmission,
} from '../../../prisma/generated/client';
import { FormSubmission, type FormSubmissionProps } from '../../domain/entities/form-submission';

export interface IFormSubmissionRepository {
  findById(id: string): Promise<FormSubmission | null>;
  findByForm(
    formId: string,
    options?: { status?: string; limit?: number; offset?: number },
  ): Promise<FormSubmission[]>;
  findByTenant(
    tenantId: string,
    options?: {
      formId?: string;
      status?: string;
      limit?: number;
      offset?: number;
    },
  ): Promise<FormSubmission[]>;
  save(submission: FormSubmission, tx?: unknown): Promise<FormSubmission>;
  count(formId: string): Promise<number>;
}

function toDomain(record: PrismaFormSubmission): FormSubmission {
  return FormSubmission.fromPersistence({
    id: record.id,
    tenantId: record.tenantId,
    formId: record.formId,
    data: record.data as unknown as Record<string, unknown>,
    metadata: record.metadata as unknown as Record<string, unknown> | null,
    status: record.status as FormSubmissionProps['status'],
    submittedBy: record.submittedBy,
    submittedAt: record.submittedAt,
    processedAt: record.processedAt,
    createdAt: record.createdAt,
    updatedAt: record.updatedAt,
  });
}

export class PrismaFormSubmissionRepository implements IFormSubmissionRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async findById(id: string): Promise<FormSubmission | null> {
    const record = await this.prisma.formSubmission.findUnique({
      where: { id },
    });

    return record ? toDomain(record) : null;
  }

  async findByForm(
    formId: string,
    options: { status?: string; limit?: number; offset?: number } = {},
  ): Promise<FormSubmission[]> {
    const records = await this.prisma.formSubmission.findMany({
      where: {
        formId,
        ...(options.status && { status: options.status }),
      },
      take: options.limit ?? 100,
      skip: options.offset ?? 0,
      orderBy: { submittedAt: 'desc' },
    });

    return records.map(toDomain);
  }

  async findByTenant(
    tenantId: string,
    options: {
      formId?: string;
      status?: string;
      limit?: number;
      offset?: number;
    } = {},
  ): Promise<FormSubmission[]> {
    const records = await this.prisma.formSubmission.findMany({
      where: {
        tenantId,
        ...(options.formId && { formId: options.formId }),
        ...(options.status && { status: options.status }),
      },
      take: options.limit ?? 100,
      skip: options.offset ?? 0,
      orderBy: { submittedAt: 'desc' },
    });

    return records.map(toDomain);
  }

  async save(submission: FormSubmission, tx?: unknown): Promise<FormSubmission> {
    const client = (tx as PrismaClient) ?? this.prisma;
    const data = submission.toPersistence();
    const submissionData = data.data as unknown as Prisma.InputJsonValue;
    const metadata =
      data.metadata === null ? Prisma.DbNull : (data.metadata as unknown as Prisma.InputJsonValue);

    const record = await client.formSubmission.upsert({
      where: { id: data.id },
      create: {
        id: data.id,
        tenantId: data.tenantId,
        formId: data.formId,
        data: submissionData,
        metadata,
        status: data.status,
        submittedBy: data.submittedBy,
        submittedAt: data.submittedAt,
        processedAt: data.processedAt,
        createdAt: data.createdAt,
        updatedAt: data.updatedAt,
      },
      update: {
        status: data.status,
        processedAt: data.processedAt,
        updatedAt: data.updatedAt,
      },
    });

    return toDomain(record);
  }

  async count(formId: string): Promise<number> {
    return this.prisma.formSubmission.count({
      where: { formId },
    });
  }
}
