---
name: dx_base_create_migrate_api_values_remove_ingress_tls
description: Refactor des deploy/values/<env>/<b4f>.yaml existants : supprime les sections ingress: et tls: (déléguées au gateway).
metadata:
  reference: § 5.11
---

# dx_base_create_migrate_api_values_remove_ingress_tls

## Actions
Pour chaque deploy/values/<env>/<api>.yaml d'une B4F :
```bash
python3 -c "
import re, sys
f = sys.argv[1]
c = open(f).read()
c = re.sub(r'\ningress:\n(?:  .*\n)+(?=\n)', '\n', c)
c = re.sub(r'\ntls:\n(?:  .*\n)+(?=\n)', '\n', c)
open(f, 'w').write(c)
" "$file"
```
Vérifier ensuite avec `dx_base_check_no_certificate_in_api_chart`.
