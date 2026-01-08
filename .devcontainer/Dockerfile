FROM python:3.11-slim

# ---- System deps (git/curl + common libs for tooling & Playwright) ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates bash \
    # Playwright / Chromium common deps (minimal-ish set)
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libpango-1.0-0 \
    libgtk-3-0 libx11-xcb1 libxshmfence1 \
 && rm -rf /var/lib/apt/lists/*

# ---- Python tooling ----
RUN python -m pip install --no-cache-dir uv

# ---- Create vscode user (matches Dev Containers convention) ----
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
 && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/bash

# ---- Install Node via nvm (pin exact version) ----
ENV NVM_DIR=/usr/local/nvm
ENV NODE_VERSION=24.12.0

RUN mkdir -p $NVM_DIR \
 && curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash \
 && . "$NVM_DIR/nvm.sh" \
 && nvm install ${NODE_VERSION} \
 && nvm alias default ${NODE_VERSION} \
 && nvm use default \
 && corepack enable

# Ensure node/npm/pnpm/yarn available for all shells
ENV PATH="$NVM_DIR/versions/node/v${NODE_VERSION}/bin:${PATH}"

# ---- Workspace dir ----
RUN mkdir -p /workspaces/Ivyhousetw-META \
 && chown -R $USERNAME:$USERNAME /workspaces

USER $USERNAME
WORKDIR /workspaces/Ivyhousetw-META

# NOTE: No pip install / npm install here by design (manual + auditable)
