/**
 * Form API schemas
 */

import { z } from 'zod';

export const FormStatusSchema = z.enum(['draft', 'published', 'archived']);
export const FieldTypeSchema = z.enum([
  'text',
  'textarea',
  'number',
  'email',
  'phone',
  'date',
  'time',
  'datetime',
  'select',
  'multiselect',
  'checkbox',
  'radio',
  'file',
  'hidden',
]);

export const FormFieldSchema = z.object({
  id: z.string(),
  name: z.string(),
  label: z.string(),
  type: FieldTypeSchema,
  placeholder: z.string().optional(),
  defaultValue: z.unknown().optional(),
  required: z.boolean(),
  validation: z
    .object({
      minLength: z.number().optional(),
      maxLength: z.number().optional(),
      min: z.number().optional(),
      max: z.number().optional(),
      pattern: z.string().optional(),
      message: z.string().optional(),
    })
    .optional(),
  options: z
    .array(
      z.object({
        value: z.string(),
        label: z.string(),
      }),
    )
    .optional(),
});

export const FormSchemaSchema = z.object({
  fields: z.array(FormFieldSchema).min(1),
  sections: z
    .array(
      z.object({
        id: z.string(),
        title: z.string(),
        description: z.string().optional(),
        fields: z.array(z.string()),
      }),
    )
    .optional(),
});

export const FormSettingsSchema = z.object({
  submitButtonText: z.string().optional(),
  successMessage: z.string().optional(),
  redirectUrl: z.string().url().optional(),
  notifyOnSubmission: z.boolean().optional(),
  notificationEmails: z.array(z.string().email()).optional(),
  allowMultipleSubmissions: z.boolean().optional(),
  requireAuthentication: z.boolean().optional(),
});

export const CreateFormRequestSchema = z.object({
  name: z.string().min(1).max(255),
  description: z.string().optional(),
  schema: FormSchemaSchema,
  settings: FormSettingsSchema.optional(),
});

export const UpdateFormRequestSchema = z.object({
  name: z.string().min(1).max(255).optional(),
  description: z.string().optional(),
  schema: FormSchemaSchema.optional(),
  settings: FormSettingsSchema.optional(),
});

export const ListFormsQuerySchema = z.object({
  status: FormStatusSchema.optional(),
  limit: z.coerce.number().int().min(1).max(100).optional(),
  offset: z.coerce.number().int().min(0).optional(),
});

export const FormIdParamSchema = z.object({
  id: z.string().uuid(),
});

export const SubmitFormRequestSchema = z.object({
  data: z.record(z.unknown()),
  metadata: z.record(z.unknown()).optional(),
});

export type CreateFormRequest = z.infer<typeof CreateFormRequestSchema>;
export type UpdateFormRequest = z.infer<typeof UpdateFormRequestSchema>;
export type ListFormsQuery = z.infer<typeof ListFormsQuerySchema>;
export type FormIdParam = z.infer<typeof FormIdParamSchema>;
export type SubmitFormRequest = z.infer<typeof SubmitFormRequestSchema>;

export interface FormResponse {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  schema: unknown;
  settings: unknown;
  status: string;
  version: number;
  publishedAt: string | null;
  createdBy: string | null;
  updatedBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface FormSubmissionResponse {
  id: string;
  tenantId: string;
  formId: string;
  data: Record<string, unknown>;
  metadata: Record<string, unknown> | null;
  status: string;
  submittedBy: string | null;
  submittedAt: string;
  processedAt: string | null;
}
