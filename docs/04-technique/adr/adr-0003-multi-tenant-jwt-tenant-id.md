# ADR-0003 — Multi-tenant par `tenant_id` porté dans le JWT

- **Statut** : Accepted (documenté a posteriori) · **Date** : 2026-07-01 · **Décideur** : Alexandre Gauthier

## Contexte
CDE est un SaaS B2B servant plusieurs organisations clientes sur une infrastructure partagée. L'isolation des données entre clients est un prérequis absolu (sécurité + RGPD). Il faut un modèle d'isolation simple, imposable et vérifiable.

## Décision
Isolation **logique (row-level)** par `tenant_id` :
- Chaque entité métier porte `tenant_id` (via `TenantMixin`, `String(36)`, index, défaut `"default"`).
- Le `tenant_id` est **immuable** (fixé à la création de l'utilisateur) et **transporté dans le JWT** (`access_token`), aux côtés de `active_organization_id`, `role`, `is_super_admin`.
- Chaque requête backend **filtre** par le `tenant_id` du token.
- Distinction claire : `Tenant` (ligne d'abonnement, plan STARTER/PRO/ENTERPRISE) ≠ `Organization` (société cliente dans le CRM).

## Alternatives envisagées
1. **Base/schéma par tenant** (isolation physique) — isolation forte, mais coût opérationnel et migrations démultipliés ; mal adapté à beaucoup de petits tenants. Rejeté à ce stade.
2. **Row-level security PostgreSQL (RLS)** — filtrage au niveau DB, défense en profondeur. **Non retenu pour l'instant** (filtrage applicatif) mais **candidat sérieux** en durcissement (voir Conséquences).
3. **Isolation applicative sans marqueur uniforme** — fragile, source de fuites. Rejeté.

## Conséquences
- ✅ Simple, uniforme, imposable (mixin partagé), économique en ressources.
- ✅ Le JWT est la source de vérité du contexte → pas d'aller-retour supplémentaire.
- 🔴 **Risque n°1 du produit** : une requête qui **oublie** le filtre `tenant_id` = fuite inter-tenant (sévérité maximale). Mitigation obligatoire : **tests anti-fuite en CI** + revue systématique (voir [Threat Model](../threat-model.md)).
- ⚠️ Le défaut `"default"` ne doit **jamais** rester en prod pour un vrai tenant.
- ➡️ **Durcissement recommandé** : évaluer PostgreSQL RLS comme défense en profondeur, et chiffrement au repos des données sensibles.
