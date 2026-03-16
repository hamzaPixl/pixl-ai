# Deployment Guide

This guide covers deploying SaaS Studio services in production.

## Prerequisites

- Node.js 20+
- PostgreSQL 15+
- Redis 7+
- NATS 2.9+ (optional, for event bus)
- Docker (optional)

## Environment Configuration

### Required Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@host:5432/database

# Authentication
JWT_SECRET=your-super-secret-key-min-32-chars
JWT_EXPIRES_IN=1h
JWT_REFRESH_EXPIRES_IN=7d

# Logging
LOG_LEVEL=info
NODE_ENV=production
```

### Optional Environment Variables

```env
# Redis (for jobs/caching)
REDIS_URL=redis://localhost:6379

# NATS (for events)
NATS_URL=nats://localhost:4222

# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=saas-studio

# CORS
CORS_ORIGINS=https://app.example.com,https://admin.example.com

# Rate Limiting
RATE_LIMIT_MAX=100
RATE_LIMIT_WINDOW=1m
```

## Build for Production

```bash
# Install dependencies
pnpm install --frozen-lockfile

# Build all packages
pnpm build

# Run type checks
pnpm typecheck

# Run tests
pnpm test
```

## Database Setup

### Generate Prisma Client

```bash
# For each service
cd services/media && pnpm db:generate
cd services/form && pnpm db:generate
cd services/mail && pnpm db:generate
cd services/pdf && pnpm db:generate
```

### Run Migrations

```bash
# For each service
cd services/media && pnpm db:migrate
cd services/form && pnpm db:migrate
cd services/mail && pnpm db:migrate
cd services/pdf && pnpm db:migrate
```

## Docker Deployment

### Dockerfile (per service)

```dockerfile
FROM node:20-slim AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

FROM base AS build
WORKDIR /app
COPY pnpm-lock.yaml ./
COPY pnpm-workspace.yaml ./
COPY package.json ./
COPY turbo.json ./
COPY tsconfig.base.json ./
COPY foundation ./foundation
COPY services/media ./services/media

RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile
RUN pnpm turbo build --filter=@saas-studio/media-service

FROM base AS production
WORKDIR /app
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/services/media/dist ./dist
COPY --from=build /app/services/media/package.json ./package.json

