# Phase 6 — Patterns UNRULED (sans template HDQ)

> **Pour** : Architectes senior — révision des patterns implémentés sans template de référence.
> **Date** : 2026-03-06
> **Phase** : 6 — Agent d'enrichissement automatique (LangGraph + Groq + Serper)

---

## Résumé

| # | Pattern | Fichier | Complexité |
|---|---------|---------|------------|
| 1 | LangGraph State Schema | `app/agents/state.py` | 🟡 |
| 2 | Groq LLM Client | `app/agents/llm_client.py` | 🟡 |
| 3 | LangGraph Graph Definition | `app/agents/enrichment_graph.py` | 🔴 |
| 4 | Web Scraper Node | `app/agents/nodes/scraper_node.py` | 🟡 |
| 5 | LLM Structured Extraction | `app/agents/nodes/extraction_node.py` | 🟡 |
| 6 | Serper Maps Search | `app/presentation/routes/search_routes.py` | 🟢 |
| 7 | Intent-to-Field Mapping | `app/application/use_cases/enrich_organization.py` | 🟡 |
| 8 | Frontend Search → Select Dialog | `frontend/src/app/pages/organizations/` | 🟡 |
| 9 | Address Parsing (Maps → DB fields) | `organizations.ts:selectPlace()` | 🟢 |
| 10 | Auto-Enrich after Create | `organizations.ts:createAndEnrich()` | 🟢 |

---

## Détails par pattern

### 1. LangGraph State Schema

**Fichier** : `backend/app/agents/state.py`

```python
class EnrichmentState(TypedDict):
    organization_id: str
    organization_name: str
    tenant_id: str
    user_email: str
    search_results: List[SearchResult]
    urls_to_scrape: List[str]
    scraped_data: List[ScrapedData]
    extracted: dict
    status: str
    error: Optional[str]
```

**⚠️ Points à valider** :
- `TypedDict` vs Pydantic `BaseModel` pour le state ?
- Le champ `extracted: dict` est non-typé — acceptable pour flexibilité LLM ?
- Pas de versioning du state schema — acceptable pour v1 ?

---

### 2. Groq LLM Client (Singleton)

**Fichier** : `backend/app/agents/llm_client.py`

**Pattern** : Singleton global `llm_client = LLMClient()` instancié au module-level.

**⚠️ Points à valider** :
- Le singleton est créé à l'import → crash si `GROQ_API_KEY` est vide
- Pas de retry/backoff sur les appels Groq
- Pas de circuit breaker
- `temperature=0.1` par défaut — acceptable ?
- JSON mode activé via `response_format={"type": "json_object"}`

---

### 3. LangGraph Graph Definition

**Fichier** : `backend/app/agents/enrichment_graph.py`

```
search → scrape → extract → END
```

**⚠️ Points à valider** :
- Graph linéaire (pas de branches conditionnelles) — suffisant pour v1 ?
- Pas de retry node en cas d'échec d'un node
- `ainvoke()` synchrone dans le endpoint FastAPI — timeout possible sur requests longues
- Le graph est compilé au module-level (`enrichment_pipeline = build_enrichment_graph()`)
- Pas de checkpointing/persistence du state entre nodes

---

### 4. Web Scraper Node

**Fichier** : `backend/app/agents/nodes/scraper_node.py`

**Pattern** : `httpx.AsyncClient` + regex pour strip HTML.

**⚠️ Points à valider** :
- `User-Agent: CrooBot/1.0` — acceptable pour scraping commercial ?
- HTML stripping via regex (pas de BeautifulSoup) — fragile mais léger
- Truncation à 8000 chars — suffisant pour le contexte LLM ?
- Pas de respect robots.txt
- Pas de rate limiting sur les requêtes

---

### 5. LLM Structured Extraction

**Fichier** : `backend/app/agents/nodes/extraction_node.py`

**Pattern** : System prompt avec JSON schema → Groq JSON mode → `json.loads()`.

**⚠️ Points à valider** :
- Le system prompt hardcode le schema Organization — couplage fort
- Pas de validation Pydantic sur l'output LLM (juste `json.loads`)
- Contexte limité à 3 pages × 3000 chars = 9k chars — suffisant ?
- `temperature=0.0` pour extraction déterministe
- Pas de fallback si le LLM retourne un JSON invalide (juste error log)

---

### 6. Serper Maps Search

**Fichier** : `backend/app/presentation/routes/search_routes.py`

**Pattern** : `POST /api/v1/search/maps` → Serper Maps API → `PlaceResult[]`.

**⚠️ Points à valider** :
- Coût Serper : 3 credits par recherche Maps — budget à surveiller
- Pas de cache (même recherche = nouveau call API)
- Pas de limitation du nombre de recherches par utilisateur
- Le mapping `place.types[0] → industry` est simpliste

---

### 7. Intent-to-Field Mapping (Use Case)

**Fichier** : `backend/app/application/use_cases/enrich_organization.py`

**Pattern** : Itération sur `allowed_fields`, ne remplit que les champs vides, marque `ai_enriched=Y`.

**⚠️ Points à valider** :
- `allowed_fields` liste hardcodée — couplage avec l'entity Organization
- `org.updated_by = f"ai-agent ({user_email})"` — format de traçabilité acceptable ?
- Pas d'event/notification après enrichissement (pas d'event bus utilisé ici)
- `setattr(org, field, extracted[field])` sans coercion de type

---

### 8. Frontend Search → Select Dialog

**Fichiers** : `frontend/src/app/pages/organizations/organizations.{ts,html,css}`

**Pattern** : Dialog modal en 2 étapes — search bar → result cards → create + auto-enrich OR manual form.

**⚠️ Points à valider** :
- Pas de composant réutilisable (dialog inline dans le component)
- Pas de debounce sur la recherche (bouton explicit OK, mais enter aussi trigger)
- L'état du dialog est géré via booleans multiples — acceptable pour v1 ?

---

### 9. Address Parsing (Maps → DB fields)

**Fichier** : `frontend/src/app/pages/organizations/organizations.ts` — `selectPlace()`

```typescript
const addressParts = place.address.split(', ');
// [0] = street, [1] = city, [2] = "QC G7H 1S5", [3] = "Canada"
```

**⚠️ Points à valider** :
- Parsing naïf par `, ` split — fragile pour adresses avec virgules dans le street name
- Format Google Maps supposé constant — pas de garantie
- State/postal code séparés par espace — ne marchera pas pour tous les pays

---

### 10. Auto-Enrich after Create

**Pattern** : `create()` → `enrich()` en chaîne d'Observables dans le frontend.

**⚠️ Points à valider** :
- L'enrichissement est synchrone côté API (~15-30s) — UX bloquée
- Pas de background task / polling pattern
- Si l'enrichissement échoue, l'org est créée mais pas enrichie — acceptable ?
- Pas de retry côté frontend

---

## Recommandations pour template HDQ

Les patterns suivants devraient devenir des templates réutilisables :

| Priorité | Pattern | Template proposé |
|----------|---------|------------------|
| 🔴 Haute | LangGraph graph | `agent-graph-langgraph` |
| 🔴 Haute | LLM Client | `llm-client-groq` |
| 🟡 Moyenne | State Schema | `agent-state-typed-dict` |
| 🟡 Moyenne | LLM Extraction | `llm-structured-extraction` |
| 🟡 Moyenne | Serper Maps Search | `connector-serper-maps` |
| 🟢 Basse | Web Scraper | `node-web-scraper` |
| 🟢 Basse | Search Dialog | `component-search-select-dialog` |
