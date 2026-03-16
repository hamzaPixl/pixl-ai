# CI/CD Patterns

## Pipeline Stages

```
lint → typecheck → test → architecture-check → build → deploy-staging → deploy-production
```

### Stage Details

1. **Lint** — Biome/ESLint, fail fast on style issues
2. **Typecheck** — `tsc --noEmit`, catch type errors early
3. **Test** — Unit + integration tests with coverage
4. **Architecture** — `check:transactions` fitness function
5. **Build** — Compile and bundle
6. **Deploy staging** — Automatic on main branch merge
7. **Deploy production** — Manual approval gate

## GitHub Actions Pattern

```yaml
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: oven-sh/setup-bun@v2
      - run: bun install --frozen-lockfile
      - run: bun run lint
      - run: bun run typecheck
      - run: bun run test
      - run: bun run check:transactions

  build:
    needs: quality
    runs-on: ubuntu-latest
    steps:
      - run: bun run build
```

## Cloud Run Deployment

```yaml
deploy:
  needs: build
  runs-on: ubuntu-latest
  steps:
    - uses: google-github-actions/auth@v2
    - uses: google-github-actions/deploy-cloudrun@v2
      with:
        service: ${{ env.SERVICE_NAME }}
        region: europe-west1
        image: gcr.io/${{ env.PROJECT_ID }}/${{ env.SERVICE_NAME }}
```

## Caching

- Cache `node_modules` or `bun.lock` hash for faster installs
- Cache Docker layers in CI
- Cache turbo build artifacts for monorepos
