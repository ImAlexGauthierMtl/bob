# Vision Produit — Croo Digital Experience

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 00 · Vision · **Dernière MAJ** : 2026-07-01
> **Horizon** : 3 ans (2026 → 2029)

## 1. Vision (l'énoncé)

> **CDE est l'espace de travail commercial où un copilote IA — « Bob » — exécute réellement le travail à la place de l'équipe : il lit les emails, tient le CRM à jour, prépare les devis et déclenche les relances, sous le contrôle de l'humain. Pas un assistant qui suggère : un collègue numérique qui agit.**

Là où les CRM classiques demandent à l'humain de nourrir la machine (saisir, taguer, mettre à jour), CDE inverse la charge : **la machine nourrit et fait avancer le pipeline**, l'humain valide et décide.

## 2. Le problème que nous résolvons

Les équipes commerciales des PME passent **plus de temps à administrer leur outil qu'à vendre** :

- Les données CRM sont saisies à la main, en retard, incomplètes → le pipeline ment.
- Les emails clients vivent dans une boîte séparée du CRM → contexte perdu, relances oubliées.
- La connaissance (qui est ce client ? où en est le deal ?) est dans la tête des gens, pas dans le système.
- Les outils IA existants « suggèrent » mais ne **font** rien : l'humain reste l'exécutant.

**Coût** : du chiffre d'affaires perdu par manque de suivi, une visibilité pipeline erronée, et des commerciaux qui font de la saisie au lieu de la relation.

## 3. La solution : un espace de travail piloté par un agent

CDE réunit dans une seule interface (micro-frontends Angular) cinq capacités, orchestrées par un copilote agentique :

| Domaine | Ce que ça fait aujourd'hui (dans le code) |
|---|---|
| **CRM** | Contacts, organisations, opportunités (pipeline 6 étapes), devis avec lignes produits, activités, catalogue produits — enrichis automatiquement (Hunter, Bright Data). |
| **Inbox / Communication** | Synchronisation email (Pipedream + Microsoft 365), **smart labels** IA, liaison automatique email ↔ contact/organisation. |
| **Bob (copilote)** | Conversation, exécution d'outils avec **confirmation humaine** sur les actions sensibles, mémoire RAG privée/organisationnelle, gouvernance fine des outils. |
| **Knowledge Base** | Articles, catégories, recherche, feedback — base de connaissance interne. |
| **Platform** | Workflows/automatisations (déclencheurs événementiels), analytics, **compteur d'usage & facturation** (ledger append-only). |

Ce qui fait la différence, ce n'est aucune de ces briques prise isolément — c'est **Bob qui les traverse toutes** : il peut lire un email dans l'inbox, retrouver le contact dans le CRM, consulter la KB, et proposer une action, en gardant une trace vérifiable (narration steps) et en demandant confirmation avant tout envoi.

## 4. Pourquoi maintenant

- **Les LLM savent enfin utiliser des outils de façon fiable** (tool-calling, JSON structuré). Le tool-call loop de CDE (max 5 itérations, gating de confirmation) est ce qui rend l'exécution sûre.
- **Les plateformes d'intégration (Pipedream, MCP)** rendent viable la connexion à des dizaines de services (mail, calendrier, Slack, Teams, Drive) sans construire chaque connecteur.
- **Le coût d'inférence a chuté** au point qu'un agent peut tourner sur chaque email entrant.

## 5. Ce que nous NE sommes PAS

- ❌ Un CRM « de plus » qui rivalise sur le nombre de champs. Notre différenciateur est l'**exécution agentique**, pas la richesse fonctionnelle brute.
- ❌ Un chatbot greffé sur un produit existant. Bob est **au centre**, pas dans une bulle en bas à droite.
- ❌ Un outil qui agit sans contrôle. Toute action sensible (*write*, *destructive*) passe par une **confirmation explicite** et un *readback*.
- ❌ Une plateforme no-code générique. CDE est **vertical** : la vente B2B.

## 6. État actuel (honnête)

CDE est une base technique substantielle et **fonctionnelle en local (Docker)** : 7 API B4F, 14 backends, un frontend Angular 21, un runtime agentique maison (provider Fireworks + fallback local) remplaçant progressivement LangGraph. L'architecture est **conforme à la norme interne v1.4**. Ce qui reste : durcissement CI/CD vers l'infra de production (Harbor, K8s), finalisation de la migration du runtime, et les surfaces UI de configuration de Bob. Voir [Launch Readiness](../05-delivery/launch-readiness.md).

> ⚠️ **Note de cadrage** : Ce projet a été construit sans document de vision préalable. Le présent document *formalise a posteriori* l'intention que le code révèle. Il doit être **relu et corrigé par le fondateur** — certaines affirmations (marché cible précis, business model) sont des inférences à valider. Voir les `[À VALIDER]` dans le [PR/FAQ](../01-discovery/prfaq.md).

## 7. Boussole à 3 ans

- **Année 1 — Fiabilité** : Bob exécute sans erreur les tâches CRM+email du quotidien sous supervision. Confiance = tout est traçable et confirmable.
- **Année 2 — Autonomie encadrée** : Bob agit en mode « auto » sur les tâches à faible risque (labellisation, mise à jour, brouillons), l'humain ne validant que l'exception.
- **Année 3 — Multi-agents** : une équipe d'agents spécialisés (BCC) se répartit les comptes clients, coordonnée par le Bob Control Center.

Métrique unique qui juge tout : voir [North Star Metric](north-star-metric.md).
