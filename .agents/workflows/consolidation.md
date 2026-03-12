---
description: "Automatiser la phase de clôture pour s'assurer qu'elle n'est plus sautée"
---

# /consolidation — Phase de Clôture Automatisée

Ce workflow garantit que l'élan de livraison ne sacrifie pas la stabilisation structurée.

## Étapes obligatoires

1. **Lecture des diffs récents** : Vérifier l'état actuel
```bash
git status
git diff --stat HEAD~1
```

2. **Mise à jour du Walkthrough** : Documenter les preuves et l'explication finale dans `walkthrough.md`

3. **Capture de la dette technique** :
   - Y a-t-il eu des compromis ? (mock laissé en place, type hint manquant, coverage < 100%)
   - Si oui : ajouter une entrée dans `.agents/docs/dette-technique.md`

4. **Vérification de conformité** :
   - L'architecture définie dans `context/projet.md` est-elle respectée ?
   - Les mocks de services externes sont-ils bien marqués ?
   - Les migrations sont-elles commitées ?
   - **Si frontend touché** : Playwright exécuté ? Screenshots dans le walkthrough ? (voir `rules/regle-playwright.md`)

5. **Vérification des gaps** :
   - Relire `.agents/docs/gaps.md`
   - Des gaps ont-ils été comblés durant cette implémentation ? → Marquer `[x]`
   - De nouveaux gaps ont-ils été découverts ? → Les ajouter

6. **Commit de clôture** : Format sémantique avec préfixe service
```bash
git add -A && git commit -m "[service] type: description"
git push origin $(git branch --show-current)
```
