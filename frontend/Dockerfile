# --- build the React app ---
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci
COPY tsconfig.json vite.config.ts index.html ./
COPY src ./src
RUN npm run build

# --- serve it with nginx, proxying /api to the backend ---
FROM nginx:1.27-alpine
ENV BACKEND_URL=http://backend:8000 \
    ADMIN_TOKEN=""
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8501
HEALTHCHECK --interval=15s --timeout=3s CMD wget -qO- http://127.0.0.1:8501/ >/dev/null || exit 1
