---
name: dx_base_check_update_skills_script_present
description: Vérifie que .agents/update-skills.sh existe et est exécutable.
metadata:
  reference: § 10.4
---

# dx_base_check_update_skills_script_present

## Actions
```bash
[ -x .agents/update-skills.sh ] \
    || { echo "FAIL: .agents/update-skills.sh absent ou non exécutable"; exit 1; }

# Doit pointer sur le bon repo
grep -qE "croo-dev/code-agent-skills-v1\.0" .agents/update-skills.sh \
    || echo "FAIL: update-skills.sh pointe sur un mauvais repo"
```
