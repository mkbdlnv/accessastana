# ---- build stage: compile the SPA ----
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Leave VITE_API_BASE unset so the bundle calls "/api", which nginx proxies.
RUN npm run build

# ---- serve stage: static files + reverse proxy to the API ----
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
