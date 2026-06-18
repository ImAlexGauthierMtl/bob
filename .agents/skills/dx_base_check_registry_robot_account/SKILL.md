---
name: dx_base_check_registry_robot_account
description: Vérifie la configuration robot account Harbor : variables HARBOR_URL / HARBOR_PROJECT / HARBOR_ROBOT_USER (protégée) / HARBOR_ROBOT_TOKEN (protégée+masquée), defaults K8S_SERVICE_ACCOUNT=harbor-registry-deployer et K8S_REGISTRY_SECRET=harbor-registry-cred.
metadata:
  reference: § 7.2 + § 7.3
---

# dx_base_check_registry_robot_account

## Actions
```bash
# Audit du pipeline : les variables Harbor sont requises
for v in HARBOR_URL HARBOR_PROJECT HARBOR_ROBOT_USER HARBOR_ROBOT_TOKEN; do
    grep -rqE "\b$v\b" .gitlab-ci.yml templates/ deploy/ 2>/dev/null \
        || echo "WARN: $v non référencée"
done

# Defaults
grep -rqE "harbor-registry-deployer" templates/ deploy/ 2>/dev/null \
    || echo "WARN: default K8S_SERVICE_ACCOUNT inattendu"
grep -rqE "harbor-registry-cred" templates/ deploy/ 2>/dev/null \
    || echo "WARN: default K8S_REGISTRY_SECRET inattendu"

# Le Secret docker-registry pointe sur https://${HARBOR_URL}
grep -rE "docker-server.*HARBOR_URL" templates/ deploy/ 2>/dev/null | head -1 | grep -q . \
    || echo "WARN: provision-registry-access ne pointe pas sur HARBOR_URL"
```

## Contrat robot account (vérification manuelle Harbor UI)
- Nom : `robot$<projet>+ci`
- Permissions : push + pull + scan:read + scan:create + artifact:read
- Rotation : 90 jours
