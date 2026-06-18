---
name: dx_base_check_local_dev_one_command_bootstrap
description: Vérifie qu'un nouveau dev peut lancer le projet avec une seule commande : `./run.sh` (compose up + migrate + smoke).
metadata:
  reference: § 11
---

# dx_base_check_local_dev_one_command_bootstrap

## Actions
Lire run.sh et confirmer qu'il appelle dans l'ordre : `cp -n .env.example .env`, `docker compose up -d`, attente readiness, migrate par API, smoke local.
