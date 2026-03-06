# Template: Tests Unitaires de Composant (Angular)

> Recette pour créer les tests unitaires d'un composant Angular avec TestBed.
> **Zéro décision** : suivre exactement ce pattern.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `COMPONENT` | Nom du composant (PascalCase) | `OpportunityDetail` |
| `component` | Nom (kebab-case) | `opportunity-detail` |

## Fichier à créer

`{component}/{component}.component.spec.ts`

## Code exact

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

import { provideMockStore, MockStore } from '@ngrx/store/testing';

import { {Component}Component } from './{component}.component';

describe('{Component}Component', () => {
  let component: {Component}Component;
  let fixture: ComponentFixture<{Component}Component>;
  let store: MockStore;

  const initialState = {
    // Définir l'état initial du store ici
    auth: { user: null, accessToken: null, loading: false, error: null },
    {resources}: { items: [], selectedItem: null, loading: false, error: null },
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [{Component}Component],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        provideMockStore({ initialState }),
      ],
    }).compileComponents();

    store = TestBed.inject(MockStore);
    fixture = TestBed.createComponent({Component}Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should render title', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    // Adapter selon le composant
    expect(compiled.querySelector('h1')?.textContent).toBeTruthy();
  });

  describe('initialization', () => {
    it('should subscribe to store on init', () => {
      spyOn(store, 'select').and.callThrough();
      component.ngOnInit();
      expect(store.select).toHaveBeenCalled();
    });
  });

  describe('user interactions', () => {
    it('should handle button click', () => {
      // Adapter selon le composant
      spyOn(component, 'onSubmit' as never);
      const button = fixture.nativeElement.querySelector('button[type="submit"]');
      if (button) {
        button.click();
        // expect(component.onSubmit).toHaveBeenCalled();
      }
    });
  });

  describe('store dispatching', () => {
    it('should dispatch action on submit', () => {
      spyOn(store, 'dispatch');
      // Adapter selon le composant
      // component.onSubmit();
      // expect(store.dispatch).toHaveBeenCalledWith(jasmine.objectContaining({ type: '...' }));
    });
  });

  afterEach(() => {
    fixture.destroy();
  });
});
```

## Règles NON-NÉGOCIABLES

1. `provideMockStore` pour le store NgRx — jamais de vrai store
2. `provideHttpClientTesting` — jamais de vrais appels HTTP
3. `provideRouter([])` pour le routing — routes vides pour l'isolation
4. `fixture.detectChanges()` dans le `beforeEach`
5. `fixture.destroy()` dans le `afterEach`
6. Tester : création, rendu, interactions utilisateur, dispatching store
7. `standalone: true` → composant importé directement dans `TestBed.configureTestingModule`

## Pattern pour les composants avec Input/Output

```typescript
it('should emit event on action', () => {
  spyOn(component.submitForm, 'emit');
  component.onSubmit();
  expect(component.submitForm.emit).toHaveBeenCalled();
});
```
