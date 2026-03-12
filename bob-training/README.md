# Bob Training — Playwright Testing & BCC Workflow

## Playwright Navigation

> **N'utilisez JAMAIS `page.goto()` après le login.** Ça déclenche un full page reload, Angular re-bootstrap, et l'auth guard efface le token JWT.

Utilisez **`playwright-helper.js`** pour toute navigation:

```js
const { login, navigateTo, openBob, sendBobMessage, screenshot } = require('./playwright-helper');

const ok = await login(page);                              // form login
await navigateTo(page, '/settings/bob-control-center');    // SPA-safe (2 hops)
await navigateTo(page, '/dashboard');                       // retour au dashboard
await openBob(page);                                        // ouvre le panel Bob
await sendBobMessage(page, 'Je veux une opportunité');      // envoie un message
await screenshot(page, 'mon_screenshot');                   // capture d'écran
```

### Routes disponibles

| Route | Description |
|-------|-------------|
| `/dashboard` | Overview |
| `/organizations` | Liste des organisations |
| `/contacts` | Liste des contacts |
| `/opportunities` | Liste des opportunités |
| `/tasks` | Activities |
| `/analytics` | BI / Analytics |
| `/team` | Équipe |
| `/settings` | Paramètres |
| `/settings/bob-control-center` | BCC (2 hops) |
| `/knowledge-base` | Base de connaissances |

---

## Create Opportunity Wizard

Le workflow `create_prospect` est contrôlé par le BCC, pas le LLM.

### Steps

| # | Action | Artifact |
|---|--------|----------|
| 1 | "Je veux une nouvelle opportunité" | Carte vide, demande le nom |
| 2 | User tape le nom | Carte avec nom, demande org |
| 3 | "existante" → liste numérotée | Carte avec résultats |
| 4 | User sélectionne par # | ✅ Carte complète (Créé) |

### Resume Handlers (backend)

| Handler | Key |
|---------|-----|
| Capturer nom | `prospect_ask_name` |
| Choisir org | `prospect_ask_org` |
| Créer nouvelle org | `prospect_create_org_name` |
| Sélectionner org existante | `prospect_org_selected` |

---

## Exécution des tests

```bash
# BCC + Bob Wizard
cd frontend && node test-bcc-wizard.js

# Captures Zoho
cd frontend && node capture.js
```

## Déploiement backend

```bash
docker compose build api --no-cache
docker compose up -d api
```

> ⚠️ `docker restart` ne prend PAS les changements de code (pas de volume mount).
