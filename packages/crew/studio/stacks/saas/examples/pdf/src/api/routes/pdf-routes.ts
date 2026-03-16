/**
 * PDF API routes
 */

import type { FastifyInstance } from 'fastify';
import { NotFoundError, ValidationError } from '@saas-studio/contracts';
import { requireAuth, withRequestContext, type RequestContext } from '@saas-studio/identity';
import { permissionGuard, permission } from '@saas-studio/rbac';
import type { UnitOfWork } from '@saas-studio/outbox';
import type { IPdfTemplateRepository } from '../../infrastructure/repositories/pdf-template-repository';
import type { IPdfDocumentRepository } from '../../infrastructure/repositories/pdf-document-repository';
import { PdfTemplate } from '../../domain/entities/pdf-template';
import { PdfDocument } from '../../domain/entities/pdf-document';
import {
  CreatePdfTemplateRequestSchema,
  UpdatePdfTemplateRequestSchema,
  GeneratePdfRequestSchema,
  ListDocumentsQuerySchema,
  ListTemplatesQuerySchema,
  IdParamSchema,
  type CreatePdfTemplateRequest,
  type UpdatePdfTemplateRequest,
  type GeneratePdfRequest,
  type ListDocumentsQuery,
  type ListTemplatesQuery,
  type IdParam,
  type PdfTemplateResponse,
  type PdfDocumentResponse,
} from '../schemas/pdf-schemas';

function toTemplateResponse(template: PdfTemplate): PdfTemplateResponse {
  const data = template.toPersistence();
  return {
    id: data.id,
    tenantId: data.tenantId,
    name: data.name,
    description: data.description,
    htmlContent: data.htmlContent,
    cssStyles: data.cssStyles,
    variables: data.variables,
    pageSize: data.pageSize,
    orientation: data.orientation,
    margins: data.margins,
    header: data.header,
    footer: data.footer,
    status: data.status,
    version: data.version,
    createdBy: data.createdBy,
    updatedBy: data.updatedBy,
    createdAt: data.createdAt.toISOString(),
    updatedAt: data.updatedAt.toISOString(),
  };
}

function toDocumentResponse(document: PdfDocument): PdfDocumentResponse {
  const data = document.toPersistence();
  return {
    id: data.id,
    tenantId: data.tenantId,
    templateId: data.templateId,
    name: data.name,
    data: data.data,
    filePath: data.filePath,
    fileSize: data.fileSize?.toString() ?? null,
    pageCount: data.pageCount,
    status: data.status,
    generatedAt: data.generatedAt?.toISOString() ?? null,
    expiresAt: data.expiresAt?.toISOString() ?? null,
    metadata: data.metadata,
    createdBy: data.createdBy,
    createdAt: data.createdAt.toISOString(),
  };
}

