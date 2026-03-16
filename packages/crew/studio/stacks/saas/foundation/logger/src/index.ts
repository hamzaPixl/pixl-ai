import pino, { type Logger as PinoLogger, type LoggerOptions } from 'pino';

export type LogLevel = 'trace' | 'debug' | 'info' | 'warn' | 'error' | 'fatal';

export interface LoggerContext {
  correlationId?: string;
  tenantId?: string;
  userId?: string;
  serviceName?: string;
  requestId?: string;
  [key: string]: unknown;
}

export interface ILogger {
  trace(msg: string, data?: Record<string, unknown>): void;
  debug(msg: string, data?: Record<string, unknown>): void;
  info(msg: string, data?: Record<string, unknown>): void;
  warn(msg: string, data?: Record<string, unknown>): void;
  error(msg: string, data?: Record<string, unknown>): void;
  fatal(msg: string, data?: Record<string, unknown>): void;
  child(context: LoggerContext): ILogger;
}

export class Logger implements ILogger {
  private readonly pino: PinoLogger;

  constructor(pino: PinoLogger) {
    this.pino = pino;
  }

  trace(msg: string, data?: Record<string, unknown>): void {
    if (data) {
      this.pino.trace(data, msg);
    } else {
      this.pino.trace(msg);
    }
  }

  debug(msg: string, data?: Record<string, unknown>): void {
    if (data) {
      this.pino.debug(data, msg);
    } else {
      this.pino.debug(msg);
    }
  }

  info(msg: string, data?: Record<string, unknown>): void {
    if (data) {
      this.pino.info(data, msg);
    } else {
      this.pino.info(msg);
    }
  }

  warn(msg: string, data?: Record<string, unknown>): void {
    if (data) {
      this.pino.warn(data, msg);
    } else {
      this.pino.warn(msg);
    }
  }

  error(msg: string, data?: Record<string, unknown>): void {
    if (data) {
      this.pino.error(data, msg);
    } else {
      this.pino.error(msg);
    }
  }

  fatal(msg: string, data?: Record<string, unknown>): void {
    if (data) {
      this.pino.fatal(data, msg);
    } else {
      this.pino.fatal(msg);
    }
  }

  child(context: LoggerContext): ILogger {
    return new Logger(this.pino.child(context));
  }

  getPino(): PinoLogger {
    return this.pino;
  }
}

export interface LoggerConfig {
  level?: LogLevel;
  serviceName: string;
  serviceVersion?: string;
  environment?: string;
  pretty?: boolean;
  redact?: string[];
}

export function createLogger(config: LoggerConfig): Logger {
  const options: LoggerOptions = {
    level: config.level ?? 'info',
    base: {
      service: config.serviceName,
      version: config.serviceVersion ?? '0.0.0',
      env: config.environment ?? 'development',
    },
    timestamp: pino.stdTimeFunctions.isoTime,
    formatters: {
      level: (label) => ({ level: label }),
    },
    redact: config.redact ?? [
      'password',
      'token',
      'accessToken',
      'refreshToken',
      'authorization',
      'cookie',
      'secret',
      'apiKey',
      '*.password',
      '*.token',
      '*.secret',
    ],
  };

  const transport = config.pretty
    ? {
        target: 'pino-pretty',
        options: {
          colorize: true,
          translateTime: 'SYS:standard',
          ignore: 'pid,hostname',
        },
      }
    : undefined;

  const pinoLogger = transport ? pino(options, pino.transport(transport)) : pino(options);

  return new Logger(pinoLogger);
}

export function createRequestLogger(
  logger: Logger,
  context: {
    correlationId?: string;
    tenantId?: string;
    userId?: string;
    method?: string;
    path?: string;
  },
): Logger {
  return logger.child({
    correlationId: context.correlationId,
    tenantId: context.tenantId,
    userId: context.userId,
    request:
      context.method && context.path ? { method: context.method, path: context.path } : undefined,
  }) as Logger;
}

export function logError(logger: ILogger, error: unknown, message?: string): void {
  if (error instanceof Error) {
    logger.error(message ?? error.message, {
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack,
      },
    });
  } else {
    logger.error(message ?? 'Unknown error', { error });
  }
}

export function createNoopLogger(): ILogger {
  const noop = (): void => {};
  return {
    trace: noop,
    debug: noop,
    info: noop,
    warn: noop,
    error: noop,
    fatal: noop,
    child: () => createNoopLogger(),
  };
}

// Re-export Pino types for convenience
export type { PinoLogger, LoggerOptions };
