import type { FastifyRequest } from 'fastify';

declare module 'fastify' {
  interface FastifyRequest {
    user?: {
      tenantId?: string;
    };
  }
}

export type TenantResolutionStrategy = 'header' | 'subdomain' | 'path' | 'jwt';

export interface TenantResolver {
  strategy: TenantResolutionStrategy;
  resolve(request: FastifyRequest): string | null;
}

export class HeaderTenantResolver implements TenantResolver {
  readonly strategy: TenantResolutionStrategy = 'header';
  private readonly headerName: string;

  constructor(headerName = 'x-tenant-id') {
    this.headerName = headerName.toLowerCase();
  }

  resolve(request: FastifyRequest): string | null {
    const value = request.headers[this.headerName];
    return typeof value === 'string' ? value : null;
  }
}

export class SubdomainTenantResolver implements TenantResolver {
  readonly strategy: TenantResolutionStrategy = 'subdomain';
  private readonly baseDomain: string;

  constructor(baseDomain: string) {
    this.baseDomain = baseDomain.toLowerCase();
  }

  resolve(request: FastifyRequest): string | null {
    const host = request.headers.host?.toLowerCase();
    if (!host) return null;

    const hostname = host.split(':')[0];
    if (!hostname) return null;

    if (!hostname.endsWith(`.${this.baseDomain}`)) {
      return null;
    }

    const subdomain = hostname.slice(0, -(this.baseDomain.length + 1));

    if (['www', 'api', 'app'].includes(subdomain)) {
      return null;
    }

    return subdomain || null;
  }
}

export class PathTenantResolver implements TenantResolver {
  readonly strategy: TenantResolutionStrategy = 'path';
  private readonly pathPrefix: string;
  private readonly paramIndex: number;

  constructor(pathPrefix = '/tenant/', paramIndex = 0) {
    this.pathPrefix = pathPrefix;
    this.paramIndex = paramIndex;
  }

  resolve(request: FastifyRequest): string | null {
    const path = request.url;
    if (!path.startsWith(this.pathPrefix)) {
      return null;
    }

    const pathAfterPrefix = path.slice(this.pathPrefix.length);
    const segments = pathAfterPrefix.split('/');
    const tenantId = segments[this.paramIndex];

    return tenantId || null;
  }
}

export class JwtTenantResolver implements TenantResolver {
  readonly strategy: TenantResolutionStrategy = 'jwt';

  resolve(request: FastifyRequest): string | null {
    return request.user?.tenantId ?? null;
  }
}

export class CompositeTenantResolver implements TenantResolver {
  readonly strategy: TenantResolutionStrategy = 'header';
  private readonly resolvers: TenantResolver[];

  constructor(resolvers: TenantResolver[]) {
    this.resolvers = resolvers;
  }

  resolve(request: FastifyRequest): string | null {
    for (const resolver of this.resolvers) {
      const tenantId = resolver.resolve(request);
      if (tenantId) {
        return tenantId;
      }
    }
    return null;
  }
}

export function createDefaultResolver(baseDomain?: string): TenantResolver {
  const resolvers: TenantResolver[] = [new JwtTenantResolver(), new HeaderTenantResolver()];

  if (baseDomain) {
    resolvers.push(new SubdomainTenantResolver(baseDomain));
  }

  return new CompositeTenantResolver(resolvers);
}
