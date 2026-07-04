# Personas — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 01 · Discovery · **Dernière MAJ** : 2026-07-01
> Personas **inférés du code** (rôles, écrans, RBAC). À confronter à de vraies interviews utilisateurs — voir `[À VALIDER]`.

Les rôles techniques observés (`is_super_admin`, rôles système Admin/Member/Viewer, RBAC `resource:action`) et les surfaces produit (settings équipe, tool-governance, BCC, usage cross-tenant) dessinent quatre personas.

---

## P1 — Sofia, la commerciale (utilisatrice quotidienne) — persona primaire

- **Rôle CDE** : Member. **Écrans** : Dashboard, Inbox, Contacts, Opportunités, Devis, Activités, Chat Bob.
- **Objectif** : conclure plus de deals en passant moins de temps dans l'outil.
- **Journée type** : ouvre l'inbox le matin, Bob a déjà trié/labellisé les emails et rattaché les contacts. Elle demande à Bob « crée un contact pour Jean Dupont chez Acme » en langage naturel, avance une opportunité en « Négociation », génère un devis.
- **Frustrations (avant CDE)** : saisir deux fois la même info, oublier des relances, un pipeline qui ne reflète pas la réalité.
- **Ce qu'elle attend de Bob** : qu'il fasse la corvée, mais qu'il **demande avant d'envoyer** quoi que ce soit à un client.
- **Citation** : *« Je veux vendre, pas nourrir un logiciel. »* `[À VALIDER]`
- **Métrique de succès** : actions Bob validées / semaine (sa contribution à la NSM).

## P2 — Marc, le directeur commercial (manager d'équipe)

- **Rôle CDE** : Admin (tenant). **Écrans** : Dashboard, Analytics, Settings › Team, Settings › Roles, Usage logs, Automation.
- **Objectif** : visibilité fiable sur le pipeline et la productivité de l'équipe ; standardiser les bonnes pratiques.
- **Ce qu'il fait dans CDE** : gère les membres et leurs rôles (RBAC), crée des **workflows** d'équipe (ex. relance automatique), configure les smart labels, surveille l'**usage** (et donc les coûts IA).
- **Frustrations** : ne pas savoir où en sont vraiment les deals ; des process qui existent « dans les têtes ».
- **Ce qu'il attend** : que Bob applique *ses* règles (workflows niveau `company`/`department`) et que l'usage/coût soit lisible.
- **Métrique de succès** : adoption de l'équipe (WAU/MAU), fiabilité du pipeline.

## P3 — Nadia, l'administratrice plateforme / IT (configuration & gouvernance)

- **Rôle CDE** : Admin, avec focus gouvernance. **Écrans** : Settings › Integrations, MS365, Tool Governance, Platform Access, Knowledge, BCC.
- **Objectif** : brancher les intégrations en sécurité et **encadrer ce que Bob a le droit de faire**.
- **Ce qu'elle fait** : connecte Microsoft 365 / Pipedream, définit les **politiques d'outils** (`tool_policies` : quel outil, quel risque, quel *team_scope*, activé ou non), gère la base de connaissance, configure le Bob Control Center.
- **Frustrations** : les outils IA « boîte noire » qu'on ne peut pas restreindre ; le risque de fuite de données.
- **Ce qu'elle attend** : contrôle granulaire (whitelist/blacklist d'outils), traçabilité, conformité.
- **Métrique de succès** : zéro incident de sécurité, couverture des intégrations.

## P4 — Alex, le super-admin Croo (opérateur de la plateforme)

- **Rôle CDE** : `is_super_admin = true`. **Écrans** : Tenants (CRUD), Usage cross-tenant (`/admin/usage`), Cost rate cards.
- **Objectif** : opérer la plateforme SaaS — provisionner les tenants, suivre l'usage et les COGS across tenants, gérer les plans.
- **Ce qu'il fait** : crée/suspend des tenants, ajuste les `CostRateCard`, analyse l'usage par intent (`correlation_label`) pour piloter la marge.
- **Métrique de succès** : santé de la plateforme, marge (revenu vs COGS), rétention des tenants.

---

## Bénéficiaire indirect

## B1 — Le client final (le prospect/client de Sofia)
Ne se connecte pas à CDE, mais **subit ou bénéficie** de sa qualité : reçoit des emails mieux suivis, des devis plus rapides, moins d'oublis. Le tenet 1 (confirmation avant envoi) le protège d'un email généré à tort par l'IA.

---

## Matrice persona × valeur

| Persona | Douleur n°1 | Ce que CDE change | Feature clé |
|---|---|---|---|
| Sofia (commerciale) | Saisie & suivi manuels | Bob fait la corvée | Chat Bob + inbox auto-liée |
| Marc (directeur) | Pipeline peu fiable | Données à jour, process outillés | Analytics + Workflows |
| Nadia (IT/gouvernance) | IA non maîtrisable | Contrôle fin des outils | Tool Governance + RBAC |
| Alex (super-admin) | Piloter marge & tenants | Usage ledger + plans | Admin tenants + Usage |

> `[À VALIDER]` Ces personas sont déduits de l'architecture (rôles, écrans, permissions), pas d'interviews. Prochaine étape discovery : 5–8 entretiens par persona primaire pour valider douleurs et *willingness to pay*. Alimente les [Jobs-to-be-Done](jobs-to-be-done.md).
