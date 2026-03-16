export {
  initTracing,
  shutdownTracing,
  getTracer,
  withSpan,
  addSpanAttributes,
  recordSpanEvent,
  getCurrentTraceId,
  getCurrentSpanId,
  trace,
  context,
  SpanKind,
  SpanStatusCode,
} from './tracing';
export type { TracingConfig, Span, Tracer } from './tracing';

export {
  initMetrics,
  shutdownMetrics,
  getMeter,
  createAppMetrics,
  metrics,
} from './metrics';
export type {
  MetricsConfig,
  AppMetrics,
  Meter,
  Counter,
  Histogram,
  UpDownCounter,
  ObservableGauge,
} from './metrics';

export {
  registerObservabilityHooks,
  healthHandler,
  createReadinessHandler,
} from './fastify';
export type { ObservabilityPluginOptions, ReadinessChecker } from './fastify';

export { createPrismaMiddleware, logPrismaQuery } from './prisma';
export type { PrismaQueryEvent } from './prisma';

export interface ObservabilityConfig {
  serviceName: string;
  serviceVersion?: string;
  environment?: string;
  otelEndpoint?: string;
  tracingEnabled?: boolean;
  metricsEnabled?: boolean;
}

export async function initObservability(config: ObservabilityConfig): Promise<void> {
  const { initTracing } = await import('./tracing');
  const { initMetrics } = await import('./metrics');

  initTracing({
    serviceName: config.serviceName,
    serviceVersion: config.serviceVersion,
    environment: config.environment,
    endpoint: config.otelEndpoint,
    enabled: config.tracingEnabled ?? true,
  });

  initMetrics({
    serviceName: config.serviceName,
    serviceVersion: config.serviceVersion,
    environment: config.environment,
    endpoint: config.otelEndpoint,
    enabled: config.metricsEnabled ?? true,
  });
}

export async function shutdownObservability(): Promise<void> {
  const { shutdownTracing } = await import('./tracing');
  const { shutdownMetrics } = await import('./metrics');

  await Promise.all([shutdownTracing(), shutdownMetrics()]);
}
