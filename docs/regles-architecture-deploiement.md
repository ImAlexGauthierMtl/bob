# Règles d'Architecture & Déploiement — Document de Référence

> **Version 1.4** — alignement sur l'état réel du repo CI/CD (v1.0.64) : Harbor registry primaire (robot accounts, verify Harbor + Cosign au lieu du scan Trivy local), migrations coordonnées par **Lease Kubernetes** (plus de lock Redis), gateway à deux Ingress (API avec rewrite, frontend sans), include à deux `file:` du même repo `croo-dev/ci-cd-unified-template-v1.0`. Modèle agents-agnostique (§ 10.3 / § 10.4) sans aucune référence à un outil propriétaire.
> **Version 1.2** — durcissement des règles Alembic : toute DDL (création comprise) passe par Alembic, downgrade obligatoire et testé en CI.
> **Version 1.1** — révisée pour intégrer l'API Gateway centralisé (§ 5.11), le frontend chart (§ 5.12), et la structure à trois charts Helm du repo CI/CD (§ 13).

Référence unique pour la conception, la revue et le déploiement des projets.

---

## 1. Vue d'ensemble

```
                       Internet (HTTPS uniquement)
                              |
                              v
                  API Gateway (Ingress NGINX unique)
                  - TLS via wildcard cert
                  - HTTP -> HTTPS (force-ssl-redirect)
                  - /          -> Service frontend
                  - /api/<svc> -> Service <svc>-b4f-api
                              |
            +-----------------+-----------------+
            |                                   |
            v                                   v
        Frontend                            B4F APIs
        (Angular + NGRX)                    (apis/exposed/)
        Service ClusterIP                   Service ClusterIP
                                            logique metier, agregation
                                            pas de DB, pas d'externe
                                                |
                                                | HTTP interne (K8s DNS)
                                                v
                                            Backend APIs
                                            (apis/internal/)
                                            une entite principale + secondaires
                                            DB + migrations + services externes
                                                |
                                                +--> PgBouncer (transaction) --> PostgreSQL
                                                +--> Services externes (HTTP)
                                                +--> Redis Event Bus <--> autres Backends
                                                                          (jamais HTTP Backend->Backend)
```

**Principes structurants :**

1. **Un seul point d'entrée externe** : l'API Gateway (Ingress). Aucun pod (frontend, B4F, Backend) n'a son propre Ingress.
2. **Tout est HTTPS** : le gateway force la redirection 80 → 443 pour tout le trafic entrant.
3. **TLS centralisé** : un unique secret TLS (wildcard) sur l'Ingress du gateway, copié depuis le namespace `cert-manager` au déploiement.
4. **Le frontend est packagé comme une API** : son propre Helm chart (`frontend-chart`), son propre Service ClusterIP, exposé via le gateway sur `/`.
5. **Les Backends restent invisibles** : pas de Service exposé via le gateway, accessibles uniquement par DNS K8s interne aux B4F.

---

## 2. Architecture des APIs — Modèle deux tiers

### 2.1 Tableau comparatif

| Aspect | B4F API | Backend API |
|---|---|---|
| **Emplacement** | `apis/exposed/` | `apis/internal/` |
| **Nommage** | `<service>-b4f-api` | `<service>-backend-api` |
| **Exposé sur le gateway** | OUI, sur `/api/<service>` | NON (DNS K8s interne) |
| **Ingress propre** | NON (le gateway centralise) | NON |
| **Accès BDD** | NON | OUI |
| **Services externes** | NON (délègue) | OUI |
| **Migrations** | NON | OUI (Alembic) |
| **Organisé par** | Domaine aligné frontend | 1 entité principale + secondaires |
| **Synchro inter-backend** | N/A | Event bus (Redis) |

### 2.2 Responsabilités B4F API

- Chaque B4F = un domaine aligné avec le frontend
- **Endpoints conçus pour réduire les appels frontend** : agrégation, composition, pré-jointures
- Filtrage, tri, agrégation des données issues des Backend APIs
- Application des règles métier et validation de domaine
- **JAMAIS** d'accès direct DB ou services externes
- Appels Backend via DNS K8s interne

#### Exception plateforme : Bob Cloud Auth/IAM/Licences

Bob Cloud est l'autorité plateforme pour les tenants, licences, sessions,
utilisateurs, rôles et capabilities fournis à CDE. Une B4F peut appeler Bob Cloud
directement uniquement via l'adapter partagé `BobCloudClient`, et seulement pour :

- valider une session utilisateur;
- lire le tenant courant;
- vérifier une licence, un entitlement ou une capability;
- déléguer une opération IAM/RBAC explicitement couverte par le contrat Bob Cloud.

Cette exception ne permet aucun appel fournisseur métier arbitraire depuis une B4F.
Les mutations via Bob Cloud exigent `Idempotency-Key`, forwarding d'identité et
mapping d'erreur sans fuite de secret. En local/CI, `BOB_CLOUD_MODE=stub` peut
pointer vers `bob-cloud-stub-api`; ce mode est interdit en production. Les
Backends internes continuent de recevoir uniquement un `X-Session-Context` signé
par la B4F après validation Bob Cloud.

### 2.3 Responsabilités Backend API

- Une **entité principale** par Backend (`rooms`, `clients`, `rates`...) avec CRUD complet
- **Entités secondaires** liées autorisées (ex. `room-types` dans `rooms-backend-api`) **sans dépendances vers d'autres Backends**
- Possession du schéma BDD et des migrations
- Intégrations services externes
- **NON** exposé hors du cluster
- Accès PostgreSQL via **PgBouncer en transaction pooling**
- Synchronisation inter-backend **via event bus uniquement**

### 2.4 Event Bus (Redis)

#### Infrastructure
- Redis **obligatoire** dans le déploiement (docker-compose en local, Helm en K8s)
- Tous les Backends sur la même instance Redis
- Convention : `REDIS_URL` (ex. `redis://redis:6379/0`)

#### Contrat d'événement
- **Channel** : `{source-api}.{entity}.{action}` — ex. `rates-backend-api.rate-plan.updated`
- **Payload JSON** :
```json
  {
    "event": "<channel>",
    "timestamp": "<ISO8601>",
    "tenant_id": "<tenant>",
    "trace_id": "<W3C trace-id, 32 hex chars>",
    "data": { }
  }
```
- **Publisher** : le Backend propriétaire de l'entité
- **Subscriber** : tout Backend qui doit réagir

#### Règles
- Backend → Backend en HTTP : **INTERDIT**
- Événements **fire-and-forget** (cohérence éventuelle)
- Subscribers **idempotents**
- Payloads **petits** : IDs et champs modifiés
- B4F : ni publish ni subscribe
- Redis est dédié à l'event bus — les migrations utilisent un **Lease Kubernetes**, pas Redis (cf. § 2.7.5)

### 2.5 Cas particulier : Authentication API

`authentication-api` est un monolithe historique. Il **DOIT** être splitté en :

| Nouvelle API | Emplacement | Responsabilités |
|---|---|---|
| `auth-b4f-api` | `apis/exposed/` | Login, refresh token, session |
| `iam-backend-api` | `apis/internal/` | CRUD users, rôles, hashing |

**Aucune exception** : pas de traitement spécial dans le pipeline.

#### Naming : « authentication » est banni

Le terme **`authentication`** ne doit apparaître nulle part. Utiliser **`auth`** (forme courte).

- **Service** : `authentication-api` → split en `auth-b4f-api` + `iam-backend-api`
- **Dossiers** : `apis/authentication-api/` → `apis/exposed/auth-b4f-api/` + `apis/internal/iam-backend-api/`
- **Schéma DB** : `authentication` → renommé en `iam`
- **Tables préfixées** : `authentication_users` → `iam.users`
- **Variables, classes, modules, fichiers** : `auth`/`Auth`, `iam`/`Iam`, ou supprimé

#### Migration via Alembic

```python
# alembic/versions/0001_rename_authentication_to_iam.py
def upgrade():
    op.execute("CREATE SCHEMA IF NOT EXISTS iam")
    op.execute("GRANT USAGE, CREATE ON SCHEMA iam TO app_user")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA iam GRANT ALL ON TABLES TO app_user")
    op.execute("ALTER TABLE authentication_users SET SCHEMA iam")
    op.execute("ALTER TABLE iam.authentication_users RENAME TO users")
    op.execute("ALTER TABLE authentication_roles SET SCHEMA iam")
    op.execute("ALTER TABLE iam.authentication_roles RENAME TO roles")
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA iam TO app_user")
    op.execute("GRANT ALL ON ALL SEQUENCES IN SCHEMA iam TO app_user")
    op.execute("DROP SCHEMA IF EXISTS authentication CASCADE")
```

### 2.6 Versioning

- L'**API Gateway** gère le routing par version
- Les **B4F** : routes versionnées (`routes/v1/`, `routes/v2/`)
- Backends : même pattern

### 2.7 Accès base de données

Les Backends partagent une **même instance PostgreSQL** via PgBouncer en transaction pooling.

#### 2.7.1 Utilisateur et base partagés (variables CI/CD)

Tous les Backends utilisent **le même utilisateur, la même base et le même hôte**.

| Variable CI/CD | Description | Scope |
|---|---|---|
| `DB_HOST` | Hôte PgBouncer | par env |
| `DB_USERNAME` | Utilisateur applicatif partagé | par env |
| `DB_PASSWORD` | Mot de passe (masqué) | par env |
| `DB_DATABASE` | Nom de la base partagée | par env |
| `DATABASE_SSLMODE` | Mode SSL libpq. **Default `disable`** intra-cluster | par env |

**Règles :**
- **Un seul user applicatif** pour tous les Backends
- **Une seule base** partagée par environnement
- Credentials **exclusivement** depuis variables CI/CD scopées (cf. § 6)
- L'URL DB :
```
  postgresql://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}/${DB_DATABASE}?sslmode=${DATABASE_SSLMODE}
```
- **`DATABASE_SSLMODE=disable` par défaut** intra-cluster

#### 2.7.2 Isolation par schéma PostgreSQL

- Chaque Backend possède un schéma au **nom du service** : `<service>`
- Le schéma est créé par la **première migration Alembic** du Backend

```sql
CREATE SCHEMA IF NOT EXISTS <service>;
GRANT USAGE, CREATE ON SCHEMA <service> TO app_user;
GRANT ALL ON ALL TABLES IN SCHEMA <service> TO app_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA <service> TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA <service> GRANT ALL ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA <service> GRANT ALL ON SEQUENCES TO app_user;
```

**Référencement des tables** — toujours en **noms qualifiés** :

```python
class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = {"schema": "rooms"}
```

**Configuration Alembic** :

```python
# env.py
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    include_schemas=True,
    version_table="<service>_alembic_version",
    version_table_schema="public",
)
```

La table de version Alembic est une exception technique : elle reste dans
`public`, mais son nom est obligatoirement préfixé par le service
(`<service>_alembic_version`). Cette convention évite toute DDL dans `env.py`
avant que la première migration ait créé le schéma métier. Les tables métier,
index, contraintes et clés étrangères restent toujours qualifiés dans le schéma
du service (`<service>.*`). `SET search_path` demeure interdit.

#### 2.7.3 Pool de connexions applicatif (SQLAlchemy)

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=2,
    max_overflow=3,
    pool_pre_ping=True,
    pool_recycle=300,
)
```

**Règles :**
- `pool_size` ≤ **5** par pod (cible 2-3)
- `max_overflow` ≤ **5** (cible 3)
- `pool_pre_ping=True` **obligatoire**
- `pool_recycle` ≤ 300s
- Pas de pool partagé entre processus
- **Désactiver les prepared statements** au niveau driver :
```python
  # asyncpg
  create_async_engine(URL, connect_args={"statement_cache_size": 0})
  # psycopg
  create_engine(URL, connect_args={"prepare_threshold": None})
```

#### 2.7.4 Contraintes PgBouncer (transaction mode)

##### Autorisé
- Transactions explicites courtes
- Sessions SQLAlchemy session-per-request
- Requêtes standard, joins, CTEs, sous-requêtes

##### Interdit
- `SET` / `SET LOCAL` hors transaction
- `SET search_path` (utiliser des noms qualifiés)
- `PREPARE` / `DEALLOCATE`
- `LISTEN` / `NOTIFY`
- Advisory locks hors transaction
- Sessions long-vivantes
- `DECLARE CURSOR` hors transaction

#### 2.7.5 Migrations Alembic

**Règle fondamentale** : **toute** modification du schéma DB — création initiale incluse — passe **exclusivement** par une migration Alembic versionnée. Le code applicatif ne crée **jamais** de structure DB au démarrage, et aucun script SQL artisanal n'est exécuté hors d'Alembic.

##### Toutes les opérations DDL via Alembic

Sans exception. Y compris :

- La **création du schéma PG** (`CREATE SCHEMA <service>`) — c'est la première migration du Backend
- La **création des tables initiales**
- Tout `CREATE INDEX`, `CREATE TYPE`, `CREATE EXTENSION`
- Toute attribution de droits (`GRANT`, `ALTER DEFAULT PRIVILEGES`)
- Les **données de seed** non transactionnelles si elles sont reproductibles (`INSERT` idempotents dans une migration ou via `op.bulk_insert`)
- Le renommage, l'ALTER, le DROP

**Aucun fichier `.sql` exécuté manuellement** ne doit exister dans le repo (pas de `migrations/manual/`, `db/init.sql`, `psql -f setup.sql`...). Toute opération qu'on serait tenté de mettre dans un tel fichier devient une révision Alembic.

##### Downgrade obligatoire et testé

Chaque révision Alembic **doit** fournir un `downgrade()` non vide qui inverse strictement l'`upgrade()`. C'est non négociable :

- `def downgrade(): pass` est **interdit**
- `def downgrade(): raise NotImplementedError` est **interdit**
- Le downgrade doit être **symétrique** : pour chaque `op.X` dans `upgrade`, un `op.Y` inverse dans `downgrade`. Exemples :
  - `create_table` → `drop_table`
  - `add_column` → `drop_column`
  - `create_index` → `drop_index`
  - `execute("CREATE SCHEMA ...")` → `execute("DROP SCHEMA ... CASCADE")`
  - `bulk_insert` → `op.execute("DELETE FROM ... WHERE ...")`
- Pour les changements **destructifs** côté upgrade (drop column avec données), le downgrade recrée la colonne **et** documente que la donnée est perdue (commentaire en tête de migration)
- Le downgrade est **testé** : la pipeline du Backend exécute une étape `alembic downgrade -1 && alembic upgrade head` sur la dernière révision en CI pour garantir la réversibilité

**Justification** : un déploiement raté en prod doit pouvoir être rollback en quelques minutes. Sans downgrade fiable, le seul recours est la restauration de backup, qui prend des heures et perd des données.

##### Patterns interdits

- `Base.metadata.create_all(engine)` au boot
- `CREATE SCHEMA IF NOT EXISTS` exécuté hors migration
- `engine.execute("CREATE TABLE ...")` dans un startup hook
- `db.create_all()` (Flask-SQLAlchemy)
- Auto-DDL via `SQLModel.metadata.create_all`
- DDL depuis un `lifespan` / `startup` event
- `Base.metadata.drop_all()` même en test
- **Fichier SQL exécuté hors d'Alembic** (`init.sql`, `seed.sql`, `psql -f ...`)
- **Migration avec `downgrade()` vide** ou `pass` ou `NotImplementedError`
- **Migration asymétrique** où le downgrade ne défait pas réellement l'upgrade

##### Lieu d'exécution

Les migrations s'exécutent **uniquement depuis Kubernetes**, jamais depuis un runner GitLab CI. Mécanisme retenu : **initContainer** du Deployment du Backend.

```yaml
spec:
  template:
    spec:
      initContainers:
        - name: migrate
          image: {{ .Values.image.repository }}:{{ .Values.image.tag }}
          command: ["python", "scripts/migrate_with_lease.py"]
          env:
            - name: MIGRATION_SERVICE
              value: {{ .Values.apiName }}
            - name: MIGRATION_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
          envFrom:
            - secretRef:
                name: backend-runtime-secrets    # variables DB
            - configMapRef:
                name: {{ .Values.apiName }}-config
      containers:
        - name: app
          image: {{ .Values.image.repository }}:{{ .Values.image.tag }}
```

**Règles :**
- L'initContainer utilise la **même image** que le Backend et appelle `scripts/migrate_with_lease.py`
- Reçoit les mêmes variables DB que le Backend (via `backend-runtime-secrets`)
- Aucune migration lancée par le conteneur applicatif
- Pas de Helm hook séparé
- Pas de Job Kubernetes externe ni de migration manuelle
- SecurityContext durci : `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `capabilities: { drop: [ALL] }`

