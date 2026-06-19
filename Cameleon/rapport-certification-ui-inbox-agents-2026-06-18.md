# Rapport de certification UI — Inbox Gmail-like et Agents

Date: 2026-06-18
Branche: `refactor/cde-ui-theme-conversation-standard`
Changement certifie: retrait du bloc `Smart Suggestions`, renommage `Assistant` vers `Agents`, refonte UX Inbox inspiree de Gmail, mailbox plein ecran, favicon Bob, nouvelle page login avec maquette simplifiee CDE, slogan Bob et fond abstrait plage/ocean/quai.

## Portee

- Navigation globale: `frontend/src/app/shared/layout/layout.html`
- Inbox shell: `frontend/src/app/pages/inbox/inbox-overview.html`
- Inbox navigation: `frontend/src/app/pages/inbox/components/inbox-sidebar/*`
- Feed conversations: `frontend/src/app/pages/inbox/components/email-list/*`
- Lecture/reponse: `frontend/src/app/pages/inbox/components/email-reading-pane/*`
- Mapping email Pipedream: `frontend/src/app/shared/services/email.service.ts`, `frontend/src/app/shared/services/membrane-backend.service.ts`
- Store Inbox NGRX: `frontend/src/app/store/inbox/*`
- Login: `frontend/src/app/pages/login/login.html`, `frontend/src/app/pages/login/login.css`
- Asset login: `frontend/public/login-abstract-art.png`
- Favicon: `frontend/public/favicon.png`, `frontend/public/favicon.ico`, `frontend/src/index.html`
- Matrice utilisee: `Cameleon/matrice-certification-regles-architecture-v1.5.md`
- Criteres applicables: `CERT-10`, `CERT-16`, `CERT-17`

## Preuves locales

| Preuve | Resultat |
| --- | --- |
| Build frontend | `cd frontend && npm run build` termine avec succes |
| Store Inbox NGRX | Les composants Inbox dispatchent des actions et lisent des selectors; les appels HTTP sont dans `InboxEffects` |
| Absence appels directs Inbox | `rg "EmailService\|SmartLabelService\|\\.subscribe\\(" frontend/src/app/pages/inbox -g '*.ts'` ne retourne rien |
| Recherche texte retire | `Smart Suggestions` et `Assistant` absents de la sidebar et de l'Inbox |
| Navigation globale | Section `Agents` visible |
| Navigation Inbox | `Compose`, `Mailbox`, `Inbox`, `Unread`, `Starred`, `Sent`, `Drafts`, `Trash`, `Priority`, `Actionable` visibles |
| Feed conversation | Liste de conversations avec sender, sujet, preview, tags et selection |
| Lecture conversation | Message selectionne visible dans le panneau de lecture |
| Reply/Forward | Onglets `Reply` et `Forward` visibles; champ reply saisissable |
| Champs Agent | `smart_label`, `ai_summary`, `ai_action_items` propages depuis Pipedream vers le modele unifie |
| Mailbox plein ecran | `.inbox-layout` couvre 100 % du viewport avec `position: fixed` |
| Bouton fermer | `X` fixe au coin superieur droit: `x=1380`, `y=24`, `rightGap=24`, `topGap=24` sur viewport `1440x950`; fond transparent, contour noir |
| Login | Slogan exact `Bob travaille fort pour que vous n'ayez pas à le faire.` |
| Login | Maquette simplifiee CDE a gauche, formulaire de connexion a droite |
| Login | Fond abstrait evoquant plage, ocean et long quai en bois avec teinte bleutee legere |
| Favicon | `favicon.png` declare dans `index.html`, logo Bob blanc dans un rond noir |
| Capture reelle sans email connecte | `captures/ui-inbox-gmail-like-agents.png` |
| Capture controlee avec conversation | `captures/ui-inbox-conversation-reply.png` |
| Capture mailbox plein ecran | `captures/ui-inbox-fullscreen-list.png` |
| Capture lecture Gmail-like | `captures/ui-inbox-gmail-reading.png` |
| Capture login | `captures/ui-login-cde-product-mock.png` |
| Capture login finale | `captures/ui-login-ocean-pier-abstract.png` |
| Capture login ajustee | `captures/ui-login-ocean-pier-lower-clearer.png` |
| Capture login liquid glass | `captures/ui-login-liquid-glass-50.png` |
| Capture login spacing/app agrandie | `captures/ui-login-spacing-bigger-app.png` |
| Capture login centre + Connexion gras | `captures/ui-login-centered-bold-connexion.png` |
| Capture login slogan gras + verre plus visible | `captures/ui-login-bold-slogan-clearer-glass.png` |
| Capture login glass 16 % | `captures/ui-login-glass-alpha-16.png` |
| Capture Inbox NGRX finale | `captures/ui-inbox-ngrx-reading.png` |
| Captures ignorees par Git | `captures/` reste ignore |

## Notes

Le build produit des avertissements Angular/CSS/CommonJS deja presents dans le projet. Aucun avertissement nouveau n'est lie a cette refonte.

La capture controlee utilise des reponses API locales interceptees pour valider le rendu du feed, du panneau de lecture, du bloc Reply/Forward, du store Inbox NGRX et de la mailbox plein ecran sans dependre d'une boite mail externe connectee.

## Verdict local

Certification locale attendue: `10/10` pour la portee UI/frontend de cette demande, incluant `CERT-10`, `CERT-16` et `CERT-17`.
