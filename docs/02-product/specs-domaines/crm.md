# Spec produit — Domaine CRM

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 02 · Produit · **Dernière MAJ** : 2026-07-01
> Parent : [PRD §4.1](../prd-cahier-des-charges.md#41-crm--spec-détaillée) · Modèle de données : [Data Model](../../04-technique/data-model.md)

## 1. Objet

Le CRM est le **socle de données** de CDE : contacts, organisations, opportunités, devis, activités, produits. C'est ce que Bob lit et met à jour. Il couvre les jobs [JTBD-1](../../01-discovery/jobs-to-be-done.md) (saisie zéro) et [JTBD-3](../../01-discovery/jobs-to-be-done.md) (faire avancer un deal).

## 2. Entités & règles métier

### 2.1 Contact
- **Champs** : identité (first/last name, email, phone, mobile), pro (job_title, department, seniority), social (linkedin_url, headline, followers), enrichissement (`contact_profile` JSON), `status` ∈ {ACTIVE, INACTIVE, LEAD}, `organization_id`, `owner_id`.
- **Règles** : rattaché à ≤ 1 organisation ; owner = créateur par défaut ; soft-delete ; chaque mutation publie un event (`contact.created/updated/deleted`).

### 2.2 Organisation & Département
- **Organisation** : `name`, `industry`, `website`, adresse, `status` ∈ {ACTIVE, INACTIVE, PROSPECT, CUSTOMER, CHURNED}, `org_type` ∈ {CORPORATION, SMB, STARTUP, GOVERNMENT, NONPROFIT, OTHER}, `employee_count`, `annual_revenue`, enrichissement (`organization_profile`, LinkedIn), `ai_enriched`.
- **Département** : `name`, `manager_user_id`, avec table `UserDepartment` (appartenance + is_manager).
- **Règles** : une organisation regroupe N contacts, N opportunités, N devis, N activités.

### 2.3 Opportunité & lignes produits
- **Opportunité** : `name`, `stage` ∈ {PROSPECTING, QUALIFICATION, PROPOSAL, NEGOTIATION, CLOSED_WON, CLOSED_LOST}, `priority` ∈ {LOW, MEDIUM, HIGH, CRITICAL}, `amount`, `probability`, `close_date`, `source`, `organization_id`, `contact_id`, `owner_id`.
- **Pipeline ouvert** = {PROSPECTING, QUALIFICATION, PROPOSAL, NEGOTIATION} (utilisé par le dashboard).
- **Ligne produit** (`OpportunityProduct`) : `product_id`, `quantity`, `unit_price`, `discount_percent`. Cascade delete avec l'opportunité.

### 2.4 Devis (Quote)
- **Champs** : `status` ∈ {DRAFT, SENT, ACCEPTED, REJECTED, EXPIRED}, `subtotal`, `discount_percent`, `tax_percent`, `total`, `valid_until`, `terms`, `opportunity_id`, `organization_id`.
- **Règle de calcul** : `subtotal = Σ(qty × unit_price × (1 − discount))`, puis application remise et taxe → `total`.

### 2.5 Activité / tâche
- **Champs** : `subject`, `activity_type` ∈ {CALL, EMAIL, MEETING, TASK, NOTE}, `priority`, `status` ∈ {PENDING, IN_PROGRESS, COMPLETED, CANCELLED}, `due_date`, `completed_at`, **multi-liens** (`contact_ids`, `organization_ids`, `opportunity_ids` en JSON), `assigned_to`.
- **Règle** : une activité peut être liée à N contacts / orgs / opportunités.

### 2.6 Produit
- **Champs** : `category` ∈ {SOFTWARE, SERVICE, ADD_ON, CONSULTING, HARDWARE}, `unit_price`, `currency` (déf. CAD), `sku`, taxe, quantités min/max, plus champs spécialisés (billing_cycle, license_type, max_users, billing_unit, hardware…). Hiérarchie via `parent_product_id` (add-ons).

## 3. Parcours utilisateur clés

1. **Cycle lead → client** : Contact(LEAD) → Contact(ACTIVE) + Org(PROSPECT) → Opportunité(PROSPECTING) → progression du stage → Devis(DRAFT→SENT→ACCEPTED) → Opportunité(CLOSED_WON) + Org(CUSTOMER).
2. **Génération de devis** : depuis une opportunité, ajouter des lignes produits → créer un devis (calcul auto) → cycle de statut.
3. **Suivi d'activités** : créer/assigner une activité multi-liée → PENDING → COMPLETED.
4. **Création NL par Bob** : « crée un contact pour X chez Y » → Bob parse → champs extraits (avec confidence) → confirmation → création.

## 4. Surfaces UI

Pages : Contacts (liste + profil 360° avec onglets Overview/Activities/Emails/Client Map), Organisations (liste + détail), Opportunités (liste, filtre par stage), Devis (liste + profil), Activités, Produits (dans Settings). **Dashboard** consolidé par le B4F (`/dashboard/summary`) : totaux + highlights (max 5/type) + next_actions (`review_pipeline`, `follow_up`).

## 5. Exigences & priorités

Voir [PRD §4.1](../prd-cahier-des-charges.md#41-crm--spec-détaillée). Cœur (Must) : EF-CRM-1 à 6, 9. Should : enrichissement (8), création NL (10), catalogue (7).

## 6. À approfondir / gaps

- **Enrichissement** (EF-CRM-8) : les champs `*_profile` existent ; le déclenchement/rafraîchissement automatique est à consolider.
- **Relations N:N via JSON** (activités) : simples mais non requêtables en SQL relationnel — acceptable à cette échelle, à surveiller (voir [ADR data model](../../04-technique/data-model.md)).
- **`OpportunityProduct`↔`Product`** : pas de FK stricte (lien par ID) — cohérence applicative.

## 7. Métriques du domaine
Qualité des données (taux de contacts rattachés à une org, opportunités avec montant/échéance), vélocité du pipeline (temps par stage), taux de conversion devis (ACCEPTED/SENT).