##### Concurrence et Lease Kubernetes

Plusieurs pods peuvent démarrer simultanément. La coordination passe par un **Lease Kubernetes** (`coordination.k8s.io/v1`), mécanisme natif du cluster — aucune dépendance à Redis pour les migrations (Redis reste dédié à l'event bus, cf. § 2.4).

**Contrat du Lease :**
- Nom : `migration-<service>` dans le namespace du déploiement
- `holderIdentity` : token unique du pod (`$HOSTNAME-<uuid>`)
- Acquisition : `create` (404 → premier arrivé) ou `update` conditionnel si le Lease est expiré
- Renouvellement : thread de renew (`renewTime`) toutes les `LEASE_DURATION/3` secondes pendant la migration
- Release : remise à zéro du `holderIdentity` en fin de migration
- Expiration de sécurité : `leaseDurationSeconds` (600s par défaut) — un pod crashé ne bloque jamais indéfiniment

**Variables :**

| Variable | Default | Description |
|---|---|---|
| `MIGRATION_SERVICE` | — | Nom du service → nom du Lease |
| `MIGRATION_NAMESPACE` | fieldRef `metadata.namespace` | Namespace du Lease |
| `MIGRATION_LEASE_DURATION_S` | `600` | Durée de validité du Lease |
| `MIGRATION_WAIT_TIMEOUT_S` | `900` | Timeout total d'attente |
| `MIGRATION_WAIT_INTERVAL_S` | `5` | Intervalle de polling |

**Script wrapper** (`scripts/migrate_with_lease.py`, fourni par le repo CI/CD partagé) :

- Utilise le client Python `kubernetes` avec `config.load_incluster_config()`
- Boucle : tente `create` du Lease ; si conflit (409), lit le Lease, vérifie l'expiration (`renewTime + leaseDurationSeconds`), tente un `update` compare-and-swap si expiré
- Une fois titulaire : lance un thread de renouvellement puis `alembic upgrade head`
- En `finally` : arrête le renouvellement et libère le Lease
- Dépendance : package `kubernetes` dans l'image du Backend (`pip install kubernetes`)

**RBAC requis** (déployé par le chart `api-chart`, template `migration-lease-rbac.yaml`) :

```yaml
rules:
  - apiGroups: ["coordination.k8s.io"]
    resources: ["leases"]
    verbs: ["create"]
  - apiGroups: ["coordination.k8s.io"]
    resources: ["leases"]
    resourceNames: ["migration-<service>"]
    verbs: ["get", "update", "patch"]
```

Le `RoleBinding` cible le ServiceAccount du pod. Principe de moindre privilège : `create` général (les resourceNames ne s'appliquent pas à create), mais `get/update/patch` restreints au Lease nommé.

**Codes de sortie :**

| Code | Signification |
|---|---|
| `0` | Migration appliquée (ou no-op) |
| `1` | Erreur Alembic |
| `2` | Timeout d'attente du Lease |
| `3` | API Kubernetes injoignable |

##### Visibilité des erreurs dans le pipeline CI

```bash
helm upgrade --install "${API_NAME}" ./chart \
  --namespace "${NAMESPACE}" \
  --values "${VALUES_FILE}" \
  --wait --timeout 5m

if [ $? -ne 0 ]; then
  echo "=== Migration logs (initContainer 'migrate') ==="
  kubectl logs -n "${NAMESPACE}" -l app="${API_NAME}" -c migrate --tail=200 || true
  echo "=== Pod events ==="
  kubectl describe pod -n "${NAMESPACE}" -l app="${API_NAME}" || true
  exit 1
fi
```

##### Stratégie de déploiement
- `RollingUpdate` avec `maxSurge: 1, maxUnavailable: 0`
- Première installation avec `replicas: 1`, scale-up après stabilisation
- Migrations idempotentes (`CREATE ... IF NOT EXISTS`)

##### Règles d'écriture des migrations

- Wrapper chaque étape dans une transaction explicite
- Désactiver les advisory locks
- Migrations courtes et idempotentes
- **Première migration** : crée le schéma `<service>`, accorde les droits, crée les tables initiales — entièrement en Alembic
- **`upgrade()` ET `downgrade()` toujours définis et non vides** (cf. ci-dessus)
- Le downgrade est **symétrique** et **testé en CI** (`alembic downgrade -1 && alembic upgrade head`)
- Pour les migrations destructives en upgrade, documenter en commentaire la perte de données potentielle en downgrade

### 2.8 Restructuration : violations et procédure de split

#### Violations à détecter

| Violation | Symptôme | Action |
|---|---|---|
| B4F accède à la DB | `alembic/`, modèles SQLAlchemy, `DATABASE_URL` | Extraire vers une Backend |
| B4F appelle un service externe | HTTP direct vers tiers | Router via Backend |
| Backend exposé en ingress | Présent dans routes gateway / config front | Créer une B4F devant |
| Frontend → Backend direct | URL Backend dans config API frontend / services Angular | Router via la B4F |
| API monolithique | DB + routes frontend-facing dans la même API | Splitter en B4F + Backend |
| Backend → Backend en HTTP | `httpx`/`requests` vers `*-backend-api` | Remplacer par event bus |
| Backend possède entités non liées | Modèles dépendants d'autres Backends | Déplacer ou créer nouvelle Backend |
| B4F simple proxy CRUD | 1:1 sans agrégation | Ajouter logique métier ou fusionner |
| B4F non alignée frontend | Domaine non lié à une section UI | Réorganiser |
| Backend avec son propre user/DB | `DB_USERNAME` ou `DB_DATABASE` spécifique | Migrer vers user/DB partagés |
| Schéma DB hors convention | Schéma ne porte pas le nom du service | Renommer ou migrer |
| Pool SQLAlchemy trop large | `pool_size > 5` ou `max_overflow > 5` | Réduire selon § 2.7.3 |
| Prepared statements actifs | `statement_cache_size` non nul | Désactiver au niveau driver |
| Code applicatif crée des structures DB | `Base.metadata.create_all()`, DDL dans startup hook | Supprimer et générer une migration |
| Fichier SQL exécuté hors d'Alembic | `init.sql`, `seed.sql`, `psql -f`, scripts manuels | Convertir en révision Alembic |
| Migration sans downgrade | `def downgrade(): pass` ou `raise NotImplementedError` | Écrire un downgrade symétrique à l'upgrade |
| Première migration sans CREATE SCHEMA | DDL initiale via SQL externe ou script | Refactorer en première révision Alembic |
| InitContainer migrate sans Lease K8s | `alembic upgrade head` direct dans l'initContainer | Remplacer par `migrate_with_lease.py` |

#### Procédure de split (zéro perte de données)

1. **Créer la Backend en premier** dans `apis/internal/` :
   - Modèles DB et migrations Alembic (**même nom de schéma**)
   - Repositories
   - Intégrations externes
   - Routes CRUD comme endpoints internes

2. **Créer/mettre à jour la B4F** dans `apis/exposed/` :
   - Logique métier (filtrage, tri, agrégation, validation)
   - Signatures de routes frontend (mêmes paths, mêmes schémas)
   - Remplacer DB direct par appels HTTP

3. **Sécurité BDD** :
   - **JAMAIS** drop ou rename du schéma pendant le split
   - Backend hérite du schéma existant
   - Historique `versions/` Alembic transféré intact
   - Aucune migration destructive
   - Tester avant suppression de l'ancienne API

4. **Cutover** :
   1. Déployer Backend
   2. Déployer B4F
   3. Mettre à jour gateway → B4F
   4. Mettre à jour config frontend → B4F
   5. Décommissionner l'ancien monolithe

### 2.9 Intégration frontend

Le frontend ne communique **qu'avec les B4F**.

```typescript
export const API_CONFIG = {
  myDomain: '.../<service>-b4f-api',
};
```

**INTERDIT** : toute URL `*-backend-api`.

### 2.10 Code partagé entre APIs

| Dossier | Portée | Contenu |
|---|---|---|
| `apis/shared/` | Toutes les APIs | Logger, helpers OTel, base d'erreurs HTTP, pagination, schémas Pydantic communs, middleware générique |
| `apis/exposed/shared/` | B4F uniquement | Client HTTP vers les Backend, patterns d'agrégation, schémas de réponse frontend, gestion de session |
| `apis/internal/shared/` | Backend uniquement | Setup SQLAlchemy + pool tuning, base classes Repository, config Alembic, client Redis event bus, helpers de schéma |

#### Règles
- Les `shared/` **ne sont pas des APIs**
- **Aucune logique métier** dans `shared/`
- **Aucun modèle d'entité métier** dans `apis/internal/shared/`
- `apis/exposed/shared/` **ne consomme jamais** `apis/internal/shared/`
- Tout `shared/` peut consommer `apis/shared/` mais pas l'inverse

---

## 3. Architecture Frontend — Angular + NGRX

### 3.1 Règles fondamentales

1. **Un Service par B4F**
2. **Un feature de Store par B4F**
3. **Effects appellent les Services**
4. **Components n'utilisent que NGRX**
5. **Templates bindent les observables directement** via `| async`

### 3.2 Flux de données

```
Template (async pipe) <-- Store.select(selector)
Component dispatch --> Action --> Effect --> Service --> B4F API
                                  Effect --> Success/Failure --> Reducer --> Store
```

### 3.3 Structure de fichiers

```
frontend/src/app/
├── store/
│   ├── index.ts
│   └── <feature>/
│       ├── <feature>.actions.ts
│       ├── <feature>.reducer.ts
│       ├── <feature>.effects.ts
│       └── <feature>.selectors.ts
├── services/
│   └── <feature>.service.ts
├── pages/
└── components/
```

### 3.4 Mapping Feature ↔ API (1:1)

Chaque feature de store mappe 1:1 vers une B4F. Ex : `auth` ↔ `AuthService` ↔ `auth-b4f-api`.

### 3.5 Conventions de nommage

| Artefact | Pattern |
|---|---|
| Dossier feature | kebab-case |
| Fichier actions | `<feature>.actions.ts` |
| Action type | `[Feature] Verb Noun` |
| Interface State | `<Feature>State` |
| Classe Effects | `<Feature>Effects` |
| Selectors | `select<Feature><Property>` |
| Classe Service | `<Feature>Service` |

### 3.6 Patterns interdits

```typescript
// FAUX — service injecté
constructor(private clientsService: ClientsService) {}

// FAUX — variable statique
clients: Client[] = [];

// FAUX — HTTP hors Effects
ngOnInit() { this.http.get('/api/...').subscribe(...); }
```

### 3.7 Créer un nouveau feature

1. Service `services/<feature>.service.ts`
2. Actions (load/success/failure)
3. Reducer
4. Effects
5. Selectors
6. Register dans `store/index.ts` et `provideEffects()`

### 3.8 Tests E2E (Playwright)

Le frontend est testé end-to-end avec **Playwright**. Ces tests valident des parcours utilisateur complets contre une instance Frontend + B4F + Backend.

#### Périmètre

- Tests de parcours métier critiques (login, création de réservation, navigation principale, etc.)
- **Pas** de tests unitaires (ceux-ci sont en Jest, cf. § 4.9) ni de tests visuels
- Cible : un environnement de test local (Docker compose + frontend lancé) ou un environnement de review déployé

#### Localisation et structure

```
frontend/
├── e2e/
│   ├── playwright.config.ts
│   ├── fixtures/
│   ├── tests/
│   │   ├── auth.spec.ts
│   │   ├── reservations.spec.ts
│   │   └── ...
│   └── helpers/
└── ...
```

#### Lancement

| Contexte | Commande |
|---|---|
| Manuel, racine projet | `./run_frontend_e2e.sh` |
| Manuel, dans `frontend/` | `npx playwright test` |
| Headed (debug) | `npx playwright test --headed` |
| UI mode | `npx playwright test --ui` |

Le script wrapper `run_frontend_e2e.sh` (cf. § 11.1) lance Playwright avec la config attendue.

#### Pas dans le pipeline CI

Les tests E2E **ne tournent pas** dans le pipeline GitLab. Raison :
- Coût d'orchestration (lancer un environnement complet pour chaque pipeline)
- Lenteur (plusieurs minutes vs secondes pour les tests Jest)
- Flakiness potentielle (timing, état asynchrone) — mauvais signal sur un pipeline qui doit rester rouge ou vert sans ambiguïté
- Le smoke-test (cf. § 4.11) couvre la disponibilité ; les E2E couvrent les parcours, c'est le rôle des humains de les déclencher avant les MRs ou avant un tag de release

#### Pre-commit hook recommandé

Idéalement, un **hook git pre-commit** détecte les modifications dans `frontend/` et lance les E2E avant le commit. Implémentation recommandée via **husky** :

```json
// frontend/package.json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:changed": "playwright test --grep @smoke"
  },
  "husky": {
    "hooks": {
      "pre-commit": "../scripts/pre-commit-frontend.sh"
    }
  }
}
```

```bash
#!/usr/bin/env bash
# scripts/pre-commit-frontend.sh
set -e

# Détecte si des fichiers frontend ont changé dans le commit en cours
CHANGED=$(git diff --cached --name-only --diff-filter=ACMR | grep -E '^frontend/' || true)

if [ -z "$CHANGED" ]; then
  exit 0
fi

echo "[pre-commit] frontend changes detected, running Playwright E2E (smoke)..."
cd frontend && npm run test:e2e:changed
```

**Règles :**
- Le hook n'est pas obligatoire (`git commit --no-verify` reste possible)
- Tagger les tests critiques avec `@smoke` pour que le pre-commit lance un sous-ensemble rapide ; lancer la suite complète manuellement avant push ou MR
- Le développeur est responsable de lancer `npm run test:e2e` en complet avant d'ouvrir une MR qui touche le frontend

#### Anti-patterns

1. **Tests E2E dans le pipeline GitLab** — viole la politique (lenteur, flakiness, complexité d'orchestration)
2. **Pas de pre-commit hook** — les régressions E2E sont détectées trop tard (par les humains lors de la review ou en review env)
3. **Tests E2E dans `frontend/src/`** — confond avec les tests unitaires Jest ; toujours sous `frontend/e2e/`
4. **Tests E2E qui dépendent d'un environnement spécifique** (ex. URLs hardcodées dev) — paramétrer via `playwright.config.ts` et variables d'env
5. **Pas de tag `@smoke`** sur les tests critiques — pas moyen de lancer un sous-ensemble rapide en pre-commit

---

## 4. Pipeline CI/CD

### 4.1 Pipeline et chart Helm partagés

| Repo | Contenu |
|---|---|
| `croo-dev/ci-cd-unified-template-v1.0` (partagé) | Templates `.gitlab-ci.yml` (parent + child), scripts dans `/deploy/scripts/`, chart `api-chart` dans `/deploy/helm/`, image Kaniko wrappée |
| Projet `<projet>` | Code des APIs, frontend, **uniquement les values** dans `/deploy/values/{env}/<api>.yaml` |

#### Convention `/deploy`

| Chemin | Repo concerné | Contenu |
|---|---|---|
| `/deploy/scripts/` | Repo partagé | Scripts shell et Python de déploiement |
| `/deploy/helm/` | Repo partagé | Chart Helm générique `api-chart` |
| `/deploy/values/{env}/<api>.yaml` | Projet | Values Helm spécifiques |

#### Structure attendue côté projet

```
<projet>/
├── apis/
│   ├── shared/
│   ├── exposed/
│   │   ├── shared/
│   │   ├── auth-b4f-api/
│   │   │   ├── run_api.sh
│   │   │   └── run_tests.sh
│   │   └── front-office-b4f-api/
│   └── internal/
│       ├── shared/
│       ├── iam-backend-api/
│       │   ├── run_api.sh
│       │   ├── migrate.sh
│       │   └── run_tests.sh
│       └── rooms-backend-api/
├── frontend/
├── deploy/
│   └── values/
│       ├── dev/
│       ├── staging/
│       └── prod/
├── docs/                             # cf. § 10.1
├── data/                             # cf. § 10.2
├── docker-compose.yml                # cf. § 11.3
├── .env.example
├── run_all_apis.sh                   # cf. § 11.1
├── migrate_all_apis.sh
├── run_all_apis_tests.sh
├── run_frontend.sh
├── run_frontend_tests.sh
├── run_frontend_e2e.sh               # cf. § 3.8
└── .gitlab-ci.yml
```

#### `.gitlab-ci.yml` minimal

**Deux `file:`-includes du même repo partagé** `croo-dev/ci-cd-unified-template-v1.0`. Tout est consolidé dans ce repo : templates pipeline, scripts, charts Helm, image Kaniko wrappée.

```yaml
include:
  # 1. Templates Kaniko (.kaniko_build / .kaniko_frontend_build)
  - project: 'croo-dev/ci-cd-unified-template-v1.0'
    ref: v1.0.64                  # pin strict — recommandé en production
    file: '/kaniko.yml'
  # 2. Pipeline complet (5 stages, charts, scripts)
  - project: 'croo-dev/ci-cd-unified-template-v1.0'
    ref: v1.0.64
    file: '/templates/parent.yml'
```

Les **deux refs doivent être identiques** (même tag). L'URL complète du repo : `git@gitlab.tools.thesmartcrew.com:croo-dev/ci-cd-unified-template-v1.0.git`. Aucun autre repo n'est référencé : `infrastructure/ci-templates` et `shared/cicd-templates` n'existent plus.

### 4.2 Architecture parent / child

#### Pipeline parent — un seul stage

| Stage | Job | Rôle |
|---|---|---|
| `discover` | `generate-child-pipeline` | Scanne `apis/` et génère le child pipeline |

#### Pipeline child — 5 stages

| Stage | Rôle | When |
|---|---|---|
| `test` | Tests + linting | Auto |
| `build` | Build Docker, label OCI, push vers Registry | Auto |
| `deploy` | `helm upgrade --install` | Auto sur dev/review, manuel sur staging/prod |
| `smoke-test` | Test de santé post-deploy | Auto après deploy |
| `rollback` | `helm rollback` | **Manuel** uniquement |

**Règles :**
- **Aucun autre stage**
- L'échec d'un stage bloque les stages suivants pour la même API mais pas les autres APIs
- `rollback` en `when: manual`
- Pas de stage de migration (initContainer uniquement)

### 4.3 Déclencheurs et stratégie de tags d'image

| Évènement Git | Stages | Tag d'image | Déploiement |
|---|---|---|---|
| Push/merge sur `main` | test → build → deploy → smoke-test | `${CI_COMMIT_SHA}` | **Auto** sur dev |
| MR ouverte | test → build → deploy → smoke-test | `${CI_COMMIT_SHA}` | **Auto** sur review |
| Tag `v*` | test → build | `${CI_COMMIT_TAG}` | **Manuel** sur staging ou prod |

#### Tagging et labels d'image

```bash
docker build \
  --label org.opencontainers.image.version="${CI_COMMIT_TAG:-$CI_COMMIT_SHA}" \
  --label org.opencontainers.image.revision="${CI_COMMIT_SHA}" \
  --label org.opencontainers.image.source="${CI_PROJECT_URL}" \
  -t "${CI_REGISTRY_IMAGE}/${API_NAME}:${CI_COMMIT_TAG:-$CI_COMMIT_SHA}" .
```

#### Règles
- **Aucun déploiement automatique sur staging ou prod**
- Tag `v*` permet redéploiement sans rebuild
- Pas de tags `latest` ni mutables

### 4.4 Limitation de la concurrence (`CICD_MAX_PARALLEL_JOBS`)

| Variable | Default | Description |
|---|---|---|
| `CICD_MAX_PARALLEL_JOBS` | non définie = pas de limite | Nombre max de jobs simultanés |

```yaml
.with_concurrency_limit:
  resource_group: ${CICD_MAX_PARALLEL_JOBS:+throttle-${CI_PIPELINE_ID}}

build:auth-b4f-api:
  extends: .with_concurrency_limit
  stage: build
```

### 4.5 Pipeline agnostique

- Templates utilisent `${API_NAME}`
- Scripts acceptent l'API en paramètre, **aucun branchement par nom**
- Helm chart générique
- Nom de projet via `CI_PROJECT_PATH`
- **Aucune exception** pour aucune API

### 4.6 Backend APIs : initContainer migration + pas d'ingress

| Concern | Exigence |
|---|---|
| Migration | **initContainer** du pod Backend (cf. § 2.7.5) |
| Ingress | **Jamais** dans la gateway |
| Réseau | Interne uniquement |
| Dossier | `apis/internal/` |

### 4.7 B4F APIs : pas de migration + exposition via gateway

| Concern | Exigence |
|---|---|
| Migration | Aucune |
| Ingress propre | **Jamais** (le gateway centralise) |
| Exposition | Service ClusterIP référencé par l'Ingress du **gateway** sur `/api/<service>` (cf. § 5.11) |
| Dossier | `apis/exposed/` |

### 4.8 Trois environnements, même processus

Dev, staging, prod **identiques** sur le script et le chart. Différences :

| Paramètre | Source |
|---|---|
| Déclencheur | Voir § 4.3 |
| Tag d'image | SHA pour dev, `v*` pour staging/prod |
| Namespace | `NAMESPACE` scopé |
| Values file | `deploy/values/{env}/<api>.yaml` |

### 4.9 Stage `test` — qualité, couverture et rapports

#### Aucun job ne « échoue en silence »

**Aucun `allow_failure: true`** dans le child pipeline.

#### Couverture de test : seuil minimum 85 %

```yaml
# Python — pytest
test:<api>:
  stage: test
  script:
    - pytest \
        --cov=<package> \
        --cov-fail-under=85 \
        --cov-report=xml \
        --cov-report=term \
        --junitxml=junit.xml
  coverage: '/(?i)TOTAL.*\s+(\d+(?:\.\d+)?)%/'
  artifacts:
    when: always
    reports:
      junit: junit.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

```yaml
# Frontend — Jest
test:frontend:
  stage: test
  script:
    - npm test -- --coverage --reporters=default --reporters=jest-junit
  coverage: '/Lines\s*:\s*(\d+(?:\.\d+)?)%/'
  artifacts:
    when: always
    reports:
      junit: junit.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml
```

```javascript
// jest.config.js
coverageThreshold: {
  global: { branches: 85, functions: 85, lines: 85, statements: 85 }
}
```

#### Test coverage limits and badge colors

| Statut | Couverture | Couleur |
|---|---|---|
| Insuffisant | < 75 % | rouge |
| Warning | 75 – 85 % | jaune |
| Conforme | 85 – 95 % | vert |
| Excellent | > 95 % | vert brillant |

```markdown
![pipeline](https://gitlab.tools.thesmartcrew.com/<group>/<project>/badges/main/pipeline.svg)
![coverage](https://gitlab.tools.thesmartcrew.com/<group>/<project>/badges/main/coverage.svg)
```

### 4.10 Stage `build` — Kaniko + verify Harbor

Le stage `build` se compose de **deux jobs séquentiels** dans le DAG GitLab :

1. **`build:<api>`** — construit et pousse l'image avec **Kaniko** (image wrappée du repo CI/CD) vers **Harbor**
2. **`verify:<api>`** — interroge l'**API Harbor** pour vérifier le résultat du scan Trivy natif (auto-scan on push) **et** la présence de la signature Cosign ; si vulnérabilités `HIGH`/`CRITICAL` non whitelistées ou signature absente, fait échouer le pipeline → le stage `deploy` ne tournera pas

```
build:<api>  ──(kaniko build + push)──►  Harbor
                                           │  auto-scan Trivy on push
                                           │  auto-sign Cosign si clean
                                           │
                                           ▼
                                    verify:<api>  ──(poll API Harbor)──►  pass / fail
                                                                                │
                                                                                ▼
                                                                         deploy:<api>
```

#### Pourquoi Kaniko (pas docker-in-docker)

- Pas besoin de privilèges root ni de socket Docker exposé → réduction surface d'attaque
- Pas de service `docker:dind` à provisionner pour chaque job → builds plus rapides en démarrage
- Cache de layers natif côté Kaniko (poussé dans le registry, `--cache-repo ${IMAGE}/cache`)
- Kaniko exécute toutes les étapes du Dockerfile en userspace
- L'image Kaniko **wrappée** (repo CI/CD, `/kaniko.yml`) injecte automatiquement `--registry-mirror=dockerhub-mirror.tools.thesmartcrew.com` : tous les `FROM` Docker Hub passent par le proxy-cache Harbor (pas de rate limit)

#### Job `build:<api>`

- `extends: .kaniko_build` (ou `.kaniko_frontend_build` pour le frontend — pod sizing étendu)
- Auth : robot account Harbor (`HARBOR_ROBOT_USER` / `HARBOR_ROBOT_TOKEN`)
- Destinations poussées :
  - `${HARBOR_URL}/${HARBOR_PROJECT}/<api>:${CI_COMMIT_SHA}`
  - `${HARBOR_URL}/${HARBOR_PROJECT}/<api>:${CI_COMMIT_SHORT_SHA}`
  - `${HARBOR_URL}/${HARBOR_PROJECT}/<api>:${CI_COMMIT_TAG}` (si tag Git)
- **Jamais `:latest`** (cf. § 4.3)
- Contexte de build = racine du repo (les Dockerfiles peuvent copier `apis/shared/`)

#### Job `verify:<api>`

- Image : `harbor.tools.thesmartcrew.com/infrastructure/harbor-verify:vX.Y.Z` (pinnée)
- `needs: ["build:<api>"]`
- Poll l'API Harbor jusqu'à la fin du scan natif (timeout configurable)
- **Échoue** si :
  - vulnérabilités `HIGH` ou `CRITICAL` non présentes dans l'allow-list du projet Harbor
  - signature Cosign absente (l'auto-sign n'a pas eu lieu = scan pas clean)
- Le DAG GitLab garantit que `deploy` ne tourne que si `build` **et** `verify` passent

#### Allow-list CVE

Gérée **côté Harbor** (project-level CVE allowlist), synchronisée depuis `lint/harbor-cve-whitelist.yaml` du repo `croo-dev/ci-cd-unified-template-v1.0` (cf. § 7.5). Chaque entrée : raison + ticket + expiration max 6 mois.

Le fichier `.trivyignore` n'existe plus.

#### Limitation acceptée

Kaniko pousse l'image **avant** que le scan tourne. La fenêtre est courte et contrôlée :
- Le projet Harbor n'est jamais public
- `deploy` n'est jamais déclenché si `verify` échoue
- La retention Harbor purge les images non signées (> 30 jours)

Si un "scan avant push" strict devient nécessaire, l'option `--no-push --tar-path image.tar` + scan du tarball + push `crane` est documentée mais n'est pas le mode par défaut.

#### Sécurité des Dockerfiles

- `USER` non-root dans le Dockerfile
- `--no-install-recommends` pour `apt-get`
- Pinning des versions (pas de `latest` ni `*`)

#### Anti-patterns

1. **Pas de job `verify:<api>` après le build** — l'image serait déployable sans contrôle de scan ni signature
2. **`build:<api>` et `verify:<api>` dans des stages différents** — les deux **doivent** être dans le stage `build`, séquencés par `needs`
3. **`verify:<api>` sans `needs:`** — GitLab pourrait le lancer avant la fin du build
4. **Scan Trivy local dans le pipeline** (`aquasec/trivy`, `trivy image`) — le scan vit côté Harbor ; un scan local fait doublon et diverge de l'allow-list
5. **Push vers le GitLab Container Registry** (`${CI_REGISTRY_IMAGE}`) — il est éteint ; Harbor uniquement
6. **`DEPLOY_TOKEN_*` ou `CI_REGISTRY_*`** dans le pipeline — credentials = robot Harbor
7. **Allow-list CVE sans date d'expiration** — les exceptions deviennent permanentes
8. **Docker-in-docker (`docker:24-dind`) au lieu de Kaniko** — privilèges root, socket Docker
9. **`:latest` poussé ou déployé** — tags immuables uniquement (SHA ou tag Git)

### 4.11 Stage `smoke-test` — contrat

Le stage `smoke-test` du child pipeline (cf. § 4.2) tourne après `deploy` et **valide qu'aucun élément attendu ne manque** sur le déploiement. Objectif : exhaustivité de **présence**, pas test de fonctionnalités métier.

#### Scope par job

Un job `smoke-test` par API. Cible :
- L'**URL externe** via gateway pour les B4F (`https://${INGRESS_HOST}/<service>/...`)
- L'**URL interne** K8s pour les Backend (`http://<service>-backend-api.<namespace>.svc.cluster.local/...`)

#### Ce que le smoke-test doit vérifier

1. **Chaque endpoint de probe répond** (cf. § 5.10) :
   - `GET /liveness` → 200
   - `GET /readiness` → 200
   - `GET /startup` → 200
   - `GET /metrics` → 200, content-type `text/plain` (Prometheus)
   - `GET /health` → 200 et `status` ∈ {`healthy`, `degraded`} (jamais `unhealthy`)
2. **`/health` confirme la présence de toutes les dépendances déclarées** :
   - Backend : `postgres`, `redis`, et chaque service externe configuré
   - B4F : chaque Backend listé dans la config + service `auth`
3. **Au moins un endpoint canonique** répond sans 5xx :
   - `GET /` ou `GET /api/v1/` → 2xx, 3xx, 401 ou 404 acceptés (jamais 5xx)

#### Configuration

| Paramètre | Valeur | Description |
|---|---|---|
| Timeout total du job | 5 min | Au-delà, échec |
| Retries par check | 3 | Tolérance au rolling update |
| Délai entre retries | 10 s | Stabilisation pod |
| Délai initial | 30 s | Après `helm --wait` |
| Échec | Pipeline rouge | Pas de rollback auto, rollback manuel |

#### Implémentation côté repo partagé

```bash
#!/bin/bash
# /deploy/scripts/smoke-test.sh
set -euo pipefail

API_NAME="$1"
API_URL="$2"
EXPECTED_DEPS="$3"   # virgule-séparée, depuis values.yaml de l'API

check_endpoint() {
  local path="$1" expected="${2:-200}"
  for attempt in 1 2 3; do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${API_URL}${path}")
    [ "$code" = "$expected" ] && return 0
    sleep 10
  done
  echo "FAIL: ${path} returned ${code}, expected ${expected}"; return 1
}

check_endpoint /liveness 200
check_endpoint /readiness 200
check_endpoint /startup 200
check_endpoint /metrics 200

health=$(curl -s --max-time 10 "${API_URL}/health")
status=$(echo "$health" | jq -r '.status')
[ "$status" = "unhealthy" ] && { echo "FAIL: /health unhealthy"; exit 1; }

for dep in ${EXPECTED_DEPS//,/ }; do
  echo "$health" | jq -e ".dependencies.\"$dep\"" >/dev/null \
    || { echo "FAIL: dependency '$dep' missing in /health"; exit 1; }
done

canonical=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${API_URL}/")
case "$canonical" in
  2*|3*|404|401) ;;
  *) echo "FAIL: canonical / returned ${canonical}"; exit 1 ;;
esac

echo "OK: smoke-test passed for ${API_NAME}"
```

#### Anti-patterns

1. **Smoke-test qui teste de la logique métier** — c'est le rôle des tests d'intégration / E2E
2. **Smoke-test qui ne vérifie pas `/health`** — risque de déployer une API sans accès DB
3. **Smoke-test sans retry** — un rolling update prend quelques secondes
4. **Rollback automatique sur échec** — décision humaine (cf. § 4.2)
5. **Smoke-test qui consomme des credentials applicatifs** — les probes sont non protégées (cf. § 5.10)

### 4.12 Anti-patterns

1. Logique CI/CD ou Helm dupliquée dans le projet
2. `include:` avec `ref: main`
3. Stages au-delà des 5
4. Stage de migration séparé
5. Déploiement automatique sur staging ou prod
6. Tag `latest` ou tag mutable
7. Branchement conditionnel par nom d'API
8. Commandes Helm inline
9. `kubectl apply` pour les APIs
10. Backends dans l'ingress gateway
11. Commandes différentes selon le stage
12. `allow_failure: true` dans le child pipeline
13. Job `test:*` sans seuil 85 %
14. Job `test:*` sans rapport JUnit ni Cobertura
15. `artifacts:when: on_success` sur les jobs `test:*`
16. `coverage:` regex absent
17. Parallélisme custom contournant `CICD_MAX_PARALLEL_JOBS`

---

## 5. Configuration Kubernetes

### 5.1 Convention de noms d'environnements

Noms canoniques : **`dev`**, **`staging`**, **`prod`**. Pas d'exception.

Si un projet utilise `production`, le renommer **partout** (variables CI/CD, GitLab Environments, manifests, scripts, doc, labels K8s).

### 5.2 Stratégie de scoping dev + reviews

Variables CI/CD en **scope global** (sans scope d'env) pour que les **reviews** héritent de dev.

| Scope GitLab | Concerne |
|---|---|
| (aucun, global) | `dev` + tous les environnements de review |
| `staging` | environnement staging |
| `prod` | environnement production |

#### Variables dynamiques pour review

| Variable | En `dev` | En review |
|---|---|---|
| `NAMESPACE` | Variable globale (`asq-dev`) | `${CI_PROJECT_NAME}-review-${CI_MERGE_REQUEST_IID}` |
| `INGRESS_HOST` | Variable globale (`dev.asq.example.com`) | `mr-${CI_MERGE_REQUEST_IID}.asq.example.com` |

Le pipeline détecte le contexte review via `CI_MERGE_REQUEST_IID` et **override**.

### 5.3 NAMESPACE depuis variable scopée

```yaml
# CORRECT — défini dans GitLab Variables
#   NAMESPACE = asq-dev       (global → dev + review)
#   NAMESPACE = asq-staging   (scope: staging)
#   NAMESPACE = asq-prod      (scope: prod)
```

**Convention `<projet>-<env>`** : namespace prod = `<projet>-prod`, **jamais** juste `<projet>`.

### 5.4 KUBECONFIG via indirection KUBECONFIG_VARIABLE

#### Type des variables système : File (jamais Variable / jamais base64)

Les kubeconfigs sont stockés en **variables CI/CD de type `File`**.

#### Correct

```bash
if [ -z "${KUBECONFIG_VARIABLE:-}" ]; then
  echo "ERROR: KUBECONFIG_VARIABLE is not set"
  exit 1
fi

eval "KUBECONFIG_REF=\$$KUBECONFIG_VARIABLE"
if [ -z "${KUBECONFIG_REF:-}" ]; then
  echo "ERROR: ${KUBECONFIG_VARIABLE} is empty"
  exit 1
fi

if [ ! -f "${KUBECONFIG_REF}" ]; then
  echo "ERROR: ${KUBECONFIG_VARIABLE} ne pointe pas sur un fichier valide."
  echo "Vérifier qu'elle est configurée en type 'File' dans GitLab CI/CD."
  exit 1
fi
export KUBECONFIG="${KUBECONFIG_REF}"
```

### 5.5 Variables CI/CD requises

#### Niveau projet

| Variable | Scope | Type | Valeur exemple |
|---|---|---|---|
| `NAMESPACE` | global | Variable | `asq-dev` |
| `NAMESPACE` | staging | Variable | `asq-staging` |
| `NAMESPACE` | prod | Variable | `asq-prod` |
| `INGRESS_HOST` | global | Variable | `dev.asq.example.com` |
| `INGRESS_HOST` | staging | Variable | `staging.asq.example.com` |
| `INGRESS_HOST` | prod | Variable | `app.example.com` |
| `KUBECONFIG_VARIABLE` | global | Variable | `OVH_KUBECONFIG` |
| `KUBECONFIG_VARIABLE` | staging | Variable | `OVH_KUBECONFIG_STAGING` |
| `KUBECONFIG_VARIABLE` | prod | Variable | `OVH_KUBECONFIG_PROD` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | par env | Variable | `http://alloy.observability.svc.cluster.local:4317` |
| `PROMETHEUS_URL` | par env | Variable | `https://prometheus-dev.example.com` |

#### Niveau instance/groupe GitLab (admin)

| Variable | Type | Description |
|---|---|---|
| `OVH_KUBECONFIG` | **File** | Cluster dev |
| `OVH_KUBECONFIG_STAGING` | **File** | Cluster staging |
| `OVH_KUBECONFIG_PROD` | **File** | Cluster prod |

### 5.6 Exceptions

- `CI_JOB_TOKEN` pour `docker login` en build : acceptable
- Reviews : `NAMESPACE` et `INGRESS_HOST` calculés dynamiquement

### 5.7 Certificats TLS et Ingress

Deux stratégies :
- **Wildcard** : `*.<domaine>` couvre plusieurs sous-domaines (dev + reviews)
- **Spécifique** : certificat dédié au host (staging, prod)

#### Stratégie de résolution

1. **Tester l'existence d'un wildcard** dans `cert-manager` couvrant l'`INGRESS_HOST`
2. **Si oui** → copier le secret du wildcard dans le namespace de déploiement
3. **Si non** → faire émettre un certificat spécifique par cert-manager dans le namespace cible

#### Logique de déploiement

```bash
INGRESS_HOST="${INGRESS_HOST}"
INGRESS_DOMAIN="${INGRESS_HOST#*.}"
WILDCARD_SECRET_NAME="wildcard-${INGRESS_DOMAIN//./-}-tls"

if kubectl -n cert-manager get secret "${WILDCARD_SECRET_NAME}" >/dev/null 2>&1; then
  kubectl get secret "${WILDCARD_SECRET_NAME}" -n cert-manager -o yaml \
    | sed -e "s/namespace: cert-manager/namespace: ${NAMESPACE}/" \
          -e "/^  resourceVersion:/d" \
          -e "/^  uid:/d" \
          -e "/^  creationTimestamp:/d" \
    | kubectl apply -n "${NAMESPACE}" -f -
  TLS_STRATEGY="wildcard"
  TLS_SECRET="${WILDCARD_SECRET_NAME}"
else
  TLS_STRATEGY="specific"
  TLS_SECRET="${API_NAME}-tls"
fi

helm upgrade --install "${API_NAME}" .../api-chart \
  --namespace "${NAMESPACE}" \
  --values "${VALUES_FILE}" \
  --set tls.strategy="${TLS_STRATEGY}" \
  --set tls.secretName="${TLS_SECRET}" \
  --wait --timeout 5m
```

#### Règles
- Tester systématiquement le wildcard **avant** émission spécifique
- Le wildcard est émis **uniquement** dans le namespace `cert-manager`
- Le chart porte les deux modes via `tls.strategy`
- Copy idempotent (`kubectl apply`)

### 5.8 Observabilité — logs et monitoring centralisés

**Alloy** en DaemonSet sur chaque cluster ramasse logs (stdout/stderr), métriques (Prometheus scrape) et traces (OTLP).

#### Variables CI/CD

| Variable | Scope | Description |
|---|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | par env | URL OTLP Alloy. Typiquement `http://alloy.observability.svc.cluster.local:4317` |
| `PROMETHEUS_URL` | par env | URL Prometheus pour les jobs CI |

#### Variables OpenTelemetry standard injectées par le chart

| Variable | Source | Exemple |
|---|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | CI/CD | `http://alloy.observability.svc.cluster.local:4317` |
| `OTEL_SERVICE_NAME` | Chart (= `${API_NAME}`) | `rooms-backend-api` |
| `OTEL_RESOURCE_ATTRIBUTES` | Chart | `deployment.environment=prod,service.version=v1.2.3` |
| `OTEL_TRACES_SAMPLER` | Chart | `parentbased_traceidratio` |
| `OTEL_TRACES_SAMPLER_ARG` | Chart | `1.0` en dev, `0.1` en prod |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | Chart | `grpc` |

#### Règles côté application

- **Logs** : stdout/stderr en JSON structuré (jamais sur disque)
- **Métriques** : endpoint `/metrics` exposé
- **Traces** : SDK OTel via `OTEL_EXPORTER_OTLP_ENDPOINT`, instrumentation auto privilégiée
- **Pas d'agent propriétaire** (Datadog, New Relic...) — Alloy fait tout

#### Anti-patterns
1. Logs dans des fichiers
2. Push direct vers backend distant (bypass Alloy)
3. URL OTLP hardcodée
4. Agent propriétaire dans les images
5. Logs non structurés en prod
6. Sampling 100 % en prod

### 5.9 Tracing distribué et propagation du `trace_id`

L'instrumentation OTel (cf. § 5.8) génère et propage un `trace_id` à travers tous les composants. Le backend **Tempo** (Grafana stack) sera utilisé pour stocker et afficher les traces.

#### Standard W3C Trace Context

Propagation via le header HTTP `traceparent` :

```
traceparent: 00-<trace-id>-<span-id>-<flags>
                  ^ 32 hex      ^ 16 hex
```

#### Chemin complet d'une trace

```
[User Action]
     |
     v genère trace_id
Frontend (Angular)
     | Header: traceparent
     v
API Gateway / Ingress (pass-through)
     |
     v
B4F API
     | enrichit la trace de spans (use case, transformation...)
     |--- httpx auto-inject `traceparent` ---> Backend API #1
     |--- httpx auto-inject `traceparent` ---> Backend API #2
     | tous les spans -> OTLP -> Alloy -> Tempo
     v
[Réponse Frontend]
```

Pour les **événements asynchrones** sur Redis :

```
Backend A
     | écriture DB OK
     | publie event avec trace_id dans le payload (cf. § 2.4)
     v
Redis pub/sub
     v
Backend B (subscriber)
     | extrait trace_id du payload
     | ouvre un nouveau span rattaché au trace_id parent
     v
[Side effect]
```

#### Propagation par couche

| Couche | Mécanisme | Notes |
|---|---|---|
| Frontend Angular | `HttpInterceptor` ou OTel Web SDK | Génère `trace_id` par "navigation" ou "user action" |
| API Gateway | Pass-through `traceparent` | Aucune transformation |
| B4F → Backend (HTTP) | Auto-instrumentation `httpx` / FastAPI | `traceparent` injecté automatiquement |
| Backend → Backend (event bus) | **Manuel** : champ `trace_id` dans payload JSON | Subscriber extrait et continue la trace |
| Logs JSON | Champ `trace_id` extrait du span actif | Drill-down log → trace dans Grafana |

#### Implémentation Python — publisher

```python
# infrastructure/messaging/publisher.py
from opentelemetry import trace

def publish(channel: str, data: dict, tenant_id: str) -> None:
    span = trace.get_current_span()
    trace_id_hex = format(span.get_span_context().trace_id, "032x")
    payload = {
        "event": channel,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "tenant_id": tenant_id,
        "trace_id": trace_id_hex,
        "data": data,
    }
    redis.publish(channel, json.dumps(payload))
```

#### Implémentation Python — subscriber

```python
# infrastructure/messaging/subscriber.py
from opentelemetry import trace
from opentelemetry.trace import SpanContext, TraceFlags, NonRecordingSpan

def handle(message: bytes) -> None:
    payload = json.loads(message)
    trace_id_hex = payload.get("trace_id")
    if trace_id_hex:
        ctx = SpanContext(
            trace_id=int(trace_id_hex, 16),
            span_id=0,
            is_remote=True,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        with trace.use_span(NonRecordingSpan(ctx)):
            with tracer.start_as_current_span(f"subscriber.{payload['event']}"):
                process(payload)
```

#### Implémentation Frontend — interceptor minimal

```typescript
// presentation/interceptors/traceparent.interceptor.ts
@Injectable()
export class TraceparentInterceptor implements HttpInterceptor {
  intercept(req: HttpRequest<any>, next: HttpHandler) {
    const traceId = this.generateTraceId();   // 32 hex chars
    const spanId = this.generateSpanId();     // 16 hex chars
    const traceparent = `00-${traceId}-${spanId}-01`;
    return next.handle(req.clone({
      setHeaders: { traceparent }
    }));
  }
}
```

À terme, remplacer par le **OpenTelemetry Web SDK** complet pour des spans côté navigateur.

#### Inclusion du `trace_id` dans tous les logs

Tous les logs JSON émis par les APIs **DOIVENT** inclure `trace_id` (et `span_id` si possible) :

```json
{
  "timestamp": "2024-05-08T14:23:11.123Z",
  "level": "INFO",
  "service": "rooms-backend-api",
  "message": "Room created",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "tenant_id": "acme",
  "room_id": "..."
}
```

Permet le drill-down dans Grafana : depuis un log, accès direct à la trace dans Tempo.

#### Anti-patterns

1. **`traceparent` non propagé** entre B4F et Backend — la trace s'interrompt à la frontière HTTP
2. **`trace_id` absent du payload event bus** — la trace s'interrompt à la frontière asynchrone
3. **Logs sans `trace_id`** — impossible de corréler logs et traces dans Grafana
4. **Génération de `trace_id` aléatoire à chaque service** — chaque service crée sa propre trace
5. **Sampling 1.0 en prod** — coût Tempo prohibitif, garder 0.1 par défaut

### 5.10 Probes Kubernetes et endpoints de santé

Toutes les APIs (B4F et Backend) exposent **cinq endpoints non protégés** dédiés à la santé et à l'observabilité. C'est le **contrat opérationnel commun** : K8s s'en sert pour ses probes, le smoke-test du pipeline les vérifie (cf. § 4.11), Alloy scrape `/metrics`, et les ops ont une vue uniforme du parc.

#### Endpoints exposés

Tous les endpoints sont **non authentifiés** et **non autorisés** (les probes K8s n'ont pas de credentials applicatifs). Ils ne renvoient **aucune donnée métier sensible** — uniquement de l'état technique.

| Endpoint | Code | Réponse | Usage |
|---|---|---|---|
| `GET /liveness` | 200 si processus tourne | `{"status": "alive"}` | K8s livenessProbe |
| `GET /readiness` | 200 si peut servir le trafic | `{"status": "ready"}` | K8s readinessProbe |
| `GET /startup` | 200 quand init terminé | `{"status": "started"}` | K8s startupProbe |
| `GET /health` | 200 healthy/degraded, 503 unhealthy | JSON détaillé | Smoke-test, dashboards, debug |
| `GET /metrics` | 200 | Format Prometheus | Scrape par Alloy |

#### Sémantique précise

- **`/liveness`** : "le processus tourne et peut servir une requête HTTP". **Aucun appel externe** — pas de DB, pas de Redis, pas de Backend. Si KO, K8s tue le pod.
- **`/readiness`** : "l'API a fini son init et peut servir du trafic métier". Vérifie les **dépendances critiques au démarrage**. Si KO, K8s retire du Service mais ne tue pas.
- **`/startup`** : "l'init applicatif est terminé". Pour apps lentes à démarrer. K8s désactive liveness/readiness tant que `/startup` ne renvoie pas 200.
- **`/health`** : check **complet** des dépendances avec timing. **N'est pas utilisé par les probes K8s** (trop coûteux en boucle 10s) — sert au smoke-test et à l'humain.
- **`/metrics`** : exposition Prometheus standard.

#### Contrat JSON de `/health`

```json
{
  "status": "healthy",
  "timestamp": "2024-05-08T14:23:11.123Z",
  "service": "rooms-backend-api",
  "version": "v1.2.3",
  "dependencies": {
    "postgres": {
      "status": "healthy",
      "latency_ms": 5
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 2
    },
    "external_pms": {
      "status": "degraded",
      "latency_ms": 1450,
      "error": "timeout > 1000ms"
    }
  }
}
```

**Règles de calcul du `status` global :**
- `healthy` : toutes les dépendances healthy
- `degraded` : au moins une dépendance non-critique dégradée mais l'API reste fonctionnelle
- `unhealthy` : au moins une dépendance critique KO → l'API ne peut plus servir

Code HTTP :
- `healthy` ou `degraded` → `200 OK`
- `unhealthy` → `503 Service Unavailable`

**Règles d'inclusion des dépendances :**
- Backend : DB (PgBouncer), Redis, chaque service externe consommé
- B4F : chaque Backend appelé (DNS interne K8s) + service `auth`
- Chaque check rapide en parallèle (timeout 1s typique)
- `/health` répond en < 2s même en cas de dégradation

#### Configuration K8s — chart partagé

```yaml
livenessProbe:
  httpGet:
    path: /liveness
    port: http
  periodSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /readiness
    port: http
  periodSeconds: 5
  failureThreshold: 2

startupProbe:
  httpGet:
    path: /startup
    port: http
  periodSeconds: 5
  failureThreshold: 60     # 5 min max d'init avant kill
```

#### Implémentation côté API

- Endpoints dans `presentation/` (cf. § 12.2)
- Checks de dépendances via Ports (`HealthCheckPort`) implémentés dans `infrastructure/`
- Pas de logique métier
- Les checks DB **n'utilisent pas le pool applicatif** : mini-pool dédié de 1 connexion ou raw `SELECT 1` court (libère immédiatement)

#### Anti-patterns

1. **Endpoints de santé authentifiés** — les probes K8s n'ont pas de token
2. **`/liveness` qui ping la DB** — fait redémarrer le pod si la DB hoquette → cascade
3. **`/health` qui consomme des connexions du pool applicatif** — peut épuiser le pool
4. **`/health` qui renvoie de la donnée métier** (compteurs d'utilisateurs...) — fuite d'info
5. **Logique métier dans les checks** — un health check est binaire
6. **Différentes APIs avec différents formats de `/health`** — uniformité requise (cf. § 12.1)

### 5.11 API Gateway — Ingress unique du namespace

Tout le trafic externe entrant transite par **un seul Ingress**, le **gateway**, déployé via le chart `gateway-chart` du repo CI/CD partagé. Ni les B4F ni le frontend n'ont d'Ingress propre.

#### Responsabilités

1. **Routage** par préfixe de chemin :
   - `/` → Service `frontend` (port 80)
   - `/api/<service>` → Service `<service>-b4f-api` (port 80), avec rewrite du préfixe `/api/<service>` → `/`
2. **Terminaison TLS** avec un certificat **wildcard** copié depuis le namespace `cert-manager` au déploiement (cf. § 5.7)
3. **Redirection HTTP → HTTPS** forcée sur 100 % du trafic
4. **CORS** géré globalement (annotations NGINX)

#### Manifeste de référence

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-gateway
  namespace: {{ .Release.Namespace }}
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "20m"
    # Rewrite : /api/auth/login → /login pour la B4F auth-b4f-api
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - {{ .Values.host }}
      secretName: {{ .Values.tls.secretName }}        # wildcard copié
  rules:
    - host: {{ .Values.host }}
      http:
        paths:
          # 1) Routage API : /api/<service>(/...) -> <service>-b4f-api
          {{- range .Values.routes.apis }}
          - path: /api/{{ .name }}/v1(/|$)(.*)
            pathType: ImplementationSpecific
            backend:
              service:
                name: {{ .service }}                 # ex. auth-b4f-api
                port:
                  number: 80
          {{- end }}
          # 2) Catch-all : / -> frontend
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
```

#### Annotations obligatoires

| Annotation | Valeur | Raison |
|---|---|---|
| `nginx.ingress.kubernetes.io/ssl-redirect` | `"true"` | Redirige HTTP → HTTPS (308) |
| `nginx.ingress.kubernetes.io/force-ssl-redirect` | `"true"` | Force la redirection même derrière un proxy en HTTP |
| `nginx.ingress.kubernetes.io/use-regex` | `"true"` | Active la regex sur les paths `/api/<svc>/v1(/|$)(.*)` (Ingress API uniquement) |
| `nginx.ingress.kubernetes.io/rewrite-target` | `/$2` | Réécrit le path avant de passer au pod B4F (Ingress API uniquement — l'Ingress frontend n'a **pas** de rewrite pour préserver les chemins des assets statiques) |

> Pour un autre ingress controller (Traefik, HAProxy...) : adapter les annotations mais conserver le contrat fonctionnel (TLS unique, HTTPS forcé, routage `/` et `/api/<service>`).

#### Copie du certificat wildcard

Le secret TLS wildcard (ex. `wildcard-example-com-tls`) est émis par cert-manager dans le namespace `cert-manager`. Le `gateway-chart` embarque un **Job de copie** (RBAC limité) qui :

1. Lit le secret source depuis `cert-manager/<wildcard-secret>`
2. Crée/met à jour le secret cible dans le namespace de déploiement
3. Tourne à chaque `helm upgrade` (idempotent)

Une alternative recommandée si disponible cluster-wide : **`reflector`** ou **`kubed`** annote le secret source et la copie est automatique. Le Job du chart reste le fallback de référence pour ne pas dépendre d'un opérateur externe.

#### Routes attendues

Le `gateway-chart` reçoit en values la liste des routes API :

```yaml
# values overridé par le pipeline avec discover-apis.sh
host: dev.app.example.com
tls:
  secretName: wildcard-example-com-tls
routes:
  apis:
    - name: auth                  # → /api/auth/...
      service: auth-b4f-api
    - name: rooms
      service: rooms-b4f-api
    - name: front-office
      service: front-office-b4f-api
```

La liste est **générée automatiquement** par `discover-apis.sh` qui scanne `apis/exposed/` et déduit `name = <api>-b4f-api`'s prefix sans suffixe `-b4f-api`.

#### Règles

- **Aucun pod n'a son propre Ingress.** Tout passe par le gateway.
- **Un seul certificat TLS** dans le namespace (le wildcard copié). Pas de certificat par B4F.
- Le gateway est déployé en **dernier** dans la séquence du stage `deploy` (après frontend + toutes les APIs).
- Le `helm upgrade` du gateway est **toujours full** (pas de partial deploy) : il représente la photo du routage à un instant T.
- Si une B4F est ajoutée/supprimée, la pipeline régénère les values du gateway et redéploie.

#### Anti-patterns

1. **Une B4F qui définit son propre Ingress** — viole la centralisation
2. **Pas de force-ssl-redirect** — du HTTP en clair peut atteindre les pods
3. **Un certificat émis dans chaque namespace cible** — gaspille des challenges ACME et alourdit cert-manager
4. **Le frontend exposé via une URL différente du gateway** — casse le modèle d'origine unique (et le CORS devient un problème)
5. **Routage manuel codé en dur dans `gateway-chart/values.yaml`** — utiliser `discover-apis.sh` pour rester en phase

### 5.12 Frontend chart — paritaire avec les APIs

Le frontend Angular (cf. § 3) est déployé via un **Helm chart dédié** (`frontend-chart`, distinct de `api-chart`) du repo CI/CD partagé. Cette parité avec les APIs garantit que tout le déploiement est piloté par les mêmes scripts génériques.

#### Contenu du chart

- `Deployment` (réplicas, probes, OTel env)
- `Service` ClusterIP sur le port 80 → port du conteneur Angular (80 si NGINX statique, 4200 si servi par Node en SSR)
- **Pas d'Ingress** (le gateway s'en charge)
- `ServiceAccount` avec `imagePullSecrets`

#### Probes spécifiques

Le frontend expose des probes statiques (pas de logique applicative) :
- `/healthz` (200 OK statique servi par NGINX)
- `/` (200 OK = SPA chargée)

Liveness/readiness pointent sur `/healthz`.

#### Build et image

- Image construite via `.kaniko_frontend_build` (cf. § 4.10) qui réserve plus de CPU/RAM pour le bundling Angular
- Tag = `${CI_COMMIT_SHA}` (jamais `:latest` côté déploiement, même si le wrapped Kaniko tague aussi `:latest` côté registry)

#### Values

```yaml
# deploy/values/<env>/frontend.yaml côté projet
image:
  repository: gitlab.tools.thesmartcrew.com:5050/<group>/<project>/frontend
  tag: ""                  # set par --set par le pipeline
replicaCount: 2
resources:
  requests: { cpu: 50m, memory: 64Mi }
  limits:   { cpu: 200m, memory: 256Mi }
env:
  - name: API_BASE_URL
    value: /api            # le frontend tape sur son origine, pas en cross-domain
```

#### Anti-patterns

1. **Frontend déployé en dehors de Helm** (kubectl apply manuel) — perd la cohérence rollback
2. **Frontend qui appelle un Backend directement** — viole § 2 (passage obligatoire par B4F via gateway)
3. **`API_BASE_URL` pointant ailleurs que `/api`** — casse le modèle origine unique
4. **Build du frontend avec `.kaniko_build` standard** — manque de RAM, builds lents/instables
5. **Frontend avec son propre Ingress** — viole § 5.11

---

## 6. Variables d'environnement — Scoping GitLab

### 6.1 Règle

**Jamais** de préfixes `DEV_`, `STAGING_`, `PROD_`. **Utiliser le scoping GitLab natif.**

### 6.2 Pourquoi
1. Bloat de scripts (résolution dynamique au runtime)
2. Sprawl de secrets (3 variables au lieu d'1)
3. Indirection fragile (`${!VAR_NAME}`)
4. Non portable

### 6.3 Comparaison

| Faux | Correct | Scope |
|---|---|---|
| `DEV_KUBECONFIG` | `KUBECONFIG_VARIABLE` → `OVH_KUBECONFIG` | dev (global) |
| `DEV_DATABASE_HOST` | `DB_HOST` | dev (global) |

### 6.4 Migration

1. Project > Settings > CI/CD > Variables
2. Créer la variable au nom non préfixé
3. Définir le scope (`staging`, `prod`) — **pas de scope `dev`** (utiliser global)
4. Définir la valeur
5. Supprimer l'ancienne variable préfixée
6. Mettre à jour `.gitlab-ci.yml` et scripts

---
## 7. Harbor — registry primaire

### 7.1 Architecture

````
Build job (Kaniko) ──push──► Harbor (harbor.tools.thesmartcrew.com)
                                │  - auto-scan Trivy on push
                                │  - signature Cosign auto si scan clean
                                │  - retention : purge images non signées > 30j
                                │
                                │ pull (robot account / imagePullSecret)
                                ▼
                        Kubernetes nodes (containerd)
````

**Harbor est le registry unique.** Le GitLab Container Registry est éteint : aucune image n'y est poussée ni tirée.

- **1 projet Harbor par projet GitLab** — path d'image : `harbor.tools.thesmartcrew.com/<HARBOR_PROJECT>/<api>:<sha>`
- **Auto-scan Trivy on push** côté Harbor — pas de scan dans le pipeline
- **Signature Cosign automatique** quand le scan est clean
- Le proxy-cache Docker Hub (`dockerhub-mirror.tools.thesmartcrew.com`) vit aussi dans Harbor — utilisé par l'image Kaniko wrappée pour les `FROM` des Dockerfiles

### 7.2 Stratégie credentials — robot accounts

L'authentification passe par un **robot account Harbor** par projet (jamais de compte humain, jamais de deploy token GitLab) :

- **Nom** : `robot$<projet>+ci`
- **Permissions** : push + pull + scan:read + scan:create + artifact:read
- **Rotation** : 90 jours

Le pipeline provisionne dans chaque namespace :

1. Un **Secret** Kubernetes `docker-registry` (`harbor-registry-cred`) pointant sur `https://${HARBOR_URL}`
2. Un **ServiceAccount** dédié (`harbor-registry-deployer`) avec `imagePullSecrets`

Les pods utilisent ce ServiceAccount → restart/scale/reschedule **sans dépendre du CI/CD**.

### 7.3 Variables CI/CD

| Variable | Scope | Type | Protégée | Masquée | Exemple |
|---|---|---|---|---|---|
| `HARBOR_URL` | aucun | Variable | Non | Non | `harbor.tools.thesmartcrew.com` |
| `HARBOR_PROJECT` | aucun | Variable | Non | Non | `asq` |
| `HARBOR_ROBOT_USER` | aucun | Variable | Oui | Non | `robot$asq+ci` |
| `HARBOR_ROBOT_TOKEN` | aucun | Variable | Oui | Oui | — |

#### Variables optionnelles

| Variable | Default | Description |
|---|---|---|
| `K8S_SERVICE_ACCOUNT` | `harbor-registry-deployer` | Nom du ServiceAccount |
| `K8S_REGISTRY_SECRET` | `harbor-registry-cred` | Nom du Secret docker-registry |

**Supprimés** (n'existent plus) : `DEPLOY_TOKEN_USER`, `DEPLOY_TOKEN_PASSWORD`, toute variable `CI_REGISTRY_*` dans les scripts du pipeline.

### 7.4 Setup d'un nouveau projet

1. Créer le **projet Harbor** (1:1 avec le projet GitLab) sur `harbor.tools.thesmartcrew.com`
2. Configurer : auto-scan on push, severity gate HIGH/CRITICAL, auto-sign Cosign sur clean scan, retention purge images non signées > 30 jours
3. Créer le **robot account** `robot$<projet>+ci` avec les permissions listées en § 7.2
4. Provisionner les 4 variables CI/CD (§ 7.3)
5. Lancer `provision-registry-access:<env>` sur chaque environnement (crée Secret + ServiceAccount)

### 7.5 Allow-list CVE

Les CVEs acceptées sont gérées **côté Harbor** (project-level CVE allowlist), synchronisées depuis le fichier versionné `lint/harbor-cve-whitelist.yaml` du repo `croo-dev/ci-cd-unified-template-v1.0`.

Règles inchangées : raison documentée + ticket + **date d'expiration max 6 mois** + revue trimestrielle.

Le fichier `.trivyignore` n'existe plus (le scan ne tourne plus dans le pipeline).

### 7.6 Mécanisme d'indirection du kubeconfig

(inchangé — cf. § 5.4)

````
Projet CI/CD                            GitLab Instance (admin)
-------------                           ----------------------
KUBECONFIG_VARIABLE=                    OVH_KUBECONFIG (type File)
  "OVH_KUBECONFIG"               --->     -> chemin du fichier
  (global, dev + review)

KUBECONFIG_VARIABLE=                    OVH_KUBECONFIG_STAGING (type File)
  "OVH_KUBECONFIG_STAGING"       --->     -> chemin du fichier
  (scope: staging)

KUBECONFIG_VARIABLE=                    OVH_KUBECONFIG_PROD (type File)
  "OVH_KUBECONFIG_PROD"          --->     -> chemin du fichier
  (scope: prod)
````

Résolution : `eval echo "\$$KUBECONFIG_VARIABLE"` → chemin de fichier → `export KUBECONFIG=$KUBECONFIG_REF`. **Aucun décodage base64.**

### 7.7 Stages du pipeline

**`build`** — Kaniko (image wrappée du repo CI/CD) : auth robot Harbor, build + push vers `${HARBOR_URL}/${HARBOR_PROJECT}/<api>` avec tags `:${CI_COMMIT_SHA}` + `:${CI_COMMIT_SHORT_SHA}` (+ `:${CI_COMMIT_TAG}` si tag Git). **Jamais `:latest`.**

**`verify`** — (remplace l'ancien scan local) : poll l'API Harbor jusqu'à fin du scan natif, échoue si vulnérabilités HIGH/CRITICAL non whitelistées ou si la signature Cosign manque. Image : `harbor.tools.thesmartcrew.com/infrastructure/harbor-verify:vX.Y.Z`.

**`provision-registry-access`** (job partagé, idempotent, manuel) :
1. Résout le kubeconfig par indirection
2. Crée le Secret `docker-registry` pointant sur `https://${HARBOR_URL}` (`--dry-run=client | kubectl apply`)
3. Crée le ServiceAccount avec `imagePullSecrets`

**`deploy-*`** — `helm upgrade --install` avec `IMAGE=${HARBOR_URL}/${HARBOR_PROJECT}/<api>:<sha>`. Le pod utilise `serviceAccountName`.

### 7.8 Renouvellement du robot account

1. Régénérer le token du robot dans Harbor (ou créer un nouveau robot)
2. Mettre à jour les variables CI/CD :
   ```bash
   glab variable update HARBOR_ROBOT_USER  --value "robot\$<projet>+ci"
   glab variable update HARBOR_ROBOT_TOKEN --value "<nouveau-token>"
   ```
3. Relancer `provision-registry-access` par environnement
4. Révoquer l'ancien token

### 7.9 Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `ImagePullBackOff` après restart | Secret manquant ou robot token expiré | `kubectl get secret -n <NS>` + vérifier le robot Harbor |
| `unauthorized` au push Kaniko | `HARBOR_ROBOT_*` erronés ou robot sans permission push | Vérifier le robot account dans Harbor UI |
| Job `verify` timeout | Scan Harbor lent ou image énorme | Augmenter le timeout du job, vérifier la file de scan Harbor |
| `verify` échoue sur CVE connue | CVE pas dans l'allow-list Harbor | PR sur `lint/harbor-cve-whitelist.yaml` + sync |
| `verify` échoue sur signature | Cosign auto-sign non configuré côté projet Harbor | Vérifier la config auto-sign du projet Harbor |
| Pod ne pull pas malgré le secret | Mauvais ServiceAccount | Vérifier `serviceAccountName` = `harbor-registry-deployer` |

---

## 8. Checklist consolidée de revue

### 8.1 Architecture des APIs
- [ ] Aucun `*-backend-api` dans `apis/exposed/`
- [ ] Aucun `*-b4f-api` dans `apis/internal/`
- [ ] Aucune B4F avec `alembic/`, modèles DB, `DATABASE_URL`
- [ ] Aucune Backend dans les routes ingress
- [ ] Aucune URL `*-backend-api` côté frontend
- [ ] Aucune API monolithique sans suffixe
- [ ] Aucun HTTP entre Backends (event bus uniquement)
- [ ] Une entité principale par Backend
- [ ] Chaque B4F mappe un domaine frontend
- [ ] B4F minimisent les allers-retours
- [ ] Tous les Backends utilisent les mêmes `DB_HOST`/`DB_USERNAME`/`DB_PASSWORD`/`DB_DATABASE`/`DATABASE_SSLMODE`
- [ ] Chaque Backend possède un schéma au nom du service
- [ ] Pool SQLAlchemy : `pool_size` ≤ 5, `max_overflow` ≤ 5, `pool_pre_ping=True`
- [ ] Prepared statements désactivés
- [ ] Aucun `metadata.create_all()`, `db.create_all()` ou DDL au startup
- [ ] Migrations exécutées via initContainer, jamais depuis runner CI
- [ ] **Toute DDL passe par Alembic** — y compris CREATE SCHEMA initial, droits, seeds reproductibles
- [ ] **Aucun fichier `.sql` exécuté hors d'Alembic** (pas de `db/init.sql`, `seed.sql`, `psql -f ...`)
- [ ] **Chaque révision a un `downgrade()` non vide et symétrique** à l'`upgrade()`
- [ ] Aucun `downgrade(): pass` ni `raise NotImplementedError`
- [ ] La CI du Backend exécute `alembic downgrade -1 && alembic upgrade head` sur la dernière révision
- [ ] InitContainer `migrate` exécute `scripts/migrate_with_lease.py`
- [ ] `MIGRATION_SERVICE` + `MIGRATION_NAMESPACE` (fieldRef) injectés dans l'initContainer migrate
- [ ] RBAC Lease (`migration-lease-rbac.yaml`) déployé pour le ServiceAccount du Backend
- [ ] `helm upgrade --wait` + récupération des logs sur échec
- [ ] Stratégie `RollingUpdate` avec `maxSurge: 1, maxUnavailable: 0`
- [ ] Migrations idempotentes
- [ ] Redis présent dans docker-compose et Helm

### 8.2 Frontend
- [ ] Un service Angular par B4F
- [ ] Un feature NGRX par B4F
- [ ] Aucune injection de service dans les components
- [ ] Aucune variable statique cachant un observable
- [ ] Aucun HTTP hors des Effects
- [ ] Templates utilisent `| async`
- [ ] Tests E2E Playwright présents dans `frontend/e2e/` (cf. § 3.8)
- [ ] Tests E2E **absents** du pipeline CI (lancement manuel uniquement)
- [ ] Hook git pre-commit configuré (husky) pour lancer les E2E `@smoke` sur changement frontend
- [ ] Wrapper racine `run_frontend_e2e.sh` présent (cf. § 11.1)
- [ ] Tests E2E critiques tagués `@smoke` pour exécution rapide en pre-commit

### 8.3 Pipeline CI/CD
- [ ] `.gitlab-ci.yml` du projet ne contient que des `include:` du repo partagé
- [ ] Aucun `deploy/scripts/`, `deploy/helm/templates/`, `Chart.yaml` côté projet
- [ ] `include:` versionné via tag (jamais `main`)
- [ ] `deploy/values/{env}/<api>.yaml` pour chaque API × env
- [ ] Pipeline parent (`discover`) + child (5 stages : test, build, deploy, smoke-test, rollback)
- [ ] Aucun stage en dehors de ces 5
- [ ] Backends ont un initContainer `migrate`
- [ ] Backends absents de l'ingress gateway
- [ ] B4F sans initContainer migrate
- [ ] Déclencheurs : push `main` → dev auto, MR → review auto, tag `v*` → build + deploy staging/prod manuel
- [ ] Build sur tag `v*` → image taggée `${CI_COMMIT_TAG}`, label OCI
- [ ] Staging et prod déploient le tag `v*`, redéploiement sans rebuild
- [ ] Aucun déploiement auto sur staging ou prod
- [ ] Aucun tag `latest` ni mutable
- [ ] Pas de noms d'API hardcodés
- [ ] Pas de nom de projet hardcodé (`CI_PROJECT_PATH`)
- [ ] Aucun branchement conditionnel par nom d'API
- [ ] `helm upgrade --install` est le seul mécanisme
- [ ] `CICD_MAX_PARALLEL_JOBS` respectée
- [ ] Aucun `allow_failure: true`
- [ ] Chaque `test:*` enforce 85 % de couverture
- [ ] Chaque `test:*` produit un JUnit
- [ ] Chaque `test:*` produit un Cobertura
- [ ] `coverage:` regex configuré
- [ ] `artifacts:when: always`
- [ ] Coverage thresholds 75/85/95 dans Project Settings
- [ ] Badges pipeline + coverage dans le `README.md`
- [ ] `/deploy/scripts/` n'existe que dans le repo partagé
- [ ] `/deploy/helm/` n'existe que dans le repo partagé
- [ ] Projet ne contient que `/deploy/values/`
- [ ] Aucun `Makefile`/`Taskfile`/`Justfile` portant la logique de déploiement à la racine
- [ ] Stage `build` utilise **Kaniko** pour le build + push (jamais `docker:24-dind`) (cf. § 4.10)
- [ ] Stage `build` contient un job `verify:<api>` avec `needs: [build:<api>]` qui interroge l'API Harbor (scan natif + signature Cosign)
- [ ] `verify:<api>` fait échouer le pipeline sur `HIGH`/`CRITICAL` non whitelistées ou signature Cosign manquante
- [ ] Allow-list `.trivyignore` au niveau repo partagé uniquement, exceptions datées
- [ ] Aucun scan Trivy local dans le pipeline (le scan vit côté Harbor) ; allow-list = `lint/harbor-cve-whitelist.yaml` du repo partagé
- [ ] Aucun tests E2E Playwright dans le pipeline (manuels uniquement, cf. § 3.8)
- [ ] Stage `smoke-test` vérifie présence de `/liveness`, `/readiness`, `/startup`, `/metrics`, `/health` (cf. § 4.11)
- [ ] Stage `smoke-test` vérifie chaque dépendance déclarée dans `/health`

### 8.4 Configuration Kubernetes
- [ ] Noms d'environnement : `dev`, `staging`, `prod` (jamais `production`)
- [ ] `NAMESPACE` jamais hardcodé par job
- [ ] Convention `<projet>-<env>` — namespace prod = `<projet>-prod`
- [ ] Variables dev + review en scope global
- [ ] Pipeline calcule dynamiquement `NAMESPACE` et `INGRESS_HOST` en review
- [ ] `KUBECONFIG_VARIABLE` partout (jamais `OVH_KUBECONFIG` direct ni préfixé)
- [ ] Variables système kubeconfig en type **File**
- [ ] Aucun `base64 -d` sur le kubeconfig
- [ ] Résolution `eval` (compatible ash/Alpine)
- [ ] Templates deploy/migrate/rollback utilisent l'indirection
- [ ] Pipeline teste le wildcard avant émission spécifique
- [ ] Wildcard copié, jamais ré-émis ailleurs que dans `cert-manager`
- [ ] Chart `api-chart` supporte `tls.strategy=wildcard`/`specific`
- [ ] Aucun secret TLS hardcodé dans les values
- [ ] Toutes les APIs exposent `/liveness`, `/readiness`, `/startup`, `/health`, `/metrics` (cf. § 5.10)
- [ ] Endpoints de santé non authentifiés
- [ ] `/liveness` ne fait aucun appel externe
- [ ] `/health` JSON liste toutes les dépendances avec status + latency_ms
- [ ] `/health` n'utilise pas le pool applicatif
- [ ] **Aucune B4F ne définit son propre Ingress** — tout passe par le gateway (§ 5.11)
- [ ] **Aucun frontend ne définit son propre Ingress** — passe par le gateway (§ 5.12)
- [ ] **Un seul Ingress par namespace** : le gateway (`api-gateway`)
- [ ] Le gateway porte les annotations `nginx.ingress.kubernetes.io/ssl-redirect: "true"` + `force-ssl-redirect: "true"`
- [ ] Le gateway route `/` → `frontend` Service
- [ ] Le gateway route `/api/<service>/v1(/|$)(.*)` → `<service>-b4f-api` avec rewrite-target `/$2` (Ingress API séparé de l'Ingress frontend, qui lui n'a pas de rewrite)
- [ ] Le gateway utilise un certificat TLS **wildcard** unique pour tout le namespace
- [ ] Le wildcard est **copié** depuis `cert-manager/` (via Job du `gateway-chart` ou reflector)
- [ ] La liste des routes API est **générée par `discover-apis.sh`**, pas codée en dur
- [ ] Le frontend possède son propre `frontend-chart` distinct de `api-chart`
- [ ] Le frontend expose `/healthz` (statique) en plus de `/`
- [ ] Le frontend a `API_BASE_URL=/api` (origine unique, jamais cross-domain)

### 8.5 Variables d'environnement
- [ ] Aucune variable préfixée `DEV_`, `STAGING_`, `PROD_`
- [ ] Aucune résolution dynamique de préfixe
- [ ] Variables env-spécifiques scopées dans GitLab (sauf dev/review en global)

### 8.6 Registry (Harbor) → K8s
- [ ] Projet Harbor créé (1:1 avec le projet GitLab) avec auto-scan + auto-sign Cosign + retention
- [ ] Robot account `robot$<projet>+ci` créé (push + pull + scan:read + scan:create + artifact:read, rotation 90j)
- [ ] Variables `HARBOR_URL` / `HARBOR_PROJECT` / `HARBOR_ROBOT_USER` (protégée) / `HARBOR_ROBOT_TOKEN` (protégée + masquée) configurées
- [ ] Aucune variable `DEPLOY_TOKEN_*` ni usage de `CI_REGISTRY_*` dans le pipeline
- [ ] `provision-registry-access` exécuté par environnement
- [ ] ServiceAccount `harbor-registry-deployer` avec `imagePullSecrets` (`harbor-registry-cred`) provisionné
- [ ] Deployments utilisent `serviceAccountName`
- [ ] Secret idempotent via `--dry-run=client | kubectl apply`
- [ ] Test : suppression d'un pod → restart sans `ImagePullBackOff`

### 8.7 Conventions du projet
- [ ] `/docs` à la racine pour toute la doc (cf. § 10.1)
- [ ] `/data` à la racine pour les données client (cf. § 10.2)
- [ ] Aucun document libre dans `apis/`, `frontend/`, `deploy/`
- [ ] Aucune donnée client réelle non anonymisée commitée
- [ ] Aucun fichier de config d'outil IA spécifique (cf. § 10.3) — ni `.kilo*`, ni `.cursor*`, ni `.claude*`, ni `.aider*`, ni `.continue*`, ni `.windsurf*`, ni `.codeium*`, ni `.copilot*`
- [ ] `.agents/skills/` présent et versionné dans le projet (copie depuis `croo-dev/code-agent-skills-v1.0`, cf. § 10.4)
- [ ] `AGENTS.md` à la racine
- [ ] Aucun `SKILL.md` modifié manuellement dans `.agents/skills/` (la source de vérité est le repo central)
- [ ] Le script `./.agents/update-skills.sh` est présent et permet de bumper les skills
- [ ] Trois niveaux de code partagé : `apis/shared/`, `apis/exposed/shared/`, `apis/internal/shared/`
- [ ] Aucune logique métier dans les `shared/`
- [ ] Aucun modèle d'entité partagé entre Backends
- [ ] `apis/exposed/shared/` ne consomme pas `apis/internal/shared/`

### 8.8 Observabilité
- [ ] Logs sur stdout/stderr en JSON structuré
- [ ] Endpoint `/metrics` exposé par chaque API
- [ ] SDK OTel via `OTEL_EXPORTER_OTLP_ENDPOINT`
- [ ] `OTEL_SERVICE_NAME`, `OTEL_RESOURCE_ATTRIBUTES`, `OTEL_TRACES_SAMPLER*` injectés par le chart
- [ ] Aucun agent propriétaire (Datadog, NewRelic...)
- [ ] Sampling : 1.0 en dev, ≤ 0.1 en prod
- [ ] Aucun appel direct app -> backend observabilité
- [ ] `traceparent` (W3C) propagé sur tous les appels HTTP entre composants (cf. § 5.9)
- [ ] `trace_id` inclus dans le payload de chaque event Redis (cf. § 2.4)
- [ ] Subscribers Redis rattachent leur span au `trace_id` parent extrait du payload
- [ ] Tous les logs JSON incluent `trace_id` (et `span_id` si possible)

### 8.9 Développement local
- [ ] Scripts wrappers à la racine : `run_all_apis.sh`, `migrate_all_apis.sh`, `run_all_apis_tests.sh`, `run_frontend.sh`, `run_frontend_tests.sh`, `run_frontend_e2e.sh`
- [ ] Aucune logique métier dans les wrappers
- [ ] Chaque API porte `run_api.sh` et `run_tests.sh`
- [ ] Chaque Backend porte en plus `migrate.sh`
- [ ] Aucune B4F ne porte `migrate.sh`
- [ ] `docker-compose.yml` à la racine avec `postgres` + `pgbouncer` + `redis` + `alloy`
- [ ] PgBouncer du compose en `pool_mode = transaction`
- [ ] `.env.example` à la racine, à jour, sans secrets de prod
- [ ] `.env` racine non commité
- [ ] Variables globales (DB, Redis, OTel) sans préfixe ; variables API préfixées par nom de dossier en SNAKE_CASE
- [ ] Aucun `AUTHENTICATION_*` (banni)
- [ ] Ports applicatifs portés par `<API_PREFIX>_PORT`, jamais hardcodés
- [ ] `docker compose up` + `./migrate_all_apis.sh` + `./run_all_apis.sh` donne un environnement fonctionnel depuis zéro
- [ ] Compose suit les évolutions infra au même rythme que la prod

### 8.10 Structure interne des APIs (Clean Architecture + SOLID)
- [ ] Toutes les APIs suivent **la même structure** de couches
- [ ] Quatre couches : `domain/`, `application/`, `infrastructure/`, `presentation/`
- [ ] `domain/` n'importe aucun framework
- [ ] `application/` n'importe aucun framework non plus
- [ ] Use cases dépendent de Ports (ABC), jamais d'implémentations
- [ ] Aucune entité métier ne hérite de `BaseModel` ni de `DeclarativeBase`
- [ ] Aucune route FastAPI ne renvoie un modèle SQLAlchemy
- [ ] Aucune logique métier dans les routes
- [ ] Pas de `Service`/`Manager`/`Helper` fourre-tout
- [ ] Lint `import-linter` configuré dans le stage `test`
- [ ] Tests organisés en `unit/`, `integration/`, `e2e/`

### 8.11 Repo `cicd-templates` (audit du repo partagé)
- [ ] Arborescence conforme à § 13.1 (templates/, deploy/scripts/, deploy/helm/, lint/, examples/, tests/)
- [ ] Versioning Semver via tags Git (`v1.0.0`...) avec CHANGELOG.md
- [ ] Tests automatisés : `shellcheck`, `helm lint`/`template`, validation pipeline YAML
- [ ] `examples/minimal-project/` à jour et déploye correctement
- [ ] `docs/upgrade-guide.md` à jour pour chaque MAJOR
- [ ] Pas de logique projet-spécifique dans le repo partagé

### 8.12 Frontend Clean Architecture
- [ ] Toutes les features frontend suivent **la même structure** de couches (cf. § 14.1, § 14.2)
- [ ] Quatre couches : `domain/`, `application/`, `infrastructure/`, `presentation/`
- [ ] `domain/` n'importe rien de `@angular/*`, `@ngrx/*`, `rxjs`
- [ ] `application/` n'importe rien de `@angular/*`, `@ngrx/*`, `rxjs` non plus
- [ ] Use cases dépendent de Ports (interfaces TS), jamais d'implémentations concrètes
- [ ] Aucun component n'injecte `HttpClient` directement (passe par use case)
- [ ] Aucun DTO HTTP brut stocké dans le state NGRX (toujours mapper en Model domain)
- [ ] ESLint custom rules configurées pour bloquer les imports interdits par couche
- [ ] Tests organisés par couche (`domain/*.spec.ts`, `application/*.spec.ts`, etc.)

---

## 9. Format de rapport de revue

````
## Revue Architecture & Déploiement

### Architecture APIs
OK / VIOLATION : ...

### Frontend NGRX
OK / VIOLATION : ...

### Pipeline CI/CD
OK / VIOLATION : ...

### Configuration K8s
OK / VIOLATION : ...

### Scoping variables
OK / VIOLATION : ...

### Registry → K8s
OK / VIOLATION : ...

### Conventions projet
OK / VIOLATION : ...

### Observabilité
OK / VIOLATION : ...

### Développement local
OK / VIOLATION : ...

### Structure interne (Clean Archi + SOLID)
OK / VIOLATION : ...

### Repo cicd-templates
OK / VIOLATION : ...

### Frontend Clean Architecture
OK / VIOLATION : ...

### Résumé
- Violations critiques : X
- Violations à corriger : Y
- Points conformes : Z

### Variables CI/CD à créer/modifier dans GitLab
| Variable | Scope | Valeur attendue |
|---|---|---|
| ... | ... | ... |
````

---

## 10. Conventions du projet

### 10.1 Documentation : `/docs`

Toute la documentation projet vit sous **`/docs`**. Sous-arborescence libre.

````
<projet>/
└── docs/
    ├── architecture/
    │   ├── overview.md
    │   └── decisions/
    │       └── ADR-001-redis-event-bus.md
    ├── runbooks/
    │   ├── deploy-prod.md
    │   └── rollback.md
    └── user-guide/
````

**Règles :**
- Tout document écrit va sous `/docs`
- `README.md`, `CONTRIBUTING.md`, `LICENSE`, `CHANGELOG.md` restent à la racine
- Aucun document éparpillé dans `apis/`, `frontend/`, `deploy/`

### 10.2 Données client : `/data`

Toutes les données (échantillons, fixtures, exports anonymisés...) vivent sous **`/data`**.

````
<projet>/
└── data/
    ├── samples/
    ├── fixtures/
    │   └── tests/
    └── exports/
        └── anonymized/
````

**Règles :**
- Tout dataset va sous `/data`
- **Aucune donnée client réelle non anonymisée** commitée
- Fixtures de tests sous `/data/fixtures/`
- Fichiers volumineux : Git LFS ou stockage externe

### 10.3 Outillage IA : agnostique via `.agents/` et `AGENTS.md`

Les projets sont **agents-agnostiques**. Aucun outil d'assistance IA particulier n'est privilégié dans l'arborescence du projet. La configuration IA repose **exclusivement** sur trois éléments standards et portables :

| Élément | Localisation | Rôle |
|---|---|---|
| `.agents/skills/` | racine du projet | Copie locale des skills `dx_*` (cf. § 10.4), versionnée avec le projet |
| `AGENTS.md` | racine du projet | Instructions générales pour tout agent (architecture, conventions, refus, modes recommandés) |
| `SKILL.md` | un par dossier `.agents/skills/<name>/` | Un skill atomique : frontmatter YAML + corps Markdown |

#### Tout le reste est interdit

**Aucun** dossier ou fichier spécifique à un agent ne doit exister à la racine ni en sous-arborescence du projet :

- `.kilo/`, `.kilocode/`, `.kiloignore`, `.kilorules`
- `.cursor/`, `.cursorrules`, `.cursorignore`
- `.claude/`, `.claudeignore`, `CLAUDE.md`
- `.aider*`, `.aiderconfig`
- `.continue/`, `.continuerc`
- `.windsurf/`, `.windsurfrules`
- `.codeium*`, `.copilot*`
- `.github/copilot-instructions.md`
- Tout autre fichier nommé d'après un outil spécifique

Si un agent particulier a besoin de mappages internes (modes, rules, etc.), il est responsable de les **dériver à la volée** depuis `.agents/skills/` et `AGENTS.md`, sans matérialiser de fichier dans le repo du projet.

#### Vérifications

```bash
# 1. .agents/skills/ et AGENTS.md présents
[ -d .agents/skills ] || echo "FAIL: .agents/skills/ absent"
[ -f AGENTS.md ]      || echo "FAIL: AGENTS.md absent"

# 2. Aucun dossier ou fichier d'outil spécifique
find . -maxdepth 3 \
    \( -name '.kilo*' -o -name '.cursor*' -o -name '.claude*' \
       -o -name '.aider*' -o -name '.continue*' -o -name '.windsurf*' \
       -o -name '.codeium*' -o -name '.copilot*' -o -name 'CLAUDE.md' \) \
    -not -path './.git/*' -not -path './node_modules/*' \
    | grep . && echo "FAIL: fichier/dossier d'outil IA interdit"

# 3. .github/copilot-instructions.md absent
[ -f .github/copilot-instructions.md ] && echo "FAIL"

# 4. README/CONTRIBUTING ne mentionnent pas d'outil propriétaire
grep -E "(Cursor|Claude Code|Aider|Windsurf|Continue|Copilot|Kilo Code)" \
    README.md CONTRIBUTING.md 2>/dev/null && echo "WARN: outil cité"
```

### 10.4 Skills `dx_*` dans le projet

Une **copie** des skills du repo `croo-dev/code-agent-skills-v1.0` est placée dans le projet sous `.agents/skills/`. Pas de symlink, pas de submodule : les skills sont **commités** dans le repo projet et versionnés avec lui.

#### Pourquoi une copie versionnée

1. Le projet est **autonome** : tout reviewer, tout agent, tout pipeline voit immédiatement quelles règles le projet applique, sans dépendance externe à résoudre.
2. La **traçabilité** : `git log .agents/` montre quand et comment les skills ont évolué dans le projet.
3. La **reproductibilité** : un checkout à un commit donné restore les skills exactement comme à ce moment-là.
4. Le projet peut **vivre désynchronisé** du repo central pendant une mise en attente sans rien casser.

#### Bump : script `update-skills.sh`

Pour récupérer la dernière version des skills depuis le repo central et la commiter dans le projet :

```bash
./.agents/update-skills.sh             # vers le dernier tag MINOR mobile (v1)
SKILLS_TAG=v1.3.0 ./.agents/update-skills.sh    # pin strict
PUSH=yes ./.agents/update-skills.sh    # commit + push auto
```

Le script :
1. Clone (ou pull) `git@gitlab.tools.thesmartcrew.com:croo-dev/code-agent-skills-v1.0.git` dans un dossier temporaire au tag demandé
2. Synchronise `.agents/skills/` du projet avec celui du repo central (suppression des skills retirés inclus)
3. Met à jour `AGENTS.md` si nécessaire
4. `git add .agents/ AGENTS.md && git commit -m "chore(skills): bump to <tag>"`
5. (Si `PUSH=yes`) `git push`

#### Anti-patterns

1. **Modifier directement un `SKILL.md` dans `.agents/skills/`** — toute évolution passe par une PR sur `croo-dev/code-agent-skills-v1.0` puis un bump via `update-skills.sh`. Les modifications locales sont écrasées au prochain bump.
2. **Versionner `.agents/skills/` via submodule git** — les performances de clone sont mauvaises et la résolution est fragile. Une simple copie est plus robuste.
3. **Symlinker `.agents/skills/` vers un dossier extérieur au projet** — casse la portabilité et la reproductibilité.
4. **Ne pas commiter `.agents/`** — viole la traçabilité ; le projet n'est plus autonome.

---

## 11. Développement local

### 11.1 Scripts racine — wrappers d'orchestration

| Script | Rôle |
|---|---|
| `run_all_apis.sh` | Découvre toutes les APIs et lance chaque `run_api.sh` en arrière-plan. Supporte `--stop` et `--restart` |
| `migrate_all_apis.sh` | Découvre tous les Backend et exécute `migrate.sh` |
| `run_all_apis_tests.sh` | Découvre toutes les APIs et exécute `run_tests.sh`. Agrège les rapports de coverage |
| `run_frontend.sh` | Lance `ng serve` |
| `run_frontend_tests.sh` | Lance `ng test` avec coverage |
| `run_frontend_e2e.sh` | Lance les tests Playwright E2E du frontend (cf. § 3.8). Hors pipeline CI |

#### Règles
- **Aucune logique métier ni technique propre à une API** — pure orchestration
- Découverte par convention : `apis/exposed/*-b4f-api/` et `apis/internal/*-backend-api/`
- Code de retour `0` si tout réussit, non-zéro si au moins un sous-script échoue
- Logs identifiables (préfixage par nom d'API)
- `--stop` propre : `SIGTERM` puis `SIGKILL` après timeout
- Filtre optionnel : `./run_all_apis.sh rooms-backend-api`

### 11.2 Scripts par-API standardisés

| Script | Localisation | Présence | Rôle |
|---|---|---|---|
| `run_api.sh` | `apis/<tier>/<api>/` | Toutes APIs | Lance l'API en local |
| `migrate.sh` | `apis/internal/<api>/` | Backend uniquement | `alembic upgrade head` localement |
| `run_tests.sh` | `apis/<tier>/<api>/` | Toutes APIs | Tests + coverage, produit `junit.xml` + `coverage.xml` |

#### Règles
- **Mêmes noms dans toutes les APIs**
- Lecture des variables d'env DB/Redis/OTel depuis l'environnement parent
- `run_api.sh` ne fait **pas** la migration au démarrage
- `run_tests.sh` enforce 85 % de couverture localement
- Les B4F n'ont **pas** de `migrate.sh`

### 11.3 Docker-compose pour l'infrastructure locale

#### Services obligatoires

| Service | Rôle | Image |
|---|---|---|
| `postgres` | DB partagée | `postgres:16-alpine` |
| `pgbouncer` | Pool **transaction mode** | `bitnami/pgbouncer` ou `edoburu/pgbouncer` |
| `redis` | Event bus + locks de migration | `redis:7-alpine` |
| `alloy` | Collecteur OTLP local — toutes les APIs envoient vers `http://alloy:4317` | `grafana/alloy` |

#### Services optionnels

| Service | Rôle |
|---|---|
| `mailhog` | SMTP local |
| `minio` | Stockage S3-compatible |

#### Règles
- **Mêmes noms de variables d'env** que les variables CI/CD
- **PgBouncer en `pool_mode = transaction`**
- `docker compose up -d` + `./migrate_all_apis.sh` + `./run_all_apis.sh` doit donner un env fonctionnel depuis zéro
- Volumes nommés
- Compose suit les évolutions infra
- Pas de secrets de prod dans le repo

### 11.4 Configuration via `.env`

#### Hiérarchie des fichiers

| Fichier | Rôle | Versionné |
|---|---|---|
| `.env.example` (racine) | Documentation exhaustive | Oui |
| `.env` (racine) | Valeurs effectives dev | **Non** |
| `apis/<tier>/<api>/.env` | **Optionnel.** Override par API | **Non** |

Ordre de chargement : `.env` racine → `.env` par API.

#### Convention de nommage

##### 1. Variables globales (sans préfixe)

| Variable | Exemple |
|---|---|
| `DB_HOST` | `pgbouncer` |
| `DB_USERNAME` | `app_user` |
| `DB_PASSWORD` | `devpassword` |
| `DB_DATABASE` | `app` |
| `DATABASE_SSLMODE` | `disable` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://alloy:4317` |

Ces variables suivent les **mêmes noms** que les variables CI/CD.

##### 2. Variables par API — préfixées par nom de dossier en SNAKE_CASE

| Dossier | Préfixe |
|---|---|
| `auth-b4f-api` | `AUTH_B4F_API_` |
| `iam-backend-api` | `IAM_BACKEND_API_` |
| `rooms-backend-api` | `ROOMS_BACKEND_API_` |
| `front-office-b4f-api` | `FRONT_OFFICE_B4F_API_` |

Variables courantes :

| Variable | Exemple |
|---|---|
| `<API_PREFIX>_PORT` | `AUTH_B4F_API_PORT=8001` |
| `<API_PREFIX>_LOG_LEVEL` | `IAM_BACKEND_API_LOG_LEVEL=DEBUG` |
| `<API_PREFIX>_FEATURE_FLAG_X` | `ROOMS_BACKEND_API_FEATURE_FLAG_PRICING_V2=true` |

Chaque API lit **uniquement ses propres variables** via Pydantic Settings (`env_prefix="ROOMS_BACKEND_API_"`).

#### Règles
- `.env.example` **obligatoire**, à jour
- `.env` racine **jamais commité**
- `.env` par API **optionnel**
- **Aucun secret de production** dans aucun `.env`
- Mêmes noms en local et en CI/CD K8s
- Ports applicatifs **toujours** dans `<API_PREFIX>_PORT`
- Préfixe **dérivable mécaniquement** du nom de dossier

#### Exemple `.env.example`

```env
# Variables globales
DB_HOST=pgbouncer
DB_USERNAME=app_user
DB_PASSWORD=devpassword
DB_DATABASE=app
DATABASE_SSLMODE=disable

REDIS_URL=redis://redis:6379/0

OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy:4317

# Variables par API
AUTH_B4F_API_PORT=8001
AUTH_B4F_API_LOG_LEVEL=DEBUG

IAM_BACKEND_API_PORT=9001
IAM_BACKEND_API_LOG_LEVEL=DEBUG

ROOMS_BACKEND_API_PORT=9002
ROOMS_BACKEND_API_LOG_LEVEL=INFO

FRONT_OFFICE_B4F_API_PORT=8002
FRONT_OFFICE_B4F_API_LOG_LEVEL=INFO
```

#### Anti-patterns
1. Variable globale sans préfixe portant un sens API-spécifique
2. Préfixe différent du nom de dossier
3. **`AUTHENTICATION_*`** — banni
4. Hardcoder un port dans `docker-compose.yml` ou `run_api.sh`
5. Secrets de prod dans `.env.example`
6. `.env` commité
7. API qui lit des variables sans son préfixe

---

## 12. Structure interne des APIs

### 12.1 Uniformité

**Toutes les APIs suivent la même structure interne, les mêmes conventions de nommage, les mêmes patterns.** Un développeur qui ouvre une API doit pouvoir prédire où trouver chaque chose. Toute dérive est une violation à corriger immédiatement.

### 12.2 Clean Architecture — quatre couches

Chaque API est organisée en **quatre couches concentriques** avec une **règle de dépendance unidirectionnelle** :

````
┌─────────────────────────────────────────────────────┐
│ presentation/      FastAPI routes, schemas Pydantic │
│   ┌───────────────────────────────────────────────┐ │
│   │ infrastructure/   SQLAlchemy, Redis, httpx    │ │
│   │   ┌─────────────────────────────────────────┐ │ │
│   │   │ application/   Use cases, orchestration │ │ │
│   │   │   ┌───────────────────────────────────┐ │ │ │
│   │   │   │ domain/   Entities, ports, règles │ │ │ │
│   │   │   └───────────────────────────────────┘ │ │ │
│   │   └─────────────────────────────────────────┘ │ │
│   └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
        Le domain ne connaît AUCUNE des couches externes.
````

#### Structure de fichiers — Backend API

````
apis/internal/<service>-backend-api/
├── src/<service>_backend_api/
│   ├── domain/                          # Aucun import de framework
│   │   ├── entities/                    # Modèles métier (dataclasses)
│   │   ├── value_objects/               # Objets-valeurs immuables
│   │   ├── exceptions.py                # DomainError, NotFound, BusinessRuleViolation...
│   │   └── ports/                       # ABCs : repositories, event_publisher
│   ├── application/                     # Aucun import de framework
│   │   ├── use_cases/                   # Un fichier = un use case
│   │   │   ├── create_<entity>.py
│   │   │   ├── update_<entity>.py
│   │   │   └── list_<entity>.py
│   │   └── dtos/
│   ├── infrastructure/                  # Adapters concrets
│   │   ├── persistence/
│   │   │   ├── models.py                # SQLAlchemy
│   │   │   ├── mappers.py               # Entity ↔ Model
│   │   │   ├── repositories.py
│   │   │   └── session.py
│   │   ├── messaging/
│   │   │   ├── publisher.py
│   │   │   └── subscriber.py
│   │   └── config.py                    # Pydantic Settings
│   └── presentation/
│       ├── api/v1/
│       │   ├── routes.py                # Thin adapter
│       │   └── schemas.py               # Pydantic Request/Response
│       ├── deps.py                      # DI FastAPI
│       ├── exception_handlers.py
│       └── main.py
├── tests/
│   ├── unit/                            # domain/ + application/
│   ├── integration/                     # infrastructure/
│   └── e2e/                             # Via TestClient
├── alembic/versions/
├── run_api.sh
├── migrate.sh
├── run_tests.sh
├── pyproject.toml
└── Dockerfile
````

#### Structure de fichiers — B4F API

Mêmes couches. `infrastructure/` contient des **clients HTTP vers les Backend** au lieu de SQLAlchemy. `domain/` reste pur.

````
apis/exposed/<service>-b4f-api/
├── src/<service>_b4f_api/
│   ├── domain/
│   │   ├── models/
│   │   ├── exceptions.py
│   │   └── ports/
│   ├── application/
│   │   └── use_cases/
│   ├── infrastructure/
│   │   ├── backends/
│   │   │   ├── iam_client.py
│   │   │   ├── rooms_client.py
│   │   │   └── ...
│   │   ├── auth/
│   │   └── config.py
│   └── presentation/
└── ...
````

### 12.3 Règle de dépendance — interdictions absolues

| Couche | Peut dépendre de | NE DOIT JAMAIS dépendre de |
|---|---|---|
| `domain/` | std lib, types | `application/`, `infrastructure/`, `presentation/`, FastAPI, SQLAlchemy, Redis, httpx, Pydantic Settings |
| `application/` | `domain/` | `infrastructure/`, `presentation/`, FastAPI, SQLAlchemy, Redis, httpx |
| `infrastructure/` | `domain/`, `application/` | `presentation/` |
| `presentation/` | `domain/`, `application/`, `infrastructure/` (via DI) | — |

**Vérification mécanique** :

```bash
grep -RE "(fastapi|sqlalchemy|redis|httpx|pydantic_settings)" \
  src/*/domain/ src/*/application/ \
  && echo "VIOLATION : framework imported in domain/application" && exit 1
```

Recommandation : **`import-linter`** avec un fichier `.importlinter` partagé via `cicd-templates`.

### 12.4 SOLID — application stricte

#### S — Single Responsibility
- **Un use case = une opération métier**, exposant exactement un `execute()`
- **Pas de "Service" fourre-tout**
- Classes `domain/` portent **uniquement** des règles métier intrinsèques

#### O — Open/Closed
- Extensions par **nouvelles classes implémentant des Ports**
- Ajouter une source = nouvelle implémentation, pas un `if backend_type == "v2":`

#### L — Liskov Substitution
- Toute implémentation d'un Port respecte le **contrat exact**
- `MockRepository` réellement interchangeable
- Pas de `raise NotImplementedError` dans une implémentation

#### I — Interface Segregation
- Ports **petits et focalisés**
- Pas de `RoomsRepository` avec 40 méthodes — séparer en `RoomsReader` / `RoomsWriter`

#### D — Dependency Inversion
- **Le domain n'importe rien du concret**
- L'application dépend de **Ports**
- Inversion résolue dans `presentation/` via FastAPI `Depends`
- Repositories et clients HTTP **toujours injectés** via constructeur

#### Exemple — flux d'une requête

```python
# domain/ports/repositories.py
class RoomRepository(ABC):
    @abstractmethod
    async def get_by_id(self, room_id: UUID) -> Room: ...

# domain/exceptions.py
class RoomNotFound(DomainError): ...

# application/use_cases/get_room.py
class GetRoom:
    def __init__(self, rooms: RoomRepository) -> None:
        self._rooms = rooms
    async def execute(self, room_id: UUID) -> Room:
        return await self._rooms.get_by_id(room_id)

# infrastructure/persistence/repositories.py
class SqlAlchemyRoomRepository(RoomRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
    async def get_by_id(self, room_id: UUID) -> Room:
        model = await self._session.get(RoomModel, room_id)
        if model is None:
            raise RoomNotFound(room_id)
        return map_model_to_entity(model)

# presentation/deps.py
def get_room_use_case(session: AsyncSession = Depends(get_session)) -> GetRoom:
    return GetRoom(rooms=SqlAlchemyRoomRepository(session))

# presentation/api/v1/routes.py
@router.get("/rooms/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: UUID,
    use_case: GetRoom = Depends(get_room_use_case),
) -> RoomResponse:
    room = await use_case.execute(room_id)
    return RoomResponse.from_entity(room)
```

### 12.5 Anti-patterns

1. **Modèle SQLAlchemy renvoyé par une route FastAPI** — toujours mapper vers Entity → Pydantic Response
2. **Use case appelant directement une session SQLAlchemy**
3. **Routes contenant de la logique métier** — thin adapter uniquement
4. **Entité métier héritant de `BaseModel` ou `DeclarativeBase`**
5. **Service "manager" / "facade" / "helper" générique** dans `application/`
6. **Repository avec une méthode `execute_raw_query(sql)`**
7. **Fichier `utils.py` dans `domain/` ou `application/`**
8. **Pydantic schema importé dans `domain/`**
9. **Configuration lue depuis `domain/` ou `application/`**
10. **Dépendance circulaire entre couches**
11. **APIs avec une structure différente d'autres APIs du même projet** — viole § 12.1


---

## 13. Structure du repo `cicd-templates` (recommandation)

Le repo partagé qui porte le pipeline et le chart Helm doit être lui-même structuré, testé, versionné et documenté. Il s'audite avec les mêmes exigences qu'un projet métier.

### 13.1 Arborescence recommandée

```
cicd-templates/
├── README.md                           # Doc principale, usage côté projet
├── CHANGELOG.md                        # Versions et breaking changes
├── CONTRIBUTING.md                     # Workflow PR, tests, release
├── LICENSE
├── docs/
│   ├── usage.md                        # Comment un projet s'y branche
│   ├── upgrade-guide.md                # Migration v1 -> v2 etc.
│   └── architecture.md
├── templates/
│   ├── parent.yml                      # Importé par les projets
│   └── child/
│       ├── stages/
│       │   ├── test.yml
│       │   ├── build.yml               # Kaniko + verify Harbor (cf. § 4.10)
│       │   ├── deploy.yml
│       │   ├── smoke-test.yml          # cf. § 4.11
│       │   └── rollback.yml
│       └── jobs/
│           ├── provision-registry-access.yml
│           └── discover-apis.yml
├── deploy/
│   ├── scripts/
│   │   ├── discover-apis.sh
│   │   ├── deploy-api.sh
│   │   ├── deploy-frontend.sh          # cf. § 5.12
│   │   ├── deploy-gateway.sh           # cf. § 5.11 — toujours en dernier
│   │   ├── smoke-test.sh
│   │   ├── rollback-api.sh
│   │   ├── migrate_with_lease.py
│   │   ├── resolve-kubeconfig.sh
│   │   ├── resolve-tls.sh
│   │   └── lib/
│   │       ├── helpers.sh
│   │       └── env.sh
│   └── helm/
│       ├── api-chart/                  # B4F + Backend
│       │   ├── Chart.yaml
│       │   ├── values.yaml             # Defaults
│       │   ├── values.schema.json      # Validation des values
│       │   └── templates/
│       │       ├── deployment.yaml     # initContainer migrate, probes, OTel env
│       │       ├── service.yaml        # ClusterIP uniquement
│       │       ├── serviceaccount.yaml
│       │       ├── networkpolicy.yaml  # Optionnel
│       │       └── _helpers.tpl
│       ├── frontend-chart/             # Frontend Angular (cf. § 5.12)
│       │   ├── Chart.yaml
│       │   ├── values.yaml
│       │   └── templates/
│       │       ├── deployment.yaml
│       │       ├── service.yaml        # ClusterIP, pas d'Ingress
│       │       ├── serviceaccount.yaml
│       │       └── _helpers.tpl
│       └── gateway-chart/              # API Gateway (cf. § 5.11)
│           ├── Chart.yaml
│           ├── values.yaml
│           └── templates/
│               ├── ingress.yaml        # UNIQUE Ingress du namespace
│               ├── cert-copy-job.yaml  # Job de copie wildcard cert
│               ├── cert-copy-rbac.yaml # ServiceAccount + Role + RoleBinding
│               └── _helpers.tpl
├── lint/
│   ├── importlinter-template.toml      # Pour Python Clean Archi (cf. § 12)
│   ├── eslintrc-template.js            # Pour Frontend Clean Archi (cf. § 14)
│   └── harbor-cve-whitelist.yaml       # Allow-list CVE Harbor (cf. § 7.5)
├── examples/
│   └── minimal-project/                # Bootstrap pour nouveau projet
│       ├── .gitlab-ci.yml
│       ├── apis/
│       │   ├── exposed/example-b4f-api/
│       │   └── internal/example-backend-api/
│       └── deploy/values/
├── tests/
│   ├── shellcheck/                     # Lint des scripts shell
│   ├── helm/                           # `helm lint`, `helm template`, snapshot tests
│   └── pipeline/                       # Validate `.gitlab-ci.yml` syntax
└── .gitlab-ci.yml                      # Pipeline du repo partagé lui-même
```

### 13.2 Versioning

- **Semver via tags Git** : `v1.0.0`, `v1.1.0`, `v2.0.0`
  - MAJOR : breaking change → exige migration côté projet
  - MINOR : ajout rétrocompatible
  - PATCH : correctif sans impact API
- Les projets pinnent `ref: v1` (suit MINOR) ou `ref: v1.2.3` (pin strict)
- **CHANGELOG.md** maintenu à chaque release, section "Breaking changes" obligatoire pour MAJOR
- **Migration guide** dans `docs/upgrade-guide.md` pour chaque MAJOR

### 13.3 Tests automatisés

Le pipeline du repo partagé lui-même applique :

- `shellcheck` sur tous les `.sh` de `/deploy/scripts/`
- `helm lint` + `helm template` sur le chart `api-chart` avec différentes valeurs (B4F, Backend, avec/sans TLS wildcard...)
- Validation YAML des templates pipeline
- Tests d'intégration sur `examples/minimal-project/` : déploiement complet sur un cluster de test
- Couverture 85 % sur les scripts Python (`migrate_with_lease.py`, etc.)

### 13.4 Règles de contribution

- Toute évolution passe par PR avec : tests verts + CHANGELOG mis à jour + doc à jour si comportement visible côté projet change
- Les MAJOR exigent une review élargie (toutes les équipes consommatrices)
- Période de support : la dernière MAJOR + l'avant-dernière supportées en parallèle
- Deprecation : warning visible dans les logs du job pendant ≥ 1 cycle MINOR avant suppression

### 13.5 Anti-patterns

1. **Logique projet-spécifique dans le repo partagé** — il doit rester agnostique
2. **Breaking change en MINOR ou PATCH** — viole Semver
3. **Pas de tests sur le repo partagé** — les bugs deviennent visibles seulement en cassant les projets consommateurs
4. **`examples/` désynchronisé du chart** — l'exemple ne sert plus de documentation vivante
5. **Scripts sans `shellcheck`** — bugs subtils en production

---

## 14. Frontend Clean Architecture (recommandation)

L'application Angular suit les **mêmes principes de Clean Architecture** que les APIs (cf. § 12), adaptés à NGRX et au navigateur. Toute la logique métier est isolée du framework, l'infrastructure est remplaçable.

### 14.1 Uniformité

**Toutes les sections frontend (auth, front-office, rooms, clients...) suivent la même structure interne.** Toute dérive est une violation à corriger.

### 14.2 Quatre couches frontend

```
┌─────────────────────────────────────────────────────┐
│ presentation/    Components Angular, templates      │
│   ┌───────────────────────────────────────────────┐ │
│   │ infrastructure/   HttpClient, NGRX, storage   │ │
│   │   ┌─────────────────────────────────────────┐ │ │
│   │   │ application/   Use cases, facades       │ │ │
│   │   │   ┌───────────────────────────────────┐ │ │ │
│   │   │   │ domain/   Entities, ports, règles │ │ │ │
│   │   │   └───────────────────────────────────┘ │ │ │
│   │   └─────────────────────────────────────────┘ │ │
│   └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
        Le domain ne connaît AUCUN framework.
```

### 14.3 Structure de fichiers

```
frontend/src/app/
├── core/                                # Cross-cutting (DI tokens, guards globaux)
├── shared/                              # Composants UI réutilisables (présentation pure)
└── features/
    └── <feature>/                       # Une par B4F (cf. § 3.4)
        ├── domain/
        │   ├── models/                  # Interfaces TS pures (pas de classe Angular)
        │   │   ├── room.model.ts
        │   │   └── reservation.model.ts
        │   ├── errors/                  # DomainError, NotFound, ValidationError
        │   └── ports/                   # Interfaces des repositories / clients
        │       └── rooms.repository.ts
        ├── application/
        │   ├── use-cases/               # Un fichier = une opération
        │   │   ├── load-rooms.use-case.ts
        │   │   ├── book-room.use-case.ts
        │   │   └── cancel-booking.use-case.ts
        │   └── dtos/
        ├── infrastructure/
        │   ├── api/
        │   │   ├── rooms.http.ts        # Implémente RoomsRepository via HttpClient
        │   │   └── rooms.dto.ts         # DTO ↔ Model
        │   └── store/                   # NGRX (cf. § 3)
        │       ├── rooms.actions.ts
        │       ├── rooms.reducer.ts
        │       ├── rooms.effects.ts
        │       └── rooms.selectors.ts
        └── presentation/
            ├── pages/
            │   └── rooms-list.page.ts   # Smart component, dispatch + select
            ├── components/
            │   └── room-card.component.ts   # Dumb component, @Input/@Output
            └── facades/
                └── rooms.facade.ts      # Optionnel, expose store + use cases
```

### 14.4 Règle de dépendance — interdictions absolues

| Couche | Peut dépendre de | NE DOIT JAMAIS dépendre de |
|---|---|---|
| `domain/` | TypeScript types/utils | `application/`, `infrastructure/`, `presentation/`, `@angular/*`, NGRX, RxJS, HttpClient |
| `application/` | `domain/` | `infrastructure/`, `presentation/`, `@angular/*`, NGRX, RxJS, HttpClient |
| `infrastructure/` | `domain/`, `application/`, NGRX, HttpClient | `presentation/` |
| `presentation/` | `domain/`, `application/`, `infrastructure/` (via DI Angular) | — |

**Vérification mécanique** via ESLint custom rules dans `.eslintrc.js` :

```javascript
// .eslintrc.js (template dans cicd-templates/lint/)
'no-restricted-imports': ['error', {
  patterns: [
    { group: ['@angular/*', '@ngrx/*', 'rxjs'],
      message: 'Forbidden in domain/ and application/ layers' }
  ]
}]
```

Configurer par overrides : la règle s'applique uniquement sur les fichiers `**/domain/**` et `**/application/**`.

### 14.5 SOLID — application stricte

#### S — Single Responsibility
- **Un use case = une opération métier** (`LoadRoomsUseCase`, `BookRoomUseCase`)
- Pas de "Service" fourre-tout (`RoomsService` avec 30 méthodes)
- Components dumb : 1 component = 1 responsabilité d'affichage

#### O — Open/Closed
- Nouvelles fonctionnalités via nouveaux use cases ou nouveaux components
- Pas de `if (variant === 'v2') { ... }` dans le code existant

#### L — Liskov Substitution
- Toute implémentation de `RoomsRepository` (HTTP, mock, in-memory pour tests) est interchangeable
- Mêmes signatures, même sémantique d'erreur

#### I — Interface Segregation
- Ports petits (`RoomsReader` / `RoomsWriter` séparés si la liste de méthodes enfle)
- Components prennent en `@Input` uniquement ce dont ils ont besoin

#### D — Dependency Inversion
- Le `domain/` n'importe rien de concret
- Les use cases dépendent des **Ports** (interfaces TS), jamais de `HttpClient` directement
- Inversion résolue via Angular DI :
  ```typescript
  // infrastructure/rooms.module.ts
  providers: [
    { provide: RoomsRepository, useClass: RoomsHttpRepository }
  ]
  ```

### 14.6 NGRX dans cette architecture

NGRX vit dans `infrastructure/store/`. Le store n'est **pas** la couche application :

- Les **actions** sont déclenchées depuis `presentation/` (components → `store.dispatch`)
- Les **effects** appellent les **use cases** (cf. § 3 : "Effects appellent les Services" → ici "Effects appellent les Use Cases")
- Les **use cases** appellent les **ports** (interfaces du domain)
- Les **ports** sont implémentés en `infrastructure/api/` via `HttpClient`
- Le **state du store** ne stocke que des **Models domain** ou des DTOs de présentation, jamais de DTO HTTP brut

```typescript
// infrastructure/store/rooms.effects.ts
loadRooms$ = createEffect(() => this.actions$.pipe(
  ofType(loadRooms),
  switchMap(() => this.loadRoomsUseCase.execute().pipe(
    map(rooms => loadRoomsSuccess({ rooms })),
    catchError(err => of(loadRoomsFailure({ err })))
  ))
));
```

### 14.7 Tests organisation

Comme côté APIs (cf. § 12.2) :

```
features/<feature>/
├── domain/
│   └── *.spec.ts                        # Tests unitaires purs (pas d'Angular)
├── application/
│   └── *.spec.ts                        # Tests unitaires use cases avec mocks de Ports
├── infrastructure/
│   ├── api/*.spec.ts                    # HttpTestingController
│   └── store/*.spec.ts                  # NGRX TestBed
└── presentation/
    └── *.spec.ts                        # ComponentFixture
```

### 14.8 Anti-patterns

1. **Component qui injecte `HttpClient` directement** — viole la règle de dépendance, le component est en `presentation/`
2. **Use case qui importe NGRX** — le use case est en `application/`, NGRX est en `infrastructure/`
3. **Modèle domain qui hérite d'`Observable`** ou est décoré `@Injectable()` — l'entité reste pure TypeScript
4. **DTO HTTP exposé tel quel dans le store** — toujours mapper DTO → Model
5. **Logique métier dans un component** — le component dispatch et select, c'est tout
6. **Service "Manager" / "Helper" générique** dans `application/`
7. **Pas d'inversion de dépendance** : use case qui new() une implémentation HTTP — toujours injecter via DI
8. **Sections frontend avec structures différentes** — viole § 14.1 (uniformité)
