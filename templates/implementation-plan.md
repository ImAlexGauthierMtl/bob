# [Nom du Module] — Plan d'implémentation

> Généré via `/nouveau-module` ou `/start`.
> Ce plan doit être approuvé avant de déclencher `/implante`.

## 1. Contexte & logique métier

[Brièvement : que fait le module et ses règles métier principales]

## 2. Database & modèle de domaine

```python
# SQLAlchemy model
class [ResourceName](Base):
    __tablename__ = "[table_name]"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    # ... champs
    tenant_id = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

## 3. Backend (Clean Architecture)

### 3.1 Schemas (Input/Output)
| Fichier | Contenu |
|---------|---------|
| `schemas/[resource].py` | `[Resource]Create`, `[Resource]Update`, `[Resource]Response` |

### 3.2 Repository
| Fichier | Contenu |
|---------|---------|
| `repositories/[resource]_repository.py` | CRUD async, filtres, pagination |

### 3.3 Service (Domain Logic)
| Fichier | Contenu |
|---------|---------|
| `services/[resource]_service.py` | Logique métier, validations |

### 3.4 Use Cases
| Fichier | Contenu |
|---------|---------|
| `use_cases/[resource]_use_cases.py` | Create, Get, List, Update, Delete |

### 3.5 Routes
| Fichier | Contenu |
|---------|---------|
| `routes/v1/[resource]s.py` | GET /, GET /{id}, POST /, PUT /{id}, DELETE /{id} |

## 4. Frontend

### 4.1 Models (TypeScript)
| Fichier | Contenu |
|---------|---------|
| `models/[resource].model.ts` | Interface, enums, types Create/Update |

### 4.2 Service HTTP
| Fichier | Contenu |
|---------|---------|
| `services/[resource].service.ts` | HttpClient + mock data support |

### 4.3 NGRX Store
| Fichier | Contenu |
|---------|---------|
| `store/[resource]s/[resource]s.actions.ts` | Load, Create, Update, Delete + Success/Failure |
| `store/[resource]s/[resource]s.reducer.ts` | État initial, transitions |
| `store/[resource]s/[resource]s.effects.ts` | Side effects HTTP |
| `store/[resource]s/[resource]s.selectors.ts` | Selectors memoïsés |

### 4.4 Composants UI
| Fichier | Contenu |
|---------|---------|
| `pages/[resource]-list.page.ts` | Liste avec filtres, pagination |
| `pages/[resource]-detail.page.ts` | Détail avec onglets |
| `pages/[resource]-form.page.ts` | Formulaire create/edit |

## 5. Tests

### 5.1 Backend
- **Positifs** : [Lister les cas]
- **Négatifs (30%)** : [Lister les cas]

### 5.2 Frontend
- [Lister les cas]

## 6. Checklist HDQ

- [ ] No N+1 queries (selectinload)
- [ ] Typed return values pour Use Cases (pas de dict)
- [ ] Strict types everywhere (no `any` en TypeScript)
- [ ] 30% negative test coverage
- [ ] CamelCase pour API responses (Pydantic CamelModel)
- [ ] tenant_id isolation respectée
- [ ] Pas de secrets dans le code
