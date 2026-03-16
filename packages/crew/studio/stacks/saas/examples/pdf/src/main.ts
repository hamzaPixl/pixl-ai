/**
 * PDF service entry point
 */

import { PrismaClient } from '../prisma/generated/client';
import { createApiFactory } from '@saas-studio/api-factory';
import { createUnitOfWork } from '@saas-studio/outbox';
import { createTenantScopeExtension } from '@saas-studio/tenancy';
import { permissionRegistry, crudPermissions, roleRegistry } from '@saas-studio/rbac';
import { PrismaPdfTemplateRepository } from './infrastructure/repositories/pdf-template-repository';
import { PrismaPdfDocumentRepository } from './infrastructure/repositories/pdf-document-repository';
import { registerPdfRoutes } from './api/routes/pdf-routes';

async function bootstrap(): Promise<void> {
  const prisma = new PrismaClient().$extends(
    createTenantScopeExtension({
      excludedModels: ['Tenant', 'AuditLog', 'Outbox'],
    }),
  ) as unknown as PrismaClient;

  permissionRegistry.registerCrud('pdf-templates');
  permissionRegistry.registerCrud('pdf');
  permissionRegistry.register('pdf:generate', 'Generate PDFs');

  roleRegistry.register({
    name: 'admin',
    description: 'Administrator with full access',
    permissions: [...crudPermissions('pdf-templates'), ...crudPermissions('pdf'), 'pdf:generate'],
  });

  roleRegistry.register({
    name: 'member',
    description: 'Regular member',
    permissions: [
      'pdf-templates:list',
      'pdf-templates:read',
      'pdf:list',
      'pdf:read',
      'pdf:generate',
    ] as ReturnType<typeof crudPermissions>,
    inherits: [],
  });

  roleRegistry.register({
    name: 'viewer',
    description: 'Read-only access',
    permissions: ['pdf-templates:list', 'pdf-templates:read', 'pdf:list', 'pdf:read'] as ReturnType<
      typeof crudPermissions
    >,
  });

  const { app, logger, start } = await createApiFactory({
    name: 'pdf-service',
    version: '0.1.0',
    port: Number(process.env['PORT']) || 3004,
    logLevel: (process.env['LOG_LEVEL'] as 'info') || 'info',
    logPretty: process.env['NODE_ENV'] !== 'production',
    jwt: {
      secret: process.env['JWT_SECRET'] || 'development-secret-change-in-production',
    },
    cors: {
      origins: (process.env['CORS_ORIGINS'] || '*').split(','),
    },
    swagger: {
      title: 'PDF Service API',
      description: 'Service for PDF generation, manipulation, and templating',
      version: '0.1.0',
      tags: [
        { name: 'templates', description: 'PDF template management' },
        { name: 'documents', description: 'PDF document generation' },
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
  const templateRepository = new PrismaPdfTemplateRepository(prisma);
  const documentRepository = new PrismaPdfDocumentRepository(prisma);

  registerPdfRoutes(app, {
    templateRepository,
    documentRepository,
    unitOfWork,
  });

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
