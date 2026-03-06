# Template: Modèle TypeScript (Interface + DTOs)

> Recette pour créer l'interface TypeScript d'une ressource.
> **Zéro décision** : miroir exact du schema Pydantic Response.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `RESOURCE` | Nom (PascalCase) | `Account` |
| `FIELDS` | Champs du schema Pydantic Response | copier |
| `STATUSES` | Enum de statuts (si existent) | `AccountStatus` |

## Fichier à créer

`frontend/src/app/models/{resource}.model.ts`

## Code exact

```typescript
// 1. Type union pour les enums (pas d'enum TS, utiliser type union)
export type {Resource}Status = '{VALUE_1}' | '{VALUE_2}' | '{VALUE_3}';

// 2. Interface principale — miroir exact du {Resource}Response Pydantic
export interface {Resource} {
  id: string;
  name: string;                    // champs obligatoires = string
  description: string;             // champs texte = string (pas string | null)
  status: {Resource}Status;
  parent_id: string | null;        // FK = string | null
  parent_name: string | null;      // champs enrichis = string | null
  created_at: string;              // dates = string (ISO)
  updated_at: string;
}

// 3. DTO de création — champs obligatoires requis, reste optional
export interface Create{Resource}Dto {
  name: string;                    // champs requis dans Pydantic = obligatoire
  description?: string;            // champs avec défaut dans Pydantic = optional
  status?: {Resource}Status;
  parent_id?: string | null;
}

// 4. DTO de mise à jour — tout optional (Partial)
export type Update{Resource}Dto = Partial<Create{Resource}Dto>;
```

## Règles NON-NÉGOCIABLES

1. Enums = type union `'VALUE_1' | 'VALUE_2'` (pas `enum`)
2. Dates = `string` (ISO format, pas `Date`)
3. FK optionnelles = `string | null`
4. Pas de `any` (TypeScript strict mode)
5. Interface = miroir du Pydantic Response (mêmes noms)
6. `UpdateDto = Partial<CreateDto>` (toujours)
