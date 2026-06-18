---
name: dx_base_check_alembic_downgrade_not_empty
description: Vérifie que chaque révision Alembic a un downgrade() non vide (pas de `pass`, pas de `raise NotImplementedError`). Le downgrade est obligatoire.
metadata:
  reference: § 2.7.5 + § 8.1
---

# dx_base_check_alembic_downgrade_not_empty

## Règle
`def downgrade(): pass` est interdit. `raise NotImplementedError` est interdit. Le downgrade doit faire un vrai travail.

## Actions
```bash
fail=0
for f in apis/internal/*/alembic/versions/*.py; do
  [ -f "$f" ] || continue
  # Extraire le corps de downgrade()
  body=$(awk '/^def downgrade/,/^def [a-z_]+|^$/' "$f" \
         | sed '1d; $d' \
         | grep -vE '^\s*#' \
         | grep -vE '^\s*$')
  if [ -z "$body" ] || echo "$body" | grep -qE '^\s*pass\s*$|NotImplementedError'; then
    echo "FAIL: $f a un downgrade vide ou NotImplementedError"
    fail=$((fail+1))
  fi
done
[ "$fail" -eq 0 ] || exit 1
```
