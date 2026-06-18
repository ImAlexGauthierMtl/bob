---
name: dx_base_check_registry_harbor_primary
description: Vérifie que Harbor est le registry unique : images sur ${HARBOR_URL}/${HARBOR_PROJECT}/, aucune référence à ${CI_REGISTRY_IMAGE} ni au GitLab Container Registry, aucune variable DEPLOY_TOKEN_*.
metadata:
  reference: § 7.1 + § 7.3
---

# dx_base_check_registry_harbor_primary

## Actions
```bash
# 1. Aucun usage du GitLab Container Registry
grep -rE '\$\{?CI_REGISTRY' \
    --include="*.yml" --include="*.yaml" --include="*.sh" \
    .gitlab-ci.yml deploy/ templates/ 2>/dev/null \
    | grep . && echo "FAIL: CI_REGISTRY_* utilisé (GitLab Registry éteint)"

# 2. Aucune variable deploy token
grep -rE "DEPLOY_TOKEN_(USER|PASSWORD)" \
    --include="*.yml" --include="*.yaml" --include="*.sh" --include="*.md" \
    . 2>/dev/null | grep -v CHANGELOG | grep -v upgrade-guide \
    | grep . && echo "FAIL: DEPLOY_TOKEN_* résiduel"

# 3. Les images référencent Harbor
grep -rE "HARBOR_URL.*HARBOR_PROJECT|harbor\.tools\.thesmartcrew\.com" \
    deploy/ templates/ 2>/dev/null | head -1 | grep -q . \
    || echo "FAIL: aucune référence Harbor trouvée"
```
