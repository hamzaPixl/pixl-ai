/**
 * PDF API schemas
 */

import { z } from 'zod';

export const DocumentStatusSchema = z.enum(['pending', 'generating', 'ready', 'failed', 'expired']);
export const TemplateStatusSchema = z.enum(['active', 'inactive', 'archived']);
export const PageSizeSchema = z.enum(['A4', 'A3', 'Letter', 'Legal', 'Tabloid']);
export const OrientationSchema = z.enum(['portrait', 'landscape']);

export const PageMarginsSchema = z.object({
  top: z.string(),
  right: z.string(),
  bottom: z.string(),
  left: z.string(),
});

export const TemplateVariableSchema = z.object({
  name: z.string(),
  description: z.string().optional(),
  required: z.boolean(),
  defaultValue: z.string().optional(),
});

export const CreatePdfTemplateRequestSchema = z.object({
  name: z.string().min(1).max(255),
  description: z.string().optional(),
  htmlContent: z.string().min(1),
  cssStyles: z.string().optional(),
  variables: z.array(TemplateVariableSchema).optional(),
  pageSize: PageSizeSchema.optional(),
  orientation: OrientationSchema.optional(),
  margins: PageMarginsSchema.optional(),
  header: z.string().optional(),
  footer: z.string().optional(),
});

export const UpdatePdfTemplateRequestSchema = z.object({
  name: z.string().min(1).max(255).optional(),
  description: z.string().optional(),
  htmlContent: z.string().min(1).optional(),
  cssStyles: z.string().optional(),
  variables: z.array(TemplateVariableSchema).optional(),
  pageSize: PageSizeSchema.optional(),
  orientation: OrientationSchema.optional(),
  margins: PageMarginsSchema.optional(),
  header: z.string().optional(),
  footer: z.string().optional(),
  status: TemplateStatusSchema.optional(),
});

export const GeneratePdfRequestSchema = z.object({
  templateId: z.string().uuid().optional(),
  name: z.string().min(1).max(255),
  data: z.record(z.unknown()).optional(),
  htmlContent: z.string().optional(),
  cssStyles: z.string().optional(),
  pageSize: PageSizeSchema.optional(),
  orientation: OrientationSchema.optional(),
  margins: PageMarginsSchema.optional(),
  expiresAt: z.string().datetime().optional(),
});

export const ListDocumentsQuerySchema = z.object({
  templateId: z.string().uuid().optional(),
  status: DocumentStatusSchema.optional(),
  limit: z.coerce.number().int().min(1).max(100).optional(),
  offset: z.coerce.number().int().min(0).optional(),
});

export const ListTemplatesQuerySchema = z.object({
  status: TemplateStatusSchema.optional(),
  limit: z.coerce.number().int().min(1).max(100).optional(),
  offset: z.coerce.number().int().min(0).optional(),
});

export const IdParamSchema = z.object({
  id: z.string().uuid(),
});

export type CreatePdfTemplateRequest = z.infer<typeof CreatePdfTemplateRequestSchema>;
export type UpdatePdfTemplateRequest = z.infer<typeof UpdatePdfTemplateRequestSchema>;
export type GeneratePdfRequest = z.infer<typeof GeneratePdfRequestSchema>;
export type ListDocumentsQuery = z.infer<typeof ListDocumentsQuerySchema>;
export type ListTemplatesQuery = z.infer<typeof ListTemplatesQuerySchema>;
export type IdParam = z.infer<typeof IdParamSchema>;

export interface PdfTemplateResponse {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  htmlContent: string;
  cssStyles: string | null;
  variables: unknown;
  pageSize: string;
  orientation: string;
  margins: unknown;
  header: string | null;
  footer: string | null;
  status: string;
  version: number;
  createdBy: string | null;
  updatedBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface PdfDocumentResponse {
  id: string;
  tenantId: string;
  templateId: string | null;
  name: string;
  data: Record<string, unknown> | null;
  filePath: string | null;
  fileSize: string | null;
  pageCount: number | null;
  status: string;
  generatedAt: string | null;
  expiresAt: string | null;
  metadata: Record<string, unknown> | null;
  createdBy: string | null;
  createdAt: string;
}
