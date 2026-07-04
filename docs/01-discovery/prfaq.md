# PR/FAQ — Croo Digital Experience

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 01 · Discovery · **Dernière MAJ** : 2026-07-01
> **Format** : *Working Backwards* (Amazon). On écrit le communiqué de presse **et** la FAQ *avant* de construire, pour partir du client et non de la techno.

---

# PARTIE 1 — Communiqué de presse (fictif, daté de la sortie visée)

## Croo lance CDE : le premier espace de travail commercial où l'IA fait le travail, pas juste des suggestions

**Montréal — [Date de lancement].** Croo annonce aujourd'hui la disponibilité de **Croo Digital Experience (CDE)**, un espace de travail pour équipes commerciales dans lequel un copilote IA nommé **Bob** exécute concrètement les tâches du quotidien — tenir le CRM à jour, trier et traiter les emails, préparer les devis, déclencher les relances — sous le contrôle permanent de l'utilisateur.

Contrairement aux CRM traditionnels, qui demandent aux commerciaux de **saisir** l'information, et contrairement aux assistants IA qui se contentent de **suggérer**, CDE renverse la logique : Bob lit le contexte (emails, fiches contacts, historique), propose des actions concrètes, puis **les exécute après validation humaine**. Chaque action est tracée, explicable et confirmable.

« Les commerciaux passent plus de temps à nourrir leur CRM qu'à parler à leurs clients. On a construit l'inverse : un collègue numérique qui fait la saisie, le suivi et la préparation, pendant que l'humain garde la relation et la décision », explique Alexandre Gauthier, fondateur de Croo. `[À VALIDER : citation]`

Concrètement, avec CDE une équipe peut : synchroniser sa boîte email (Microsoft 365 ou via Pipedream) et voir chaque message automatiquement rattaché au bon contact et à la bonne organisation ; laisser Bob classer les emails via des **smart labels** intelligents ; demander à Bob de créer un contact ou une opportunité en langage naturel ; suivre un pipeline commercial en 6 étapes ; générer des devis avec lignes produits ; et automatiser des workflows déclenchés par des événements (ex. « quand une opportunité passe en négociation, prépare le devis »).

Le tout repose sur une architecture multi-tenant sécurisée, un moteur d'exécution d'outils avec garde-fous (confirmation obligatoire sur toute action sensible), et une mémoire contextuelle privée à chaque organisation.

CDE est disponible pour les PME B2B. `[À VALIDER : tarification, disponibilité géographique, date]`

---

# PARTIE 2 — FAQ

## FAQ clients

**En quoi CDE est différent d'un CRM classique (HubSpot, Pipedrive, Salesforce) ?**
Un CRM classique est une base de données que *vous* remplissez. CDE est un espace de travail où *Bob* remplit et fait avancer les choses pour vous. Le CRM (contacts, organisations, opportunités, devis, activités, produits) est présent et complet, mais c'est le **socle** ; la valeur est dans l'agent qui l'opère.

**Bob peut-il envoyer des emails ou modifier des données sans que je le sache ?**
Non. Toute action « sensible » (envoi d'email, suppression, modification chez un tiers) déclenche une **confirmation explicite** : Bob vous montre ce qu'il s'apprête à faire (*readback*) et attend votre clic. Vous pouvez régler ce comportement (`require_write_confirmation`). Les actions de simple lecture ne demandent pas de confirmation.

**Comment mes emails arrivent-ils dans CDE ?**
Deux voies : l'intégration **Microsoft 365** (directe) et **Pipedream** (moderne, via webhooks signés, supportant Outlook et Gmail). Les emails sont synchronisés, puis automatiquement **rattachés** au contact et à l'organisation correspondants, et peuvent être classés par des smart labels IA.

**Qu'est-ce qu'un « smart label » ?**
Une étiquette de classement d'email qui combine des mots-clés et un *hint* pour l'IA. Les labels sont hiérarchiques (label / sous-label) et permettent à Bob de trier automatiquement votre boîte selon vos catégories métier.

**Mes données sont-elles isolées des autres clients ?**
Oui. Chaque donnée porte un identifiant de *tenant* et est filtrée à chaque requête. L'isolation multi-tenant est une garantie d'architecture, pas une option. Voir la [DPIA](../06-gouvernance/privacy-dpia.md).

**Bob se souvient-il de mes échanges ?**
Oui, via une mémoire contextuelle (RAG). Chaque entrée de mémoire a un **périmètre** (privé à l'utilisateur, organisationnel, partagé) et une **sensibilité** typée. Bob n'utilise que la mémoire autorisée pour le contexte courant.

**Que se passe-t-il si l'IA « tombe » ?**
Le système dégrade proprement : si le fournisseur LLM principal (Fireworks) est indisponible, un moteur local déterministe prend le relais pour les routages simples. Vous n'êtes jamais bloqué avec un écran cassé.

**Puis-je automatiser des tâches répétitives sans Bob ?**
Oui. Le module **Platform** propose des workflows déclenchés par des événements (ex. `contact.created`, `opportunity.updated`) ou manuellement, avec un mode d'exécution réglable (*suggest*, *auto*, *require_approval*).

## FAQ internes (parties prenantes)

**Quel est le marché cible précis ?** `[À VALIDER]`
Hypothèse actuelle : PME B2B (10–200 employés) avec une équipe commerciale de 3–30 personnes, déjà sous Microsoft 365, pour qui l'hygiène CRM est un problème réel. À confirmer par le fondateur.

**Quel est le business model ?** `[À VALIDER]`
Le code contient un ledger d'usage (`UsageTransaction`) avec COGS par action et des plans `STARTER / PRO / ENTERPRISE` (`Tenant.plan`). Cela suggère un modèle **abonnement par siège + facturation à l'usage IA** (tokens, minutes voix, enrichissements). À formaliser.

**Qu'est-ce qui est réellement construit vs à faire ?**
Construit et fonctionnel en local : CRM complet, inbox dual-provider, runtime agentique (Fireworks + fallback), mémoire RAG, gouvernance d'outils, workflows, usage ledger, frontend Angular 21. À finaliser : migration complète hors LangGraph, surfaces UI de configuration de Bob, durcissement CI/CD production. Voir [Launch Readiness](../05-delivery/launch-readiness.md).

**Quel est le principal risque produit ?**
La **confiance**. Si Bob exécute une mauvaise action une fois de trop, l'utilisateur reprend tout à la main et le produit perd sa raison d'être. D'où les tenets 1 et 2 (confirmation + traçabilité). Voir [Risk Register](../06-gouvernance/risk-register.md).

**Quel est le principal risque technique ?**
La fiabilité et le coût du tool-call loop à grande échelle, et la complexité opérationnelle de 21 services. Voir [System Design Doc](../04-technique/system-design-doc.md).

**Pourquoi un runtime agentique maison plutôt que LangGraph ?**
Voir [ADR-0004](../04-technique/adr/adr-0004-runtime-agentique-maison-vs-langgraph.md). En bref : contrôle du gating de confirmation, du routage MCP déterministe et de la gouvernance d'outils, sans la boîte noire d'un framework tiers.

---

> **Rappel Working Backwards** : si une réponse de cette FAQ vous met mal à l'aise (« on ne sait pas », « ce n'est pas encore vrai »), c'est un signal produit à traiter — pas à cacher. Les `[À VALIDER]` sont la liste de travail du fondateur.
