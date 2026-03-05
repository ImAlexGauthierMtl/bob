# 🎨 Backlog — Templates Frontend Manquants

> Patterns frontend Angular identifiés dans **ASQ-CRM**, **Madysta ERP**, **Le Baluchon** qui n'ont PAS de template HDQ.
> Chaque entrée = 1 template à créer dans `templates/code/frontend/`.

---

## 🔴 Priorité HAUTE — Bloquants pour tout nouveau projet

### 1. `page-detail` — Page détail avec onglets
- **Pattern** : Page de détail d'une ressource avec navigation par onglets
- **Vu dans** : Madysta `opportunity-detail`, ASQ-CRM `contact`, Baluchon `generic-detail`
- **Fichiers** : `{resource}-detail.component.ts/html/scss/spec.ts`
- **Détails** : Header avec actions, onglets dynamiques, chargement par ID depuis la route, breadcrumb, skeleton loading

### 2. `component-form` — Formulaire create/edit
- **Pattern** : Formulaire réactif Angular avec validation
- **Vu dans** : ASQ-CRM `form/`, Madysta `opportunities-import-modal`
- **Fichiers** : `{resource}-form.component.ts/html/scss/spec.ts`
- **Détails** : ReactiveFormsModule, FormGroup/FormControl, validation sync/async, error messages, submit/cancel

### 3. `auth-guard` — Guard d'authentification
- **Pattern** : CanActivate guard pour routes protégées
- **Vu dans** : Madysta `core/guards/auth.guard.ts`, Baluchon `core/guards/auth.guard.ts`, ASQ-CRM `guards/`
- **Fichiers** : `core/guards/auth.guard.ts`, `core/guards/auth.guard.spec.ts`
- **Détails** : Vérification du token en mémoire, redirect vers /login, guard fonctionnel (nouveau style Angular)

### 4. `guest-guard` — Guard pour routes publiques
- **Pattern** : Guard empêchant l'accès aux pages login/register si déjà authentifié
- **Vu dans** : Madysta `core/guards/guest.guard.ts`, Baluchon `core/guards/public.guard.ts`
- **Fichiers** : `core/guards/guest.guard.ts`, `core/guards/guest.guard.spec.ts`
- **Détails** : Redirect vers dashboard si déjà connecté

### 5. `interceptor-auth` — Intercepteur HTTP d'authentification
- **Pattern** : Injection automatique du Bearer token + auto-refresh sur 401
- **Vu dans** : Madysta `core/interceptors/auth.interceptor.ts`, Baluchon
- **Fichiers** : `core/interceptors/auth.interceptor.ts`, `core/interceptors/auth.interceptor.spec.ts`
- **Détails** : Ajout du header Authorization, interception des 401, refresh token, retry de la requête originale

### 6. `service-auth` — Service d'authentification
- **Pattern** : Service gérant login/logout/register/refresh + stockage token en mémoire
- **Vu dans** : Madysta `core/services/auth.service.ts`, Baluchon `services/authentication.service.ts`, ASQ-CRM `services/`
- **Fichiers** : `core/services/auth.service.ts`, `core/services/auth.service.spec.ts`
- **Détails** : Token en mémoire (pas localStorage), httpOnly cookie pour refresh, BehaviorSubject isAuthenticated

### 7. `layout-main` — Layout principal (header + sidebar + content)
- **Pattern** : Shell layout avec header fixe, sidebar collapsible, zone de contenu
- **Vu dans** : Madysta `layout/`, Baluchon `layouts/main-layout`, ASQ-CRM `components/sidebar` + `components/header`
- **Fichiers** : `layout/main-layout.component.ts/html/scss/spec.ts`
- **Détails** : Router-outlet, sidebar responsive, header avec user menu, toggle sidebar

### 8. `layout-auth` — Layout d'authentification
- **Pattern** : Layout plein écran pour login/register/reset password
- **Vu dans** : Madysta `layout/auth-layout/`
- **Fichiers** : `layout/auth-layout.component.ts/html/scss/spec.ts`
- **Détails** : Centré verticalement, branding, router-outlet pour les pages auth

### 9. `page-login` — Page de login
- **Pattern** : Page de connexion avec formulaire email/password
- **Vu dans** : Tous les projets (ASQ-CRM, Madysta, Baluchon)
- **Fichiers** : `pages/public/login/login.component.ts/html/scss/spec.ts`
- **Détails** : Formulaire réactif, validation, spinner de chargement, gestion d'erreurs, redirection post-login

