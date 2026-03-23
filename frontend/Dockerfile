# ── Dev stage (hot-reload for docker-compose) ──
FROM node:22-alpine AS dev
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
EXPOSE 4200
CMD ["npx", "ng", "serve", "--host", "0.0.0.0", "--port", "4200", "--poll", "2000"]

# ── Production build stage ──
FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npx ng build --configuration=production

# ── Production serve stage ──
FROM nginx:alpine AS production
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
EXPOSE 4700
