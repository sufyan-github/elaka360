# Elaka360 API image (NestJS). Build from the repository root:
#   docker build -f apps/api/Dockerfile -t elaka360-api .
# Runs on Render (render.yaml) or any container host; configure with the variables in docs/ENVIRONMENT.md.

FROM node:22.23.2-bookworm-slim AS build
ENV PNPM_HOME=/pnpm PATH=/pnpm:$PATH CI=true
RUN corepack enable
WORKDIR /repo
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages/shared/package.json packages/shared/
COPY apps/api/package.json apps/api/
RUN pnpm install --frozen-lockfile --filter @elaka360/api...
COPY tsconfig*.json ./
COPY packages/shared packages/shared
COPY apps/api apps/api
RUN pnpm --filter @elaka360/shared build && pnpm --filter @elaka360/api build \
 && pnpm --filter @elaka360/api deploy --legacy --prod /out

FROM node:22.23.2-bookworm-slim
ENV NODE_ENV=production PORT=4000
# psql runs the migrations (Render pre-deploy command) and the one-time seed load
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build --chown=node:node /out ./
COPY --chown=node:node db/migrations db/migrations
COPY --chown=node:node db/seed/seed.sql db/seed/seed.sql
COPY --chown=node:node scripts/db-migrate.sh scripts/db-seed-once.sh scripts/
USER node
EXPOSE 4000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD node -e "fetch('http://127.0.0.1:'+process.env.PORT+'/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "dist/main.js"]