USER node
EXPOSE 3001
CMD ["node", "dist/main.js"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: saas
      POSTGRES_PASSWORD: password
      POSTGRES_DB: saas_studio
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  nats:
    image: nats:2.9-alpine
    ports:
      - "4222:4222"
      - "8222:8222"

  media-service:
    build:
      context: .
      dockerfile: services/media/Dockerfile
    environment:
      - DATABASE_URL=postgresql://saas:password@postgres:5432/saas_studio
      - JWT_SECRET=${JWT_SECRET}
      - REDIS_URL=redis://redis:6379
      - NATS_URL=nats://nats:4222
    ports:
      - "3001:3001"
    depends_on:
      - postgres
      - redis
      - nats

  form-service:
    build:
      context: .
      dockerfile: services/form/Dockerfile
    environment:
      - DATABASE_URL=postgresql://saas:password@postgres:5432/saas_studio
      - JWT_SECRET=${JWT_SECRET}
      - REDIS_URL=redis://redis:6379
      - NATS_URL=nats://nats:4222
    ports:
      - "3002:3002"
    depends_on:
      - postgres
      - redis
      - nats

  mail-service:
    build:
      context: .
      dockerfile: services/mail/Dockerfile
    environment:
      - DATABASE_URL=postgresql://saas:password@postgres:5432/saas_studio
      - JWT_SECRET=${JWT_SECRET}
      - REDIS_URL=redis://redis:6379
      - NATS_URL=nats://nats:4222
    ports:
      - "3003:3003"
    depends_on:
      - postgres
      - redis
      - nats

  pdf-service:
    build:
      context: .
      dockerfile: services/pdf/Dockerfile
    environment:
      - DATABASE_URL=postgresql://saas:password@postgres:5432/saas_studio
      - JWT_SECRET=${JWT_SECRET}
      - REDIS_URL=redis://redis:6379
      - NATS_URL=nats://nats:4222
    ports:
      - "3004:3004"
    depends_on:
      - postgres
      - redis
      - nats

volumes:
  postgres_data:
```

## Kubernetes Deployment

### Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: media-service
  labels:
    app: media-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: media-service
  template:
    metadata:
      labels:
        app: media-service
    spec:
      containers:
        - name: media-service
          image: your-registry/media-service:latest
          ports:
            - containerPort: 3001
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: saas-secrets
                  key: database-url
            - name: JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: saas-secrets
                  key: jwt-secret
          livenessProbe:
            httpGet:
              path: /health
              port: 3001
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 3001
            initialDelaySeconds: 5
            periodSeconds: 5
          resources:
            limits:
              cpu: "500m"
              memory: "512Mi"
            requests:
              cpu: "100m"
              memory: "128Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: media-service
spec:
  selector:
    app: media-service
  ports:
    - port: 80
      targetPort: 3001
  type: ClusterIP
```

### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: saas-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - api.example.com
      secretName: api-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /media
            pathType: Prefix
            backend:
              service:
                name: media-service
                port:
                  number: 80
          - path: /forms
            pathType: Prefix
            backend:
              service:
                name: form-service
                port:
                  number: 80
          - path: /mail
            pathType: Prefix
            backend:
              service:
                name: mail-service
                port:
                  number: 80
          - path: /pdf
            pathType: Prefix
            backend:
              service:
                name: pdf-service
                port:
                  number: 80
```

## Monitoring

### Health Checks

All services expose:

- `GET /health` - Liveness probe
- `GET /ready` - Readiness probe

### OpenTelemetry

Configure OTEL exporter to send traces to your observability platform:

```env
OTEL_EXPORTER_OTLP_ENDPOINT=https://otel-collector.example.com:4318
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer your-token
OTEL_SERVICE_NAME=media-service
OTEL_RESOURCE_ATTRIBUTES=environment=production,version=1.0.0
```

### Logging

Logs are output in JSON format to stdout:

```json
{
  "level": "info",
  "time": "2024-01-15T10:30:00.000Z",
  "msg": "Request completed",
  "service": "media-service",
  "tenantId": "tenant-123",
  "correlationId": "req-456",
  "method": "GET",
  "path": "/media",
  "statusCode": 200,
  "duration": 45
}
```

## Scaling

### Horizontal Scaling

Services are stateless and can be horizontally scaled:

```bash
# Docker Compose
docker-compose up --scale media-service=3

# Kubernetes
kubectl scale deployment media-service --replicas=5
```

### Database Connection Pooling

Configure connection pooling for high-traffic scenarios:

```env
DATABASE_URL=postgresql://user:pass@host:5432/db?connection_limit=20&pool_timeout=10
```

### Redis Cluster

For high availability, use Redis Cluster:

```env
REDIS_URL=redis://node1:6379,node2:6379,node3:6379
```

## Security Checklist

- [ ] Use strong JWT secret (min 32 characters)
- [ ] Enable HTTPS/TLS in production
- [ ] Configure CORS with specific origins
- [ ] Set rate limiting
- [ ] Use secrets management (Vault, AWS Secrets Manager)
- [ ] Enable database connection encryption
- [ ] Configure network policies (Kubernetes)
- [ ] Regular security updates

## Backup & Recovery

### Database Backup

```bash
# PostgreSQL backup
pg_dump -h host -U user -d database > backup.sql

# Restore
psql -h host -U user -d database < backup.sql
```

### Disaster Recovery

1. Maintain database replicas
2. Regular automated backups
3. Test restore procedures
4. Document recovery steps
