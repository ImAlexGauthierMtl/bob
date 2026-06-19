# Rapport de certification UI — retrait Training

Date: 2026-06-18
Branche: `refactor/cde-ui-theme-conversation-standard`
Changement certifie: retrait du lien `Training` dans la sidebar applicative.

## Portee

- Fichier modifie: `frontend/src/app/shared/layout/layout.html`
- Matrice utilisee: `Cameleon/matrice-certification-regles-architecture-v1.5.md`
- Criteres applicables: `CERT-16` UI et theme, `CERT-17` tests locaux

## Preuves locales

| Preuve | Resultat |
| --- | --- |
| Build frontend | `cd frontend && npm run build` termine avec succes |
| Validation navigateur | `http://localhost:4700/dashboard` charge avec la sidebar |
| Assertion UI | Texte `Training` absent de `.sidebar` |
| Capture | `captures/ui-remove-training-sidebar.png` |
| Git ignore capture | `captures/ui-remove-training-sidebar.png` est ignore par Git |

## Notes

Le build produit des avertissements Angular/CSS/CommonJS deja presents dans le projet. Aucun avertissement nouveau n'est lie au retrait du lien `Training`.

## Verdict local

Certification locale attendue: `10/10` pour le changement UI limite au retrait du lien de navigation `Training`.
