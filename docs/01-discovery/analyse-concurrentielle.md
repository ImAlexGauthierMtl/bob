# Analyse concurrentielle — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 01 · Discovery · **Dernière MAJ** : 2026-07-01
> ⚠️ Analyse de **positionnement**, basée sur la connaissance générale du marché (janvier 2026) et sur ce que CDE fait réellement. Les faits sur les concurrents évoluent vite — `[À VÉRIFIER]` avant tout usage externe/commercial.

## 1. Où se situe CDE

CDE joue à l'intersection de trois catégories qui convergent :

```
        CRM classique                 Assistant IA "copilote"
     (HubSpot, Pipedrive,            (chat greffé, suggestions)
        Salesforce, Zoho)                      │
              │                                │
              └──────────────┬─────────────────┘
                             ▼
                    ESPACE DE TRAVAIL
                    AGENTIQUE VERTICAL
                          = CDE
                     (l'agent exécute
                      le travail CRM+email
                      sous contrôle humain)
                             ▲
                             │
                  Plateforme d'automatisation
                    (Zapier, Make, n8n)
```

CDE n'est ni un « CRM avec un chatbot », ni un « Zapier avec des LLM » : c'est un **espace de travail où un agent opère un CRM vertical**, avec garde-fous.

## 2. Grille comparative

| Critère | CRM classique | Copilote IA greffé | Plateforme d'auto. | **CDE** |
|---|---|---|---|---|
| CRM intégré (contacts/opp/devis) | 🟢 riche | ⚪ dépend de l'hôte | 🔴 non | 🟢 complet |
| Inbox email native + liaison CRM | 🟡 add-on | 🟡 variable | 🔴 non | 🟢 dual-provider natif |
| Agent qui **exécute** (pas suggère) | 🔴 non | 🟡 partiel | 🟡 scripté | 🟢 tool-call loop |
| Garde-fous sur actions (confirm/readback) | n/a | 🔴 rare | 🟡 approbation basique | 🟢 gating natif |
| Gouvernance fine des outils IA | 🔴 non | 🔴 non | 🟡 par connecteur | 🟢 policies + risk + scope |
| Mémoire RAG par organisation | 🔴 non | 🟡 générique | 🔴 non | 🟢 scope + sensibilité |
| Traçabilité des actions IA | n/a | 🔴 opaque | 🟡 logs | 🟢 narration + ledger |
| Multi-tenant / isolation | 🟢 mûr | dépend | 🟢 mûr | 🟢 by design |
| Écosystème / maturité | 🟢 énorme | 🟢 gros | 🟢 gros | 🔴 naissant |

Légende : 🟢 fort · 🟡 partiel · ⚪ neutre · 🔴 faible/absent. `[À VÉRIFIER]`

## 3. Concurrents par catégorie

### CRM avec couche IA
**HubSpot (Breeze), Salesforce (Einstein/Agentforce), Pipedrive, Zoho.**
- **Forces** : maturité, écosystème, confiance, données déjà en place.
- **Angle CDE** : leur IA reste largement **assistive** (résumés, rédaction, scoring) et **branchée** sur un CRM conçu pour la saisie humaine. CDE part de l'agent : l'exécution encadrée est le défaut, pas une option premium. Salesforce **Agentforce** est le concurrent le plus proche philosophiquement — à surveiller de près `[À VÉRIFIER]` ; l'angle de CDE est le **vertical PME + Microsoft 365 + garde-fous granulaires**, là où Salesforce vise l'entreprise.

### Assistants / copilotes généralistes
**Microsoft Copilot, ChatGPT + connecteurs, Claude + MCP.**
- **Forces** : puissance des modèles, ubiquité.
- **Angle CDE** : ils ne portent **pas** l'état métier (pas de CRM, pas de pipeline, pas d'isolation tenant commerciale). CDE est un produit vertical avec sa donnée, ses écrans, sa gouvernance — pas un chat généraliste. (Note : CDE *consomme* ces briques — LLM via Fireworks, outils via MCP.)

### Plateformes d'automatisation
**Zapier, Make, n8n, + Pipedream (que CDE *utilise*).**
- **Forces** : largeur des connecteurs, flexibilité.
- **Angle CDE** : elles automatisent des *flux* déterministes ; elles ne *raisonnent* pas sur un contexte commercial et n'ont pas d'UI métier. CDE utilise Pipedream comme **tuyau d'intégration**, et met par-dessus l'agent + le CRM + la gouvernance.

## 4. Douves (moats) potentielles de CDE

1. **La gouvernance d'outils comme produit** : `tool_policies` (risque, scope équipe, activation) + préférences utilisateur + confirmation. Peu de concurrents offrent ce niveau de contrôle sur *ce que l'IA a le droit de faire*. C'est un argument de vente en environnement régulé.
2. **La traçabilité de bout en bout** : narration steps + ledger d'usage avec `correlation_id`. Auditable → vendable aux clients prudents.
3. **La verticalité** : le contexte CRM+email rend l'agent *utile immédiatement*, là où un agent générique doit être configuré.
4. **La donnée propriétaire accumulée** : mémoire organisationnelle + historique d'actions confirmées = un actif qui grossit avec l'usage (effet de rétention).

## 5. Faiblesses & risques concurrentiels (lucides)

- **Maturité & confiance** : un acteur naissant face à des suites installées. La barre de fiabilité est haute.
- **Les incumbents avancent vite sur l'agentique** (Agentforce, Breeze). La fenêtre est réelle mais pas infinie.
- **Complexité opérationnelle** : 21 services à opérer vs un SaaS mono-produit concurrent.
- **Dépendance à des tiers** (Fireworks, Pipedream, MS Graph) : risque de coût, de rate-limit, de rupture d'API.

Voir [Risk Register](../06-gouvernance/risk-register.md).

## 6. Positionnement synthétique

> **Pour** les équipes commerciales B2B de PME sous Microsoft 365
> **qui** perdent leur temps à administrer leur CRM et à trier leurs emails,
> **CDE est** un espace de travail commercial piloté par un copilote IA
> **qui** exécute réellement le travail de suivi — sous contrôle et traçable.
> **Contrairement à** un CRM assisté par IA ou un chatbot greffé,
> **CDE** met l'agent au centre, avec des garde-fous natifs sur chaque action.

> `[À VÉRIFIER]` Confirmer les capacités actuelles d'Agentforce/Breeze et la tarification des concurrents avant tout usage commercial de ce document.
