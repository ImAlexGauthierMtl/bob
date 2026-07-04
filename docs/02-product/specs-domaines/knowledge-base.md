# Spec produit — Knowledge Base

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 02 · Produit · **Dernière MAJ** : 2026-07-01
> Parent : [PRD §4.4](../prd-cahier-des-charges.md#44-knowledge-base--spec-détaillée)

## 1. Objet

Base de connaissance interne du tenant : process, produits, réponses types. Couvre [JTBD-6](../../01-discovery/jobs-to-be-done.md) (trouver la connaissance au bon moment) — pour l'humain **et** pour Bob (complément de la mémoire RAG).

## 2. Modèle de données

- **Catégorie** (`kb_categories`) : `name`, `slug`, `description`, `icon`, `color`, `sort_order`, `article_count` (dénormalisé).
- **Article** (`kb_articles`) : `title`, `slug` (unique), `excerpt`, `content`, `category_id`, `tags[]`, `visibility` ∈ {internal, shared, public}, `required_module`, `required_role`, métadonnées auteur, **engagement** (`read_time_minutes`, `view_count`, `helpful_yes`, `helpful_no`), `is_published`, `is_featured`, soft-delete.

## 3. Fonctionnalités

- **CRUD** articles & catégories (tenant-scoped).
- **Recherche** plein texte (titre/excerpt/tags) + filtres (catégorie, visibilité).
- **Home KB** composée par le B4F (`/kb/home`) : catégories + articles récents + populaires + stats + empty-state (hint de création).
- **Feedback** : vote utile/pas utile (`/kb/articles/{id}/feedback`) incrémentant `helpful_yes/no`.
- **Stats globales** (`/kb/stats`) : total articles, publiés, catégories, vues, helpfulness moyen.
- **Contrôle d'accès** par `visibility` + `required_module`/`required_role`.

## 4. Parcours

1. Un admin/éditeur crée des catégories puis des articles (contenu manuel).
2. Un utilisateur cherche, lit (compteur de vues), vote utile/pas utile.
3. Bob interroge la KB pour répondre en contexte (via mémoire/outils).

## 5. Surfaces UI
`kb-portal` (portail : catégories, populaires, récents, recherche), store NGRX `kb` (cache home), services `kb.service` (métier) et `kb-b4f.service` (home).

## 6. Exigences & priorités
Voir [PRD §4.4](../prd-cahier-des-charges.md#44-knowledge-base--spec-détaillée). Must : EF-KB-1,2,3. Should : home (4), feedback (5), access-control (6).

## 7. Gaps & hypothèses
- **Génération d'article par LLM** (EF-KB-7) : **non détectée** dans le code (contenu manuel via `ArticleCreate`). Hypothèse à trancher : soit on l'implémente (via `agent-runtime`), soit on retire l'exigence.
- **Screenshots/assets** : pas de stockage d'images dédié détecté ; probablement embarqués dans `content` (HTML) ou via CDN externe — à clarifier.
- **Lien KB ↔ mémoire RAG de Bob** : les deux coexistent (KB relationnelle vs `KnowledgeCollection`/`KnowledgeChunk` vectoriel côté agent-memory) ; définir quand utiliser l'une ou l'autre.

## 8. Métriques
Nombre d'articles publiés, taux de couverture des questions (recherches sans résultat), helpfulness moyen, usage par Bob (articles cités dans les réponses).
