# Template: Environment Config + Proxy Angular

> Recette pour configurer les environnements Angular et le proxy dev.

## Fichiers à créer

### 1. `src/environments/environment.ts` (dev)

```typescript
export const environment = {
  production: false,
  apiBaseUrl: '/api',
  authApiUrl: '/api/v1/auth',
};
```

### 2. `src/environments/environment.prod.ts`

```typescript
export const environment = {
  production: true,
  apiBaseUrl: 'https://api.{domain}.com',
  authApiUrl: 'https://api.{domain}.com/v1/auth',
};
```

### 3. `proxy.conf.json` (dev server proxy)

```json
{
  "/api/v1/auth": {
    "target": "http://localhost:8001",
    "secure": false,
    "changeOrigin": true,
    "pathRewrite": { "^/api/v1/auth": "/api/v1/auth" }
  },
  "/api/v1/clients": {
    "target": "http://localhost:8002",
    "secure": false,
    "changeOrigin": true
  }
}
```

### 4. Ajouter dans `angular.json`

```json
"serve": {
  "options": {
    "proxyConfig": "proxy.conf.json"
  }
}
```

### 5. `core/services/config-runtime.service.ts`

```typescript
import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ConfigRuntimeService {
  getAuthApiUrl(): string {
    return environment.authApiUrl;
  }

  getApiBaseUrl(): string {
    return environment.apiBaseUrl;
  }

  isProduction(): boolean {
    return environment.production;
  }
}
```

## Règles NON-NÉGOCIABLES

1. Proxy en dev pour éviter les problèmes CORS
2. URL complètes en production (pas de proxy)
3. `ConfigRuntimeService` comme abstraction — jamais d'import d'`environment` direct dans les services
4. Un endpoint proxy par API backend
