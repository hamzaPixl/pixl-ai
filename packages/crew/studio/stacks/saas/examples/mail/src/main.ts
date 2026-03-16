/**
 * Mail service entry point
 */

import { PrismaClient } from '../prisma/generated/client';
import { createApiFactory } from '@saas-studio/api-factory';
import { createUnitOfWork } from '@saas-studio/outbox';
import { createTenantScopeExtension } from '@saas-studio/tenancy';
import { permissionRegistry, crudPermissions, roleRegistry } from '@saas-studio/rbac';
import { PrismaEmailTemplateRepository } from './infrastructure/repositories/email-template-repository';
import { PrismaEmailRepository } from './infrastructure/repositories/email-repository';
import { registerMailRoutes } from './api/routes/mail-routes';

async function bootstrap(): Promise<void> {
  const prisma = new PrismaClient().$extends(
    createTenantScopeExtension({
      excludedModels: ['Tenant', 'AuditLog', 'Outbox'],
    }),
  ) as unknown as PrismaClient;

  permissionRegistry.registerCrud('mail-templates');
  permissionRegistry.registerCrud('mail');
  permissionRegistry.register('mail:send', 'Send emails');

  roleRegistry.register({
    name: 'admin',
    description: 'Administrator with full access',
    permissions: [...crudPermissions('mail-templates'), ...crudPermissions('mail'), 'mail:send'],
  });

  roleRegistry.register({
    name: 'member',
    description: 'Regular member',
    permissions: [
      'mail-templates:list',
      'mail-templates:read',
      'mail:list',
      'mail:read',
      'mail:send',
    ] as ReturnType<typeof crudPermissions>,
    inherits: [],
  });

  roleRegistry.register({
    name: 'viewer',
    description: 'Read-only access',
    permissions: [
      'mail-templates:list',
      'mail-templates:read',
      'mail:list',
      'mail:read',
    ] as ReturnType<typeof crudPermissions>,
  });

  const { app, logger, start } = await createApiFactory({
    name: 'mail-service',
    version: '0.1.0',
    port: Number(process.env['PORT']) || 3003,
    logLevel: (process.env['LOG_LEVEL'] as 'info') || 'info',
    logPretty: process.env['NODE_ENV'] !== 'production',
    jwt: {
      secret: process.env['JWT_SECRET'] || 'development-secret-change-in-production',
    },
    cors: {
      origins: (process.env['CORS_ORIGINS'] || '*').split(','),
    },
    swagger: {
      title: 'Mail Service API',
      description: 'Service for email sending, templates, and queue-based delivery',
      version: '0.1.0',
      tags: [
        { name: 'templates', description: 'Email template management' },
        { name: 'emails', description: 'Email sending and tracking' },
      ],
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
  const templateRepository = new PrismaEmailTemplateRepository(prisma);
  const emailRepository = new PrismaEmailRepository(prisma);

  registerMailRoutes(app, { templateRepository, emailRepository, unitOfWork });

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
