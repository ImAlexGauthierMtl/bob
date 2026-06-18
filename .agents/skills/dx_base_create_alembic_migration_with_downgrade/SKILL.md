---
name: dx_base_create_alembic_migration_with_downgrade
description: Génère une nouvelle révision Alembic avec upgrade ET downgrade obligatoire. Refuse de générer une migration où downgrade serait vide.
metadata:
  reference: § 2.7.5
---

# dx_base_create_alembic_migration_with_downgrade

## Actions
1. `alembic revision -m "<description>"` pour scaffold
2. Implémenter `upgrade()` avec les `op.X(...)` requis
3. Implémenter `downgrade()` **symétrique** :
   - Inverser chaque op dans l'ordre inverse de déclaration
   - Pour les renames : downgrade rename back
   - Pour les drops : downgrade recréer (et documenter la perte de données via commentaire `# IRREVERSIBLE` si applicable)

## Refus
- Refuser de finaliser la migration si `downgrade()` est vide ou contient seulement `pass`/`NotImplementedError`
- Refuser de mettre un `op.execute()` avec du SQL brut si une fonction Alembic équivalente existe
