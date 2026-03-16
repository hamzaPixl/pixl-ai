/**
 * Mail API routes
 */

import type { FastifyInstance } from 'fastify';
import { NotFoundError, ValidationError } from '@saas-studio/contracts';
import { requireAuth, withRequestContext, type RequestContext } from '@saas-studio/identity';
import { permissionGuard, permission } from '@saas-studio/rbac';
import type { UnitOfWork } from '@saas-studio/outbox';
import type { IEmailTemplateRepository } from '../../infrastructure/repositories/email-template-repository';
import type { IEmailRepository } from '../../infrastructure/repositories/email-repository';
import { EmailTemplate } from '../../domain/entities/email-template';
import { Email } from '../../domain/entities/email';
import {
  CreateEmailTemplateRequestSchema,
  UpdateEmailTemplateRequestSchema,
  SendEmailRequestSchema,
  ListEmailsQuerySchema,
  ListTemplatesQuerySchema,
  IdParamSchema,
  type CreateEmailTemplateRequest,
  type UpdateEmailTemplateRequest,
  type SendEmailRequest,
  type ListEmailsQuery,
  type ListTemplatesQuery,
  type IdParam,
  type EmailTemplateResponse,
  type EmailResponse,
} from '../schemas/mail-schemas';

function toTemplateResponse(template: EmailTemplate): EmailTemplateResponse {
  const data = template.toPersistence();
  return {
    id: data.id,
    tenantId: data.tenantId,
    name: data.name,
    subject: data.subject,
    htmlBody: data.htmlBody,
    textBody: data.textBody,
    variables: data.variables,
    category: data.category,
    status: data.status,
    version: data.version,
    createdBy: data.createdBy,
    updatedBy: data.updatedBy,
    createdAt: data.createdAt.toISOString(),
    updatedAt: data.updatedAt.toISOString(),
  };
}

function toEmailResponse(email: Email): EmailResponse {
  const data = email.toPersistence();
  return {
    id: data.id,
    tenantId: data.tenantId,
    templateId: data.templateId,
    fromAddress: data.fromAddress,
    fromName: data.fromName,
    toAddresses: data.toAddresses,
    ccAddresses: data.ccAddresses,
    bccAddresses: data.bccAddresses,
    subject: data.subject,
    status: data.status,
    priority: data.priority,
    scheduledFor: data.scheduledFor?.toISOString() ?? null,
    sentAt: data.sentAt?.toISOString() ?? null,
    failedAt: data.failedAt?.toISOString() ?? null,
    failureReason: data.failureReason,
    createdBy: data.createdBy,
    createdAt: data.createdAt.toISOString(),
  };
}

