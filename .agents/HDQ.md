# How Do I... (HDQ) — Framework

> Point d'entrée principal. Toute session IA commence ici.
> **Taper `/start` pour démarrer.**

---

## Architecture du framework

```
                        /start
                           │
              ┌────────────┼──────────────┐
              ▼            ▼              ▼
           /zoho    /nouveau-module  /nouveau-projet
              │            │              │
              ▼            ▼              ▼
         ┌─────────────────────────────────────┐
         │  Rule-Gap Analysis                  │
         │  ✅ RULED → appliquer               │
         │  ⚠️ UNRULED → signaler + gaps.md    │
         └──────────────────┬──────────────────┘
                            ▼
         ┌─────────────────────────────────────┐
         │  /implante (boucle par étape)       │
         │  Code → Test → /overview → Commit   │
         └──────────────────┬──────────────────┘
                            ▼
                     /consolidation
```

## Commandes disponibles

| Commande | Usage |
|----------|-------|
| `/start` | **Point d'entrée unique** — intake, classification, route HDQ |
| `/zoho` | Fetch ticket Zoho + pièces jointes + analyse vision |
| `/nouveau-projet` | Bootstrap un projet complet avec .agents/ |
| `/nouveau-module` | Ajouter un module backend + frontend |
| `/nouveau-ingenierie` | Travail exploratoire / R&D |
| `/implante` | Implémentation structurée avec checkpoints |
| `/delta` | Forcer un arrêt Δ-point (vérification profonde) |
| `/overview` | Vue d'altitude Ω₁-Ω₅ |
| `/big` | Décision architecturale (thèse/antithèse/synthèse) |
| `/consolidation` | Clôture (walkthrough, dette, conformité) |
| `/deploy` | Déploiement CI/CD |

## Fichiers projet à personnaliser

Après installation, personnaliser ces fichiers :

| Fichier | Action |
|---------|--------|
| `context/projet.md` | Copier le template, remplir identité projet |
| `decisions/decisions.md` | Initialiser le journal ADR |
| `docs/gaps.md` | Se remplit automatiquement via /start |

## Conventions

- **Commits** : `[service] type: description`
- **Coverage** : 100% obligatoire
- **Langue** : Code en anglais, UI en français
- **Secrets** : Jamais dans le code
