# Template: Service Mapper (Angular)

> Mapping bidirectionnel API DTO ↔ modèle UI.

## Fichier

`core/services/{resource}-mapper.service.ts`

```typescript
import { Injectable } from '@angular/core';

export interface {Resource}ApiDto {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  // Ajouter les champs API (snake_case)
}

export interface {Resource}UiModel {
  id: string;
  name: string;
  createdAt: Date;
  updatedAt: Date;
  displayLabel: string;
  // Ajouter les champs UI enrichis
}

@Injectable({ providedIn: 'root' })
export class {Resource}MapperService {
  toUiModel(dto: {Resource}ApiDto): {Resource}UiModel {
    return {
      id: dto.id,
      name: dto.name,
      createdAt: new Date(dto.created_at),
      updatedAt: new Date(dto.updated_at),
      displayLabel: dto.name,
    };
  }

  toApiDto(model: Partial<{Resource}UiModel>): Partial<{Resource}ApiDto> {
    return {
      name: model.name,
      // Mapper les champs UI → API
    };
  }

  toUiModels(dtos: {Resource}ApiDto[]): {Resource}UiModel[] {
    return dtos.map((dto) => this.toUiModel(dto));
  }
}
```

## Règle : Toujours mapper dans les effects NgRx, jamais dans les composants.
