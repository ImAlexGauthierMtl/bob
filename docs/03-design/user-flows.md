# User Flows — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 03 · Design · **Dernière MAJ** : 2026-07-01
> Parcours utilisateurs clés, dérivés du routing réel (`app.routes.ts`) et des [JTBD](../01-discovery/jobs-to-be-done.md).

## Flow 0 — Authentification & sélection d'organisation

```
/login ──(email+password)──► Auth B4F (JWT access 24h + refresh 7j)
   │                              │
   └── échec (rate-limit 5/15min) └──► /select-organization ──► set active_organization_id
                                              │
                                              └──► / (layout protégé par authGuard)
```
- Interceptor : ajoute `Bearer`, refresh auto sur 401, redirige au dashboard sur 403.

## Flow 1 — Créer un contact en langage naturel (JTBD-1)

```
Chat Bob : « crée un contact Jean Dupont, dir. achats chez Acme »
   │
   ▼
Bob parse (NLP) → champs extraits + confidence
   │
   ▼
[Gate de confirmation] readback : "Créer Contact {Jean Dupont, Acme, ...} ?"
   │                                   │
  Annuler                            Confirmer
   │                                   │
  (rien)                    POST contact → event contact.created
                                        │
                                        └──► visible dans /contacts, rattaché à l'org Acme
```

## Flow 2 — Traiter l'inbox (JTBD-2)

```
Email entrant ──► webhook Pipedream (HMAC) / MS365 ──► email-backend
   │
   ▼
Rattachement auto (linked_contact_id / linked_organization_id) + smart_label
   │
   ▼
/inbox : filtre (dossier/label/non-lu/important) ──► reading pane
   │
   ├── Répondre / Transférer (action Pipedream) ── [gate si envoi] ──► envoyé
   └── Ouvrir le contact lié ──► /contacts/{id} (profil 360°, onglet Emails)
```

## Flow 3 — Faire avancer un deal et générer un devis (JTBD-3)

```
/opportunities ──► opportunité (stage: QUALIFICATION)
   │
   ├── changer le stage ──► NEGOTIATION
   ├── ajouter lignes produits (qty, prix, remise)
   ▼
Créer un devis ──► calcul auto (subtotal → remise → taxe → total)
   │
   ▼
Quote: DRAFT ──► SENT ──► ACCEPTED ──► Opportunité: CLOSED_WON + Org: CUSTOMER
```

## Flow 4 — Bob exécute une action outillée avec gouvernance (JTBD-4)

```
Message utilisateur
   │
   ▼
Contexte mémoire (RAG, selon scope+sensibilité)
   │
   ▼
Routage MCP déterministe (si mot-clé famille) ── sinon ──► LLM sélectionne outils
   │
   ▼
Filtrage gouvernance (policies admin + préférences user)
   │
   ▼
Tool-call loop (≤5 itérations) : LLM → tool_calls
   │
   ├── outil read ────────────────► exécute directement
   └── outil write/destructive ──► [Gate confirmation + readback]
                                          │
                                    Confirmer ──► exécute (confirmed=True)
   │
   ▼
Run stocké (provider, modèle, narration, coût) ──► réponse + narration + confirmations
```

## Flow 5 — Automatiser un process d'équipe (JTBD-5)

```
Admin ──► Settings › Automation › Builder
   │
   ▼
Créer Workflow (level: company, trigger: event contact.created, mode: require_approval)
   │
   ▼
Définir steps (DAG : entry → step → on_success/on_failure)
   │
   ▼
Événement contact.created ──► webhook ──► WorkflowExecution (log par step)
   │
   └── mode require_approval ──► [validation humaine] ──► exécution
```

## Flow 6 — Manager pilote (JTBD-7)

```
/dashboard : totaux CRM (composition B4F parallèle) + highlights + next_actions
   │
   ├──► /analytics : métriques CRM + plateforme
   └──► /usage-logs : transactions (service/catégorie/date) + synthèse par intent
                          │
                          └── super-admin ──► /admin/usage (cross-tenant) + rate cards
```

## Points de friction à surveiller (design)
- Le **gate de confirmation** ne doit pas devenir un réflexe « OK » aveugle (fatigue de confirmation) → soigner le readback, différencier visuellement le risque.
- La **liaison auto** email→contact peut se tromper → prévoir la correction manuelle simple.
- La **densité** des profils 360° (onglets) ne doit pas noyer l'action principale.

> `[À COMPLÉTER]` Ces flows sont textuels (dérivés du routing et des specs). Étape suivante : wireframes/prototypes cliquables pour les 3 flows différenciants (1, 2, 4) et tests d'utilisabilité.
