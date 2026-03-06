# Template: Service HTTP Angular

> Recette pour créer un service CRUD HttpClient.
> **Zéro décision** : 5 méthodes standard.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `RESOURCE` | Nom (PascalCase) | `Account` |
| `resources` | Pluriel (kebab ou snake) | `accounts` |

## Fichier à créer

`frontend/src/app/services/{resource}.service.ts`

## Code exact

```typescript
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { {Resource}, Create{Resource}Dto, Update{Resource}Dto } from '../models/{resource}.model';

@Injectable({ providedIn: 'root' })
export class {Resource}Service {
  private http = inject(HttpClient);
  private readonly API = environment.apiUrl;

  getAll(): Observable<{Resource}[]> {
    return this.http.get<{Resource}[]>(`${this.API}/{resources}`);
  }

  getById(id: string): Observable<{Resource}> {
    return this.http.get<{Resource}>(`${this.API}/{resources}/${id}`);
  }

  create(dto: Create{Resource}Dto): Observable<{Resource}> {
    return this.http.post<{Resource}>(`${this.API}/{resources}`, dto);
  }

  update(id: string, dto: Update{Resource}Dto): Observable<{Resource}> {
    return this.http.put<{Resource}>(`${this.API}/{resources}/${id}`, dto);
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.API}/{resources}/${id}`);
  }
}
```

## Règles NON-NÉGOCIABLES

1. `inject(HttpClient)` — pas de constructor injection
2. `Injectable({ providedIn: 'root' })` — toujours root
3. `environment.apiUrl` — jamais d'URL hardcodée
4. Méthodes typées avec generics `this.http.get<Type>()`
5. Retourne `Observable<T>` — jamais de `.subscribe()` dans le service
6. Nommage : `getAll()`, `getById()`, `create()`, `update()`, `delete()`
