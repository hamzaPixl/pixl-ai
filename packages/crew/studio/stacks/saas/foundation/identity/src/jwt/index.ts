import { z } from 'zod';
import type { FastifyInstance, FastifyRequest } from 'fastify';
import type { Actor } from '../actor';

export const JwtPayloadSchema = z.object({
  sub: z.string().uuid(),
  tenantId: z.string().uuid(),
  email: z.string().email().optional(),
  name: z.string().optional(),
  roles: z.array(z.string()).default([]),
  permissions: z.array(z.string()).default([]),
  type: z.enum(['access', 'refresh']).default('access'),
  iat: z.number().optional(),
  exp: z.number().optional(),
});
export type JwtPayload = z.infer<typeof JwtPayloadSchema>;

export interface JwtConfig {
  secret: string;
  accessExpiresIn?: string;
  refreshExpiresIn?: string;
  issuer?: string;
  audience?: string;
}

export interface TokenPair {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

export async function registerJwtPlugin(
  fastify: FastifyInstance,
  config: JwtConfig,
): Promise<void> {
  const { default: fastifyJwt } = await import('@fastify/jwt');

  await fastify.register(fastifyJwt, {
    secret: config.secret,
    sign: {
      expiresIn: config.accessExpiresIn ?? '1h',
      iss: config.issuer,
      aud: config.audience,
    },
    verify: {
      allowedIss: config.issuer,
      allowedAud: config.audience,
    },
  });
}

export function signTokenPair(
  fastify: FastifyInstance,
  payload: Omit<JwtPayload, 'type' | 'iat' | 'exp'>,
  config: { accessExpiresIn?: string; refreshExpiresIn?: string } = {},
): TokenPair {
  const accessToken = fastify.jwt.sign(
    { ...payload, type: 'access' },
    { expiresIn: config.accessExpiresIn ?? '1h' },
  );

  const refreshToken = fastify.jwt.sign(
    { sub: payload.sub, tenantId: payload.tenantId, type: 'refresh' },
    { expiresIn: config.refreshExpiresIn ?? '7d' },
  );

  // Decode to get expiry
  const decoded = fastify.jwt.decode<JwtPayload>(accessToken);
  const expiresIn = decoded?.exp ? decoded.exp - Math.floor(Date.now() / 1000) : 3600;

  return { accessToken, refreshToken, expiresIn };
}

export async function verifyToken(fastify: FastifyInstance, token: string): Promise<JwtPayload> {
  const decoded = await fastify.jwt.verify<JwtPayload>(token);
  return JwtPayloadSchema.parse(decoded);
}

export function decodeToken(fastify: FastifyInstance, token: string): JwtPayload | null {
  const decoded = fastify.jwt.decode<JwtPayload>(token);
  if (!decoded) return null;

  const result = JwtPayloadSchema.safeParse(decoded);
  return result.success ? result.data : null;
}

export function extractPayloadFromRequest(request: FastifyRequest): JwtPayload | null {
  const user = request.user as JwtPayload | undefined;
  if (!user) return null;

  const result = JwtPayloadSchema.safeParse(user);
  return result.success ? result.data : null;
}

export function payloadToActor(payload: JwtPayload): Actor {
  return {
    type: 'user',
    id: payload.sub,
    tenantId: payload.tenantId,
    email: payload.email,
    name: payload.name,
    roles: payload.roles,
    permissions: payload.permissions,
  };
}

export function extractBearerToken(authHeader: string | undefined): string | null {
  if (!authHeader) return null;

  const parts = authHeader.split(' ');
  if (parts.length !== 2 || parts[0]?.toLowerCase() !== 'bearer') {
    return null;
  }

  return parts[1] ?? null;
}
