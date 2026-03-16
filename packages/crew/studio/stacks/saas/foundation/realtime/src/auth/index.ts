import type { FastifyInstance, FastifyRequest } from 'fastify';
import { AuthenticationError } from '@saas-studio/contracts';

declare module 'fastify' {
  interface FastifyInstance {
    jwt: {
      verify<T>(token: string): Promise<T>;
      sign(payload: object, options?: { expiresIn?: string }): string;
    };
  }
}

export interface WsAuthResult {
  authenticated: boolean;
  tenantId?: string;
  userId?: string;
  permissions?: string[];
  error?: string;
}

export interface WsTokenVerifier {
  verify(token: string): Promise<WsAuthResult>;
}

export class JwtWsTokenVerifier implements WsTokenVerifier {
  constructor(private readonly fastify: FastifyInstance) {}

  async verify(token: string): Promise<WsAuthResult> {
    try {
      const decoded = await this.fastify.jwt.verify<{
        sub: string;
        tenantId: string;
        permissions?: string[];
      }>(token);

      return {
        authenticated: true,
        tenantId: decoded.tenantId,
        userId: decoded.sub,
        permissions: decoded.permissions,
      };
    } catch (error) {
      return {
        authenticated: false,
        error: error instanceof Error ? error.message : 'Token verification failed',
      };
    }
  }
}

export interface TokenExtractionResult {
  token: string | null;
  source: 'header' | 'protocol' | 'query' | null;
}

export function extractWsToken(request: FastifyRequest): string | null {
  const result = extractWsTokenWithSource(request);
  return result.token;
}

/**
 * Token extraction priority: Authorization header > Sec-WebSocket-Protocol > Query parameter.
 * Query parameter is deprecated as tokens can leak via browser history, logs, and referrer headers.
 */
export function extractWsTokenWithSource(request: FastifyRequest): TokenExtractionResult {
  const auth = request.headers.authorization;
  if (auth?.startsWith('Bearer ')) {
    return { token: auth.slice(7), source: 'header' };
  }

  const protocol = request.headers['sec-websocket-protocol'];
  if (protocol) {
    const parts = protocol.split(',').map((p) => p.trim());
    const tokenPart = parts.find((p) => p.startsWith('token.'));
    if (tokenPart) {
      return { token: tokenPart.slice(6), source: 'protocol' };
    }
  }

  // DEPRECATED: Query parameter tokens are insecure - can leak via logs, history, referrer headers
  const query = request.query as { token?: string };
  if (query.token) {
    console.warn(
      '[SECURITY WARNING] WebSocket token received via query parameter. ' +
        'This is deprecated and insecure. Use Authorization header or Sec-WebSocket-Protocol instead.',
    );
    return { token: query.token, source: 'query' };
  }

  return { token: null, source: null };
}

export async function authenticateWsConnection(
  request: FastifyRequest,
  verifier: WsTokenVerifier,
): Promise<WsAuthResult> {
  const token = extractWsToken(request);

  if (!token) {
    return {
      authenticated: false,
      error: 'No authentication token provided',
    };
  }

  return verifier.verify(token);
}

export async function requireWsAuth(
  request: FastifyRequest,
  verifier: WsTokenVerifier,
): Promise<{ tenantId: string; userId: string; permissions?: string[] }> {
  const result = await authenticateWsConnection(request, verifier);

  if (!result.authenticated || !result.tenantId) {
    throw new AuthenticationError(result.error ?? 'Authentication failed');
  }

  return {
    tenantId: result.tenantId,
    userId: result.userId ?? '',
    permissions: result.permissions,
  };
}

export function createJwtWsVerifier(fastify: FastifyInstance): JwtWsTokenVerifier {
  return new JwtWsTokenVerifier(fastify);
}
