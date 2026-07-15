# syntax=docker/dockerfile:1
# Frontend production image — multi-stage build + nginx

# ── Stage 1: build ───────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Build-time API URL (empty = same-origin /api via nginx proxy)
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ── Stage 2: nginx ───────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Drop default site; use our conf
RUN rm -f /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

# Non-root: nginx alpine already has nginx user; ensure perms
RUN chown -R nginx:nginx /usr/share/nginx/html \
    && chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

# Allow nginx master to bind :80 as non-root via net.ipv4... not always available;
# keep default nginx user for port 80 (standard in official image).
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
