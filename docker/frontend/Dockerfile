FROM node:20-alpine AS base
WORKDIR /app

# ============================================================
# Development target — dependencies only, source via volume
# ============================================================
FROM base AS development
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# ============================================================
# Builder — production Next.js build
# ============================================================
FROM node:20-slim AS builder
WORKDIR /app

# Install system deps required by some npm native packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 make g++ \
    && rm -rf /var/lib/apt/lists/*

# Build-time env vars (baked into static assets)
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_APP_NAME=Kaasb

ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_APP_NAME=${NEXT_PUBLIC_APP_NAME}

COPY package.json package-lock.json* ./
RUN npm ci --legacy-peer-deps
COPY . .
RUN npm run build

# ============================================================
# Production target — minimal standalone image, non-root user
# ============================================================
FROM node:20-alpine AS production

RUN addgroup -S kaasb && adduser -S kaasb -G kaasb

WORKDIR /app

# Copy only the standalone output — everything else is excluded
COPY --from=builder --chown=kaasb:kaasb /app/.next/standalone ./
COPY --from=builder --chown=kaasb:kaasb /app/.next/static ./.next/static
COPY --from=builder --chown=kaasb:kaasb /app/public ./public

USER kaasb

ENV PORT=3000
ENV HOSTNAME=0.0.0.0
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD node -e "require('http').get('http://localhost:3000/',r=>process.exit(r.statusCode<500?0:1)).on('error',()=>process.exit(1))"

CMD ["node", "server.js"]
