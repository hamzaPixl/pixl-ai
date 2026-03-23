FROM docker.io/cloudflare/sandbox:0.7.18

# Python 3.12 via deadsnakes PPA (pixl needs >=3.12)
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.12 python3.12-venv python3.12-dev && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    rm -rf /var/lib/apt/lists/*

# uv (Python package manager) — pinned version
RUN curl -LsSf https://astral.sh/uv/0.6.0/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# pixl — install from local wheels (dev) or PyPI (prod)
# Dev: `make dev` builds wheels automatically before starting wrangler
# Prod: replace with `RUN uv tool install pixl==<version>`
COPY dist/*.whl /tmp/pixl-wheels/
RUN uv tool install --find-links /tmp/pixl-wheels pixl-cli && \
    ln -sf /root/.local/bin/pixl /usr/local/bin/pixl && \
    rm -rf /tmp/pixl-wheels

# Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code@latest

# Command timeout for long workflows (5 minutes)
ENV COMMAND_TIMEOUT_MS=300000

# Init script + test workflow
COPY init.sh /usr/local/bin/pixl-init.sh
COPY test-workflow.yaml /opt/pixl/test-workflow.yaml
RUN chmod +x /usr/local/bin/pixl-init.sh

RUN mkdir -p /workspace/.pixl/sessions /workspace/.pixl/workflows
EXPOSE 3000
WORKDIR /workspace
