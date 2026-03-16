/**
 * Form domain events
 */

export const FormEvents = {
  FORM_CREATED: 'form.created',
  FORM_UPDATED: 'form.updated',
  FORM_PUBLISHED: 'form.published',
  FORM_DELETED: 'form.deleted',
  SUBMISSION_RECEIVED: 'form.submission.received',
  SUBMISSION_PROCESSED: 'form.submission.processed',
} as const;

export type FormEventType = (typeof FormEvents)[keyof typeof FormEvents];
