import type { ILogger } from '@saas-studio/logger';
import type {
  NotificationPayload,
  NotificationResult,
  NotificationChannel,
  ChannelConfig,
} from '../types';

export interface INotificationChannel {
  readonly channel: NotificationChannel;
  send(payload: NotificationPayload): Promise<NotificationResult>;
  isConfigured(): boolean;
}

export abstract class BaseNotificationChannel<TConfig extends ChannelConfig>
  implements INotificationChannel
{
  abstract readonly channel: NotificationChannel;

  constructor(
    protected readonly config: TConfig,
    protected readonly logger?: ILogger,
  ) {}

  abstract send(payload: NotificationPayload): Promise<NotificationResult>;

  isConfigured(): boolean {
    return this.config.enabled;
  }
}

export class InAppNotificationChannel extends BaseNotificationChannel<ChannelConfig> {
  readonly channel: NotificationChannel = 'in-app';

  private notifications: NotificationPayload[] = [];

  async send(payload: NotificationPayload): Promise<NotificationResult> {
    this.logger?.debug('Sending in-app notification', { id: payload.id, type: payload.type });

    this.notifications.push(payload);

    return {
      id: payload.id,
      status: 'delivered',
      deliveredAt: new Date(),
    };
  }

  getNotifications(recipientId: string): NotificationPayload[] {
    return this.notifications.filter((n) => n.recipient.id === recipientId);
  }

  markAsRead(notificationId: string): void {
    const notification = this.notifications.find((n) => n.id === notificationId);
    if (notification) {
      this.logger?.debug('Marking notification as read', { id: notificationId });
    }
  }

  clear(): void {
    this.notifications = [];
  }
}

export class WebhookNotificationChannel extends BaseNotificationChannel<{
  enabled: boolean;
  timeout: number;
  retries: number;
  headers?: Record<string, string>;
}> {
  readonly channel: NotificationChannel = 'webhook';

  async send(payload: NotificationPayload): Promise<NotificationResult> {
    const webhookUrl = payload.recipient.webhookUrl;

    if (!webhookUrl) {
      return {
        id: payload.id,
        status: 'failed',
        error: 'No webhook URL provided',
      };
    }

    this.logger?.debug('Sending webhook notification', { id: payload.id, url: webhookUrl });

    try {
      const response = await fetch(webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.config.headers,
        },
        body: JSON.stringify({
          id: payload.id,
          type: payload.type,
          subject: payload.subject,
          body: payload.body,
          data: payload.data,
          timestamp: new Date().toISOString(),
        }),
        signal: AbortSignal.timeout(this.config.timeout),
      });

      if (!response.ok) {
        throw new Error(`Webhook returned ${response.status}`);
      }

      return {
        id: payload.id,
        status: 'delivered',
        deliveredAt: new Date(),
      };
    } catch (error) {
      this.logger?.error('Webhook notification failed', {
        id: payload.id,
        error: error instanceof Error ? error.message : 'Unknown',
      });

      return {
        id: payload.id,
        status: 'failed',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }
}

export class ConsoleNotificationChannel extends BaseNotificationChannel<ChannelConfig> {
  readonly channel: NotificationChannel = 'email';

  async send(payload: NotificationPayload): Promise<NotificationResult> {
    console.log('=== NOTIFICATION ===');
    console.log(`Channel: ${payload.channel}`);
    console.log(`To: ${payload.recipient.email ?? payload.recipient.id}`);
    console.log(`Subject: ${payload.subject}`);
    console.log(`Body: ${payload.body}`);
    console.log('==================');

    return {
      id: payload.id,
      status: 'delivered',
      deliveredAt: new Date(),
    };
  }
}
