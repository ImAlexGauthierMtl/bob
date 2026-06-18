---
name: dx_base_check_b4f_no_individual_ingress
description: Vérifie qu'AUCUNE B4F (ni Backend, ni frontend) n'a son propre Ingress. Un seul Ingress par namespace : api-gateway.
metadata:
  reference: § 5.11 + § 4.7 + § 8.4
---

# dx_base_check_b4f_no_individual_ingress

## Actions
```bash
# Compter les Ingress dans le namespace : doit valoir 1
n=$(kubectl -n "$NAMESPACE" get ingress -o name | wc -l)
[ "$n" = "1" ] || echo "FAIL: $n Ingress dans $NAMESPACE (doit être 1 : api-gateway)"

# Vérifier le nom
names=$(kubectl -n "$NAMESPACE" get ingress -o jsonpath='{.items[*].metadata.name}')
[ "$names" = "api-gateway" ] || echo "FAIL: Ingress nommé(s) '$names' (attendu: api-gateway)"

# Côté chart : api-chart ne doit pas avoir de templates/ingress.yaml
[ -f /tmp/cicd-templates/deploy/helm/api-chart/templates/ingress.yaml ] \
  && echo "FAIL: api-chart contient encore un ingress.yaml"
```
