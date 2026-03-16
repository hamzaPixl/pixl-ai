import type { FastifyInstance, FastifyRequest } from 'fastify';
import type { WebSocket, RawData } from 'ws';
import type { ILogger } from '@saas-studio/logger';
import { SubscriptionManager, type Channel } from '../subscriptions';
import { type WsTokenVerifier, authenticateWsConnection } from '../auth';

export const WsMessageType = {
  SUBSCRIBE: 'subscribe',
  UNSUBSCRIBE: 'unsubscribe',
  MESSAGE: 'message',
  ERROR: 'error',
  PING: 'ping',
  PONG: 'pong',
} as const;

export type WsMessageTypeValue = (typeof WsMessageType)[keyof typeof WsMessageType];

export interface WsMessage {
  type: WsMessageTypeValue;
  channel?: string;
  data?: unknown;
  error?: string;
}

export interface WsGatewayConfig {
  path?: string;
  pingInterval?: number;
  authRequired?: boolean;
  maxPayloadSize?: number;
}

export class WebSocketGateway {
  private readonly subscriptions: SubscriptionManager;
  private readonly config: Required<WsGatewayConfig>;
  private pingTimers = new Map<WebSocket, NodeJS.Timeout>();

  constructor(
    private readonly fastify: FastifyInstance,
    private readonly verifier: WsTokenVerifier,
    private readonly logger: ILogger,
    config: WsGatewayConfig = {},
  ) {
    this.config = {
      path: config.path ?? '/ws',
      pingInterval: config.pingInterval ?? 30000,
      authRequired: config.authRequired ?? true,
      maxPayloadSize: config.maxPayloadSize ?? 1024 * 1024,
    };

    this.subscriptions = new SubscriptionManager(logger);
  }

  async register(): Promise<void> {
    const websocket = await import('@fastify/websocket');
    await this.fastify.register(websocket.default);

    this.fastify.get(
      this.config.path,
      { websocket: true },
      async (socket: WebSocket, request: FastifyRequest) => {
        await this.handleConnection(socket, request);
      },
    );

    this.logger.info('WebSocket gateway registered', {
      path: this.config.path,
    });
  }

  private async handleConnection(socket: WebSocket, request: FastifyRequest): Promise<void> {
    const auth = await authenticateWsConnection(request, this.verifier);

    if (this.config.authRequired && !auth.authenticated) {
      this.sendError(socket, auth.error ?? 'Authentication required');
      socket.close(4001, 'Unauthorized');
      return;
    }

    const metadata = {
      tenantId: auth.tenantId ?? '',
      userId: auth.userId,
    };

    this.logger.info('WebSocket connection established', {
      tenantId: metadata.tenantId,
      userId: metadata.userId,
    });

    this.setupPing(socket);

    socket.on('message', (data) => {
      this.handleMessage(socket, data, metadata);
    });

    socket.on('close', () => {
      this.handleClose(socket, metadata);
    });

    socket.on('error', (error) => {
      this.logger.error('WebSocket error', {
        error: error.message,
        tenantId: metadata.tenantId,
      });
    });
  }

  private handleMessage(
    socket: WebSocket,
    data: RawData,
    metadata: { tenantId: string; userId?: string },
  ): void {
    try {
      const message = JSON.parse(data.toString()) as WsMessage;

      switch (message.type) {
        case WsMessageType.SUBSCRIBE:
          if (message.channel) {
            this.subscriptions.subscribe(socket, message.channel as Channel, metadata);
            this.send(socket, {
              type: WsMessageType.MESSAGE,
              data: { subscribed: message.channel },
            });
          }
          break;

        case WsMessageType.UNSUBSCRIBE:
          if (message.channel) {
            this.subscriptions.unsubscribe(socket, message.channel as Channel);
            this.send(socket, {
              type: WsMessageType.MESSAGE,
              data: { unsubscribed: message.channel },
            });
          }
          break;

        case WsMessageType.PING:
          this.send(socket, { type: WsMessageType.PONG });
          break;

        default:
          this.sendError(socket, `Unknown message type: ${message.type}`);
      }
    } catch (error) {
      this.sendError(socket, error instanceof Error ? error.message : 'Invalid message format');
    }
  }

  private handleClose(socket: WebSocket, metadata: { tenantId: string; userId?: string }): void {
    const timer = this.pingTimers.get(socket);
    if (timer) {
      clearInterval(timer);
      this.pingTimers.delete(socket);
    }

    this.subscriptions.removeSocket(socket);

    this.logger.info('WebSocket connection closed', {
      tenantId: metadata.tenantId,
      userId: metadata.userId,
    });
  }

  private setupPing(socket: WebSocket): void {
    const timer = setInterval(() => {
      if (socket.readyState === socket.OPEN) {
        socket.ping();
      }
    }, this.config.pingInterval);

    this.pingTimers.set(socket, timer);
  }

  private send(socket: WebSocket, message: WsMessage): void {
    if (socket.readyState === socket.OPEN) {
      socket.send(JSON.stringify(message));
    }
  }

  private sendError(socket: WebSocket, error: string): void {
    this.send(socket, { type: WsMessageType.ERROR, error });
  }

  broadcast(channel: Channel, data: unknown): number {
    return this.subscriptions.broadcast(channel, {
      type: WsMessageType.MESSAGE,
      channel,
      data,
    });
  }

  broadcastToTenant(tenantId: string, data: unknown): number {
    return this.subscriptions.broadcastToTenant(tenantId, {
      type: WsMessageType.MESSAGE,
      data,
    });
  }

  getStats(): { channels: number; connections: number } {
    return {
      channels: this.subscriptions.channelCount,
      connections: this.subscriptions.connectionCount,
    };
  }
}

export function createWebSocketGateway(
  fastify: FastifyInstance,
  verifier: WsTokenVerifier,
  logger: ILogger,
  config?: WsGatewayConfig,
): WebSocketGateway {
  return new WebSocketGateway(fastify, verifier, logger, config);
}
