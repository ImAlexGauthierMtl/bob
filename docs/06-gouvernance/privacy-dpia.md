# Privacy & DPIA (préliminaire) — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 06 · Gouvernance · **Dernière MAJ** : 2026-07-01
> Analyse d'impact relative à la protection des données (DPIA/AIPD), **préliminaire**. CDE traite des données personnelles (contacts, emails) et les fait manipuler par une IA → une DPIA formelle est requise avant une mise en production à l'échelle. ⚠️ Ce document n'est **pas un avis juridique** ; à faire valider par un conseil RGPD.

## 1. Pourquoi une DPIA
Déclencheurs présents : traitement à grande échelle de données personnelles, **profilage/enrichissement** (Hunter, Bright Data, LinkedIn), traitement automatisé par IA (Bob agissant sur des données), données de communication (emails). Ces facteurs rendent la DPIA fortement recommandée/obligatoire (RGPD art. 35).

## 2. Cartographie des données personnelles

| Donnée | Catégorie | Où | Base légale probable `[À VALIDER juridiquement]` |
|---|---|---|---|
| Contacts (nom, email, tel, poste, LinkedIn) | données pro | `contact` backend | intérêt légitime (prospection B2B) |
| Enrichissement (`contact_profile`, `organization_profile`) | données agrégées de tiers | CRM backends | intérêt légitime + transparence |
| Emails synchronisés (contenu, PJ, expéditeurs) | correspondance | `email` backend | exécution (mandat du client sur sa boîte) |
| Mémoire de Bob (insights, faits sur personnes) | dérivées | `agent-memory` (PG + Milvus) | intérêt légitime + sensibilité typée |
| Utilisateurs CDE (auth, rôles) | identité | `user` backend | contrat |
| Ledger d'usage (user_id/email, actions) | traçabilité | `usage` backend | intérêt légitime (facturation/sécurité) |

## 3. Rôles RGPD
- **Client (tenant)** = **responsable de traitement** de ses données CRM/emails.
- **Croo/CDE** = **sous-traitant** (traite pour le compte du client) → nécessite un **DPA** (Data Processing Agreement) par client. `[À CRÉER]`
- **Sous-traitants ultérieurs** : Fireworks (LLM), Pipedream, Microsoft, Milvus, Hunter/Bright Data → à lister dans le DPA, avec localisation des données. `[À VÉRIFIER : transferts hors UE]`

## 4. Principes & état de conformité

| Principe RGPD | État CDE | Écart / action |
|---|---|---|
| **Minimisation** | enrichissement large (profils tiers) | 🟡 justifier la nécessité de chaque champ enrichi |
| **Limitation des finalités** | données CRM/email pour la vente | ✅ cohérent ; documenter |
| **Isolation / sécurité** | `tenant_id`, backends non exposés, TLS | 🟡 chiffrement au repos + tests anti-fuite (R1) |
| **Conservation limitée** | soft-delete ; `expires_at` sur mémoire | ⛔ **politique de rétention/purge à définir et outiller** (emails, ledger, mémoire) |
| **Droit d'accès/portabilité** | données structurées par tenant | 🟡 export tenant à outiller |
| **Droit à l'effacement** | soft-delete (pas de purge physique) | ⛔ **purge réelle** (hard delete + vecteurs Milvus) à implémenter |
| **Transparence** | — | ⛔ mentions d'information / politique de confidentialité à rédiger |
| **Sensibilité IA** | `MemoryEntry.sensitivity` filtrée en RAG | ✅ bon point ; à documenter côté client |

## 5. Risques spécifiques IA (RGPD + IA Act)
- **Décisions automatisées** : Bob agit, mais le **gating de confirmation** garde un humain dans la boucle → limite le profilage/décision automatisée « produisant des effets juridiques » (RGPD art. 22). À documenter comme garantie.
- **Données personnelles dans les prompts/mémoire** envoyées à Fireworks → clarifier la non-rétention côté fournisseur, la localisation, l'anonymisation possible.
- **Empoisonnement/fuite de mémoire** : voir [Threat Model](../04-technique/threat-model.md).

## 6. Mesures existantes (à valoriser)
`tenant_id`, sensibilité typée + scope de mémoire, soft-delete + audit, gating humain, traçabilité (ledger), backends non exposés, TLS.

## 7. Actions prioritaires
1. ⛔ **Politique de rétention** (durées par type de donnée) + **purge physique** outillée (droit à l'effacement, y compris vecteurs Milvus).
2. ⛔ **DPA** + liste des sous-traitants + localisation des données + transferts hors UE.
3. ⛔ **Mentions d'information / politique de confidentialité**.
4. 🟡 **Chiffrement au repos** des données sensibles (tokens OAuth, emails).
5. 🟡 **Export tenant** (portabilité).
6. ✅→doc **Garantie humain-dans-la-boucle** (art. 22) formalisée.
7. **DPIA formelle** validée par un conseil juridique avant scale.

> Croisé avec [Risk Register R8](risk-register.md) et [Launch Readiness §3](../05-delivery/launch-readiness.md).
