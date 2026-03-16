export {
  SubscriptionManager,
  createSubscriptionManager,
} from './subscriptions';
export type { Channel, Subscription } from './subscriptions';

export {
  JwtWsTokenVerifier,
  extractWsToken,
  extractWsTokenWithSource,
  authenticateWsConnection,
  requireWsAuth,
  createJwtWsVerifier,
} from './auth';
export type { WsAuthResult, WsTokenVerifier, TokenExtractionResult } from './auth';

export {
  WebSocketGateway,
  WsMessageType,
  createWebSocketGateway,
} from './gateway';
export type {
  WsMessage,
  WsMessageTypeValue,
  WsGatewayConfig,
} from './gateway';

// ============================================================================
// Infrastructure
// ============================================================================

export {
  RealtimeInfrastructure,
  createRealtimeInfrastructure,
} from './infrastructure';
export type {
  RealtimeInfrastructureOptions,
  EntityBroadcaster,
} from './infrastructure';
