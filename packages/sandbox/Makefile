.PHONY: dev deploy typecheck test-e2e docker-build docker-test setup build-wheel help

setup:
	npm install

build-wheel: ## Build pixl wheels into docker/dist/ for Docker image
	cd ../.. && uv build --package pixl-engine --wheel --out-dir packages/sandbox/docker/dist
	cd ../.. && uv build --package pixl-cli --wheel --out-dir packages/sandbox/docker/dist

dev: build-wheel
	npx wrangler dev

deploy:
	npx wrangler deploy

typecheck:
	npx tsc --noEmit

test-e2e:
	bash scripts/test-e2e.sh

docker-build: build-wheel
	docker build -t pixl-sandbox docker/

docker-test: docker-build
	docker run --rm pixl-sandbox bash -c "pixl --version && claude --version"

help:
	@echo "make setup          Install dependencies"
	@echo "make build-wheel    Build pixl wheels for Docker image"
	@echo "make dev            Run local dev server (builds wheels first)"
	@echo "make deploy         Deploy to Cloudflare"
	@echo "make typecheck      Run TypeScript type checks"
	@echo "make test-e2e       Run end-to-end tests"
	@echo "make docker-build   Build sandbox Docker image"
	@echo "make docker-test    Build and smoke-test Docker image"
