# KB Article Writing Norms

> Reference document for all Knowledge Base article content.
> Every article MUST follow these rules without exception.

---

## 1 — Language & Branding

| Rule | Do | Don't |
|------|----|-------|
| AI identity | "Bob", "your AI assistant" | Groq, Claude, GPT, LangGraph, Serper |
| Technology | "AI enrichment", "smart search" | Name specific LLMs, APIs, frameworks |
| Product name | "Croo Digital Experience", "Bob" | Internal codenames |
| Tone | Professional, concise, action-oriented | Casual, verbose, developer-focused |
| Language | English (US) | French, mixed |

**Rule #1 — Bob IS the AI.** Every reference to AI capabilities uses "Bob" as the actor. Never expose underlying technology names (Groq, Serper, LangGraph, OpenAI, etc.) to the end user.

---

## 2 — Example Companies

When examples are needed (search queries, demo data, screenshots), use companies from these industries ONLY:

| Industry | Example companies |
|----------|------------------|
| Hospitality | Le Baluchon Éco Resort, Auberge du Lac, Hôtel & Spa Mont-Gabriel |
| Restaurants | Rôtisserie St-Hubert, Restaurant Le Continental, Brasserie Artisanale |
| Tourism | Tourisme Mauricie, Croisières AML, Aventure Écotourisme Québec |
| Mining | Mine Canadian Malartic, ArcelorMittal Mines, Nemaska Lithium |
| Manufacturing | Bombardier, Cascades, BRP (Produits Récréatifs) |
| Producers | Fromagerie Boivin, Ferme Tournevent, Domaine Pinnacle |

> **NEVER** use technology companies (Shopify, Google, Apple, Microsoft, Meta, etc.) as examples.

---

## 3 — Article Structure

Every article follows this structure:

```
# [Feature Name]

[1-2 sentence summary of what the feature does and why it matters]

## Overview
[Context paragraph — what this module is, how it fits in the CRM]

## Step 1 — [Action verb] [Object]
[Instruction paragraph]
![Screenshot alt text](/assets/kb/screenshots/feature-stepN.png)
- [Detail list items]

## Step 2 — [Next action]
...

## What Happens After [Action]
[Describe what Bob does automatically]

## [Feature] Fields
[Complete field reference list]

## Tips
[3-5 practical tips as bullet points]
```

---

## 4 — Screenshots

| Rule | Details |
|------|---------|
| Format | PNG, full-page or dialog-focused |
| Resolution | 1440×900 viewport |
| Annotations | **None** — clean screenshots only |
| Location | `frontend/src/assets/kb/screenshots/` |
| Naming | `feature-stepN-description.png` |
| Alt text | Descriptive, context-rich alt text |

**No annotations.** Each step gets its own screenshot showing the exact UI state. The step text provides the context — the screenshot is visual proof.

---

## 5 — Content Rules

1. **No jargon** — Write for a CRM user, not a developer
2. **No internal references** — No mentions of API endpoints, database fields, or code
3. **Action-first** — Each step starts with a verb: "Navigate", "Click", "Type", "Select"
4. **Field lists use** `**Bold** —` format: `**Name** — Company legal or trade name`
5. **Callouts** use `>` blockquotes for tips or important notes
6. **Status values** in `**CAPS**` format: `**PROSPECT**`, `**CUSTOMER**`

---

## 6 — Visibility & Audience

| Visibility | Who sees it | Content type |
|------------|-------------|--------------|
| `shared` | Internal team + clients | Feature guides, how-tos |
| `internal` | Internal team only | Admin settings, advanced config |
| `public` | Everyone | General product info |

Default visibility for feature articles: **`shared`**

---

## 7 — Article Metadata

| Field | Convention |
|-------|-----------|
| `author_name` | "Bob AI" |
| `author_role` | "AI Knowledge Assistant" |
| `tags` | Module name + key concepts (max 5) |
| `category` | Map to existing module category |
| `reading_time` | Auto-calculated or "5 min read" |
