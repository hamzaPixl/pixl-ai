import {
  metrics,
  type Meter,
  type Counter,
  type Histogram,
  type UpDownCounter,
  type ObservableGauge,
} from '@opentelemetry/api';
import { MeterProvider, PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { Resource } from '@opentelemetry/resources';
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION } from '@opentelemetry/semantic-conventions';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http';

export interface MetricsConfig {
  serviceName: string;
  serviceVersion?: string;
  environment?: string;
  endpoint?: string;
  enabled?: boolean;
  exportIntervalMs?: number;
}

let meterProvider: MeterProvider | null = null;

export function initMetrics(config: MetricsConfig): void {
  if (!config.enabled) {
    return;
  }

  const resource = new Resource({
    [ATTR_SERVICE_NAME]: config.serviceName,
    [ATTR_SERVICE_VERSION]: config.serviceVersion ?? '0.0.0',
    'deployment.environment': config.environment ?? 'development',
  });

  const metricExporter = config.endpoint
    ? new OTLPMetricExporter({ url: `${config.endpoint}/v1/metrics` })
    : undefined;

  const metricReader = metricExporter
    ? new PeriodicExportingMetricReader({
        exporter: metricExporter,
        exportIntervalMillis: config.exportIntervalMs ?? 60000,
      })
    : undefined;

  meterProvider = new MeterProvider({
    resource,
    readers: metricReader ? [metricReader] : [],
  });

  metrics.setGlobalMeterProvider(meterProvider);
}

export async function shutdownMetrics(): Promise<void> {
  if (meterProvider) {
    await meterProvider.shutdown();
    meterProvider = null;
  }
}

export function getMeter(name: string, version?: string): Meter {
  return metrics.getMeter(name, version);
}

export interface AppMetrics {
  httpRequestsTotal: Counter;
  httpRequestDuration: Histogram;
  httpActiveRequests: UpDownCounter;
  dbQueryDuration: Histogram;
  dbConnectionsActive: ObservableGauge;
  eventsPublished: Counter;
  eventsProcessed: Counter;
  jobsQueued: Counter;
  jobsProcessed: Counter;
  jobsFailed: Counter;
}

export function createAppMetrics(meter: Meter): AppMetrics {
  return {
    httpRequestsTotal: meter.createCounter('http_requests_total', {
      description: 'Total number of HTTP requests',
    }),
    httpRequestDuration: meter.createHistogram('http_request_duration_ms', {
      description: 'HTTP request duration in milliseconds',
      unit: 'ms',
    }),
    httpActiveRequests: meter.createUpDownCounter('http_active_requests', {
      description: 'Number of active HTTP requests',
    }),
    dbQueryDuration: meter.createHistogram('db_query_duration_ms', {
      description: 'Database query duration in milliseconds',
      unit: 'ms',
    }),
    dbConnectionsActive: meter.createObservableGauge('db_connections_active', {
      description: 'Number of active database connections',
    }),
    eventsPublished: meter.createCounter('events_published_total', {
      description: 'Total number of events published',
    }),
    eventsProcessed: meter.createCounter('events_processed_total', {
      description: 'Total number of events processed',
    }),
    jobsQueued: meter.createCounter('jobs_queued_total', {
      description: 'Total number of jobs queued',
    }),
    jobsProcessed: meter.createCounter('jobs_processed_total', {
      description: 'Total number of jobs processed',
    }),
    jobsFailed: meter.createCounter('jobs_failed_total', {
      description: 'Total number of failed jobs',
    }),
  };
}

// Re-export OpenTelemetry types
export { metrics };
export type { Meter, Counter, Histogram, UpDownCounter, ObservableGauge };
