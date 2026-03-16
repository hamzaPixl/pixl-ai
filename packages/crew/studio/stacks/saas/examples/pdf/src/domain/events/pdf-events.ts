/**
 * PDF domain events
 */

export const PdfEvents = {
  DOCUMENT_REQUESTED: 'pdf.document.requested',
  DOCUMENT_GENERATED: 'pdf.document.generated',
  DOCUMENT_FAILED: 'pdf.document.failed',
  TEMPLATE_CREATED: 'pdf.template.created',
  TEMPLATE_UPDATED: 'pdf.template.updated',
  TEMPLATE_DELETED: 'pdf.template.deleted',
} as const;

export type PdfEventType = (typeof PdfEvents)[keyof typeof PdfEvents];
