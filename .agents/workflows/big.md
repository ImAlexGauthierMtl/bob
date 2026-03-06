---
description: "Déclencher le Protocole Big Bang pour les décisions architecturales complexes"
---

# /big — Protocole Big Bang

Ce workflow s'utilise face à un choix architectural majeur ou une implémentation sans direction évidente.

## Étapes obligatoires

1. **Thèse (L'Ingénieur Pragmatique)** : Propose la solution la plus directe et rapide. Argumente fortement en sa faveur.

2. **Antithèse (L'Architecte Paranoïaque)** : Propose la solution opposée, la plus robuste et scalable. Argumente fortement contre la Thèse.

3. **Collision & Revue Architecturale** : Confronte les deux options à la lumière de :
   - `.agents/rules/architecture.md` — *"Cette approche respecte-t-elle l'architecture définie ?"*
   - `.agents/rules/backend-python.md` — *"La Clean Architecture est-elle préservée ?"*
   - `.agents/context/projet.md` — *"Est-ce cohérent avec le contexte du projet ?"*
   - *"Cette solution tiendra-t-elle avec 10x plus de charge/modules/données ?"*

4. **Synthèse Émergente** : Propose la "Troisième pensée" — une synthèse (ex: solution A pour le sprint 1, solution B pour le sprint 3).

5. **Formalisation ADR** : Rédiger une entrée dans `.agents/decisions/decisions.md` au format ADR :
   - Contexte, Decision, Rationale, Alternatives Considered, Consequences
