/**
 * Media service entry point
 */

import { PrismaClient } from '../prisma/generated/client';
import { createApiFactory } from '@saas-studio/api-factory';
import { createUnitOfWork } from '@saas-studio/outbox';
import { createTenantScopeExtension } from '@saas-studio/tenancy';
import { permissionRegistry, crudPermissions, roleRegistry } from '@saas-studio/rbac';
import { PrismaMediaFileRepository } from './infrastructure/repositories/media-file-repository';
import { registerMediaRoutes } from './api/routes/media-routes';

async function bootstrap(): Promise<void> {
  const prisma = new PrismaClient().$extends(
    createTenantScopeExtension({
      excludedModels: ['Tenant', 'AuditLog', 'Outbox'],
    }),
  ) as unknown as PrismaClient;

  permissionRegistry.registerCrud('media');

  roleRegistry.register({
    name: 'admin',
    description: 'Administrator with full access',
    permissions: crudPermissions('media'),
  });

  roleRegistry.register({
    name: 'member',
    description: 'Regular member',
    permissions: ['media:list', 'media:read', 'media:create', 'media:update'] as ReturnType<
      typeof crudPermissions
    >,
    inherits: [],
  });

  roleRegistry.register({
    name: 'viewer',
    description: 'Read-only access',
    permissions: ['media:list', 'media:read'] as ReturnType<typeof crudPermissions>,
  });

  const { app, logger, start } = await createApiFactory({
    name: 'media-service',
    version: '0.1.0',
    port: Number(process.env['PORT']) || 3001,
    logLevel: (process.env['LOG_LEVEL'] as 'info') || 'info',
    logPretty: process.env['NODE_ENV'] !== 'production',
    jwt: {
      secret: process.env['JWT_SECRET'] || 'development-secret-change-in-production',
    },
    cors: {
      origins: (process.env['CORS_ORIGINS'] || '*').split(','),
    },
    swagger: {
      title: 'Media Service API',
      description: 'Service for file uploads, image processing, and storage management',
      version: '0.1.0',
      tags: [{ name: 'media', description: 'Media file management' }],
    },
    healthChecks: {
      readyChecks: {
        database: async () => {
          await prisma.$queryRaw`SELECT 1`;
          return true;
        },
      },
    },
  });

  const unitOfWork = createUnitOfWork(prisma);
  const mediaFileRepository = new PrismaMediaFileRepository(prisma);

  registerMediaRoutes(app, { mediaFileRepository, unitOfWork });

  app.addHook('onClose', async () => {
    await prisma.$disconnect();
    logger.info('Database disconnected');
  });

  await start();
}

bootstrap().catch((error) => {
  console.error('Failed to start service:', error);
  process.exit(1);
});
