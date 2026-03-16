# Docker Best Practices

## Multi-Stage Builds

```dockerfile
# Stage 1: Dependencies (cached)
FROM node:20-slim AS deps
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

# Stage 2: Build
FROM deps AS build
COPY . .
RUN bun run build

# Stage 3: Production (minimal image)
FROM node:20-slim AS production
ENV NODE_ENV=production
COPY --from=build /app/dist ./dist
COPY --from=deps /app/node_modules ./node_modules
USER nonroot
EXPOSE 3000
CMD ["node", "dist/main.js"]
```

## Bun Multi-Stage Build

```dockerfile
# Stage 1: Dependencies (cached)
FROM oven/bun:1 AS deps
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

# Stage 2: Build
FROM deps AS build
WORKDIR /app
COPY . .
RUN bun run build

# Stage 3: Production (minimal image)
FROM oven/bun:1-slim AS production
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/dist ./dist
COPY --from=deps /app/node_modules ./node_modules
USER bun
EXPOSE 3000
CMD ["bun", "dist/main.js"]
```

## Key Rules

- Pin base image versions (e.g., `node:20.11-slim`, not `node:latest`)
- Use `.dockerignore` to exclude `.git`, `node_modules`, `tests`, `.env`
- Install dependencies first for layer caching
- Use `--frozen-lockfile` for deterministic builds
- Run as non-root user in production
- Use `slim` or `alpine` base images for smaller size
- Set `NODE_ENV=production` in production stage

## Docker Compose for Development

```yaml
services:
  app:
    build: .
    ports: ["3000:3000"]
    volumes: ["./src:/app/src"]  # Hot reload
    env_file: .env
    depends_on:
      postgres: { condition: service_healthy }

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: app
      POSTGRES_PASSWORD: postgres
    healthcheck:
      test: ["CMD-ARGS", "pg_isready"]
```

## Security

- Scan images for vulnerabilities (`docker scout`)
- Don't store secrets in images (use env vars or secrets manager)
- Use read-only root filesystem where possible

## Container Isolation

### Seccomp Profiles

Use a restrictive seccomp profile to limit system calls:

```json
// custom-seccomp.json — deny dangerous syscalls
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": ["SCMP_ARCH_X86_64"],
  "syscalls": [
    { "names": ["read", "write", "open", "close", "stat", "fstat", "mmap", "mprotect", "munmap", "brk", "access", "pipe", "select", "sched_yield", "clone", "execve", "exit", "wait4", "kill", "uname", "fcntl", "flock", "fsync", "ftruncate", "getcwd", "chdir", "rename", "mkdir", "rmdir", "link", "unlink", "chmod", "chown", "lseek", "getpid", "getuid", "getgid", "geteuid", "getegid", "getppid", "setpgid", "getpgrp", "setsid", "getgroups", "setgroups", "socket", "connect", "accept", "sendto", "recvfrom", "bind", "listen", "getsockname", "getpeername", "socketpair", "setsockopt", "getsockopt", "epoll_create", "epoll_ctl", "epoll_wait", "dup", "dup2", "nanosleep", "getitimer", "alarm", "setitimer", "arch_prctl", "set_tid_address", "set_robust_list", "futex", "clock_gettime", "clock_getres", "exit_group", "tgkill", "openat", "newfstatat", "readlinkat", "getrandom", "prlimit64", "epoll_create1", "eventfd2", "pipe2", "dup3", "accept4"],
      "action": "SCMP_ACT_ALLOW" }
  ]
}
```

```bash
docker run --security-opt seccomp=custom-seccomp.json myapp
```

### AppArmor

For Linux production hosts, use an AppArmor profile:

```bash
# Load a custom profile
sudo apparmor_parser -r /etc/apparmor.d/docker-myapp
docker run --security-opt apparmor=docker-myapp myapp
```

### Key isolation rules

- Drop all capabilities, then add only what's needed: `--cap-drop=ALL --cap-add=NET_BIND_SERVICE`
- Use `--read-only` for the root filesystem, mount writable volumes only where needed
- Set memory and CPU limits: `--memory=512m --cpus=1.0`
- Use `--no-new-privileges` to prevent privilege escalation
- Run as non-root (already covered in multi-stage builds above)
- Use separate networks per service group: `docker network create --internal backend`
- In Kubernetes, use `securityContext.runAsNonRoot: true` and `readOnlyRootFilesystem: true`
