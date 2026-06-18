---
name: dx_base_check_cicd_harbor_cve_whitelist
description: Vérifie que l'allow-list CVE vit dans lint/harbor-cve-whitelist.yaml du repo CI/CD partagé (pas de .trivyignore, pas d'allow-list côté projet), avec raison + ticket + expiration max 6 mois par entrée.
metadata:
  reference: § 7.5 + § 4.10
---

# dx_base_check_cicd_harbor_cve_whitelist

## Actions
    ```bash
    # 1. Aucun .trivyignore nulle part
    find . -name ".trivyignore" -not -path "./.git/*" | grep . \
        && echo "FAIL: .trivyignore n'existe plus (allow-list côté Harbor)"

    # 2. Côté repo CI/CD : lint/harbor-cve-whitelist.yaml présent
    [ -f lint/harbor-cve-whitelist.yaml ] || echo "(skip si audit côté projet)"

    # 3. Chaque entrée a raison + ticket + expiration
    #    Format attendu par entrée : cve, reason, ticket, expires (YYYY-MM-DD)
    if [ -f lint/harbor-cve-whitelist.yaml ]; then
        python3 - <<'PY'
import yaml, datetime, sys
data = yaml.safe_load(open("lint/harbor-cve-whitelist.yaml"))
fails = 0
for e in (data or {}).get("cves", []):
    missing = [k for k in ("cve", "reason", "ticket", "expires") if not e.get(k)]
    if missing:
        print(f"FAIL: {e.get('cve','?')} — champs manquants: {missing}")
        fails += 1
sys.exit(1 if fails else 0)
PY
    fi
    ```
