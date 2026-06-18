---
name: dx_base_check_shared_audit_logs_centralized
description: Vérifie que l'audit log et le logger JSON structuré viennent de apis/shared (format uniforme avec trace_id), et qu'aucune API ne configure son propre format de log ni son propre émetteur d'audit.
metadata:
  reference: § 2.10 + § 5.8
---

# dx_base_check_shared_audit_logs_centralized

## Actions
```bash
# 1. Logger + audit dans apis/shared
grep -rqE "logging\.|structlog|getLogger|json.*log" apis/shared/ 2>/dev/null \
    || echo "WARN: logger commun introuvable dans apis/shared/"
grep -rqE "audit" apis/shared/ 2>/dev/null \
    || echo "WARN: émetteur d'audit introuvable dans apis/shared/"

# 2. Aucune API ne configure son propre logging
for api in apis/exposed/*/ apis/internal/*/; do
    [ -d "$api/src" ] || continue
    grep -rE "logging\.basicConfig|logging\.config\.dictConfig|structlog\.configure" "$api/src" 2>/dev/null \
        | grep . && echo "FAIL: $api configure son propre logging (doit venir de apis/shared)"
done

# 3. Tous les logs incluent trace_id (vérifié via le formatter commun)
grep -rqE "trace_id" apis/shared/ 2>/dev/null \
    || echo "FAIL: le logger commun n'injecte pas trace_id (§ 5.9)"
```
