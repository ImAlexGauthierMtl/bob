# Framework HDQ — Haute Définition Qualité

> Source de vérité pour le développement assisté par IA chez The Smart Crew.

## Principe

```
Si une RÈGLE existe   → le LLM l'APPLIQUE (déterministe)
Si AUCUNE règle       → le LLM le SIGNALE → gap à combler
```

Le framework grandit par l'usage. Chaque gap détecté = une future norme.

## Quick Start

### Installer dans un projet existant

```bash
# Copier la structure .agents/
cp -r /chemin/vers/framework-hdq/ mon-projet/.agents/

# Personnaliser le contexte projet
cp .agents/context/projet.template.md .agents/context/projet.md
# Éditer projet.md avec les infos spécifiques au projet
```

### Utilisation quotidienne

Toute demande de travail commence par :

```
/start
```

L'agent pose les questions, classifie la demande, annonce la route HDQ, et exécute.

## Structure

```
framework-hdq/
├── workflows/        ← Slash-commands (/start, /delta, /implante...)
├── skills/           ← Capacités agent (backend, frontend, testing...)
├── normes/           ← Standards enrichis par domaine
├── rules/            ← Règles agent (architecture, conventions...)
├── context/          ← Templates Ω:CONTEXT
├── decisions/        ← Templates ADR
├── docs/             ← Index, gaps, dette technique, case studies
└── graveyard/        ← Code/décisions retirés
```

## Mise à jour

Le workflow `/start` synchronise automatiquement le framework depuis le repo central :

```bash
# Ou manuellement
git -C ~/Dev/framework/framework-hdq pull --ff-only
```

## Projets utilisant ce framework

| Projet | Domaine | Status |
|--------|---------|--------|
| Le Baluchon | PMS hôtelier | ⭐ Gold standard |
| Bob V2 | CRM | Actif |
| ASQ | CRM consultant | Actif |
| Rondeau | CRM financier | Actif |
| Madysta | ERP | Actif |
| Croo | Pipeline IA | Actif |

## Documentation

- [HDQ.md](HDQ.md) — Point d'entrée développeur
- [docs/index.md](docs/index.md) — Index complet Ω:DOCS
- [docs/gaps.md](docs/gaps.md) — Normes à écrire (registre)
