/**
 * Form API routes
 */

import type { FastifyInstance } from 'fastify';
import { NotFoundError, ValidationError } from '@saas-studio/contracts';
import { requireAuth, withRequestContext, type RequestContext } from '@saas-studio/identity';
import { permissionGuard, permission } from '@saas-studio/rbac';
import type { UnitOfWork } from '@saas-studio/outbox';
import type { IFormRepository } from '../../infrastructure/repositories/form-repository';
import type { IFormSubmissionRepository } from '../../infrastructure/repositories/form-submission-repository';
import { Form } from '../../domain/entities/form';
import { FormSubmission } from '../../domain/entities/form-submission';
import {
  CreateFormRequestSchema,
  UpdateFormRequestSchema,
  ListFormsQuerySchema,
  FormIdParamSchema,
  SubmitFormRequestSchema,
  type CreateFormRequest,
  type UpdateFormRequest,
  type ListFormsQuery,
  type FormIdParam,
  type SubmitFormRequest,
  type FormResponse,
  type FormSubmissionResponse,
} from '../schemas/form-schemas';

function toFormResponse(form: Form): FormResponse {
  const data = form.toPersistence();
  return {
    id: data.id,
    tenantId: data.tenantId,
    name: data.name,
    description: data.description,
    schema: data.schema,
    settings: data.settings,
    status: data.status,
    version: data.version,
    publishedAt: data.publishedAt?.toISOString() ?? null,
    createdBy: data.createdBy,
    updatedBy: data.updatedBy,
    createdAt: data.createdAt.toISOString(),
    updatedAt: data.updatedAt.toISOString(),
  };
}

function toSubmissionResponse(submission: FormSubmission): FormSubmissionResponse {
  const data = submission.toPersistence();
  return {
    id: data.id,
    tenantId: data.tenantId,
    formId: data.formId,
    data: data.data,
    metadata: data.metadata,
    status: data.status,
    submittedBy: data.submittedBy,
    submittedAt: data.submittedAt.toISOString(),
    processedAt: data.processedAt?.toISOString() ?? null,
  };
}

export function registerFormRoutes(
  fastify: FastifyInstance,
  deps: {
    formRepository: IFormRepository;
    submissionRepository: IFormSubmissionRepository;
    unitOfWork: UnitOfWork;
  },
): void {
  const { formRepository, submissionRepository, unitOfWork } = deps;

  fastify.get<{ Querystring: ListFormsQuery }>(
    '/forms',
    {
      preHandler: [permissionGuard(permission('forms', 'list'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const query = ListFormsQuerySchema.parse(request.query);
        const forms = await formRepository.findByTenant(ctx.actor.tenantId, {
          status: query.status,
          limit: query.limit,
          offset: query.offset,
        });

        return { data: forms.map(toFormResponse) };
      });
    },
  );

  fastify.get<{ Params: FormIdParam }>(
    '/forms/:id',
    {
      preHandler: [permissionGuard(permission('forms', 'read'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async () => {
        const { id } = FormIdParamSchema.parse(request.params);
        const form = await formRepository.findById(id);

        if (!form) {
          throw new NotFoundError('Form', id);
        }

        return { data: toFormResponse(form) };
      });
    },
  );

  fastify.post<{ Body: CreateFormRequest }>(
    '/forms',
    {
      preHandler: [permissionGuard(permission('forms', 'create'))],
    },
    async (request, reply) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const body = CreateFormRequestSchema.parse(request.body);

        const form = Form.create({
          tenantId: ctx.actor.tenantId,
          name: body.name,
          description: body.description,
          schema: body.schema,
          settings: body.settings,
          createdBy: ctx.actor.id,
        });

        const saved = await unitOfWork.execute(async (tx) => {
          const result = await formRepository.save(form, tx);
          return {
            result,
            auditEntries: [],
            outboxEntries: [],
          };
        });

        reply.status(201);
        return { data: toFormResponse(saved) };
      });
    },
  );

  fastify.patch<{ Params: FormIdParam; Body: UpdateFormRequest }>(
    '/forms/:id',
    {
      preHandler: [permissionGuard(permission('forms', 'update'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const { id } = FormIdParamSchema.parse(request.params);
        const body = UpdateFormRequestSchema.parse(request.body);

        const form = await formRepository.findById(id);
        if (!form) {
          throw new NotFoundError('Form', id);
        }

        const updated = form.update({
          name: body.name,
          description: body.description,
          schema: body.schema,
          settings: body.settings,
          updatedBy: ctx.actor.id,
        });

        const saved = await unitOfWork.execute(async (tx) => {
          const result = await formRepository.save(updated, tx);
          return {
            result,
            auditEntries: [],
            outboxEntries: [],
          };
        });

        return { data: toFormResponse(saved) };
      });
    },
  );

  fastify.post<{ Params: FormIdParam }>(
    '/forms/:id/publish',
    {
      preHandler: [permissionGuard(permission('forms', 'update'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const { id } = FormIdParamSchema.parse(request.params);

        const form = await formRepository.findById(id);
        if (!form) {
          throw new NotFoundError('Form', id);
        }

        const published = form.publish(ctx.actor.id);

        const saved = await unitOfWork.execute(async (tx) => {
          const result = await formRepository.save(published, tx);
          return {
            result,
            auditEntries: [],
            outboxEntries: [],
          };
        });

        return { data: toFormResponse(saved) };
      });
    },
  );

  fastify.delete<{ Params: FormIdParam }>(
    '/forms/:id',
    {
      preHandler: [permissionGuard(permission('forms', 'delete'))],
    },
    async (request, reply) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const { id } = FormIdParamSchema.parse(request.params);

        const form = await formRepository.findById(id);
        if (!form) {
          throw new NotFoundError('Form', id);
        }

        const deleted = form.delete(ctx.actor.id);

        await unitOfWork.execute(async (tx) => {
          await formRepository.save(deleted, tx);
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

  fastify.post<{ Params: FormIdParam; Body: SubmitFormRequest }>(
    '/forms/:id/submit',
    {
      preHandler: [permissionGuard(permission('forms', 'submit'))],
    },
    async (request, reply) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const { id } = FormIdParamSchema.parse(request.params);
        const body = SubmitFormRequestSchema.parse(request.body);

        const form = await formRepository.findById(id);
        if (!form) {
          throw new NotFoundError('Form', id);
        }

        if (!form.isPublished) {
          throw new ValidationError('Form is not published', []);
        }

        const submission = FormSubmission.create({
          tenantId: ctx.actor.tenantId,
          formId: id,
          data: body.data,
          metadata: body.metadata,
          submittedBy: ctx.actor.id,
        });

        const saved = await unitOfWork.execute(async (tx) => {
          const result = await submissionRepository.save(submission, tx);
          return {
            result,
            auditEntries: [],
            outboxEntries: [],
          };
        });

        reply.status(201);
        return { data: toSubmissionResponse(saved) };
      });
    },
  );

  fastify.get<{
    Params: FormIdParam;
    Querystring: { limit?: number; offset?: number };
  }>(
    '/forms/:id/submissions',
    {
      preHandler: [permissionGuard(permission('forms', 'read'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async () => {
        const { id } = FormIdParamSchema.parse(request.params);
        const { limit, offset } = request.query;

        const submissions = await submissionRepository.findByForm(id, {
          limit,
          offset,
        });

        return { data: submissions.map(toSubmissionResponse) };
      });
    },
  );
}
