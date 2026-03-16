/**
 * Media API routes
 */

import type { FastifyInstance } from 'fastify';
import { NotFoundError } from '@saas-studio/contracts';
import { requireAuth, withRequestContext, type RequestContext } from '@saas-studio/identity';
import { permissionGuard, permission } from '@saas-studio/rbac';
import type { UnitOfWork } from '@saas-studio/outbox';
import type { IMediaFileRepository } from '../../infrastructure/repositories/media-file-repository';
import {
  CreateMediaFileRequestSchema,
  UpdateMediaFileRequestSchema,
  ListMediaFilesQuerySchema,
  MediaFileIdParamSchema,
  type CreateMediaFileRequest,
  type UpdateMediaFileRequest,
  type ListMediaFilesQuery,
  type MediaFileIdParam,
  type MediaFileResponse,
} from '../schemas/media-schemas';
import { MediaFile } from '../../domain/entities/media-file';

function toResponse(mediaFile: MediaFile): MediaFileResponse {
  const data = mediaFile.toPersistence();
  return {
    id: data.id,
    tenantId: data.tenantId,
    name: data.name,
    originalName: data.originalName,
    mimeType: data.mimeType,
    size: data.size.toString(),
    path: data.path,
    bucket: data.bucket,
    url: data.url,
    thumbnailUrl: data.thumbnailUrl,
    metadata: data.metadata,
    status: data.status,
    version: data.version,
    createdBy: data.createdBy,
    updatedBy: data.updatedBy,
    createdAt: data.createdAt.toISOString(),
    updatedAt: data.updatedAt.toISOString(),
  };
}

export function registerMediaRoutes(
  fastify: FastifyInstance,
  deps: {
    mediaFileRepository: IMediaFileRepository;
    unitOfWork: UnitOfWork;
  },
): void {
  const { mediaFileRepository, unitOfWork } = deps;

  fastify.get<{ Querystring: ListMediaFilesQuery }>(
    '/media',
    {
      preHandler: [permissionGuard(permission('media', 'list'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const query = ListMediaFilesQuerySchema.parse(request.query);
        const files = await mediaFileRepository.findByTenant(ctx.actor.tenantId, {
          status: query.status,
          limit: query.limit,
          offset: query.offset,
        });

        return { data: files.map(toResponse) };
      });
    },
  );

  fastify.get<{ Params: MediaFileIdParam }>(
    '/media/:id',
    {
      preHandler: [permissionGuard(permission('media', 'read'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async () => {
        const { id } = MediaFileIdParamSchema.parse(request.params);
        const file = await mediaFileRepository.findById(id);

        if (!file) {
          throw new NotFoundError('MediaFile', id);
        }

        return { data: toResponse(file) };
      });
    },
  );

  fastify.post<{ Body: CreateMediaFileRequest }>(
    '/media',
    {
      preHandler: [permissionGuard(permission('media', 'create'))],
    },
    async (request, reply) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const body = CreateMediaFileRequestSchema.parse(request.body);

        const mediaFile = MediaFile.create({
          tenantId: ctx.actor.tenantId,
          name: body.name,
          originalName: body.originalName,
          mimeType: body.mimeType,
          size: BigInt(body.size),
          path: body.path,
          bucket: body.bucket,
          createdBy: ctx.actor.id,
        });

        const saved = await unitOfWork.execute(async (tx) => {
          const result = await mediaFileRepository.save(mediaFile, tx);
          return {
            result,
            auditEntries: [],
            outboxEntries: [],
          };
        });

        reply.status(201);
        return { data: toResponse(saved) };
      });
    },
  );

  fastify.patch<{ Params: MediaFileIdParam; Body: UpdateMediaFileRequest }>(
    '/media/:id',
    {
      preHandler: [permissionGuard(permission('media', 'update'))],
    },
    async (request) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const { id } = MediaFileIdParamSchema.parse(request.params);
        const body = UpdateMediaFileRequestSchema.parse(request.body);

        const file = await mediaFileRepository.findById(id);
        if (!file) {
          throw new NotFoundError('MediaFile', id);
        }

        const updated = file.update({
          name: body.name,
          metadata: body.metadata,
          updatedBy: ctx.actor.id,
        });

        const saved = await unitOfWork.execute(async (tx) => {
          const result = await mediaFileRepository.save(updated, tx);
          return {
            result,
            auditEntries: [],
            outboxEntries: [],
          };
        });

        return { data: toResponse(saved) };
      });
    },
  );

  fastify.delete<{ Params: MediaFileIdParam }>(
    '/media/:id',
    {
      preHandler: [permissionGuard(permission('media', 'delete'))],
    },
    async (request, reply) => {
      requireAuth(request);

      return withRequestContext(request, async (ctx: RequestContext) => {
        const { id } = MediaFileIdParamSchema.parse(request.params);

        const file = await mediaFileRepository.findById(id);
        if (!file) {
          throw new NotFoundError('MediaFile', id);
        }

        const deleted = file.delete(ctx.actor.id);

        await unitOfWork.execute(async (tx) => {
          await mediaFileRepository.save(deleted, tx);
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
}
