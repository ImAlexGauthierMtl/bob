---
description: "Intake depuis un ticket Zoho — fetch, analyse pièces jointes, synthèse, route HDQ"
---

# /zoho — Intake Zoho Desk

// turbo-all

Ce workflow est déclenché depuis `/start` quand la source est un ticket Zoho.

---

## Étape 1 — Identifier le ticket

Demander à l'utilisateur :
- **Numéro ou ID du ticket Zoho** (ex: #12345)
- Ou **titre partiel** pour rechercher

---

## Étape 2 — Fetch le ticket

Utiliser le skill `zoho-attachments` pour récupérer :

```bash
python3 .agents/skills/zoho-attachments/scripts/fetch_ticket.py --ticket-id <ID>
```

Ce script retourne :
- Titre, description, priorité, assigné, date création, date due
- Liste des pièces jointes téléchargées dans `/tmp/zoho-<ticket_id>/`

---

## Étape 3 — Analyser les pièces jointes

Pour chaque image téléchargée dans `/tmp/zoho-<ticket_id>/` :

1. Ouvrir l'image avec `view_file`
2. Analyser :
   - **Texte visible** (labels, messages d'erreur, formulaires)
   - **Éléments annotés** (encadrés, flèches, surlignages)
   - **Contexte visuel** (quel écran, quel composant, quel état)
3. Résumer les observations

Pour chaque PDF :
1. Extraire le texte
2. Résumer le contenu pertinent

---

## Étape 4 — Synthèse enrichie

Produire une synthèse qui combine :

```markdown
## Synthèse Ticket Zoho #[ID]

**Titre** : [titre]
**Priorité** : [HIGH/MEDIUM/LOW]
**Assigné** : [nom]
**Date due** : [date]

### Description
[Description du ticket]

### Analyse des pièces jointes
[Résumé de ce qui est montré/annoté dans les screenshots]
[Contexte visuel extrait]

### Besoin identifié
[Reformulation du besoin en termes techniques]

### Services/modules touchés
[Liste des services identifiés]
```

---

## Étape 5 — Retour à /start

Avec la synthèse enrichie, retourner au flux `/start` :
- Étape 4 (Rule-Gap Analysis) avec le contexte Zoho
- Étape 5 (Annoncer la route HDQ)
- Étape 6 (Approbation)
