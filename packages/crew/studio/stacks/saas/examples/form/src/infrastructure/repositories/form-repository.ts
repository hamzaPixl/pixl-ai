/**
 * Form repository - Infrastructure layer
 *
 * Prisma-based repository implementation
 */

import {
  Prisma,
  type PrismaClient,
  type Form as PrismaForm,
} from '../../../prisma/generated/client';
import {
  Form,
  type FormProps,
  type FormSchema,
  type FormSettings,
} from '../../domain/entities/form';

export interface IFormRepository {
  findById(id: string): Promise<Form | null>;
  findByTenant(
    tenantId: string,
    options?: { status?: string; limit?: number; offset?: number },
  ): Promise<Form[]>;
  save(form: Form, tx?: unknown): Promise<Form>;
  delete(id: string): Promise<void>;
}

function toDomain(record: PrismaForm): Form {
  return Form.fromPersistence({
    id: record.id,
    tenantId: record.tenantId,
    name: record.name,
    description: record.description,
    schema: record.schema as unknown as FormSchema,
    settings: record.settings as unknown as FormSettings | null,
    status: record.status as FormProps['status'],
    version: record.version,
    publishedAt: record.publishedAt,
    createdBy: record.createdBy,
    updatedBy: record.updatedBy,
    createdAt: record.createdAt,
    updatedAt: record.updatedAt,
    deletedAt: record.deletedAt,
  });
}

export class PrismaFormRepository implements IFormRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async findById(id: string): Promise<Form | null> {
    const record = await this.prisma.form.findUnique({
      where: { id },
    });

    return record ? toDomain(record) : null;
  }

  async findByTenant(
    tenantId: string,
    options: { status?: string; limit?: number; offset?: number } = {},
  ): Promise<Form[]> {
    const records = await this.prisma.form.findMany({
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

  async save(form: Form, tx?: unknown): Promise<Form> {
    const client = (tx as PrismaClient) ?? this.prisma;
    const data = form.toPersistence();
    const schema = data.schema as unknown as Prisma.InputJsonValue;
    const settings =
      data.settings === null ? Prisma.DbNull : (data.settings as unknown as Prisma.InputJsonValue);

    const record = await client.form.upsert({
      where: { id: data.id },
      create: {
        id: data.id,
        tenantId: data.tenantId,
        name: data.name,
        description: data.description,
        schema,
        settings,
        status: data.status,
        version: data.version,
        publishedAt: data.publishedAt,
        createdBy: data.createdBy,
        updatedBy: data.updatedBy,
        createdAt: data.createdAt,
        updatedAt: data.updatedAt,
        deletedAt: data.deletedAt,
      },
      update: {
        name: data.name,
        description: data.description,
        schema,
        settings,
        status: data.status,
        version: data.version,
        publishedAt: data.publishedAt,
        updatedBy: data.updatedBy,
        updatedAt: data.updatedAt,
        deletedAt: data.deletedAt,
      },
    });

    return toDomain(record);
  }

  async delete(id: string): Promise<void> {
    await this.prisma.form.delete({
      where: { id },
    });
  }
}
