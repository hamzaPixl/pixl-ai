export type NotificationChannel = 'email' | 'sms' | 'push' | 'in-app' | 'slack' | 'webhook';

export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent';

export type NotificationStatus = 'pending' | 'sent' | 'delivered' | 'failed' | 'read';

export interface NotificationRecipient {
  id: string;
  email?: string;
  phone?: string;
  deviceToken?: string;
  webhookUrl?: string;
  slackUserId?: string;
  tenantId?: string;
}

export interface NotificationPayload {
  id: string;
  type: string;
  channel: NotificationChannel;
  recipient: NotificationRecipient;
  subject: string;
  body: string;
  data?: Record<string, unknown>;
  priority: NotificationPriority;
  scheduledAt?: Date;
  expiresAt?: Date;
  metadata?: {
    correlationId?: string;
    tenantId?: string;
    actorId?: string;
  };
}

export interface NotificationResult {
  id: string;
  status: NotificationStatus;
  sentAt?: Date;
  deliveredAt?: Date;
  error?: string;
  externalId?: string;
}

export interface ChannelConfig {
  enabled: boolean;
  [key: string]: unknown;
}

export interface EmailChannelConfig extends ChannelConfig {
  from: string;
  replyTo?: string;
  provider: 'smtp' | 'sendgrid' | 'ses' | 'postmark' | 'resend';
}

export interface SmsChannelConfig extends ChannelConfig {
  from: string;
  provider: 'twilio' | 'vonage' | 'messagebird';
}

export interface PushChannelConfig extends ChannelConfig {
  provider: 'firebase' | 'apns' | 'onesignal';
}

export interface WebhookChannelConfig extends ChannelConfig {
  timeout: number;
  retries: number;
  headers?: Record<string, string>;
}
