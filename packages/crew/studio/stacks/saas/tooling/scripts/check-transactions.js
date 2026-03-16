#!/usr/bin/env node

/**
 * Architecture fitness function: Transaction Invariant Check
 *
 * Verifies that all mutations use the UnitOfWork pattern
 * to ensure atomicity of domain changes, audit logs, and outbox entries.
 */

import { readFileSync, readdirSync, statSync } from 'fs';
import { join, relative } from 'path';

const SERVICES_DIR = './services';
const TEMPLATES_DIR = './templates';

// Patterns that indicate a mutation
const MUTATION_PATTERNS = [
  /\.create\(/,
  /\.createMany\(/,
  /\.update\(/,
  /\.updateMany\(/,
  /\.delete\(/,
  /\.deleteMany\(/,
  /\.upsert\(/,
];

// Patterns that indicate proper UnitOfWork usage
const UNIT_OF_WORK_PATTERNS = [/unitOfWork\.execute/, /UnitOfWork/, /createUnitOfWork/];

// Files/directories to skip
const SKIP_PATTERNS = [/node_modules/, /dist/, /\.test\./, /\.spec\./, /__tests__/, /test/];

function shouldSkip(path) {
  return SKIP_PATTERNS.some((pattern) => pattern.test(path));
}

function getAllFiles(dir, files = []) {
  try {
    const entries = readdirSync(dir);

    for (const entry of entries) {
      const fullPath = join(dir, entry);

      if (shouldSkip(fullPath)) {
        continue;
      }

      try {
        const stat = statSync(fullPath);

        if (stat.isDirectory()) {
          getAllFiles(fullPath, files);
        } else if (entry.endsWith('.ts') && !entry.endsWith('.d.ts')) {
          files.push(fullPath);
        }
      } catch {
        // Skip files we can't read
      }
    }
  } catch {
    // Directory doesn't exist, skip
  }

  return files;
}

function checkFile(filePath) {
  const content = readFileSync(filePath, 'utf-8');
  const violations = [];

  // Skip if file uses UnitOfWork
  const usesUnitOfWork = UNIT_OF_WORK_PATTERNS.some((pattern) => pattern.test(content));

  // Check for mutations
  for (const pattern of MUTATION_PATTERNS) {
    const matches = content.match(new RegExp(pattern.source, 'g'));

    if (matches && matches.length > 0) {
      // If mutations found but no UnitOfWork, report violation
      if (!usesUnitOfWork) {
        // Check if it's in a route/command file (where UnitOfWork should be used)
        const isRouteOrCommand =
          filePath.includes('/routes/') ||
          filePath.includes('/commands/') ||
          filePath.includes('/api/');

        if (isRouteOrCommand) {
          violations.push({
            file: relative(process.cwd(), filePath),
            pattern: pattern.source,
            count: matches.length,
          });
        }
      }
    }
  }

  return violations;
}

function main() {
  console.log('Checking transaction invariant (UnitOfWork usage)...\n');

  const allViolations = [];

  // Check services only (templates are example code)
  const serviceFiles = getAllFiles(SERVICES_DIR);
  for (const file of serviceFiles) {
    const violations = checkFile(file);
    allViolations.push(...violations);
  }

  // Note: Templates are skipped as they are example code
  // that users can modify as needed

  if (allViolations.length > 0) {
    console.error('Transaction invariant violations found:\n');

    for (const v of allViolations) {
      console.error(`  ${v.file}`);
      console.error(`    - Found ${v.count} mutation(s) without UnitOfWork`);
      console.error(`    - Pattern: ${v.pattern}\n`);
    }

    console.error('\nAll mutations in routes/commands/api must use UnitOfWork to ensure:');
    console.error('  1. Domain changes are atomic with audit logs');
    console.error('  2. Domain changes are atomic with outbox entries');
    console.error('  3. Events are guaranteed to be published\n');

    process.exit(1);
  }

  console.log('Transaction invariant check passed!');
  console.log(`  Checked ${serviceFiles.length} service files`);
}

main();