### 10. `test-frontend-component` — Tests unitaires de composant Angular
- **Pattern** : TestBed setup avec mocks/stubs pour composants
- **Vu dans** : Tous les projets (fichiers `.spec.ts` dans chaque composant)
- **Fichiers** : `{component}.component.spec.ts`
- **Détails** : TestBed.configureTestingModule, provideMockStore, HttpClientTestingModule, fixture.detectChanges

---

## 🟡 Priorité MOYENNE — Patterns récurrents dans 2+ projets

### 11. `component-sidebar` — Sidebar de navigation
- **Pattern** : Navigation latérale avec menu items, groupes, icônes
- **Vu dans** : Madysta `layout/sidebar`, Baluchon `components/sidebar`, ASQ-CRM `components/sidebar`
- **Fichiers** : `layout/sidebar/sidebar.component.ts/html/scss/spec.ts`
- **Détails** : Menu config dynamique, routerLink active, collapse/expand, responsive

### 12. `component-header` — Header applicatif
- **Pattern** : Barre de navigation supérieure avec user info, actions globales
- **Vu dans** : Madysta `layout/header`, Baluchon `components/header`, ASQ-CRM `components/header`
- **Fichiers** : `layout/header/header.component.ts/html/scss/spec.ts`
- **Détails** : User avatar/menu, notifications, search, breadcrumb

### 13. `component-data-table` — Table de données réutilisable
- **Pattern** : Composant table avec tri, filtres, sélection
- **Vu dans** : Baluchon `components/data-table`, Madysta listes
- **Fichiers** : `shared/components/data-table/data-table.component.ts/html/scss`
- **Détails** : Colonnes configurables, tri serveur/client, sélection multiple, actions par ligne

### 14. `component-pagination` — Pagination
- **Pattern** : Composant de pagination réutilisable
- **Vu dans** : Baluchon `components/pagination`
- **Fichiers** : `shared/components/pagination/pagination.component.ts/html/scss`
- **Détails** : Page courante, total, event emitter, configurable items par page

### 15. `component-toolbar` — Barre d'outils (recherche + filtres + actions)
- **Pattern** : Toolbar avec search, filtres, boutons d'actions
- **Vu dans** : Baluchon `components/toolbar`, ASQ-CRM `components/opportunity-toolbar`
- **Fichiers** : `shared/components/toolbar/toolbar.component.ts/html/scss`
- **Détails** : Input search avec debounce, dropdown filtres, boutons create/export/import

### 16. `interceptor-snake-case` — Intercepteur de transformation snake_case
- **Pattern** : Conversion automatique camelCase ↔ snake_case entre front et API
- **Vu dans** : Madysta `core/interceptors/snake-case-response.interceptor.ts`
- **Fichiers** : `core/interceptors/snake-case-response.interceptor.ts`, `.spec.ts`
- **Détails** : Transform response body keys snake_case → camelCase

### 17. `service-mapper` — Service de mapping données
- **Pattern** : Transformation des DTOs API vers les modèles frontend
- **Vu dans** : Madysta `core/services/contact-mapper.service.ts`, `account-mapper.service.ts`, Baluchon `services/mappers/`
- **Fichiers** : `core/services/{resource}-mapper.service.ts`, `.spec.ts`
- **Détails** : Mapping bidirectionnel API model ↔ UI model, transformation des dates, enrichissement

### 18. `service-cookie` — Service de gestion des cookies
- **Pattern** : Abstraction pour lire/écrire/supprimer des cookies
- **Vu dans** : Madysta `core/services/cookie.service.ts`
- **Fichiers** : `core/services/cookie.service.ts`, `.spec.ts`
- **Détails** : Get/set/delete cookie, httpOnly awareness, domain config

### 19. `service-config-runtime` — Service de configuration runtime
- **Pattern** : Chargement de config dynamique depuis l'API ou env
- **Vu dans** : Madysta `core/services/config-runtime.service.ts`, `core/services/config.service.ts`
- **Fichiers** : `core/services/config-runtime.service.ts`, `.spec.ts`
- **Détails** : APP_INITIALIZER, fetch config au bootstrap, injection dans les services

### 20. `model-api` — Modèles API communs (pagination, error, response wrapper)
- **Pattern** : Interfaces génériques pour les réponses API
- **Vu dans** : Madysta `core/models/api.models.ts`, Baluchon `models/`
- **Fichiers** : `core/models/api.models.ts`
- **Détails** : PaginatedResponse<T>, ApiError, ApiResponse<T>, QueryParams

