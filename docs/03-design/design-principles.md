# Principes de design — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 03 · Design · **Dernière MAJ** : 2026-07-01
> Principes d'expérience et de design système, dérivés des [Tenets](../00-vision/tenets.md) et de l'implémentation frontend réelle (Angular 21, CSS custom — pas de librairie Material).

## 1. Principes d'expérience (UX)

### P1 — L'agent est au centre, pas dans un coin
Bob n'est pas un bouton de chat en bas à droite. Il est présent dans le layout (overlay chat + overlay d'affichage), traverse les écrans, et agit dans le contexte courant. Le design doit refléter que **Bob est un collègue**, pas un widget.

### P2 — Toujours montrer ce que l'IA fait et va faire
Traduction directe du tenet 2. Les **narration steps** sont un élément de design de première classe : l'utilisateur voit la séquence (`demande reçue → provider → outil → confirmation → réponse`). Rien ne se passe « en douce ».

### P3 — La confirmation est un moment de design, pas une pop-up d'excuse
Le *gate* de confirmation (tenet 1) doit être clair, rapide et informatif : **quoi** (l'action), **sur quoi** (les données), **quel risque** (write/destructive). Un *readback* lisible réduit l'angoisse et accélère la décision.

### P4 — Le contexte suit l'utilisateur
Sélection d'organisation active, liaison email↔contact, mémoire : l'utilisateur ne doit jamais « rechercher » un contexte que le système connaît déjà. Le bon état par défaut > la configuration.

### P5 — Dégrader visiblement, jamais casser
Si un provider tombe (LLM, Milvus), l'UI l'indique (statut `degraded`) et propose une voie de repli, plutôt qu'un écran d'erreur. Un 403 ramène au dashboard, pas sur une page morte.

### P6 — La densité au service du pro
Public B2B qui travaille toute la journée dans l'outil : privilégier la densité d'information utile, les listes paginées scannables, les profils 360° à onglets — pas le minimalisme décoratif.

## 2. Système de design (état réel)

> Le frontend n'utilise **pas** Angular Material : styles **CSS custom** (`src/styles.css` + styles de composants, budget 20 Ko/composant). Le design system est donc à formaliser à partir de l'existant.

### Fondations à documenter (`[À COMPLÉTER]`)
- **Couleurs** : palette de marque + couleurs sémantiques (succès/alerte/danger), + les couleurs de smart labels et catégories KB (définies en données, `color` hex).
- **Typographie** : échelle de tailles, rendu markdown (lib `marked` utilisée pour les messages de Bob).
- **Espacement & grille** : à extraire du CSS.
- **Composants** : layout/shell, navigation, listes paginées, profils à onglets, reading pane email, overlays Bob (chat + display), formulaires (reactive forms), confirmations.
- **États** : loading (via NGRX `RemoteState`), vide (empty-states, ex. KB home), erreur, dégradé.

### Iconographie
Icônes de catégories (`icon` en donnée), emojis dans la doc d'architecture — à unifier sous un set cohérent.

## 3. Accessibilité & i18n

- **i18n** : l'app parle français ; réglages Bob supportent `language` ∈ {auto, fr, en, es}. Prévoir l'internationalisation des écrans si expansion.
- **Accessibilité** `[À VALIDER]` : niveau visé (WCAG AA recommandé pour B2B), contraste des couleurs de labels/catégories à vérifier, navigation clavier.

## 4. Cohérence multi-frontend

5 MFE logiques (crm, inbox, bob, platform, settings) partagent **un** shell et **un** design system. Règle : un composant partagé vit dans `shared/`, jamais dupliqué par MFE. La cohérence visuelle prime sur l'autonomie de chaque MFE.

## 5. Prochaines étapes design

1. Extraire un **design tokens** (couleurs/typo/espacement) depuis le CSS existant.
2. Documenter la **bibliothèque de composants** réelle (inventaire + captures).
3. Formaliser les **patterns Bob** (narration, confirmation, overlay, artifacts) — c'est le patrimoine UX différenciant.
4. Audit **accessibilité** AA.

> Ce document est un **squelette assumé** : le design system n'existe pas encore formellement dans le code (CSS custom épars). Sa formalisation est un chantier à part entière, à prioriser avec le fondateur.
