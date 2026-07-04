# Release Plan — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 05 · Delivery · **Dernière MAJ** : 2026-07-01
> Comment une version part en production, en sécurité et de façon réversible.

## 1. Stratégie de release

- **Versionnage image** : tag `CI_COMMIT_SHA` (jamais `latest`) ; tags `v*` pour les jalons staging/prod.
- **Promotion** : dev (auto) → staging (manuel, validation) → prod (manuel, décision humaine).
- **Déploiement K8s** : `helm upgrade --install`, stratégie `RollingUpdate` (`maxSurge: 1`, `maxUnavailable: 0`).
- **Migrations** : initContainer + **Lease Kubernetes** (une seule migration concurrente, idempotente `IF NOT EXISTS`), downgrade symétrique testé.
- **Réversibilité** : `helm rollback` (job manuel) ; migrations avec downgrade.

## 2. Checklist de release (par version)

**Avant** : CI verte (test/build/verify), scan Trivy sans HIGH/CRITICAL non whitelistés, signature Cosign présente, migrations revues (upgrade **et** downgrade), changelog rédigé, [Launch Readiness](launch-readiness.md) à jour pour les nouveautés à risque.

**Pendant** : deploy staging → smoke-test vert → validation manuelle → deploy prod (fenêtre à faible trafic) → smoke-test prod.

**Après** : surveiller dashboards (5xx, latence, runs échoués, fallback) pendant la fenêtre de garde ; error budget consommé ? ; rollback si SLO franchis.

## 3. Smoke-test post-deploy (automatique)
Vérifie : endpoints répondent 200 ; `/health` ≠ unhealthy ; dépendances déclarées présentes ; aucun 5xx sur les endpoints canoniques.

## 4. Feature flags & déploiement progressif
- **Flags par tenant** : `Tenant.settings` (JSON) permet d'activer/désactiver des capacités par tenant → **rollout progressif** (ex. mode `auto` de Bob activé d'abord sur quelques tenants).
- **Kill-switch** : toute capacité agentique à risque doit être désactivable par tenant sans redeploy.
- **Découpler deploy et release** : déployer le code désactivé, activer via flag après validation.

## 5. Communication de release `[À COMPLÉTER]`
- **Interne** : changelog + note des risques/rollback.
- **Externe** (clients) : notes de version lisibles pour les changements visibles ; préavis pour tout changement de comportement de Bob (confiance).

## 6. Gestion des incidents en release
Si un incident P0/P1 survient : rollback immédiat si nécessaire, communication, puis **postmortem sans blâme** (voir [SLO §6](../04-technique/slo-observability.md)). Un incident d'isolation inter-tenant est **P0** systématique.

## 7. Cadence
`[À VALIDER]` Cadence cible (ex. releases hebdomadaires en dev, jalonnées en prod) à fixer selon la capacité et la maturité de la CI/CD prod.