### 21. `component-stat-card` — Carte de statistique (dashboard)
- **Pattern** : Card affichant une métrique avec icône, valeur, tendance
- **Vu dans** : Baluchon `components/stat-card`
- **Fichiers** : `shared/components/stat-card/stat-card.component.ts/html/scss`
- **Détails** : Input: label, value, icon, trend, color

### 22. `page-dashboard` — Page dashboard
- **Pattern** : Page d'accueil avec grille de widgets/stats
- **Vu dans** : Madysta `features/dashboard`, Baluchon
- **Fichiers** : `features/dashboard/dashboard.component.ts/html/scss/spec.ts`
- **Détails** : Grid layout, stat cards, graphiques, données temps réel

### 23. `component-copilot` — Sidebar AI / Copilot
- **Pattern** : Sidebar contextuelle pour assistant IA
- **Vu dans** : ASQ-CRM `components/copilot-sidebar`, Baluchon `components/copilot-sidebar`
- **Fichiers** : `components/copilot-sidebar/copilot-sidebar.component.ts/html/scss`
- **Détails** : Panneau latéral toggle, chat interface, contexte dynamique

---

## 🟢 Priorité BASSE — Patterns spécialisés

### 24. `pipe-sanitize` — Pipe de sanitization HTML
- **Pattern** : Pipe Angular pour sanitizer du contenu HTML
- **Vu dans** : Baluchon `core/pipes/sanitize-html.pipe.ts`
- **Fichiers** : `core/pipes/sanitize-html.pipe.ts`
- **Détails** : DomSanitizer, bypassSecurityTrustHtml

### 25. `directive-file-drop` — Directive drag & drop fichiers
- **Pattern** : Directive pour zone de drop de fichiers
- **Vu dans** : Madysta `shared/directives/csv-file-drop.directive.ts`
- **Fichiers** : `shared/directives/csv-file-drop.directive.ts`, `.spec.ts`
- **Détails** : HostListener dragover/drop, FileList output, validation type/taille

### 26. `component-page-header` — Header de page avec titre + actions
- **Pattern** : En-tête de page avec titre, description, boutons d'actions
- **Vu dans** : Baluchon `components/page-header`
- **Fichiers** : `shared/components/page-header/page-header.component.ts/html/scss`
- **Détails** : Input: title, subtitle, actions. Content projection pour les boutons

### 27. `component-settings-card` — Carte de paramètres
- **Pattern** : Card pour section de paramètres avec toggle/input
- **Vu dans** : Baluchon `components/settings-card`
- **Fichiers** : `shared/components/settings-card/settings-card.component.ts/html/scss`
- **Détails** : Titre, description, contenu projeté (formulaires, toggles)

### 28. `routing-config` — Configuration de routing Angular
- **Pattern** : Lazy loading, route guards, nested routes
- **Vu dans** : Tous les projets
- **Fichiers** : `app.routes.ts`, `features/{module}/{module}.routes.ts`
- **Détails** : loadComponent, canActivate guards, layout routes, redirect

### 29. `store-feature-ngrx` — Store NgRx pour feature module (B4F pattern)
- **Pattern** : Store dédié aux features composées (appels B4F)
- **Vu dans** : Madysta `store/opportunities/`, Baluchon `store/front-office/`
- **Fichiers** : `store/{feature}/actions.ts`, `effects.ts`, `reducer.ts`, `selectors.ts`, `state.ts`
- **Détails** : Actions composées (load + transform), effets avec service B4F, selectors avec createFeatureSelector

---

## 📊 Résumé

| Priorité | Nombre | Templates |
|----------|--------|-----------|
| 🔴 HAUTE | 10 | page-detail, component-form, auth-guard, guest-guard, interceptor-auth, service-auth, layout-main, layout-auth, page-login, test-frontend-component |
| 🟡 MOYENNE | 13 | component-sidebar, component-header, component-data-table, component-pagination, component-toolbar, interceptor-snake-case, service-mapper, service-cookie, service-config-runtime, model-api, component-stat-card, page-dashboard, component-copilot |
| 🟢 BASSE | 6 | pipe-sanitize, directive-file-drop, component-page-header, component-settings-card, routing-config, store-feature-ngrx |
| **Total** | **29** | |
