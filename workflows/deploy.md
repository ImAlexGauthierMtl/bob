---
description: "Déployer les changements vers le pipeline CI/CD (dev, staging ou prod)"
---

# /deploy — Workflow de Déploiement

// turbo-all

> [!CAUTION]
> **RÈGLES FONDAMENTALES**
> 1. Le déploiement passe **toujours** par le pipeline CI/CD — jamais en direct
> 2. Vérifier les healthchecks après chaque déploiement
> 3. Les migrations s'exécutent **avant** le déploiement de l'API

## Pré-requis

Lire `.agents/context/projet.md` pour identifier :
- L'URL du pipeline CI/CD
- Les environnements disponibles (dev, staging, prod)
- Les URLs de healthcheck

## Étapes — Déploiement Dev

1. Vérifier les changements non commités
```bash
git status
```

2. Exécuter tous les tests
```bash
# Adapter selon le projet
python -m pytest tests/ -v --cov 2>&1 | tail -20
```

3. Pousser sur la branche de développement
```bash
git push origin $(git branch --show-current)
```

4. Vérifier le pipeline CI/CD (URL depuis context/projet.md)

5. Vérifier les healthchecks après déploiement

## Étapes — Déploiement Staging

1. Merger via Merge Request sur la branche principale
2. Déclencher manuellement le job de staging dans le pipeline
3. Vérifier les healthchecks staging

## Étapes — Déploiement Prod

1. Créer et pousser un tag sémantique
```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

2. Déclencher manuellement le job de production
3. Vérifier les healthchecks production

## Checklist pré-déploiement

```
[ ] Tests passent à 100%
[ ] Commit sémantique avec préfixe [service]
[ ] Migrations à jour si changement de schema
[ ] Variables CI/CD configurées pour l'environnement cible
[ ] Pas de secrets dans le code
```
