---
name: dx_base_create_enforce_uniform_api_structure
description: Aligne une API divergente sur la structure canonique uniforme (domain/application/infrastructure/presentation + fichiers standards). Déplace le code mal placé sans changer son comportement.
metadata:
  reference: § 12.1 + § 12.2
---

# dx_base_create_enforce_uniform_api_structure

## Actions
1. Comparer la structure de l'API cible à la structure canonique (§ 12.2)
2. Créer les couches/dossiers manquants
3. Déplacer les fichiers mal rangés vers la bonne couche (routes → presentation, repos → infrastructure/persistence, etc.)
4. Vérifier avec `dx_base_check_apis_uniform_structure` et `import-linter`

## Refus
- Refuser de laisser deux APIs du même projet avec des structures différentes
- Refuser d'introduire un `Service`/`Manager` fourre-tout en route de la migration
