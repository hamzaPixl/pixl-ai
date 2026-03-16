import { randomUUID } from 'crypto';
import type { ILogger } from '@saas-studio/logger';
import type { INotificationChannel } from '../channel';
import type {
  NotificationPayload,
  NotificationResult,
  NotificationChannel,
  NotificationRecipient,
  NotificationPriority,
} from '../types';

export interface NotificationServiceOptions {
  logger?: ILogger;
  defaultChannel?: NotificationChannel;
  defaultPriority?: NotificationPriority;
}

export interface SendNotificationOptions {
  type: string;
  channel?: NotificationChannel;
  recipient: NotificationRecipient;
  subject: string;
  body: string;
  data?: Record<string, unknown>;
  priority?: NotificationPriority;
  scheduledAt?: Date;
  expiresAt?: Date;
  correlationId?: string;
}

export class NotificationService {
  private channels = new Map<NotificationChannel, INotificationChannel>();
  private readonly logger?: ILogger;
  private readonly defaultChannel: NotificationChannel;
  private readonly defaultPriority: NotificationPriority;

  constructor(options: NotificationServiceOptions = {}) {
    this.logger = options.logger;
    this.defaultChannel = options.defaultChannel ?? 'in-app';
    this.defaultPriority = options.defaultPriority ?? 'normal';
  }

  registerChannel(channel: INotificationChannel): void {
    this.channels.set(channel.channel, channel);
    this.logger?.debug('Registered notification channel', { channel: channel.channel });
  }

  async send(options: SendNotificationOptions): Promise<NotificationResult> {
    const channel = options.channel ?? this.defaultChannel;
    const channelHandler = this.channels.get(channel);

    if (!channelHandler) {
      this.logger?.error('No channel handler registered', { channel });
      return {
        id: randomUUID(),
        status: 'failed',
        error: `No handler for channel: ${channel}`,
      };
    }

    if (!channelHandler.isConfigured()) {
      this.logger?.error('Channel not configured', { channel });
      return {
        id: randomUUID(),
        status: 'failed',
        error: `Channel not configured: ${channel}`,
      };
    }

    const payload: NotificationPayload = {
      id: randomUUID(),
      type: options.type,
      channel,
      recipient: options.recipient,
      subject: options.subject,
      body: options.body,
      data: options.data,
      priority: options.priority ?? this.defaultPriority,
      scheduledAt: options.scheduledAt,
      expiresAt: options.expiresAt,
      metadata: {
        correlationId: options.correlationId,
        tenantId: options.recipient.tenantId,
      },
    };

    this.logger?.info('Sending notification', {
      id: payload.id,
      type: payload.type,
      channel,
      recipientId: payload.recipient.id,
    });

    return channelHandler.send(payload);
  }

  async sendBulk(
    options: Omit<SendNotificationOptions, 'recipient'> & { recipients: NotificationRecipient[] },
  ): Promise<NotificationResult[]> {
    const results: NotificationResult[] = [];

    for (const recipient of options.recipients) {
      const result = await this.send({
        ...options,
        recipient,
      });
      results.push(result);
    }

    return results;
  }

  async sendMultiChannel(
    options: Omit<SendNotificationOptions, 'channel'> & { channels: NotificationChannel[] },
  ): Promise<NotificationResult[]> {
    const results: NotificationResult[] = [];

    for (const channel of options.channels) {
      const result = await this.send({
        ...options,
        channel,
      });
      results.push(result);
    }

    return results;
  }

  getAvailableChannels(): NotificationChannel[] {
    return Array.from(this.channels.keys()).filter((channel) =>
      this.channels.get(channel)?.isConfigured(),
    );
  }
}

export function createNotificationService(
  options: NotificationServiceOptions = {},
): NotificationService {
  return new NotificationService(options);
}
