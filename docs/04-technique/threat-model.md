# Threat Model — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 04 · Technique · **Dernière MAJ** : 2026-07-01
> Modèle de menaces façon **STRIDE**, adapté à un SaaS multi-tenant piloté par un agent. À réviser à chaque changement d'architecture majeur. Complète la [DPIA](../06-gouvernance/privacy-dpia.md).

## 1. Actifs à protéger

| Actif | Sensibilité | Impact si compromis |
|---|---|---|
| Données CRM par tenant (contacts, deals, devis) | élevée | fuite concurrentielle, RGPD |
| Emails synchronisés (contenu, PJ) | élevée | vie privée, secrets d'affaires |
| Mémoire de Bob (insights, procédures) | élevée | fuite de savoir-faire |
| Tokens OAuth (MS365, Pipedream) | critique | prise de contrôle des boîtes mail |
| JWT / secrets de signature | critique | usurpation, contournement RBAC |
| Ledger d'usage / facturation | moyenne | fraude, désaccords de facturation |
| Capacité d'action de Bob (outils write) | critique | actions non désirées chez des tiers |

## 2. Surfaces & frontières de confiance

```
Internet ──► Gateway (TLS)  ──► [frontière] ──► B4F ──► [frontière] ──► Backends ──► DB / externes
                                    JWT                 X-Session-Context signé      OAuth tokens
```
Frontières clés : (a) client↔B4F (JWT), (b) B4F↔runtime (contexte de session signé), (c) backends↔services externes (OAuth), (d) inter-tenant (logique, via `tenant_id`).

## 3. Analyse STRIDE

### S — Spoofing (usurpation)
- **Menace** : réutilisation de JWT volé, faux webhooks.
- **Contrôles présents** : JWT signé HS256 (access 24 h), refresh 7 j, rate-limit login (5/15 min/IP), **webhooks Pipedream signés HMAC-SHA256**, contexte de session **signé** B4F→runtime (`INTERNAL_SESSION_SECRET/KID`).
- **À renforcer** : rotation des secrets JWT, révocation de refresh token, expiration courte + rotation ; envisager RS256/asymétrique.

### T — Tampering (altération)
- **Menace** : modification de données en transit ou de payloads d'events.
- **Contrôles** : HTTPS partout (redirect forcé), TLS wildcard, events avec `trace_id`.
- **À renforcer** : signature/validation des payloads d'Event Bus, intégrité des artifacts de run.

### R — Repudiation (répudiation)
- **Menace** : nier une action (email envoyé, donnée modifiée).
- **Contrôles** : **ledger append-only** (`UsageTransaction`), narration steps, audit `created_by`/`updated_by`, `correlation_id`. **Fort** par design (tenet 2).
- **À renforcer** : journal d'audit immuable dédié pour les actions sensibles de Bob (au-delà du ledger d'usage).

### I — Information disclosure (divulgation) — **risque n°1 : fuite inter-tenant**
- **Menace** : un tenant accède aux données d'un autre ; fuite de mémoire/RAG entre scopes ; secrets exposés.
- **Contrôles** : `tenant_id` obligatoire filtré à chaque requête ; **sensibilité RAG** filtrée (`internal`/`private_user`/`public`) ; backends non exposés ; secrets hors repo (`.env` non versionné, secrets CI/K8s) ; `DATABASE_SSLMODE` intra-cluster.
- **À renforcer** : tests automatisés anti-fuite inter-tenant (obligatoires en CI) ; revue systématique que **chaque** requête porte le filtre `tenant_id` ; chiffrement au repos des tokens OAuth et du contenu email sensible.

### D — Denial of service
- **Menace** : abus du tool-loop (coût LLM), flood de webhooks, épuisement du pool DB.
- **Contrôles** : bornes de boucle (5/3/12), PgBouncer (200 clients max), rate-limit login.
- **À renforcer** : quotas d'usage par tenant (lié aux plans), rate-limiting API global au gateway, back-pressure sur webhooks, budget d'inférence par tenant.

### E — Elevation of privilege
- **Menace** : contournement RBAC, abus de `is_super_admin`, escalade via outils Bob.
- **Contrôles** : RBAC `Permission/Role/UserRole`, rôles système immuables, 403→dashboard, **gouvernance d'outils** (un outil désactivé n'est jamais proposé), **gating de confirmation** sur write/destructive.
- **À renforcer** : principe du moindre privilège sur `is_super_admin` (audit des accès cross-tenant), séparation des secrets par environnement, revue des `team_scope` de policies.

## 4. Menaces spécifiques à l'IA agentique

| Menace | Description | Mitigation présente / à ajouter |
|---|---|---|
| **Prompt injection** | un email/contenu piégé fait exécuter une action non voulue par Bob | ✅ gating de confirmation sur write ; ✅ gouvernance d'outils ; ⚠️ à ajouter : sanitation/segmentation du contenu externe, méfiance sur les instructions issues de données |
| **Exfiltration via outils** | Bob poussé à envoyer des données sensibles via un outil | ✅ confirmation + readback ; ⚠️ règles de non-divulgation, allow-list de destinataires |
| **Empoisonnement mémoire** | insertion d'entrées trompeuses dans le RAG | ✅ sensibilité + statut + `verified_at` ; ⚠️ validation des sources d'ingestion (Zoho) |
| **Fuite de contexte inter-scope** | mélange privé/organisationnel | ✅ filtrage sensibilité RAG ; ⚠️ tests dédiés |
| **Coût incontrôlé** | boucle/outils coûteux | ✅ bornes dures ; ⚠️ quotas par tenant |

## 5. Priorités de durcissement (top 5)

1. **Tests anti-fuite inter-tenant en CI** (bloquants) — l'invariant n°1.
2. **Chiffrement au repos** des tokens OAuth et contenus email sensibles.
3. **Défense prompt-injection** (contenu externe traité comme non-fiable).
4. **Quotas & rate-limiting** par tenant (coût + DoS).
5. **Journal d'audit immuable** dédié aux actions sensibles de Bob + rotation/révocation des secrets.

## 6. Hypothèses & limites
- L'infra K8s/gateway est supposée correctement configurée (TLS, secrets K8s) — hors périmètre de ce doc mais à auditer.
- Ce modèle est **initial** : il doit être complété par un test d'intrusion avant un usage production à grande échelle. Voir [Launch Readiness](../05-delivery/launch-readiness.md) et [Risk Register](../06-gouvernance/risk-register.md).
