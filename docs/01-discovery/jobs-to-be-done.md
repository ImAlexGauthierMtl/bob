# Jobs-to-be-Done — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 01 · Discovery · **Dernière MAJ** : 2026-07-01

Le cadre *Jobs-to-be-Done* (JTBD) formule les besoins comme des **« jobs »** que l'utilisateur cherche à accomplir, indépendamment de la solution. Format : *« Quand [situation], je veux [motivation], afin de [résultat attendu]. »* Chaque job est relié à ce que CDE offre aujourd'hui (dans le code) et aux [specs](../02-product/specs-domaines/).

## Job principal (high-level)

> **Quand je gère un portefeuille de prospects et clients B2B, je veux que le travail administratif de suivi se fasse quasi tout seul et de façon fiable, afin de consacrer mon temps à la relation et à la conclusion des deals — sans perdre le contrôle ni la traçabilité.**

Ce job « chapeau » se décompose en jobs fonctionnels, émotionnels et sociaux.

---

## Jobs fonctionnels

### JTBD-1 — Ne plus saisir les données à la main
*Quand* je reçois une info sur un prospect (email, appel, carte de visite), *je veux* qu'elle atterrisse dans le CRM sans double-saisie, *afin de* garder des données à jour sans effort.
- **CDE aujourd'hui** : création de contact/opportunité **en langage naturel** via Bob (`BobActionService`), enrichissement auto (Hunter, Bright Data), liaison email→contact/org automatique.
- **Spec** : [CRM](../02-product/specs-domaines/crm.md), [Inbox](../02-product/specs-domaines/inbox-communication.md).

### JTBD-2 — Trier et traiter ma boîte email dans le contexte du deal
*Quand* ma boîte se remplit, *je veux* que les emails soient classés et rattachés au bon client, *afin de* traiter les bons d'abord sans jongler entre outils.
- **CDE aujourd'hui** : sync dual-provider (Pipedream + MS365), **smart labels** hiérarchiques (mots-clés + hint IA), `linked_contact_id`/`linked_organization_id`.
- **Spec** : [Inbox / Communication](../02-product/specs-domaines/inbox-communication.md).

### JTBD-3 — Faire avancer un deal sans friction administrative
*Quand* un deal progresse, *je veux* mettre à jour l'étape, préparer un devis et planifier la suite en quelques gestes, *afin de* ne pas ralentir la vente.
- **CDE aujourd'hui** : pipeline 6 étapes (`PROSPECTING`→`CLOSED_WON/LOST`), devis avec lignes produits et calcul subtotal/remise/taxe, activités multi-liées.
- **Spec** : [CRM](../02-product/specs-domaines/crm.md).

### JTBD-4 — Déléguer les tâches répétitives à un agent, en sécurité
*Quand* une tâche revient à l'identique (relance, mise à jour, brouillon), *je veux* la confier à Bob, *afin de* gagner du temps — mais *seulement si* je peux valider avant l'irréversible.
- **CDE aujourd'hui** : tool-call loop avec **gating de confirmation**, gouvernance d'outils, mémoire contextuelle.
- **Spec** : [Bob copilote](../02-product/specs-domaines/bob-copilote.md).

### JTBD-5 — Automatiser un process d'équipe sans coder
*Quand* mon équipe suit un process (ex. « nouvelle opportunité → créer une activité de qualif »), *je veux* l'outiller une fois, *afin qu'*il s'applique tout seul.
- **CDE aujourd'hui** : workflows à 4 niveaux (`system/company/department/user`), déclencheurs événementiels, mode d'exécution réglable.
- **Spec** : [Platform](../02-product/specs-domaines/platform.md).

### JTBD-6 — Retrouver la connaissance interne au bon moment
*Quand* j'ai besoin d'une info process/produit, *je veux* la trouver (ou que Bob la trouve), *afin de* répondre juste au client.
- **CDE aujourd'hui** : Knowledge Base (articles, catégories, recherche, feedback), mémoire RAG interrogeable par Bob.
- **Spec** : [Knowledge Base](../02-product/specs-domaines/knowledge-base.md).

### JTBD-7 (manager) — Avoir une vision fiable du pipeline et des coûts
*Quand* je pilote l'équipe, *je veux* un pipeline qui reflète la réalité et une visibilité sur l'usage/coût IA, *afin de* décider et prévoir.
- **CDE aujourd'hui** : dashboard CRM composé (totaux + highlights + next actions), analytics, usage ledger avec COGS.

---

## Jobs émotionnels

- **Se sentir en contrôle** : « la machine travaille pour moi, pas l'inverse » → tenet 1 (confirmation) + tenet 2 (traçabilité).
- **Avoir confiance** : « je peux vérifier ce que Bob a fait et pourquoi » → narration steps, historique.
- **Ne pas avoir peur de l'erreur** : « rien d'irréversible ne part sans mon OK ».

## Jobs sociaux

- **Paraître réactif et organisé** auprès des clients (réponses rapides, rien oublié).
- **Montrer un pipeline crédible** à sa hiérarchie / ses investisseurs.

---

## Cartographie job → domaine → priorité

| Job | Domaine principal | Force actuelle | Priorité produit |
|---|---|---|---|
| JTBD-1 Saisie zéro | CRM + Bob | 🟢 Forte | Cœur |
| JTBD-2 Inbox contextualisée | Inbox | 🟢 Forte | Cœur |
| JTBD-3 Avancer un deal | CRM | 🟢 Forte | Cœur |
| JTBD-4 Déléguer en sécurité | Bob | 🟡 Solide, à durcir | Différenciateur |
| JTBD-5 Automatiser un process | Platform | 🟡 Présent | Extension |
| JTBD-6 Trouver la connaissance | KB + mémoire | 🟡 Base posée | Extension |
| JTBD-7 Piloter (manager) | Platform/Analytics | 🟡 Présent | Extension |

> **Insight** : les 3 jobs « cœur » (1, 2, 3) sont bien couverts par le socle CRM+Inbox. Le **différenciateur** est JTBD-4 (déléguer en sécurité) — c'est là que se concentre le risque et la valeur. La roadmap doit protéger et approfondir ce job. Voir [Roadmap](../02-product/roadmap.md).
