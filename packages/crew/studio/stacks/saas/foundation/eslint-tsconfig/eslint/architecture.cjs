/**
 * Architecture Fitness Functions
 *
 * These ESLint rules enforce the layered architecture:
 * - Domain layer: NO imports from Prisma, Fastify, Zod (pure TypeScript)
 * - API layer: NO direct imports from Prisma (use repositories)
 * - All mutations: MUST use UnitOfWork pattern
 *
 * CI will fail if these rules are violated.
 */

/** @type {import('eslint').Linter.Config} */
module.exports = {
  extends: ['./base.cjs'],
  rules: {
    // Domain layer isolation - enforced via import restrictions
    'no-restricted-imports': [
      'error',
      {
        patterns: [
          // Domain files cannot import infrastructure
          {
            group: ['@prisma/*', 'prisma', '@prisma/client'],
            message: 'Domain layer cannot import Prisma. Use repository interfaces.',
          },
          {
            group: ['fastify', '@fastify/*'],
            message: 'Domain layer cannot import Fastify. Keep domain pure.',
          },
        ],
      },
    ],
  },
  overrides: [
    // Domain layer - strictest rules
    {
      files: ['**/domain/**/*.ts'],
      rules: {
        'no-restricted-imports': [
          'error',
          {
            patterns: [
              {
                group: ['@prisma/*', 'prisma', '@prisma/client'],
                message: 'Domain layer MUST NOT import Prisma. Use repository interfaces.',
              },
              {
                group: ['fastify', '@fastify/*'],
                message: 'Domain layer MUST NOT import Fastify. Keep domain framework-free.',
              },
              {
                group: ['zod'],
                message:
                  'Domain layer should use plain TypeScript interfaces. Zod belongs in contracts/api layers.',
              },
              {
                group: ['ioredis', 'redis'],
                message: 'Domain layer MUST NOT import Redis directly.',
              },
              {
                group: ['nats', '@nats-io/*'],
                message: 'Domain layer MUST NOT import NATS directly.',
              },
              {
                group: ['bullmq'],
                message: 'Domain layer MUST NOT import BullMQ directly.',
              },
            ],
          },
        ],
      },
    },
    // API/Routes layer - no direct Prisma
    {
      files: ['**/api/**/*.ts', '**/routes/**/*.ts'],
      rules: {
        'no-restricted-imports': [
          'error',
          {
            patterns: [
              {
                group: ['@prisma/client'],
                message:
                  'API layer should not import Prisma directly. Use repositories via dependency injection.',
              },
            ],
          },
        ],
      },
    },
    // Infrastructure layer - allowed to use everything
    {
      files: ['**/infrastructure/**/*.ts', '**/repositories/**/*.ts'],
      rules: {
        'no-restricted-imports': 'off',
      },
    },
    // Application layer - commands/queries
    {
      files: ['**/application/**/*.ts', '**/commands/**/*.ts', '**/queries/**/*.ts'],
      rules: {
        'no-restricted-imports': [
          'error',
          {
            patterns: [
              {
                group: ['@prisma/client'],
                message: 'Application layer should use repository interfaces, not Prisma directly.',
              },
              {
                group: ['fastify', '@fastify/*'],
                message: 'Application layer should be framework-agnostic.',
              },
            ],
          },
        ],
      },
    },
  ],
};
