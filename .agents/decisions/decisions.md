# Decisions (ADR)

## ADR-001 — Structure .agents/ HDQ

- **Date** : 2026-03-05
- **Status** : Accepté
- **Decision** : Adoption du framework HDQ pour la collaboration IA
- **Rationale** : Standardisation des normes, workflows, et skills pour le développement assisté par IA

## ADR-002 — Angular 20+ Frontend avec Tailwind-free CSS

- **Date** : 2026-03-05
- **Status** : Accepté
- **Decision** : Conversion des mockups Tailwind HTML en Angular avec CSS natif (variables CSS)
- **Rationale** : Les mockups HTML/Tailwind servent de référence visuelle. Le frontend Angular utilisera un design system CSS pur avec variables pour la maintenabilité et le contrôle total sur les styles. Pas de dépendance Tailwind en prod.

## ADR-003 — Design DNA : Noir + Blanc + Accent #FF4500

- **Date** : 2026-03-05
- **Status** : Accepté
- **Decision** : Palette minimaliste noir/blanc avec accent orange-red, typo Inter, angles droits
- **Rationale** : Identité visuelle premium et épurée, cohérente avec la vision AI-first

---

## ADR-004 — Agent-First Architecture avec LangGraph

- **Date** : 2026-03-05
- **Status** : Accepté
- **Decision** : Utiliser **LangGraph** comme framework d'orchestration d'agents
- **Contexte** : Croo Digital Experience est un Agent-First ERP — l'interface primaire est la voix/texte, pas les formulaires. Les agents exécutent des chaînes d'actions conditionnelles (recherche → scraping → enrichissement → persistance).
- **Alternatives évaluées** :
  - CrewAI : trop simpliste pour les flows conditionnels complexes
  - Custom pur : risque de réinventer retry, state, parallélisme
  - Autogen (Microsoft) : orienté chat multi-agents, pas orchestration
- **Rationale** :
  - Graphs d'état pour les chaînes conditionnelles (l'agent décide la suite)
  - Parallélisme natif (scraper 5 sources simultanément)
  - Human-in-the-loop via `interrupt` (validation avant envoi d'email, par ex.)
  - Checkpointing : reprise en cas d'échec à n'importe quelle étape
  - Compatible Groq + OpenRouter

## ADR-005 — Stratégie LLM : Groq-first + OpenRouter fallback

- **Date** : 2026-03-05
- **Status** : Accepté
- **Decision** : **Groq** comme provider LLM principal (Llama 3.3 70B), **OpenRouter** pour les modèles plus puissants quand nécessaire (Claude, GPT)
- **Rationale** :
  - Groq : latence ultra-faible (~200ms), coût très bas, idéal pour usage intensif (parsing d'intent, enrichissement, scraping)
  - OpenRouter : accès aux modèles premium pour les tâches complexes (rédaction longue, analyses profondes)
  - Toujours favoriser Groq en priorité pour l'économie
- **Voice** : Groq Whisper (le plus rapide du marché) pour la transcription voice-to-text

## ADR-006 — Data Layer : PostgreSQL + pgvector + Apache AGE

- **Date** : 2026-03-05
- **Status** : Accepté
- **Decision** : **PostgreSQL** comme base relationnelle, **pgvector** pour les embeddings/RAG, **Apache AGE** pour le graph de cartographie d'affaires
- **Alternatives évaluées** :
  - Neo4j : puissant mais lourd, une DB de plus à opérer, licensing complexe
  - Memgraph : rapide mais écosystème limité
  - pgvector + JOINs simples : pas de traversée de graph native
- **Rationale** :
  - Une seule DB à administrer (PostgreSQL)
  - SQL classique + Cypher dans la même instance
  - Cartographie relationnelle : entreprise → contact → opportunité → industrie → concurrent
  - Migration vers Neo4j possible si nécessaire (même langage Cypher)
  - pgvector pour la recherche sémantique (RAG sur emails, notes, transcripts)

## ADR-007 — Multi-tenant hybride

- **Date** : 2026-03-05
- **Status** : Accepté
- **Decision** : Architecture **multi-tenant par `tenant_id`** dans le core, avec capacité de modules custom et de fork pour les multinationales
- **Scénarios** :
  - Client standard → Schema partagé, `tenant_id` sur chaque table
  - Client avec besoins custom → Modules additionnels par-dessus le core
  - Multinationale → Fork du repo, instance dédiée adaptée
- **Rationale** :
  - Le `tenant_id` est trivial à implémenter dès le début mais coûteux à ajouter après
  - La flexibilité fork permet d'adresser les cas extrêmes sans surcharger le core
  - Marché cible : grandes PME et multinationales → l'isolation des données est non-négociable

## ADR-008 — Interface Voice-First + Chat

- **Date** : 2026-03-05
- **Status** : Accepté
- **Decision** : L'interface primaire est **voice ou chat** (pas les formulaires), avec 2 boutons d'entrée : micro (voice) et crayon (texte)
- **Flow** :
  1. Utilisateur parle ou écrit une commande naturelle
  2. Groq Whisper transcrit (si voice) → Intent parser (Groq LLM) → Action identifiée
  3. LangGraph orchestre la chaîne d'agents appropriée
  4. Résultat affiché dans l'UI Angular
- **Rationale** :
  - Différenciateur fondamental vs Salesforce/HubSpot : on commande, on ne remplit pas de formulaires
  - Le formulaire classique reste disponible en fallback mais n'est pas l'expérience primaire
  - Contexte CRM injecté automatiquement dans chaque interaction (RAG)

## ADR-009 — Connecteurs et ingestion de données externes

- **Date** : 2026-03-05
- **Status** : Accepté
- **Decision** : Architecture de **connecteurs modulaires** pour centraliser les données depuis toutes sources externes
- **Connecteurs planifiés** :
  - **Search** : Serper.dev (+ BrightData évalué si scraping lourd)
  - **Web scraping** : Groq LLM pour extraction structurée
  - **Email** : IMAP/SMTP + API Gmail + API Outlook
  - **Call transcripts** : Groq Whisper
  - **Cloud storage** : Google Drive, OneDrive, Box, AWS S3
  - **Futurs** : systèmes comptables, marketing, opérations
- **Rationale** :
  - Le but est de centraliser TOUTE l'information client (jusqu'aux Excel dans les drives)
  - Chaque connecteur est un module indépendant, activable par tenant
  - Pipeline d'ingestion unifié : source → extraction → structuration (LLM) → persistance + embeddings

