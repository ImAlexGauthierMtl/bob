---
name: dx_base_check_shared_auth_rbac_centralized
description: Vérifie que la validation d'authentification (token/session) et le moteur RBAC vivent dans apis/shared et ne sont pas réimplémentés par API. Aucune route ne code en dur une règle d'autorisation ; aucune API ne définit son propre middleware d'auth.
metadata:
  reference: § 2.10 + § 12.5
---

# dx_base_check_shared_auth_rbac_centralized

## Règle
Auth + RBAC = primitives techniques dans `apis/shared/`, consommées via Ports injectés. Jamais réimplémentées par API, jamais codées en dur dans une route.

## Actions
```bash
# 1. Les primitives existent dans apis/shared
grep -rqE "def .*(verify_token|authenticate|decode_jwt|check_permission|authorize)" \
    apis/shared/ 2>/dev/null \
    || echo "WARN: aucune primitive auth/RBAC trouvée dans apis/shared/"

# 2. Aucune API ne réimplémente la validation de token
for api in apis/exposed/*/ apis/internal/*/; do
    [ -d "$api/src" ] || continue
    grep -rE "def .*(decode_jwt|verify_token|validate_session)" "$api/src" 2>/dev/null \
        | grep -v "import" \
        | grep . && echo "FAIL: $api réimplémente la validation de token (doit venir de apis/shared)"
done

# 3. Aucune règle RBAC codée en dur dans une route
for routes in apis/*/*/src/*/presentation/api/v1/routes.py; do
    [ -f "$routes" ] || continue
    grep -nE "if .*(role|permission|is_admin) *==|\.role *==" "$routes" \
        && echo "FAIL: règle RBAC codée en dur dans $routes (utiliser le Port d'autorisation)"
done
```
