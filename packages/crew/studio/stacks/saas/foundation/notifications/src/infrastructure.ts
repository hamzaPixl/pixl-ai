import type { ILogger } from '@saas-studio/logger';
import {
  NotificationService,
  createNotificationService,
  type NotificationServiceOptions,
  type SendNotificationOptions,
} from './service';
import {
  InAppNotificationChannel,
  ConsoleNotificationChannel,
  WebhookNotificationChannel,
  type INotificationChannel,
} from './channel';
import type {
  NotificationChannel,
  NotificationPayload,
  NotificationResult,
} from './types';

/**
 * Notifications configuration (subset of what's in @saas-studio/config).
 * Defined here to avoid circular dependency.
 */
export interface NotificationsConfig {
  enabled?: boolean;
  emailProvider?: 'console' | 'smtp' | 'sendgrid' | 'ses';
}

/**
 * Options for creating a NotificationInfrastructure instance.
 */
export interface NotificationInfrastructureOptions {
  /** Logger instance */
  logger: ILogger;
  /** Default notification channel */
  defaultChannel?: NotificationChannel;
  /** Whether to register the in-app channel (default: true) */
  enableInApp?: boolean;
  /** Whether to register the webhook channel (default: true) */
  enableWebhook?: boolean;
  /** Webhook configuration */
  webhookConfig?: {
    timeout?: number;
    retries?: number;
    headers?: Record<string, string>;
  };
}

/**
 * A channel registration for custom channels.
 */
export interface ChannelRegistration {
  channel: INotificationChannel;
}

/**
 * Factory function to create a NotificationInfrastructure instance.
 */
export function createNotificationInfrastructure(
  options: NotificationInfrastructureOptions,
): NotificationInfrastructure {
  return new NotificationInfrastructure(options);
}

/**
 * Sets up standard notifications with common defaults.
 * A convenience function for typical use cases.
 */
export function setupStandardNotifications(
  logger: ILogger,
  config?: NotificationsConfig,
  environment?: string,
): NotificationInfrastructure {
  const infra = new NotificationInfrastructure({
    logger,
    defaultChannel: 'in-app',
    enableInApp: true,
    enableWebhook: true,
    webhookConfig: {
      timeout: 5000,
      retries: 3,
    },
  });

  // Register console channel for development or when email provider is 'console'
  const emailProvider = config?.emailProvider ?? 'console';
  const isDev = environment === 'development' || environment === 'test';

  if (emailProvider === 'console' || isDev) {
    infra.registerChannel({
      channel: new ConsoleNotificationChannel({ enabled: true }, logger),
    });
  }

  infra.initialize();

  return infra;
}

/**
 * Manages the complete lifecycle of notification infrastructure:
 * - Notification service
 * - Channel registration
 * - Sending helpers
 *
 * Usage:
 * ```typescript
 * const infra = createNotificationInfrastructure({
 *   logger,
 *   enableInApp: true,
 *   enableWebhook: true,
 * });
 *
 * // Optionally register custom channels
 * infra.registerChannel({ channel: myEmailChannel });
 *
 * infra.initialize();
 *
 * // Send notifications
 * await infra.send({
 *   type: 'task.assigned',
 *   recipient: { id: userId, tenantId },
 *   subject: 'Task Assigned',
 *   body: 'You have been assigned a new task.',
 * });
 *
 * // Or use the simplified setup:
 * const infra = setupStandardNotifications(logger, config, 'development');
 * ```
 */
export class NotificationInfrastructure {
  private readonly options: NotificationInfrastructureOptions;
  private readonly logger: ILogger;
  private serviceInstance: NotificationService | null = null;
  private inAppChannelInstance: InAppNotificationChannel | null = null;
  private readonly pendingChannels: INotificationChannel[] = [];
  private initialized = false;

  constructor(options: NotificationInfrastructureOptions) {
    this.options = options;
    this.logger = options.logger;
  }

  /**
   * Registers a custom notification channel.
   * Must be called before initialize().
   */
  registerChannel(registration: ChannelRegistration): this {
    if (this.initialized) {
      // If already initialized, register directly with the service
      this.serviceInstance?.registerChannel(registration.channel);
    } else {
      this.pendingChannels.push(registration.channel);
    }
    return this;
  }

  /**
   * Initializes the notification service and registers all channels.
   */
  initialize(): NotificationService {
    if (this.initialized && this.serviceInstance) {
      this.logger.warn('NotificationInfrastructure already initialized');
      return this.serviceInstance;
    }

    const serviceOptions: NotificationServiceOptions = {
      logger: this.logger,
      defaultChannel: this.options.defaultChannel ?? 'in-app',
      defaultPriority: 'normal',
    };

    this.serviceInstance = createNotificationService(serviceOptions);

    // Register in-app channel if enabled
    if (this.options.enableInApp !== false) {
      this.inAppChannelInstance = new InAppNotificationChannel({ enabled: true }, this.logger);
      this.serviceInstance.registerChannel(this.inAppChannelInstance);
    }

    // Register webhook channel if enabled
    if (this.options.enableWebhook !== false) {
      const webhookChannel = new WebhookNotificationChannel(
        {
          enabled: true,
          timeout: this.options.webhookConfig?.timeout ?? 5000,
          retries: this.options.webhookConfig?.retries ?? 3,
          headers: this.options.webhookConfig?.headers,
        },
        this.logger,
      );
      this.serviceInstance.registerChannel(webhookChannel);
    }

    // Register any pending custom channels
    for (const channel of this.pendingChannels) {
      this.serviceInstance.registerChannel(channel);
    }
    this.pendingChannels.length = 0;

    this.initialized = true;

    this.logger.info('NotificationInfrastructure initialized', {
      channels: this.serviceInstance.getAvailableChannels(),
    });

    return this.serviceInstance;
  }

  /**
   * Returns the notification service instance.
   * Throws if not initialized.
   */
  get service(): NotificationService {
    if (!this.serviceInstance) {
      throw new Error('NotificationInfrastructure not initialized. Call initialize() first.');
    }
    return this.serviceInstance;
  }

  /**
   * Returns whether the infrastructure is initialized.
   */
  get isInitialized(): boolean {
    return this.initialized;
  }

  /**
   * Returns the in-app channel instance, if enabled.
   */
  get inAppChannel(): InAppNotificationChannel | null {
    return this.inAppChannelInstance;
  }

  /**
   * Sends a notification through the service.
   */
  async send(options: SendNotificationOptions): Promise<NotificationResult> {
    return this.service.send(options);
  }

  /**
   * Returns in-app notifications for a recipient.
   * Throws if in-app channel is not enabled.
   */
  getInAppNotifications(recipientId: string): NotificationPayload[] {
    if (!this.inAppChannelInstance) {
      throw new Error('In-app channel not enabled');
    }
    return this.inAppChannelInstance.getNotifications(recipientId);
  }

  /**
   * Returns available notification channels.
   */
  getAvailableChannels(): NotificationChannel[] {
    if (!this.serviceInstance) {
      return [];
    }
    return this.serviceInstance.getAvailableChannels();
  }

  /**
   * Clears internal state.
   * Used for testing.
   */
  clear(): void {
    if (this.inAppChannelInstance) {
      this.inAppChannelInstance.clear();
    }
    this.serviceInstance = null;
    this.inAppChannelInstance = null;
    this.initialized = false;
    this.pendingChannels.length = 0;
  }
}
