# TODO — Bob's Control Center

## Architecture Backend à adapter

L'architecture actuelle utilise un modèle plat `bcc_roles` → `bcc_skills` / `bcc_tasks` / `bcc_milestones`.

La nouvelle vision est une hiérarchie multi-niveaux par organisation :

```
Organization (The Croo Group)
  └── Département (Sales)
        └── Équipe (Digital Experience)
              └── Rôle (Sales Rep)
                    ├── Skills
                    ├── Tasks
                    ├── Milestones
                    └── Réglementations
```

### Entités à créer / adapter

- [ ] `bcc_organizations` — entité top-level (remplace le concept de role actuel au niveau liste)
- [ ] `bcc_departments` — lié à une organization
- [ ] `bcc_teams` — lié à un département
- [ ] `bcc_roles` — lié à une équipe (conserve skills/tasks/milestones)
- [ ] `bcc_regulations` — lié à une organization ou département

### API Routes à créer

- [ ] CRUD Organizations
- [ ] CRUD Departments (nested sous org)
- [ ] CRUD Teams (nested sous dept)
- [ ] CRUD Roles (nested sous team, garde les skills/tasks existants)
- [ ] CRUD Regulations

### Frontend

- [ ] Remplacer les mock data par des appels API réels
- [ ] Navigation drill-down : Org → Dept → Team → Role
- [ ] Formulaires de création pour chaque niveau

### Questions à discuter

- [ ] Est-ce que les réglementations sont au niveau org, dept, ou les deux ?
- [ ] Est-ce qu'un rôle peut exister dans plusieurs équipes ?
- [ ] Héritage des skills/rules : est-ce qu'un dept hérite des règles de l'org ?
