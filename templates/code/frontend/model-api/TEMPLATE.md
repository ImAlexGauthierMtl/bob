# Template: Modèles API Communs (Angular)

> Interfaces génériques pour les réponses API.

## Fichier à créer

`core/models/api.models.ts`

```typescript
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface ApiError {
  error: string;
  details?: string;
  requestId?: string;
}

export interface QueryParams {
  page?: number;
  pageSize?: number;
  search?: string;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  [key: string]: string | number | boolean | undefined;
}

export interface BaseEntity {
  id: string;
  createdAt: string;
  updatedAt: string;
}

export interface AuditableEntity extends BaseEntity {
  createdBy?: string;
  updatedBy?: string;
  version: number;
}

export interface SoftDeletableEntity extends AuditableEntity {
  isDeleted: boolean;
  deletedAt?: string;
  deletedBy?: string;
  deletedReason?: string;
}
```

## Règles NON-NÉGOCIABLES

1. Toutes les entités héritent de `BaseEntity`
2. `PaginatedResponse<T>` pour toutes les listes
3. Propriétés en camelCase (convertis par l'intercepteur)
4. Dates en `string` (ISO 8601)
