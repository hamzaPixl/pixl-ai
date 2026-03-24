/**
 * Form service entry point
 */

import { PrismaClient } from '../prisma/generated/client';
import { createApiFactory } from '@saas-studio/api-factory';
import { createUnitOfWork } from '@saas-studio/outbox';
import { createTenantScopeExtension } from '@saas-studio/tenancy';
import { permissionRegistry, crudPermissions, roleRegistry } from '@saas-studio/rbac';
import { PrismaFormRepository } from './infrastructure/repositories/form-repository';
import { PrismaFormSubmissionRepository } from './infrastructure/repositories/form-submission-repository';
import { registerFormRoutes } from './api/routes/form-routes';

async function bootstrap(): Promise<void> {
  const prisma = new PrismaClient().$extends(
    createTenantScopeExtension({
      excludedModels: ['Tenant', 'AuditLog', 'Outbox'],
    }),
  ) as unknown as PrismaClient;

  permissionRegistry.registerCrud('forms');
  permissionRegistry.register('forms:submit', 'Submit forms');

  roleRegistry.register({
    name: 'admin',
    description: 'Administrator with full access',
    permissions: [...crudPermissions('forms'), 'forms:submit'],
  });

  roleRegistry.register({
    name: 'member',
    description: 'Regular member',
    permissions: [
      'forms:list',
      'forms:read',
      'forms:create',
      'forms:update',
      'forms:submit',
    ] as ReturnType<typeof crudPermissions>,
    inherits: [],
  });

  roleRegistry.register({
    name: 'viewer',
    description: 'Read-only access',
    permissions: ['forms:list', 'forms:read'] as ReturnType<typeof crudPermissions>,
  });

  const jwtSecret = process.env['JWT_SECRET'];
  if (!jwtSecret) throw new Error('JWT_SECRET environment variable is required');

  const { app, logger, start } = await createApiFactory({
    name: 'form-service',
    version: '0.1.0',
    port: Number(process.env['PORT']) || 3002,
    logLevel: (process.env['LOG_LEVEL'] as 'info') || 'info',
    logPretty: process.env['NODE_ENV'] !== 'production',
    jwt: {
      secret: jwtSecret,
    },
    cors: {
      origins: process.env['CORS_ORIGINS'] ? process.env['CORS_ORIGINS'].split(',') : ['http://localhost:3000'],
    },
    swagger: {
      title: 'Form Service API',
      description: 'Service for dynamic form creation, validation, and submission handling',
      version: '0.1.0',
      tags: [
        { name: 'forms', description: 'Form management' },
        { name: 'submissions', description: 'Form submissions' },
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
  const formRepository = new PrismaFormRepository(prisma);
  const submissionRepository = new PrismaFormSubmissionRepository(prisma);

  registerFormRoutes(app, { formRepository, submissionRepository, unitOfWork });

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
