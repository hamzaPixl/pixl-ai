/**
 * Mail domain events
 */

export const MailEvents = {
  EMAIL_QUEUED: 'mail.email.queued',
  EMAIL_SENT: 'mail.email.sent',
  EMAIL_FAILED: 'mail.email.failed',
  EMAIL_BOUNCED: 'mail.email.bounced',
  TEMPLATE_CREATED: 'mail.template.created',
  TEMPLATE_UPDATED: 'mail.template.updated',
  TEMPLATE_DELETED: 'mail.template.deleted',
} as const;

export type MailEventType = (typeof MailEvents)[keyof typeof MailEvents];
