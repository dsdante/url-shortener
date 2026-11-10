FROM node:22-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY tsconfig.json vite.config.ts index.html ./
COPY src ./src
RUN npm run build

# Tiny runtime image: copies the built assets into the shared volume on
# `docker compose up`. The container exits 0 when done; nginx waits for it
# via `depends_on: condition: service_completed_successfully`.
FROM alpine:3.20
COPY --from=build /app/dist /ui
CMD ["sh", "-c", "cp -a /ui/. /out/ && echo 'ui-build: assets copied'"]