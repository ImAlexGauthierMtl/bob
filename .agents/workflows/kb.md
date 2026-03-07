---
description: "Créer un article Knowledge Base pour une feature existante"
---

# /kb — Créer un article Knowledge Base

// turbo-all

## Pré-requis

- Le backend tourne sur `localhost:8555`
- Le frontend tourne sur `localhost:4200`
- Playwright est installé (`npm install playwright --save-dev`)
- Lire `.agents/docs/kb-norms.md` **OBLIGATOIRE avant de rédiger**

---

## Étape 1 — Identifier la feature

Demander à l'utilisateur :

1. **Quelle feature ?** (ex: "Organizations", "Contacts", "Opportunities")
2. **Catégorie KB ?** (ex: "Getting Started", "CRM", "Settings")
3. **Visibilité ?** (`shared` par défaut, `internal` pour admin-only)

---

## Étape 2 — Explorer la feature dans l'app

// turbo
```bash
# Login et naviguer vers la feature via Playwright
node -e "
const { chromium } = require('playwright');
(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page.goto('http://localhost:4200/login', { waitUntil: 'networkidle' });
    await page.fill('#email', 'kb@crootest.com');
    await page.fill('#password', 'TestPass123!');
    await page.click('#login-button');
    await page.waitForURL('**/dashboard', { timeout: 10000 });
    await page.waitForTimeout(2000);
    // Navigate to target feature page
    // ... adapt selectors per feature
    await page.screenshot({ path: '/tmp/kb-explore.png', fullPage: true });
    await browser.close();
})();
"
```

Analyser la page pour identifier :
- Les étapes du flow utilisateur (step-by-step)
- Les champs et leurs descriptions
- Les actions automatiques (Bob AI)
- Les éléments visuels clés à capturer

---

## Étape 3 — Capturer les screenshots

Créer un script Playwright dans `tools/kb-[feature]-screenshots.mjs` :

**Règles screenshots** (voir `.agents/docs/kb-norms.md` §4) :
- 1440×900 viewport
- **Aucune annotation** — screenshots propres uniquement
- Un screenshot par étape du flow
- Sauvegarder dans `frontend/src/assets/kb/screenshots/`
- Nommage : `[feature]-step[N]-[description].png`

// turbo
```bash
node tools/kb-[feature]-screenshots.mjs
```

---

## Étape 4 — Rédiger l'article

**LIRE `.agents/docs/kb-norms.md` AVANT DE RÉDIGER.**

Checklist de conformité :

- [ ] **Bob = AI** — Aucun nom de LLM/technologie (Groq, Serper, LangGraph, etc.)
- [ ] **Exemples métier** — Restauration, hôtellerie, tourisme, minier, manufacturier. JAMAIS de tech
- [ ] **Structure** — Suivre le template de `kb-norms.md` §3
- [ ] **Ton** — Professionnel, concis, orienté action
- [ ] **Pas de jargon** — Écrire pour un utilisateur CRM, pas un développeur
- [ ] **Images** — `![alt text](/assets/kb/screenshots/...)` avec alt text descriptif
- [ ] **Champs** — Format `**Bold** — Description`

---

## Étape 5 — Seed via API

// turbo
```bash
# 1. Login
TOKEN=$(curl -s http://localhost:8555/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"kb@crootest.com","password":"TestPass123!"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2. Get or create category
curl -s http://localhost:8555/api/v1/kb/categories \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 3. Create article
curl -s -X POST http://localhost:8555/api/v1/kb/articles \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "[Article Title]",
    "slug": "[article-slug]",
    "content": "[markdown content]",
    "excerpt": "[1-2 sentence summary]",
    "category_id": "[category UUID]",
    "visibility": "shared",
    "tags": ["tag1", "tag2"],
    "is_featured": false,
    "is_published": true,
    "author_name": "Bob AI",
    "author_role": "AI Knowledge Assistant"
  }'
```

---

## Étape 6 — Vérifier live

// turbo
```bash
# Playwright: naviguer vers l'article et capturer un screenshot
node -e "
const { chromium } = require('playwright');
(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page.goto('http://localhost:4200/login', { waitUntil: 'networkidle' });
    await page.fill('#email', 'kb@crootest.com');
    await page.fill('#password', 'TestPass123!');
    await page.click('#login-button');
    await page.waitForURL('**/dashboard', { timeout: 10000 });
    await page.waitForTimeout(2000);
    await page.locator('a[href=\"/knowledge-base\"]').first().click();
    await page.waitForTimeout(3000);
    await page.locator('a[href*=\"[article-slug]\"]').first().click();
    await page.waitForTimeout(4000);
    await page.screenshot({ path: '/tmp/kb-verify-article.png', fullPage: true });
    console.log(page.url());
    await browser.close();
})();
"
```

Vérifier :
- [ ] Les images s'affichent correctement (pas de liens cassés)
- [ ] Le contenu respecte les normes KB
- [ ] La navigation fonctionne

---

## Étape 7 — Commit

// turbo
```bash
git add -A
git commit -m "[kb] feat: add [feature-name] KB article

- Article: [title]
- Category: [category]
- Screenshots: [N] clean screenshots
- Visibility: shared"
```
