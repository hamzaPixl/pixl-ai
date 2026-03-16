import type { FastifyInstance } from 'fastify';
import type { ILogger } from '@saas-studio/logger';
import { WebSocketGateway, createWebSocketGateway, type WsGatewayConfig } from './gateway';
import { createJwtWsVerifier, type WsTokenVerifier } from './auth';
import type { Channel } from './subscriptions';

/**
 * Options for creating a RealtimeInfrastructure instance.
 */
export interface RealtimeInfrastructureOptions {
  /** Fastify instance to register the WebSocket route */
  fastify: FastifyInstance;
  /** Logger instance */
  logger: ILogger;
  /** WebSocket path (default: '/ws') */
  path?: string;
  /** Ping interval in milliseconds (default: 30000) */
  pingInterval?: number;
  /** Whether authentication is required (default: true) */
  authRequired?: boolean;
  /** Custom token verifier (default: JWT verifier) */
  verifier?: WsTokenVerifier;
}

/**
 * An entity broadcaster for type-safe event broadcasting.
 */
export interface EntityBroadcaster<TEvent extends string = string> {
  /** Broadcasts an event to entity-specific and tenant channels */
  broadcast(
    tenantId: string,
    entityId: string,
    event: TEvent,
    data: unknown,
  ): void;
  /** Broadcasts to the entity channel only */
  broadcastToEntity(entityId: string, event: TEvent, data: unknown): void;
  /** Broadcasts to the tenant channel only */
  broadcastToTenant(tenantId: string, event: TEvent, entityId: string, data: unknown): void;
}

/**
 * Factory function to create a RealtimeInfrastructure instance.
 */
export function createRealtimeInfrastructure(
  options: RealtimeInfrastructureOptions,
): RealtimeInfrastructure {
  return new RealtimeInfrastructure(options);
}

/**
 * Manages the complete lifecycle of real-time WebSocket infrastructure:
 * - WebSocket gateway registration
 * - Broadcasting helpers
 * - Connection statistics
 *
 * Usage:
 * ```typescript
 * const infra = createRealtimeInfrastructure({
 *   fastify: app,
 *   logger,
 *   path: '/ws',
 * });
 *
 * await infra.initialize();
 *
 * // Create typed broadcasters for your entities
 * const taskBroadcaster = infra.createEntityBroadcaster<'created' | 'updated' | 'deleted'>(
 *   'task',
 *   (entityId) => `task:${entityId}`,
 *   (tenantId) => `tenant:${tenantId}:tasks`,
 * );
 *
 * // Use the broadcaster
 * taskBroadcaster.broadcast(tenantId, taskId, 'created', taskData);
 * ```
 */
export class RealtimeInfrastructure {
  private readonly options: RealtimeInfrastructureOptions;
  private readonly logger: ILogger;
  private gatewayInstance: WebSocketGateway | null = null;
  private initialized = false;

  constructor(options: RealtimeInfrastructureOptions) {
    this.options = options;
    this.logger = options.logger;
  }

  /**
   * Initializes and registers the WebSocket gateway.
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      this.logger.warn('RealtimeInfrastructure already initialized');
      return;
    }

    const verifier = this.options.verifier ?? createJwtWsVerifier(this.options.fastify);

    const config: WsGatewayConfig = {
      path: this.options.path ?? '/ws',
      pingInterval: this.options.pingInterval ?? 30000,
      authRequired: this.options.authRequired ?? true,
    };

    this.gatewayInstance = createWebSocketGateway(
      this.options.fastify,
      verifier,
      this.logger,
      config,
    );

    await this.gatewayInstance.register();
    this.initialized = true;

    this.logger.info('RealtimeInfrastructure initialized', {
      path: config.path,
    });
  }

  /**
   * Returns the underlying WebSocket gateway.
   * Throws if not initialized.
   */
  get gateway(): WebSocketGateway {
    if (!this.gatewayInstance) {
      throw new Error('RealtimeInfrastructure not initialized. Call initialize() first.');
    }
    return this.gatewayInstance;
  }

  /**
   * Returns the gateway or null if not initialized.
   */
  get gatewayOrNull(): WebSocketGateway | null {
    return this.gatewayInstance;
  }

  /**
   * Returns whether the infrastructure is initialized.
   */
  get isInitialized(): boolean {
    return this.initialized;
  }

  /**
   * Broadcasts a message to a specific channel.
   * Returns the number of clients notified.
   */
  broadcast(channel: string, data: unknown): number {
    if (!this.gatewayInstance) {
      this.logger.warn('Cannot broadcast: gateway not initialized');
      return 0;
    }
    return this.gatewayInstance.broadcast(channel as Channel, data);
  }

  /**
   * Broadcasts a message to all connections in a tenant.
   * Returns the number of clients notified.
   */
  broadcastToTenant(tenantId: string, data: unknown): number {
    if (!this.gatewayInstance) {
      this.logger.warn('Cannot broadcast: gateway not initialized');
      return 0;
    }
    return this.gatewayInstance.broadcastToTenant(tenantId, data);
  }

  /**
   * Creates a typed entity broadcaster for consistent event broadcasting.
   *
   * @param entityType - Type of entity (e.g., 'task', 'project')
   * @param entityChannelPattern - Function that returns channel for an entity ID
   * @param tenantChannelPattern - Optional function that returns channel for a tenant ID
   */
  createEntityBroadcaster<TEvent extends string = string>(
    entityType: string,
    entityChannelPattern: (entityId: string) => string,
    tenantChannelPattern?: (tenantId: string) => string,
  ): EntityBroadcaster<TEvent> {
    return {
      broadcast: (
        tenantId: string,
        entityId: string,
        event: TEvent,
        data: unknown,
      ): void => {
        if (!this.gatewayInstance) return;

        // Broadcast to tenant channel
        if (tenantChannelPattern) {
          this.gatewayInstance.broadcast(tenantChannelPattern(tenantId) as Channel, {
            event,
            entityType,
            entityId,
            data,
          });
        }

        // Broadcast to entity channel (except for delete events)
        if (event !== 'deleted') {
          this.gatewayInstance.broadcast(entityChannelPattern(entityId) as Channel, {
            event,
            data,
          });
        }
      },

      broadcastToEntity: (entityId: string, event: TEvent, data: unknown): void => {
        if (!this.gatewayInstance) return;
        this.gatewayInstance.broadcast(entityChannelPattern(entityId) as Channel, {
          event,
          data,
        });
      },

      broadcastToTenant: (
        tenantId: string,
        event: TEvent,
        entityId: string,
        data: unknown,
      ): void => {
        if (!this.gatewayInstance || !tenantChannelPattern) return;
        this.gatewayInstance.broadcast(tenantChannelPattern(tenantId) as Channel, {
          event,
          entityType,
          entityId,
          data,
        });
      },
    };
  }

  /**
   * Returns connection statistics.
   */
  getStats(): { channels: number; connections: number } {
    if (!this.gatewayInstance) {
      return { channels: 0, connections: 0 };
    }
    return this.gatewayInstance.getStats();
  }

  /**
   * Clears internal state.
   * Used for testing.
   */
  clear(): void {
    this.gatewayInstance = null;
    this.initialized = false;
  }
}
