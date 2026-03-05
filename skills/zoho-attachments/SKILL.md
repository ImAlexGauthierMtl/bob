---
name: zoho-attachments
description: "Fetch et analyser les pièces jointes d'un ticket Zoho Desk"
---

# Skill: Zoho Attachments

Ce skill permet de récupérer un ticket Zoho Desk et ses pièces jointes pour analyse par l'agent.

## Pré-requis

- Variable d'environnement `ZOHO_DESK_API_TOKEN` configurée
- Variable d'environnement `ZOHO_DESK_ORG_ID` configurée
- Python 3.11+ avec `requests` installé

## Usage

```bash
python3 .agents/skills/zoho-attachments/scripts/fetch_ticket.py --ticket-id <TICKET_ID>
```

## Ce que le script fait

1. **Fetch le ticket** : `GET /api/v1/tickets/{id}`
   - Retourne : titre, description, priorité, assigné, date création, date due

2. **Fetch les pièces jointes** : `GET /api/v1/tickets/{id}/attachments`
   - Télécharge chaque fichier dans `/tmp/zoho-{ticket_id}/`
   - Supporte : images (PNG, JPG), PDF, documents

3. **Affiche un résumé** JSON avec métadonnées du ticket et chemins des fichiers

## Après le fetch

L'agent Antigravity doit :
1. Lire chaque image avec `view_file` (capacité vision)
2. Extraire : texte visible, éléments annotés, contexte visuel
3. Intégrer dans la synthèse d'intake du workflow `/zoho`

## API Zoho Desk

```
Base URL: https://desk.zoho.com/api/v1
Headers:
  Authorization: Zoho-oauthtoken {ZOHO_DESK_API_TOKEN}
  orgId: {ZOHO_DESK_ORG_ID}

GET /tickets/{id}
GET /tickets/{id}/attachments
GET /tickets/{id}/attachments/{attachment_id}/content
```
