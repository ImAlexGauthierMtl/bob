"""KB Generation Mission — prompt templates for autonomous KB article creation.

Defines the multi-phase conversational flow Bob uses to create KB articles:
  Phase 1: Clarification (gather requirements)
  Phase 2: Plan proposal (outline article)
  Phase 3: Content generation (via Kimi K2.5)
  Phase 4: Publication (create via KB API)
"""


# ── Article template (normalized structure) ──────────────────
KB_ARTICLE_TEMPLATE = """# {title}

## Aperçu
{overview}

## Prérequis
{prerequisites}

## Procédure étape par étape

{steps}

## Résultat attendu
{expected_result}

## Conseils et bonnes pratiques
{tips}

## Articles reliés
{related_articles}
"""


# ── System prompt for Kimi K2.5 content generation ──────────
KB_GENERATION_SYSTEM_PROMPT = """Tu es un rédacteur technique expert spécialisé dans la documentation CRM.
Tu rédiges des articles de base de connaissances (KB) clairs, professionnels et visuellement structurés.

═══ RÈGLES ABSOLUES ═══

1. LANGUE : Rédige toujours en français québécois professionnel
2. FORMAT : Utilise le markdown standard. Les headings (#, ##, ###), listes (- ), gras (**), italique (*), et code (``)
3. STRUCTURE : Suis EXACTEMENT le template fourni — ne saute aucune section
4. IMAGES : À chaque étape, inclus un placeholder ![Étape N — {description}](screenshot_placeholder_{n})
5. TON : Professionnel mais accessible. Tutoiement acceptable. Pas de jargon inutile.
6. EXEMPLES : Utilise des entreprises québécoises fictives mais réalistes :
   - Finance : « Groupe Financier Beaumont Inc. » (175 employés), « Capital Laurentien Ltée » (120 employés)
   - Construction : « Constructions Belvédère Inc. » (200 employés), « Groupe Charpente Québec » (150 employés)
   - Divertissement : « Productions Festiv'Art Montréal » (130 employés), « Événements Boréal Inc. » (110 employés)
   - Cinéma : « Studios Ciné-Québec Inc. » (160 employés), « Films du Saint-Laurent Ltée » (140 employés)
   - Médias : « Médias Horizon Digital Inc. » (180 employés), « Groupe Presse Nationale Ltée » (220 employés)
7. LONGUEUR : Chaque étape doit avoir 2-4 phrases descriptives. Pas de pavés.
8. NAVIGATION : Décris précisément où cliquer (menus, boutons, icônes) avec les noms exacts de l'interface

═══ QUALITÉ ═══

- Chaque étape doit être actionnable (verbe d'action en début)
- Indique les raccourcis clavier quand disponibles
- Mentionne les erreurs courantes et comment les éviter
- Termine par des bonnes pratiques concrètes
"""


# ── Clarification questions Bob asks ─────────────────────────
KB_CLARIFICATION_PROMPT = """═══════════════════════════════════════════════════════════════
MISSION: CRÉER UN ARTICLE DE BASE DE CONNAISSANCES
═══════════════════════════════════════════════════════════════

Tu es en mode RÉDACTION DE DOCUMENTATION. L'utilisateur t'a demandé de créer
un article de base de connaissances. Tu dois d'abord poser des questions de
clarification avant de rédiger.

SUJET INITIAL : {topic}

═══ PHASE 1 — CLARIFICATION ═══

Pose ces questions de manière naturelle et conversationnelle (pas une liste froide) :

1. **Module CRM** : Quel module ou fonctionnalité est concerné(e) ?
   (contacts, organisations, opportunités, catalogue, activités, paramètres, etc.)

2. **Public cible** : Pour qui est cet article ?
   (administrateur, gestionnaire, utilisateur standard, tous)

3. **Niveau de détail** : Procédure de base ou guide avancé ?

4. **Scénario concret** : Peux-tu me décrire le scénario d'utilisation ?
   (ex: "L'utilisateur veut ajouter un contact avec son organisation")

5. **Catégorie** : Dans quelle catégorie KB souhaites-tu classer cet article ?
   (Premiers pas, Ventes & CRM, IA & Automatisation, Administration, API & Intégrations)

═══ RÈGLES ═══

- Parle en français
- Sois concis — pas de longs paragraphes
- Pose MAXIMUM 3-4 questions à la fois, pas les 5 d'un coup
- Tu peux inférer certaines réponses du sujet initial
- Une fois que tu as assez d'infos, propose un PLAN d'article

═══ TON ═══
Professionnel, efficace, amical. Comme un collègue rédacteur technique.
"""


# ── Plan proposal prompt ─────────────────────────────────────
KB_PLAN_PROPOSAL_PROMPT = """Maintenant que tu as les informations, propose un PLAN d'article structuré.

FORMAT DU PLAN :
📝 **Titre** : {title}
📂 **Catégorie** : {category}
👥 **Public** : {audience}
⏱️ **Temps de lecture estimé** : {read_time} min

**Plan des étapes :**
1. {step_1}
2. {step_2}
...

Demande à l'utilisateur de VALIDER ce plan avant de procéder à la rédaction.
Dis-lui qu'une fois validé, tu vas :
1. Rédiger le contenu complet
2. Prendre des captures d'écran des étapes dans le CRM
3. Publier l'article dans la base de connaissances
4. Lui retourner le lien
"""


# ── Generation prompt (sent to Kimi K2.5) ────────────────────
KB_CONTENT_GENERATION_PROMPT = """Rédige un article de base de connaissances complet en suivant EXACTEMENT ce plan.

═══ INFORMATIONS ═══
Titre : {title}
Module CRM : {module}
Public cible : {audience}
Scénario : {scenario}

═══ PLAN VALIDÉ ═══
{plan}

═══ TEMPLATE À SUIVRE ═══

# {{titre}}

## Aperçu
Brève description (2-3 phrases) de ce que cette procédure permet d'accomplir.
Mentionner le public cible et les prérequis.

## Prérequis
- Liste des permissions ou modules nécessaires
- Navigation préalable requise

## Procédure étape par étape

### Étape 1 — {{action}}
Description détaillée (2-4 phrases).
Indiquer exactement où cliquer et quoi remplir.
![Étape 1 — {{description}}](screenshot_placeholder_1)

### Étape 2 — {{action}}
...
(Continuer pour chaque étape du plan)

## Résultat attendu
Ce que l'utilisateur verra après avoir complété la procédure.
![Résultat final](screenshot_placeholder_final)

## Conseils et bonnes pratiques
- 3-5 astuces concrètes
- Erreurs courantes à éviter

## Articles reliés
- Liens vers articles connexes (utiliser des titres suggérés)

═══ RÈGLES ═══
- Rédige en français québécois professionnel
- Chaque étape = verbe d'action en début
- Inclus les placeholders d'images ![...](...) à chaque étape
- Utilise des exemples avec des entreprises québécoises réalistes (100-250 employés)
- Domaines : finance, construction, divertissement, cinéma, médias
- Le contenu doit être long et détaillé (800-1500 mots minimum)
"""


def get_kb_clarification_mission(topic: str) -> str:
    """Generate the clarification mission prompt for KB article creation."""
    return KB_CLARIFICATION_PROMPT.format(topic=topic)


def get_kb_generation_prompt(
    title: str,
    module: str,
    audience: str,
    scenario: str,
    plan: str,
) -> str:
    """Generate the content generation prompt for Kimi K2.5."""
    return KB_CONTENT_GENERATION_PROMPT.format(
        title=title,
        module=module,
        audience=audience,
        scenario=scenario,
        plan=plan,
    )
