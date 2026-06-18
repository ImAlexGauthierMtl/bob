# Audit frontend NGRX v1.4

Date: 2026-06-18
Projet: Croo Digital Experience (`app-cde-dev-01`)
Source: `docs/regles-architecture-deploiement.md`, sections 3 et 14

## Synthese

Le frontend ne contenait aucun store NGRX au debut de l'audit. Cette passe ajoute une fondation NGRX exploitable et testee localement:

- `@ngrx/store`, `@ngrx/effects`, `@ngrx/store-devtools`
- `provideStore`, `provideEffects`, `provideStoreDevtools` dans `app.config.ts`
- feature state par B4F: `auth`, `crm`, `communication`, `aiAgent`, `platform`, `kb`
- effects HTTP pour les endpoints B4F composes ajoutes pendant la conversion:
  - CRM: `/dashboard/summary`
  - KB: `/kb/home`
  - Communication: `/integrations/overview`
  - Platform: `/overview`
- services Angular de niveau B4F pour ces compositions:
  - `CrmB4fService`
  - `KbB4fService`
  - `CommunicationB4fService`
  - `PlatformB4fService`
- E2E local Playwright:
  - `frontend/playwright.config.ts`
  - `frontend/e2e/smoke.spec.ts`
  - `frontend/.husky/pre-commit`
  - wrapper racine `run_frontend_e2e.sh` valide

## Limites restantes

Le frontend legacy n'est pas encore completement migre vers le modele strict "actions -> effects -> services -> B4F". Plusieurs pages continuent d'appeler directement des services Angular et quelques composants injectent encore `HttpClient` directement. Cette passe installe le chemin de migration et couvre les nouvelles compositions B4F, mais ne reecrit pas toute l'application.

Exemples de reliquats a traiter dans une passe dediee:

```bash
rg -n "HttpClient|\\.subscribe\\(" frontend/src/app -g '*.ts'
```

La commande retourne encore des composants/pages legacy, notamment dans les pages CRM, settings, inbox, KB et usage.

## Validations locales

```bash
npm run build
./run_frontend_e2e.sh --project=chromium
```

Resultats:

- `npm run build`: OK, avec warnings Angular existants sur optional chaining, imports inutilises, budgets CSS et dependances CommonJS.
- `run_frontend_e2e.sh --project=chromium`: OK, 1 test passed.

## Statut par regle

| Regle | Statut | Preuve |
|---|---|---|
| F-01 service Angular par B4F | OK partiel | Services B4F ajoutes pour les compositions; services legacy par entite conserves comme support |
| F-02 feature NGRX par B4F | OK | `frontend/src/app/store/{auth,crm,communication,ai-agent,platform,kb}` |
| F-03 aucun HTTP hors Effects | VIOLATION | Migration legacy incomplete; les nouvelles compositions passent par Effects |
| F-04 templates async | VIOLATION | Plusieurs pages utilisent encore subscriptions/signals locaux; pas de migration globale dans cette passe |
| F-06 Playwright E2E | OK | `frontend/e2e/smoke.spec.ts` et `frontend/playwright.config.ts` |
| F-08 hook pre-commit smoke E2E | OK | `frontend/.husky/pre-commit` lance `npm run e2e -- --project=chromium` |
