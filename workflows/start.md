---
description: "Point d'entrée unique — Intake intelligent + sync framework + route HDQ"
---

# /start — Point d'Entrée Unique

// turbo-all

> **RÈGLE** : Toute demande de travail commence par `/start`. Sans exception.

---

## Étape 0 — Synchroniser le framework HDQ

Mettre à jour le framework depuis le repo central :

```bash
git -C ~/Dev/framework/framework-hdq pull --ff-only 2>&1 || echo "⚠️ Pull échoué — utilisation de la version locale"
```

Puis synchroniser vers le projet courant (si .agents/ existe et n'est pas le framework lui-même) :

```bash
if [ -d ".agents" ] && [ "$(git -C . remote get-url origin 2>/dev/null)" != "git@gitlab.tools.thesmartcrew.com:alexandre/framework-hdq.git" ]; then
  rsync -a --exclude='context/projet.md' --exclude='decisions/' --exclude='docs/gaps.md' --exclude='docs/dette-technique.md' --exclude='.git' ~/Dev/framework/framework-hdq/ .agents/
  echo "✅ Framework HDQ synchronisé"
fi
```

---

## Étape 1 — Charger le contexte projet

Lire silencieusement (ne pas afficher le contenu, juste l'intégrer au contexte) :

1. `.agents/context/projet.md` — Ω:CONTEXT du projet
2. `.agents/decisions/decisions.md` — ADR actives
3. `.agents/docs/gaps.md` — gaps connus

Si `context/projet.md` n'existe pas, en informer l'utilisateur et proposer de le créer avec `/nouveau-projet`.

---

## Étape 2 — Questionnaire d'intake

Poser ces questions à l'utilisateur. Adapter selon le contexte, ne poser que les questions pertinentes :

| # | Question |
|---|----------|
| 1 | **Quoi ?** Décris ce que tu veux accomplir en une phrase |
| 2 | **Source ?** Ticket Zoho, besoin client, dette technique, idée ? |
| 3 | **Où ?** Quel(s) service(s) ou module(s) sont touchés ? |
| 4 | **Taille ?** Estimation rapide : S (< 1h), M (1-4h), L (> 4h) |
| 5 | **Contraintes ?** Deadline, dépendances, risques connus ? |

---

## Étape 3 — Classifier la demande

Basé sur les réponses, déterminer la branche enfant :

| Si la source est... | Déclencher |
|---------------------|-----------|
| Un ticket Zoho | → `/zoho` (fetch ticket + pièces jointes + analyse) |
| Un nouveau projet from scratch | → `/nouveau-projet` (bootstrap complet) |
| Un nouveau module dans un projet existant | → `/nouveau-module` (backend + frontend) |
| De l'exploration, R&D, ou une décision archi | → `/nouveau-ingenierie` (recherche structurée) |

---

## Étape 4 — Rule-Gap Analysis

**OBLIGATOIRE avant toute action.**

Pour chaque action identifiée dans la demande :

1. Scanner `.agents/rules/`, `.agents/normes/`, `.agents/skills/`
2. Classifier chaque action :

### ✅ RULED — Règle/template/skill existe
- Citer la source exacte (fichier + section)
- L'action sera exécutée selon la règle

### ⚠️ UNRULED — Pas de règle trouvée
- Signaler explicitement à l'utilisateur
- Expliquer ce que le LLM va faire PAR LUI-MÊME (sa propre logique)
- Logger dans `.agents/docs/gaps.md` :

```markdown
| [DATE_ISO] | [TICKET/SOURCE] | [DESCRIPTION DU GAP] | [TYPE: skill/norme/rule] | [PRIORITÉ] | [ ] |
```

---

## Étape 5 — Annoncer la route HDQ

Présenter à l'utilisateur :

```
📋 Route HDQ
├── Type : [FEATURE / FIX / REFACTOR / EXPLORE / DEPLOY]
├── Source : [Zoho #XXX / Nouveau / R&D]
│
├── Actions RULED ✅
│   ├── [action] → source: [fichier]
│   └── ...
│
├── Actions UNRULED ⚠️
│   ├── [action] → raison: [pas de template]
│   └── ...
│
├── Workflow principal : [/implante / /delta / ...]
├── Sub-workflows : [/overview × N, /consolidation]
├── Skills : [backend-python, testing, ...]
└── Estimation : [N étapes]
```

---

## Étape 6 — Approbation

Demander : **« Cette route te convient ? »**

- **OUI** → Déclencher le workflow principal (branche enfant)
- **AJUSTER** → Modifier la route selon le feedback
- **ANNULER** → Arrêter
