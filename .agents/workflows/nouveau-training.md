---
description: "Créer une nouvelle formation — intake structuré + génération de présentation"
---

# /nouveau-training — Création de Formation

Ce workflow guide la création d'une formation utilisant `training-template` comme squelette visuel.
La V1 est manuelle (l'utilisateur fournit le contenu), la V2 utilisera des LLMs pour automatiser la génération.

---

## Étape 1 — Identification de la formation

Poser les questions suivantes :

| # | Question | Exemple |
|---|----------|---------|
| 1 | **Nom de la formation** | Onboarding CRM, Gestion des Opportunités, Accueil Client |
| 2 | **Objectif principal** | Former les nouveaux vendeurs au pipeline CRM |
| 3 | **Public cible** | Vendeurs juniors, gestionnaires, tous les employés... |
| 4 | **Durée estimée** | 15 min, 30 min, 1h, multi-session |
| 5 | **Nombre de modules/slides prévu** | 5 modules, ~24 slides total |

---

## Étape 2 — Comportement de Bob

Définir comment Bob interagit pendant la formation :

| # | Question | Options |
|---|----------|---------|
| 1 | **Rôle de Bob** | Narrateur, Coach interactif, Évaluateur, Silencieux |
| 2 | **Bob présente vocalement ?** | Oui (narration TTS) / Non (texte seul) |
| 3 | **Bob pose des questions ?** | Quiz entre slides, validation de compréhension, aucun |
| 4 | **Prise de notes automatique** | Bob résume les points clés au fur et à mesure / Manuel seulement |
| 5 | **Ton de Bob** | Formel, décontracté, motivant, technique |
| 6 | **Actions déclenchées** | Rappels, suggestions, liens vers la KB, rien |

---

## Étape 3 — Contenu et médias

Définir le contenu de chaque slide/module :

| # | Question | Exemple |
|---|----------|---------|
| 1 | **Type de contenu par slide** | Texte + icônes, Vidéo, Démo live, Schéma, Quiz |
| 2 | **Sources de données** | Texte fourni, KB existante, Documents uploadés, Généré par LLM (V2) |
| 3 | **Médias à intégrer** | Images, vidéos, captures d'écran, GIFs, aucun |
| 4 | **Assets fournis ?** | L'utilisateur fournit-il des fichiers ou tout est à créer ? |

---

## Étape 4 — Design et composants

Définir l'apparence et les panneaux latéraux :

| # | Question | Options |
|---|----------|---------|
| 1 | **Panneaux latéraux actifs** | Notes, AI Insights, Reminders — tout, partiel, aucun |
| 2 | **Barre de contrôles** | Navigation slides, volume, fullscreen, captions |
| 3 | **Thème visuel** | Par défaut (accent #FF4500), Custom (couleur + typo) |
| 4 | **Layout des slides** | Grille de cartes, Texte centré, Image plein écran, Split |
| 5 | **Animations/transitions** | Fade, slide, aucune |

---

## Étape 5 — Générer le plan d'implémentation

À partir des réponses, produire un `implementation_plan.md` contenant :

1. **Résumé de la formation** — nom, objectif, public, durée
2. **Configuration Bob** — rôle, ton, interactions, notes automatiques
3. **Structure des slides** — liste ordonnée avec type de contenu par slide
4. **Composants frontend** — quels panneaux, quel layout de slide, quels contrôles
5. **Données** — slides statiques en JSON dans le composant (V1), API backend (V2)
6. **Médias à préparer** — liste des assets à créer ou à fournir

Soumettre le plan pour approbation.

---

## Étape 6 — Déclencher /implante

Une fois le plan approuvé, déclencher le workflow `/implante` pour l'implémentation structurée.
Utiliser `training-template` comme squelette de base et adapter selon les specs.
