---
name: dx_base_check_cicd_smoke_test_dependencies
description: Vérifie que les smoke-tests vérifient aussi les dépendances : DB, Redis, services upstream.
metadata:
  reference: § 4.11
---

# dx_base_check_cicd_smoke_test_dependencies

## Actions
Inspecter le script smoke-test pour qu'il fasse un check DB (`SELECT 1` via API health enrichie) et Redis (`PING`).
