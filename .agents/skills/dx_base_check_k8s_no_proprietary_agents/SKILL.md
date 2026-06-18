---
name: dx_base_check_k8s_no_proprietary_agents
description: Vérifie qu'aucun agent propriétaire (Datadog, NewRelic, Dynatrace, AppDynamics) n'est installé.
metadata:
  reference: § 5
---

# dx_base_check_k8s_no_proprietary_agents

## Actions
```bash
grep -rE "(datadog|newrelic|dynatrace|appdynamics)" deploy/ apis/ pyproject.toml package.json && echo FAIL
```
