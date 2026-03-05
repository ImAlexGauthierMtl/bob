# Template: Formulaire Create/Edit (Angular)

> Recette pour créer un formulaire réactif avec validation.
> **Zéro décision** : suivre exactement ce pattern.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `RESOURCE` | Nom (PascalCase) | `Client` |
| `resource` | Nom (kebab-case) | `client` |
| `FIELDS` | Champs du formulaire | `[{name: 'name', type: 'text', required: true}]` |

## Fichier à créer

`features/{resources}/{resource}-form/{resource}-form.component.ts`

```typescript
import { Component, OnInit, OnDestroy, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';

import { {Resource} } from '../../../core/models/{resource}.models';

@Component({
  selector: 'app-{resource}-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
      <!-- Champ: Nom -->
      <div class="form-group">
        <label for="name">Nom <span class="required">*</span></label>
        <input
          id="name"
          type="text"
          formControlName="name"
          placeholder="Ex: Mon {resource}"
          [class.invalid]="isInvalid('name')"
        />
        @if (isInvalid('name')) {
          <span class="error">
            @if (form.get('name')?.errors?.['required']) { Ce champ est requis }
            @if (form.get('name')?.errors?.['maxlength']) { Maximum 255 caractères }
          </span>
        }
      </div>

      <!-- Champ: Description (optionnel) -->
      <div class="form-group">
        <label for="description">Description</label>
        <textarea
          id="description"
          formControlName="description"
          rows="3"
          placeholder="Description..."
        ></textarea>
      </div>

      <!-- Champ: Email (optionnel) -->
      <div class="form-group">
        <label for="email">Email</label>
        <input
          id="email"
          type="email"
          formControlName="email"
          placeholder="contact@example.com"
          [class.invalid]="isInvalid('email')"
        />
        @if (isInvalid('email') && form.get('email')?.errors?.['email']) {
          <span class="error">Format d'email invalide</span>
        }
      </div>

      <!-- Champ: Status (select) -->
      <div class="form-group">
        <label for="status">Statut</label>
        <select id="status" formControlName="status">
          <option value="active">Actif</option>
          <option value="inactive">Inactif</option>
        </select>
      </div>

      <!-- Actions -->
      <div class="form-actions">
        <button type="button" class="btn btn--secondary" (click)="onCancel()">
          Annuler
        </button>
        <button
          type="submit"
          class="btn btn--primary"
          [disabled]="form.invalid || submitting"
        >
          @if (submitting) {
            <span class="spinner"></span> Enregistrement...
          } @else {
            {{ isEdit ? 'Mettre à jour' : 'Créer' }}
          }
        </button>
      </div>
    </form>
  `,
  styleUrl: './{resource}-form.component.scss',
})
export class {Resource}FormComponent implements OnInit {
  @Input() {resource}: {Resource} | null = null;  // null = create mode, object = edit mode
  @Input() submitting = false;
  @Output() submitForm = new EventEmitter<Partial<{Resource}>>();
  @Output() cancel = new EventEmitter<void>();

  form!: FormGroup;

  get isEdit(): boolean {
    return !!this.{resource};
  }

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    this.form = this.fb.group({
      name: [this.{resource}?.name ?? '', [Validators.required, Validators.maxLength(255)]],
      description: [this.{resource}?.description ?? ''],
      email: [this.{resource}?.email ?? '', [Validators.email]],
      status: [this.{resource}?.status ?? 'active'],
      // Ajouter les champs selon FIELDS
    });
  }

  isInvalid(field: string): boolean {
    const control = this.form.get(field);
    return !!(control?.invalid && control?.touched);
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitForm.emit(this.form.value);
  }

  onCancel(): void {
    this.cancel.emit();
  }
}
```

## SCSS

```scss
form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 600px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;

  label {
    font-size: 14px;
    font-weight: 500;
    color: #374151;
  }

  .required {
    color: #ef4444;
  }

  input, textarea, select {
    padding: 10px 14px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 14px;
    transition: border-color 0.2s;

    &:focus {
      outline: none;
      border-color: var(--primary, #4f46e5);
      box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
    }

    &.invalid {
      border-color: #ef4444;
    }
  }

  textarea {
    resize: vertical;
    min-height: 80px;
  }
}

.error {
  font-size: 12px;
  color: #ef4444;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}
```

## Utilisation (dans un composant parent)

```typescript
<app-{resource}-form
  [{resource}]="{resource}"
  [submitting]="(submitting$ | async) ?? false"
  (submitForm)="onSubmit($event)"
  (cancel)="goBack()"
/>
```

## Règles NON-NÉGOCIABLES

1. `ReactiveFormsModule` — jamais template-driven
2. `@Input()` pour le mode edit (pré-remplir), `null` pour le mode create
3. `@Output()` pour submitForm et cancel — le parent gère le dispatch
4. `markAllAsTouched()` si soumission invalide
5. `Validators.required` et `Validators.maxLength` minimum
6. Bouton disabled pendant `submitting`
7. Erreurs affichées uniquement après `touched`
