/**
 * Media API schemas
 */

import { z } from 'zod';

export const MediaFileStatusSchema = z.enum([
  'pending',
  'processing',
  'ready',
  'failed',
  'archived',
]);

export const CreateMediaFileRequestSchema = z.object({
  name: z.string().min(1).max(255),
  originalName: z.string().min(1),
  mimeType: z.string().min(1),
  size: z.number().int().positive(),
  path: z.string().min(1),
  bucket: z.string().min(1),
});

export const UpdateMediaFileRequestSchema = z.object({
  name: z.string().min(1).max(255).optional(),
  metadata: z.record(z.unknown()).optional(),
});

export const ListMediaFilesQuerySchema = z.object({
  status: MediaFileStatusSchema.optional(),
  limit: z.coerce.number().int().min(1).max(100).optional(),
  offset: z.coerce.number().int().min(0).optional(),
});

export const MediaFileIdParamSchema = z.object({
  id: z.string().uuid(),
});

export type CreateMediaFileRequest = z.infer<typeof CreateMediaFileRequestSchema>;
export type UpdateMediaFileRequest = z.infer<typeof UpdateMediaFileRequestSchema>;
export type ListMediaFilesQuery = z.infer<typeof ListMediaFilesQuerySchema>;
export type MediaFileIdParam = z.infer<typeof MediaFileIdParamSchema>;

export interface MediaFileResponse {
  id: string;
  tenantId: string;
  name: string;
  originalName: string;
  mimeType: string;
  size: string;
  path: string;
  bucket: string;
  url: string | null;
  thumbnailUrl: string | null;
  metadata: Record<string, unknown> | null;
  status: string;
  version: number;
  createdBy: string | null;
  updatedBy: string | null;
  createdAt: string;
  updatedAt: string;
}