export function registerPdfRoutes(
  fastify: FastifyInstance,
  deps: {
    templateRepository: IPdfTemplateRepository;
    documentRepository: IPdfDocumentRepository;
    unitOfWork: UnitOfWork;
  },
): void {
  const { templateRepository, documentRepository, unitOfWork } = deps;

  // Template routes
  fastify.get<{ Querystring: ListTemplatesQuery }>(
    '/pdf/templates',
    {
      preHandler: [permissionGuard(permission('pdf-templates', 'list'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const query = ListTemplatesQuerySchema.parse(request.query);
        const templates = await templateRepository.findByTenant(ctx.actor.tenantId, {
          status: query.status,
          limit: query.limit,
          offset: query.offset,
        });

        return { data: templates.map(toTemplateResponse) };
      });
    },
  );

  fastify.get<{ Params: IdParam }>(
    '/pdf/templates/:id',
    {
      preHandler: [permissionGuard(permission('pdf-templates', 'read'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async () => {
        const { id } = IdParamSchema.parse(request.params);
        const template = await templateRepository.findById(id);

        if (!template) {
          throw new NotFoundError('PdfTemplate', id);
        }

        return { data: toTemplateResponse(template) };
      });
    },
  );

  fastify.post<{ Body: CreatePdfTemplateRequest }>(
    '/pdf/templates',
    {
      preHandler: [permissionGuard(permission('pdf-templates', 'create'))],
    },
    async (request, reply) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const body = CreatePdfTemplateRequestSchema.parse(request.body);

        const template = PdfTemplate.create({
          tenantId: ctx.actor.tenantId,
          name: body.name,
          description: body.description,
          htmlContent: body.htmlContent,
          cssStyles: body.cssStyles,
          variables: body.variables,
          pageSize: body.pageSize,
          orientation: body.orientation,
          margins: body.margins,
          header: body.header,
          footer: body.footer,
          createdBy: ctx.actor.id,
        });

        const saved = await unitOfWork.execute(async (tx) => {
          const result = await templateRepository.save(template, tx);
          return {
            result,
            auditEntries: [],
            outboxEntries: [],
          };
        });

        reply.status(201);
        return { data: toTemplateResponse(saved) };
      });
    },
  );

  fastify.patch<{ Params: IdParam; Body: UpdatePdfTemplateRequest }>(
    '/pdf/templates/:id',
    {
      preHandler: [permissionGuard(permission('pdf-templates', 'update'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const { id } = IdParamSchema.parse(request.params);
        const body = UpdatePdfTemplateRequestSchema.parse(request.body);

        const template = await templateRepository.findById(id);
        if (!template) {
          throw new NotFoundError('PdfTemplate', id);
        }

        const updated = template.update({
          name: body.name,
          description: body.description,
          htmlContent: body.htmlContent,
          cssStyles: body.cssStyles,
          variables: body.variables,
          pageSize: body.pageSize,
          orientation: body.orientation,
          margins: body.margins,
          header: body.header,
          footer: body.footer,
          status: body.status,
          updatedBy: ctx.actor.id,
        });

        const saved = await unitOfWork.execute(async (tx) => {
          const result = await templateRepository.save(updated, tx);
          return {
            result,
            auditEntries: [],
            outboxEntries: [],
          };
        });

        return { data: toTemplateResponse(saved) };
      });
    },
  );

  fastify.delete<{ Params: IdParam }>(
    '/pdf/templates/:id',
    {
      preHandler: [permissionGuard(permission('pdf-templates', 'delete'))],
    },
    async (request, reply) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const { id } = IdParamSchema.parse(request.params);

        const template = await templateRepository.findById(id);
        if (!template) {
          throw new NotFoundError('PdfTemplate', id);
        }

        const deleted = template.delete(ctx.actor.id);

        await unitOfWork.execute(async (tx) => {
          await templateRepository.save(deleted, tx);
          return {
            result: undefined,
            auditEntries: [],
            outboxEntries: [],
          };
        });

        reply.status(204);
      });
    },
  );

  // Document routes
  fastify.get<{ Querystring: ListDocumentsQuery }>(
    '/pdf/documents',
    {
      preHandler: [permissionGuard(permission('pdf', 'list'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const query = ListDocumentsQuerySchema.parse(request.query);
        const documents = await documentRepository.findByTenant(ctx.actor.tenantId, {
          templateId: query.templateId,
          status: query.status,
          limit: query.limit,
          offset: query.offset,
        });

        return { data: documents.map(toDocumentResponse) };
      });
    },
  );

  fastify.get<{ Params: IdParam }>(
    '/pdf/documents/:id',
    {
      preHandler: [permissionGuard(permission('pdf', 'read'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async () => {
        const { id } = IdParamSchema.parse(request.params);
        const document = await documentRepository.findById(id);

        if (!document) {
          throw new NotFoundError('PdfDocument', id);
        }

        return { data: toDocumentResponse(document) };
      });
    },
  );

  fastify.post<{ Body: GeneratePdfRequest }>(
    '/pdf/generate',
    {
      preHandler: [permissionGuard(permission('pdf', 'generate'))],
    },
    async (request, reply) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const body = GeneratePdfRequestSchema.parse(request.body);

        if (body.templateId) {
          const template = await templateRepository.findById(body.templateId);
          if (!template) {
            throw new NotFoundError('PdfTemplate', body.templateId);
          }

          if (!template.isActive) {
            throw new ValidationError('PDF template is not active', []);
          }
        } else if (!body.htmlContent) {
          throw new ValidationError('Either templateId or htmlContent is required', []);
        }

        const document = PdfDocument.create({
          tenantId: ctx.actor.tenantId,
          templateId: body.templateId,
          name: body.name,
          data: body.data,
          expiresAt: body.expiresAt ? new Date(body.expiresAt) : undefined,
          createdBy: ctx.actor.id,
        });

        const saved = await unitOfWork.execute(async (tx) => {
          const result = await documentRepository.save(document, tx);
          return {
            result,
            auditEntries: [],
            outboxEntries: [],
          };
        });

        reply.status(202);
        return { data: toDocumentResponse(saved) };
      });
    },
  );

  fastify.delete<{ Params: IdParam }>(
    '/pdf/documents/:id',
    {
      preHandler: [permissionGuard(permission('pdf', 'delete'))],
    },
    async (request, reply) => {
      requireAuth(request);

      return withRequestContext(request, async () => {
        const { id } = IdParamSchema.parse(request.params);

        const document = await documentRepository.findById(id);
        if (!document) {
          throw new NotFoundError('PdfDocument', id);
        }

        await documentRepository.delete(id);

        reply.status(204);
      });
    },
  );
}
