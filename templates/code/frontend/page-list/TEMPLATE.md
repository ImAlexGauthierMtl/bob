# Template: Page Liste Angular

> Recette pour créer une page liste avec toolbar, table, loading/error, pagination.
> **Zéro décision** : structure identique pour toutes les listes.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `RESOURCE` | Nom (PascalCase) | `Account` |
| `resources` | Pluriel | `accounts` |
| `LABEL_SINGULAR` | Label FR | `Compte` |
| `LABEL_PLURAL` | Label FR | `Comptes` |
| `COLUMNS` | Colonnes à afficher | `name, industry, phone, city, status` |
| `ICON` | Icône Font Awesome | `fa-building` |

## Fichier à créer

`frontend/src/app/pages/authenticated/{resources}/{resources}.page.ts`

## Structure du template HTML (exactement dans cet ordre)

```html
<div class="flex flex-col h-full">
  <!-- 1. TOOLBAR (h-10, bg-white, border-b) -->
  <div class="bg-white border-b border-dynamics-border px-2 py-1 flex items-center justify-between shrink-0 h-10 shadow-sm">
    <!-- Bouton Nouveau + Filtrer + Rafraîchir -->
  </div>

  <!-- 2. CONTENT (flex-1, overflow-y-auto, bg-gray-50, p-4) -->
  <div class="flex-1 overflow-y-auto bg-gray-50 p-4">
    <!-- 2a. Breadcrumb + titre -->
    <!-- 2b. @if (loading) { spinner } -->
    <!-- 2c. @if (error) { error banner avec Réessayer } -->
    <!-- 2d. @if (!loading) { table card } -->
  </div>
</div>
```

## Structure de la table

```html
<div class="bg-white border border-gray-200 rounded-sm shadow-sm">
  <!-- Header : titre + compteur + recherche + boutons -->
  <div class="p-4 border-b border-gray-200 flex items-center justify-between">
    <h2>Mes {label_plural} actifs ({{ items.length }})</h2>
    <input type="text" placeholder="Rechercher...">
  </div>

  <!-- Table -->
  <table class="w-full text-sm">
    <thead class="bg-gray-50 border-b border-gray-200">
      <tr>
        <th><!-- checkbox --></th>
        <!-- une th par COLUMN -->
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      @for (item of items; track item.id) {
        <tr class="hover:bg-gray-50">...</tr>
      }
      @if (items.length === 0 && !loading) {
        <!-- empty state avec icône + bouton créer -->
      }
    </tbody>
  </table>

  <!-- Footer : pagination -->
</div>
```

## Classe du composant

```typescript
@Component({
  selector: 'app-{resources}-page',
  standalone: true,
  template: `...`,
})
export class {Resources}Page implements OnInit {
  private service = inject({Resource}Service);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  items: {Resource}[] = [];
  loading = true;
  error = '';

  ngOnInit(): void {
    this.loadItems();
  }

  loadItems(): void {
    this.loading = true;
    this.error = '';
    this.service.getAll().subscribe({
      next: (items) => {
        this.items = items;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = 'Impossible de charger les {label_plural}.';
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
  }

  openItem(id: string): void {
    this.router.navigate(['/{resources}', id]);
  }

  createItem(): void {
    this.router.navigate(['/{resources}/new']);
  }

  deleteItem(item: {Resource}): void {
    // confirm dialog → service.delete → filter list
  }
}
```

## Route à ajouter

Dans `app.routes.ts` :
```typescript
{ path: '{resources}', component: {Resources}Page },
{ path: '{resources}/new', component: {Resource}DetailPage },
{ path: '{resources}/:id', component: {Resource}DetailPage },
```

## Règles NON-NÉGOCIABLES

1. `standalone: true` — toujours
2. `inject()` — jamais constructor injection
3. Loading state avec spinner — TOUJOURS
4. Error state avec bouton Réessayer — TOUJOURS
5. Empty state avec icône + bouton créer — TOUJOURS
6. `track item.id` dans `@for` — TOUJOURS
7. Labels UI en français
8. Noms de cliques = verb (`openItem`, `createItem`, `deleteItem`)
