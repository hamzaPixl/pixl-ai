export type {
  NotificationChannel,
  NotificationPriority,
  NotificationStatus,
  NotificationRecipient,
  NotificationPayload,
  NotificationResult,
  ChannelConfig,
  EmailChannelConfig,
  SmsChannelConfig,
  PushChannelConfig,
  WebhookChannelConfig,
} from './types';

export {
  BaseNotificationChannel,
  InAppNotificationChannel,
  WebhookNotificationChannel,
  ConsoleNotificationChannel,
  type INotificationChannel,
} from './channel';

export {
  NotificationService,
  createNotificationService,
  type NotificationServiceOptions,
  type SendNotificationOptions,
} from './service';

export {
  SimpleTemplateRenderer,
  TemplateRegistry,
  CommonTemplates,
  type NotificationTemplate,
  type TemplateVariables,
  type TemplateValue,
  type ITemplateRenderer,
} from './templates';

// ============================================================================
// Infrastructure
// ============================================================================

export {
  NotificationInfrastructure,
  createNotificationInfrastructure,
  setupStandardNotifications,
} from './infrastructure';
export type {
  NotificationInfrastructureOptions,
  ChannelRegistration,
  NotificationsConfig,
} from './infrastructure';