export function registerMailRoutes(
  fastify: FastifyInstance,
  deps: {
    templateRepository: IEmailTemplateRepository;
    emailRepository: IEmailRepository;
    unitOfWork: UnitOfWork;
  },
): void {
  const { templateRepository, emailRepository, unitOfWork } = deps;

  // Template routes
  fastify.get<{ Querystring: ListTemplatesQuery }>(
    '/mail/templates',
    {
      preHandler: [permissionGuard(permission('mail-templates', 'list'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const query = ListTemplatesQuerySchema.parse(request.query);
        const templates = await templateRepository.findByTenant(ctx.actor.tenantId, {
          category: query.category,
          status: query.status,
          limit: query.limit,
          offset: query.offset,
        });

        return { data: templates.map(toTemplateResponse) };
      });
    },
  );

  fastify.get<{ Params: IdParam }>(
    '/mail/templates/:id',
    {
      preHandler: [permissionGuard(permission('mail-templates', 'read'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async () => {
        const { id } = IdParamSchema.parse(request.params);
        const template = await templateRepository.findById(id);

        if (!template) {
          throw new NotFoundError('EmailTemplate', id);
        }

        return { data: toTemplateResponse(template) };
      });
    },
  );

  fastify.post<{ Body: CreateEmailTemplateRequest }>(
    '/mail/templates',
    {
      preHandler: [permissionGuard(permission('mail-templates', 'create'))],
    },
    async (request, reply) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const body = CreateEmailTemplateRequestSchema.parse(request.body);

        const template = EmailTemplate.create({
          tenantId: ctx.actor.tenantId,
          name: body.name,
          subject: body.subject,
          htmlBody: body.htmlBody,
          textBody: body.textBody,
          variables: body.variables,
          category: body.category,
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

  fastify.patch<{ Params: IdParam; Body: UpdateEmailTemplateRequest }>(
    '/mail/templates/:id',
    {
      preHandler: [permissionGuard(permission('mail-templates', 'update'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const { id } = IdParamSchema.parse(request.params);
        const body = UpdateEmailTemplateRequestSchema.parse(request.body);

        const template = await templateRepository.findById(id);
        if (!template) {
          throw new NotFoundError('EmailTemplate', id);
        }

        const updated = template.update({
          name: body.name,
          subject: body.subject,
          htmlBody: body.htmlBody,
          textBody: body.textBody,
          variables: body.variables,
          category: body.category,
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
    '/mail/templates/:id',
    {
      preHandler: [permissionGuard(permission('mail-templates', 'delete'))],
    },
    async (request, reply) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const { id } = IdParamSchema.parse(request.params);

        const template = await templateRepository.findById(id);
        if (!template) {
          throw new NotFoundError('EmailTemplate', id);
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

  // Email routes
  fastify.get<{ Querystring: ListEmailsQuery }>(
    '/mail/emails',
    {
      preHandler: [permissionGuard(permission('mail', 'list'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const query = ListEmailsQuerySchema.parse(request.query);
        const emails = await emailRepository.findByTenant(ctx.actor.tenantId, {
          status: query.status,
          limit: query.limit,
          offset: query.offset,
        });

        return { data: emails.map(toEmailResponse) };
      });
    },
  );

  fastify.get<{ Params: IdParam }>(
    '/mail/emails/:id',
    {
      preHandler: [permissionGuard(permission('mail', 'read'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async () => {
        const { id } = IdParamSchema.parse(request.params);
        const email = await emailRepository.findById(id);

        if (!email) {
          throw new NotFoundError('Email', id);
        }

        return { data: toEmailResponse(email) };
      });
    },
  );

  fastify.post<{ Body: SendEmailRequest }>(
    '/mail/send',
    {
      preHandler: [permissionGuard(permission('mail', 'send'))],
    },
    async (request, reply) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const body = SendEmailRequestSchema.parse(request.body);

        let htmlBody = body.htmlBody;
        let textBody = body.textBody;
        let subject = body.subject;

        if (body.templateId) {
          const template = await templateRepository.findById(body.templateId);
          if (!template) {
            throw new NotFoundError('EmailTemplate', body.templateId);
          }

          if (!template.isActive) {
            throw new ValidationError('Email template is not active', []);
          }

          const rendered = template.render(body.data ?? {});
          subject = rendered.subject;
          htmlBody = rendered.html;
          textBody = rendered.text ?? undefined;
        }

        if (!htmlBody && !textBody) {
          throw new ValidationError('Email body (HTML or text) is required', []);
        }

        const email = Email.create({
          tenantId: ctx.actor.tenantId,
          templateId: body.templateId,
          fromAddress: body.fromAddress,
          fromName: body.fromName,
          toAddresses: body.toAddresses,
          ccAddresses: body.ccAddresses,
          bccAddresses: body.bccAddresses,
          subject,
          htmlBody,
          textBody,
          priority: body.priority,
          scheduledFor: body.scheduledFor ? new Date(body.scheduledFor) : undefined,
          createdBy: ctx.actor.id,
        });

        const saved = await unitOfWork.execute(async (tx) => {
          const result = await emailRepository.save(email, tx);
          return {
            result,
            auditEntries: [],
            outboxEntries: [],
          };
        });

        reply.status(201);
        return { data: toEmailResponse(saved) };
      });
    },
  );
}
