# Install Bun on node:20-slim (oven-sh/bun image unavailable without Docker Hub auth in some environments).

FROM node:20-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates unzip \
    && curl -fsSL https://bun.sh/install | bash \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.bun/bin:${PATH}"
WORKDIR /app

ARG PUBLIC_BACKEND_URL=http://localhost:5998
ENV PUBLIC_BACKEND_URL=$PUBLIC_BACKEND_URL

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .
RUN bun run build

FROM node:20-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates unzip \
    && curl -fsSL https://bun.sh/install | bash \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.bun/bin:${PATH}"
WORKDIR /app

COPY --from=builder /app/build ./build
COPY --from=builder /app/node_modules ./node_modules
COPY package.json bun.lock ./

EXPOSE 5999
ENV PORT=5999
ENV HOST=0.0.0.0

CMD ["bun", "run", "build/index.js"]
