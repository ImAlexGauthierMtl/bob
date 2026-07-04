# Tenets — Principes directeurs de CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 00 · Vision · **Dernière MAJ** : 2026-07-01

Les *tenets* (à la manière d'Amazon) sont des **principes d'arbitrage**. Quand deux options se valent, on tranche en relisant ces principes. Ils sont ordonnés : en cas de conflit, le principe le plus haut l'emporte. Ils sont volontairement « discutables mais assumés » — un bon tenet écarte une alternative crédible.

---

### 1. L'humain garde la main sur toute action irréversible

Bob **agit**, mais toute action sensible (*write*, *destructive* : envoyer un email, supprimer, modifier chez un tiers) passe par une **confirmation explicite** avec *readback*. On préfère un friction de confirmation à une action non voulue.
> *Traduction dans le code* : `tool_result.status == "requires_confirmation"`, `AgentConfirmation`, `require_write_confirmation`.
> *Alternative rejetée* : « laisser Bob tout faire en auto pour l'effet waouh ». Non : la confiance est notre actif n°1.

### 2. Tout ce que fait Bob est traçable et explicable

Chaque run expose ses *narration steps*, ses tool-calls, son provider/modèle, et son coût. Aucune boîte noire. Un utilisateur doit pouvoir répondre à « pourquoi Bob a fait ça ? ».
> *Traduction* : `AgentRun.narration_steps`, `metadata.routing`, ledger `UsageTransaction` avec `correlation_id`.
> *Alternative rejetée* : optimiser l'UX en cachant les étapes. Non : l'opacité tue l'adoption en B2B.

### 3. Le B4F pense, le Backend range

La logique métier vit dans les B4F. Les backends sont du CRUD pur sur **une entité**, et ne se parlent qu'via l'**Event Bus** (jamais en HTTP direct). Cette discipline garde le système compréhensible et déployable pièce par pièce.
> *Traduction* : norme [v1.4](../regles-architecture-deploiement.md), import-linter, Redis event bus.
> *Alternative rejetée* : des backends « riches » qui s'appellent entre eux. Non : ça crée un monolithe distribué.

### 4. L'isolation multi-tenant n'est jamais optionnelle

Chaque donnée porte un `tenant_id`, filtré à chaque requête. Une fuite inter-tenant est un incident de sécurité de sévérité maximale, pas un bug fonctionnel.
> *Traduction* : `TenantMixin`, `tenant_id` dans le JWT, scoping systématique.
> *Alternative rejetée* : « on ajoutera l'isolation plus tard ». Non : c'est un choix d'architecture, pas une feature.

### 5. On mesure la valeur *acceptée*, pas l'activité

Le succès se compte en actions que l'humain a validées, pas en messages envoyés à Bob ni en features livrées. Une action annulée au *gate* est un signal produit, pas du bruit.
> *Traduction* : [North Star Metric](north-star-metric.md).

### 6. Vertical d'abord, générique jamais « pour le principe »

CDE sert la vente B2B. On refuse les features « parce qu'un CRM en a une » si elles ne servent pas l'exécution agentique du travail commercial. La profondeur bat la largeur.

### 7. Dégrader proprement plutôt que tomber

Si Fireworks est indisponible, le provider local déterministe prend le relais. Si Milvus est absent, la recherche mémoire se rabat sur le full-text. Un composant externe qui tombe **dégrade** l'expérience, il ne la casse pas.
> *Traduction* : `AGENT_RUNTIME_PROVIDER=auto`, fallback local, `MILVUS_ENABLED=false` en local, statut `degraded`.

### 8. La donnée du client lui appartient et le suit

Enrichissement, mémoire, emails : la donnée est *tenant-scoped*, sa sensibilité est typée (`internal`, `private_user`, `public`), et sa rétention est explicite. La confiance RGPD est un prérequis de vente en Europe/Canada.
> *Traduction* : `MemoryEntry.sensitivity`, `scope_type`, `expires_at` ; voir [DPIA](../06-gouvernance/privacy-dpia.md).

---

## Comment utiliser ces tenets

- **En revue de spec** : « Cette feature respecte-t-elle le tenet n°1 (confirmation) ? »
- **En revue d'architecture** : un ADR qui viole un tenet doit l'expliciter et le justifier.
- **En priorisation** : à valeur égale, ce qui sert un tenet plus haut passe devant.

> Les tenets ne sont pas gravés dans le marbre : on les révise quand la réalité les contredit. Toute modification passe par le [Decision Log](../06-gouvernance/decision-log.md).
