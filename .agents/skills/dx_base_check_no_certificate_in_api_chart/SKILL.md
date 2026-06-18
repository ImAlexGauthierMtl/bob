---
name: dx_base_check_no_certificate_in_api_chart
description: Vérifie que api-chart NE contient PLUS de templates/certificate.yaml (le TLS est géré uniquement par gateway-chart).
metadata:
  reference: § 5.11 + § 13.1
---

# dx_base_check_no_certificate_in_api_chart

## Actions
```bash
f=/tmp/cicd-templates/deploy/helm/api-chart/templates/certificate.yaml
[ -f "$f" ] && echo "FAIL: api-chart/templates/certificate.yaml existe encore (à supprimer)"

f=/tmp/cicd-templates/deploy/helm/api-chart/templates/ingress.yaml
[ -f "$f" ] && echo "FAIL: api-chart/templates/ingress.yaml existe encore (à supprimer)"

grep -E "^(ingress|tls):" /tmp/cicd-templates/deploy/helm/api-chart/values.yaml \
  && echo "FAIL: section ingress: ou tls: encore dans values.yaml de api-chart"
```
