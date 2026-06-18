---
name: dx_base_check_b4f_holds_business_logic
description: Vérifie que les B4F portent bien la logique d'affaire : use cases d'orchestration/règles métier présents, et ne sont pas de simples proxys 1:1 vers un seul Backend sans valeur ajoutée (agrégation, filtrage, composition).
metadata:
  reference: § 2.2 + § 2.8
---

# dx_base_check_b4f_holds_business_logic

## Règle
Le B4F porte la logique d'affaire et optimise pour le frontend. Un B4F qui ne fait que relayer un Backend 1:1 sans agréger/filtrer/composer est un anti-pattern (proxy CRUD).

## Actions
```bash
for d in apis/exposed/*-b4f-api/; do
  [ -d "$d/src" ] || continue
  name=$(basename "$d")

  # Doit avoir des use cases (logique d'affaire)
  uc=$(find "$d/src" -path "*application/use_cases/*.py" ! -name "__init__.py" 2>/dev/null | wc -l)
  [ "$uc" -gt 0 ] || echo "FAIL: $name n'a aucun use case (logique d'affaire absente)"

  # Signal de proxy 1:1 : un seul client Backend ET aucune composition
  clients=$(find "$d/src" -path "*infrastructure/backends/*_client.py" 2>/dev/null | wc -l)
  if [ "$clients" -le 1 ]; then
    # tolérable si le B4F applique néanmoins des règles/filtrage : vérifier la présence
    grep -rqiE "(aggregate|compose|filter|merge|enrich|orchestrate)" "$d/src/"*/application/ 2>/dev/null \
      || echo "WARN: $name ressemble à un proxy 1:1 (un seul Backend, pas de composition visible)"
  fi
done
```
