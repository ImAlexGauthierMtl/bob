# ADR-0001 — Architecture à deux tiers B4F / Backend

- **Statut** : Accepted (documenté a posteriori) · **Date** : 2026-07-01 · **Décideur** : Alexandre Gauthier
- **Réf. normative** : [`regles-architecture-deploiement.md` (v1.4)](../../regles-architecture-deploiement.md)

## Contexte
CDE doit exposer une UI riche (dashboard composite, agrégations) tout en gardant une persistance simple et testable, pour une petite équipe. Il faut éviter à la fois le monolithe ingérable et le micro-service anémique où toute la logique fuit vers le client.

## Décision
Séparer strictement deux tiers :
- **B4F** (`apis/exposed/<service>-b4f-api`) : logique métier, agrégation, filtrage, composition ; **aucun** accès DB ni service externe direct ; exposé au gateway sous `/api/<service>/v1`.
- **Backend** (`apis/internal/<service>-backend-api`) : CRUD pur sur **une** entité principale ; possède son schéma et ses migrations Alembic ; **non exposé** (DNS K8s interne) ; seul à parler aux services externes et à la DB.

La conformité est **outillée** : import-linter (Clean Architecture en couches domain/application/infrastructure/presentation) et revue.

## Alternatives envisagées
1. **Monolithe modulaire** — plus simple à opérer, mais couplage fort, déploiement tout-ou-rien, difficile à faire respecter par des agents de code. Rejeté pour la scalabilité organisationnelle.
2. **Backends « riches » s'appelant en HTTP** — logique proche de la donnée, mais crée un **monolithe distribué** (chaînes d'appels, couplage temporel). Rejeté (voir [ADR-0002](adr-0002-event-bus-redis-inter-backend.md)).
3. **BFF unique** (un seul B4F pour tout) — moins de services, mais redevient un monolithe côté logique. Rejeté au profit d'un B4F par domaine.

## Conséquences
- ✅ Découplage, déploiement indépendant, testabilité, frontières claires (« le B4F pense, le backend range », tenet 3).
- ✅ La composition (dashboard CRM en parallèle) vit au bon endroit (B4F).
- ⚠️ **Complexité opérationnelle** : 7 B4F + 14 backends = 21 services à opérer, pour une petite équipe (voir [Risk Register](../../06-gouvernance/risk-register.md)).
- ⚠️ Les jointures cross-domaine deviennent des compositions applicatives (pas de SQL join inter-schéma).
- ➡️ Impose l'[Event Bus](adr-0002-event-bus-redis-inter-backend.md) pour la synchro inter-backend.
