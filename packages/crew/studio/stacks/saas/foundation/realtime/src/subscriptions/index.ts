import type { WebSocket } from 'ws';
import type { ILogger } from '@saas-studio/logger';
import { AuthorizationError } from '@saas-studio/contracts';

// Channel format: tenant:{tenantId}:{resource}:{id}
export type Channel = `tenant:${string}:${string}:${string}`;

export interface Subscription {
  channel: Channel;
  socket: WebSocket;
  tenantId: string;
  userId?: string;
  subscribedAt: Date;
}

export class SubscriptionManager {
  private subscriptions = new Map<Channel, Set<WebSocket>>();
  private socketToChannels = new Map<WebSocket, Set<Channel>>();
  private socketMetadata = new Map<WebSocket, { tenantId: string; userId?: string }>();

  constructor(private readonly logger?: ILogger) {}

  subscribe(
    socket: WebSocket,
    channel: Channel,
    metadata: { tenantId: string; userId?: string },
  ): void {
    // SECURITY: Validate tenant access - must throw error, not fail silently
    const channelTenant = this.extractTenantFromChannel(channel);
    if (channelTenant && channelTenant !== metadata.tenantId) {
      this.logger?.warn('Subscription denied: tenant mismatch', {
        channel,
        requestedTenant: channelTenant,
        userTenant: metadata.tenantId,
      });
      throw new AuthorizationError(
        `Access denied: cannot subscribe to channel for tenant ${channelTenant}`,
      );
    }

    let channelSockets = this.subscriptions.get(channel);
    if (!channelSockets) {
      channelSockets = new Set();
      this.subscriptions.set(channel, channelSockets);
    }
    channelSockets.add(socket);

    let socketChannels = this.socketToChannels.get(socket);
    if (!socketChannels) {
      socketChannels = new Set();
      this.socketToChannels.set(socket, socketChannels);
    }
    socketChannels.add(channel);

    this.socketMetadata.set(socket, metadata);

    this.logger?.debug('Socket subscribed to channel', {
      channel,
      tenantId: metadata.tenantId,
      userId: metadata.userId,
    });
  }

  unsubscribe(socket: WebSocket, channel: Channel): void {
    const channelSockets = this.subscriptions.get(channel);
    if (channelSockets) {
      channelSockets.delete(socket);
      if (channelSockets.size === 0) {
        this.subscriptions.delete(channel);
      }
    }

    const socketChannels = this.socketToChannels.get(socket);
    if (socketChannels) {
      socketChannels.delete(channel);
    }

    this.logger?.debug('Socket unsubscribed from channel', { channel });
  }

  removeSocket(socket: WebSocket): void {
    const channels = this.socketToChannels.get(socket);
    if (channels) {
      for (const channel of channels) {
        const channelSockets = this.subscriptions.get(channel);
        if (channelSockets) {
          channelSockets.delete(socket);
          if (channelSockets.size === 0) {
            this.subscriptions.delete(channel);
          }
        }
      }
    }

    this.socketToChannels.delete(socket);
    this.socketMetadata.delete(socket);

    this.logger?.debug('Socket removed from all channels');
  }

  getSubscribers(channel: Channel): Set<WebSocket> {
    return this.subscriptions.get(channel) ?? new Set();
  }

  broadcast(channel: Channel, message: unknown): number {
    const sockets = this.getSubscribers(channel);
    let sent = 0;

    const payload = JSON.stringify(message);

    for (const socket of sockets) {
      if (socket.readyState === socket.OPEN) {
        socket.send(payload);
        sent++;
      }
    }

    this.logger?.debug('Broadcast to channel', {
      channel,
      subscribers: sockets.size,
      sent,
    });

    return sent;
  }

  broadcastPattern(pattern: string, message: unknown): number {
    let totalSent = 0;

    // Escape regex special characters to prevent ReDoS, then convert * to .*
    const escaped = pattern.replace(/[.+?^${}()|[\]\\]/g, '\\$&');
    const regexPattern = `^${escaped.replace(/\*/g, '.*')}$`;
    const regex = new RegExp(regexPattern);

    for (const [channel] of this.subscriptions) {
      if (regex.test(channel)) {
        totalSent += this.broadcast(channel, message);
      }
    }

    return totalSent;
  }

  broadcastToTenant(tenantId: string, message: unknown): number {
    return this.broadcastPattern(`tenant:${tenantId}:*:*`, message);
  }

  get channelCount(): number {
    return this.subscriptions.size;
  }

  get connectionCount(): number {
    return this.socketToChannels.size;
  }

  private extractTenantFromChannel(channel: Channel): string | null {
    const parts = channel.split(':');
    return parts[1] ?? null;
  }
}

export function createSubscriptionManager(logger?: ILogger): SubscriptionManager {
  return new SubscriptionManager(logger);
}
