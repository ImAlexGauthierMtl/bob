# Template: Nginx Config Frontend

> Configuration nginx pour servir le frontend Angular en production.

## `frontend/nginx.conf`

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript image/svg+xml;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA fallback — toutes les routes vers index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy vers les APIs backend
    location /api/v1/auth {
        proxy_pass http://auth-api:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Ajouter un bloc par API backend
    # location /api/v1/{resources} {
    #     proxy_pass http://{resource}-backend-api:8002;
    #     proxy_set_header Host $host;
    #     proxy_set_header X-Real-IP $remote_addr;
    # }

    # Désactiver l'accès aux fichiers cachés
    location ~ /\. { deny all; }
}
```

## `frontend/Dockerfile` (production)

```dockerfile
# Build
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npx ng build --configuration=production

# Serve
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/{project-name}/browser /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Règles : gzip, cache 1y sur assets, SPA fallback, proxy_pass vers APIs.
