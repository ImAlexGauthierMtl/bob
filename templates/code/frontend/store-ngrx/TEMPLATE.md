# Template: Store NGRX complet (5 fichiers)

> Recette pour créer un store NGRX avec actions, effects, reducer, selectors, state.
> **Zéro décision** : 5 fichiers à créer avec ce pattern exact.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `RESOURCE` | Nom (PascalCase) | `Review` |
| `resources` | Pluriel (camelCase) | `reviews` |

## Fichiers à créer

```
frontend/src/app/store/{resources}/
├── {resources}.state.ts
├── {resources}.actions.ts
├── {resources}.reducer.ts
├── {resources}.effects.ts
└── {resources}.selectors.ts
```

## 1. `{resources}.state.ts`

```typescript
import { {Resource} } from '../../models/{resource}.model';

export interface {Resources}State {
  items: {Resource}[];
  selectedId: string | null;
  loading: boolean;
  error: string | null;
}

export const initial{Resources}State: {Resources}State = {
  items: [],
  selectedId: null,
  loading: false,
  error: null,
};
```

## 2. `{resources}.actions.ts`

```typescript
import { createAction, props } from '@ngrx/store';
import { {Resource} } from '../../models/{resource}.model';

// Load all
export const load{Resources} = createAction('[{Resources}] Load');
export const load{Resources}Success = createAction('[{Resources}] Load Success', props<{ items: {Resource}[] }>());
export const load{Resources}Failure = createAction('[{Resources}] Load Failure', props<{ error: string }>());

// Load single
export const load{Resource} = createAction('[{Resources}] Load One', props<{ id: string }>());
export const load{Resource}Success = createAction('[{Resources}] Load One Success', props<{ item: {Resource} }>());
export const load{Resource}Failure = createAction('[{Resources}] Load One Failure', props<{ error: string }>());

// Create
export const create{Resource} = createAction('[{Resources}] Create', props<{ dto: Create{Resource}Dto }>());
export const create{Resource}Success = createAction('[{Resources}] Create Success', props<{ item: {Resource} }>());
export const create{Resource}Failure = createAction('[{Resources}] Create Failure', props<{ error: string }>());

// Update
export const update{Resource} = createAction('[{Resources}] Update', props<{ id: string; dto: Update{Resource}Dto }>());
export const update{Resource}Success = createAction('[{Resources}] Update Success', props<{ item: {Resource} }>());
export const update{Resource}Failure = createAction('[{Resources}] Update Failure', props<{ error: string }>());

// Delete
export const delete{Resource} = createAction('[{Resources}] Delete', props<{ id: string }>());
export const delete{Resource}Success = createAction('[{Resources}] Delete Success', props<{ id: string }>());
export const delete{Resource}Failure = createAction('[{Resources}] Delete Failure', props<{ error: string }>());

// Select
export const select{Resource} = createAction('[{Resources}] Select', props<{ id: string | null }>());

// Clear error
export const clear{Resources}Error = createAction('[{Resources}] Clear Error');
```

## 3. `{resources}.reducer.ts`

```typescript
import { createReducer, on } from '@ngrx/store';
import { initial{Resources}State } from './{resources}.state';
import * as Actions from './{resources}.actions';

export const {resources}Reducer = createReducer(
  initial{Resources}State,

  // Load all
  on(Actions.load{Resources}, (state) => ({ ...state, loading: true, error: null })),
  on(Actions.load{Resources}Success, (state, { items }) => ({ ...state, items, loading: false })),
  on(Actions.load{Resources}Failure, (state, { error }) => ({ ...state, loading: false, error })),

  // Create
  on(Actions.create{Resource}Success, (state, { item }) => ({
    ...state, items: [item, ...state.items],
  })),

  // Update
  on(Actions.update{Resource}Success, (state, { item }) => ({
    ...state, items: state.items.map(i => i.id === item.id ? item : i),
  })),

  // Delete
  on(Actions.delete{Resource}Success, (state, { id }) => ({
    ...state, items: state.items.filter(i => i.id !== id),
  })),

  // Select
  on(Actions.select{Resource}, (state, { id }) => ({ ...state, selectedId: id })),

  // Clear error
  on(Actions.clear{Resources}Error, (state) => ({ ...state, error: null })),
);
```

## 4. `{resources}.effects.ts`

```typescript
import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { of } from 'rxjs';
import { map, mergeMap, catchError } from 'rxjs/operators';
import { {Resource}Service } from '../../services/{resource}.service';
import * as {Resources}Actions from './{resources}.actions';

@Injectable()
export class {Resources}Effects {
  private actions$ = inject(Actions);
  private service = inject({Resource}Service);

  load$ = createEffect(() =>
    this.actions$.pipe(
      ofType({Resources}Actions.load{Resources}),
      mergeMap(() =>
        this.service.getAll().pipe(
          map(items => {Resources}Actions.load{Resources}Success({ items })),
          catchError(error => of({Resources}Actions.load{Resources}Failure({ error: error.message })))
        )
      )
    )
  );

  create$ = createEffect(() =>
    this.actions$.pipe(
      ofType({Resources}Actions.create{Resource}),
      mergeMap(({ dto }) =>
        this.service.create(dto).pipe(
          map(item => {Resources}Actions.create{Resource}Success({ item })),
          catchError(error => of({Resources}Actions.create{Resource}Failure({ error: error.message })))
        )
      )
    )
  );

  // update$ et delete$ suivent le même pattern
}
```

## 5. `{resources}.selectors.ts`

```typescript
import { createFeatureSelector, createSelector } from '@ngrx/store';
import { {Resources}State } from './{resources}.state';

export const select{Resources}State = createFeatureSelector<{Resources}State>('{resources}');

export const selectAll{Resources} = createSelector(select{Resources}State, (state) => state.items);
export const select{Resources}Loading = createSelector(select{Resources}State, (state) => state.loading);
export const select{Resources}Error = createSelector(select{Resources}State, (state) => state.error);
export const selectSelected{Resource}Id = createSelector(select{Resources}State, (state) => state.selectedId);
export const selectSelected{Resource} = createSelector(
  selectAll{Resources},
  selectSelected{Resource}Id,
  (items, id) => items.find(i => i.id === id) ?? null
);
```

## Enregistrer le store

Dans `app.config.ts` :
```typescript
provideStore({ {resources}: {resources}Reducer }),
provideEffects({Resources}Effects),
```

## Règles NON-NÉGOCIABLES

1. Actions = triplets Load/Success/Failure (TOUJOURS)
2. Reducer = fonctions pures (jamais de side-effects)
3. Effects = le SEUL endroit qui appelle les services HTTP
4. Selectors = memoïsés avec `createSelector`
5. Pas de state mutation directe (spread operator `...state`)
