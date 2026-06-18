---
name: dx_base_check_alembic_downgrade_symmetric
description: Vérifie que chaque opération op.X dans upgrade() a une opération inverse dans downgrade() (create_table↔drop_table, add_column↔drop_column, create_index↔drop_index).
metadata:
  reference: § 2.7.5
---

# dx_base_check_alembic_downgrade_symmetric

## Règle
Le downgrade doit être symétrique. Pour chaque op dans upgrade, l'inverse doit apparaître dans downgrade.

## Mapping inverse
| upgrade | downgrade attendu |
|---|---|
| `op.create_table('X')` | `op.drop_table('X')` |
| `op.add_column('X', ...)` | `op.drop_column('X', ...)` |
| `op.create_index('X', ...)` | `op.drop_index('X', ...)` |
| `op.execute("CREATE SCHEMA X")` | `op.execute("DROP SCHEMA X CASCADE")` |
| `op.bulk_insert(...)` | `op.execute("DELETE FROM ... WHERE ...")` |

## Actions
Pour chaque migration, extraire les `op.X(...)` de chaque section et vérifier la correspondance :
```python
# Pseudo-code de check (à implémenter en Python dans la pipeline du Backend)
import re, pathlib
UP_PATTERNS = {
    'create_table': 'drop_table',
    'add_column': 'drop_column',
    'create_index': 'drop_index',
    'create_foreign_key': 'drop_constraint',
    'create_primary_key': 'drop_constraint',
    'create_unique_constraint': 'drop_constraint',
}
# parser AST + comparer les sets
```
Si une migration upgrade contient N op.create_table et le downgrade 0 op.drop_table → FAIL.

## Échappatoire documentée
Si la symétrie est volontairement brisée (perte de données acceptée), la migration **doit** contenir le commentaire `# IRREVERSIBLE: <raison>` en tête.
