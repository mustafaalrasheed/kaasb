FROM node:20-alpine AS base
WORKDIR /app

# === Development target ===
FROM base AS development
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# === Build target ===
FROM base AS builder
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# === Production target ===
FROM base AS production

RUN addgroup -S kaasb && adduser -S kaasb -G kaasb

COPY --from=builder --chown=kaasb:kaasb /app/.next/standalone ./
COPY --from=builder --chown=kaasb:kaasb /app/.next/static ./.next/static
COPY --from=builder --chown=kaasb:kaasb /app/public ./public

USER kaasb
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
ENV NEXT_TELEMETRY_DISABLED=1

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
