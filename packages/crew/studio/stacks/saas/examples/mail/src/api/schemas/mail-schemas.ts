/**
 * Mail API schemas
 */

import { z } from 'zod';

export const EmailStatusSchema = z.enum([
  'pending',
  'queued',
  'sending',
  'sent',
  'failed',
  'bounced',
]);
export const TemplateStatusSchema = z.enum(['active', 'inactive', 'archived']);

export const TemplateVariableSchema = z.object({
  name: z.string(),
  description: z.string().optional(),
  required: z.boolean(),
  defaultValue: z.string().optional(),
});

export const CreateEmailTemplateRequestSchema = z.object({
  name: z.string().min(1).max(255),
  subject: z.string().min(1).max(500),
  htmlBody: z.string().min(1),
  textBody: z.string().optional(),
  variables: z.array(TemplateVariableSchema).optional(),
  category: z.string().optional(),
});

export const UpdateEmailTemplateRequestSchema = z.object({
  name: z.string().min(1).max(255).optional(),
  subject: z.string().min(1).max(500).optional(),
  htmlBody: z.string().min(1).optional(),
  textBody: z.string().optional(),
  variables: z.array(TemplateVariableSchema).optional(),
  category: z.string().optional(),
  status: TemplateStatusSchema.optional(),
});

export const SendEmailRequestSchema = z.object({
  templateId: z.string().uuid().optional(),
  fromAddress: z.string().email(),
  fromName: z.string().optional(),
  toAddresses: z.array(z.string().email()).min(1),
  ccAddresses: z.array(z.string().email()).optional(),
  bccAddresses: z.array(z.string().email()).optional(),
  subject: z.string().min(1).max(500),
  htmlBody: z.string().optional(),
  textBody: z.string().optional(),
  data: z.record(z.unknown()).optional(),
  priority: z.number().int().min(0).max(10).optional(),
  scheduledFor: z.string().datetime().optional(),
});

export const ListEmailsQuerySchema = z.object({
  status: EmailStatusSchema.optional(),
  limit: z.coerce.number().int().min(1).max(100).optional(),
  offset: z.coerce.number().int().min(0).optional(),
});

export const ListTemplatesQuerySchema = z.object({
  category: z.string().optional(),
  status: TemplateStatusSchema.optional(),
  limit: z.coerce.number().int().min(1).max(100).optional(),
  offset: z.coerce.number().int().min(0).optional(),
});

export const IdParamSchema = z.object({
  id: z.string().uuid(),
});

export type CreateEmailTemplateRequest = z.infer<typeof CreateEmailTemplateRequestSchema>;
export type UpdateEmailTemplateRequest = z.infer<typeof UpdateEmailTemplateRequestSchema>;
export type SendEmailRequest = z.infer<typeof SendEmailRequestSchema>;
export type ListEmailsQuery = z.infer<typeof ListEmailsQuerySchema>;
export type ListTemplatesQuery = z.infer<typeof ListTemplatesQuerySchema>;
export type IdParam = z.infer<typeof IdParamSchema>;

export interface EmailTemplateResponse {
  id: string;
  tenantId: string;
  name: string;
  subject: string;
  htmlBody: string;
  textBody: string | null;
  variables: unknown;
  category: string | null;
  status: string;
  version: number;
  createdBy: string | null;
  updatedBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface EmailResponse {
  id: string;
  tenantId: string;
  templateId: string | null;
  fromAddress: string;
  fromName: string | null;
  toAddresses: string[];
  ccAddresses: string[] | null;
  bccAddresses: string[] | null;
  subject: string;
  status: string;
  priority: number;
  scheduledFor: string | null;
  sentAt: string | null;
  failedAt: string | null;
  failureReason: string | null;
  createdBy: string | null;
  createdAt: string;
}
