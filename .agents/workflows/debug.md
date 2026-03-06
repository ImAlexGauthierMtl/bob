---
description: "Protocole de debug structuré — 10 hypothèses, validation 95%, post-mortem"
---

# /debug — Protocole de Debug Structuré

> Mode recherche systématique. Pas de guess-and-fix.

---

## Étape 1 — Reproduire le bug

1. Identifier le symptôme exact (screenshot, erreur, comportement)
2. Identifier l'état attendu vs l'état actuel
3. Documenter l'environnement (ports, processus, versions)

---

## Étape 2 — Émettre 10 hypothèses

Lister 10 causes possibles, ordonnées par probabilité décroissante.
Pour chaque hypothèse :
- **H#** : Description courte
- **Test** : Comment la valider/invalider
- **Probabilité estimée** : %

---

## Étape 3 — Tester les hypothèses

Pour chaque hypothèse, dans l'ordre de probabilité :
1. Exécuter le test décrit
2. Documenter le résultat : ✅ confirmé / ❌ éliminé
3. Si confirmé avec **≥ 95% de confiance** → passer à l'Étape 4
4. Si aucune hypothèse ≥ 95% → émettre 10 nouvelles hypothèses
5. Rechercher sur le web pour de nouvelles pistes entre chaque batch

---

## Étape 4 — Appliquer le fix

1. Corriger le bug
2. Vérifier que le fix compile / build
3. Demander à l'utilisateur de valider visuellement

---

## Étape 5 — Post-mortem

Si l'utilisateur confirme que c'est fixé :

1. **Cause racine** : Description technique
2. **Pourquoi le bug est arrivé** : Quel gap dans les règles/normes/templates
3. **Actions préventives** : Règles, normes, workflows, templates à créer/modifier
4. **Destinataire** : Senior architecte
5. **Dette technique** : Vérifier que le debug n'a pas introduit de code mort, de violations de normes, de hacks temporaires

---

## Étape 6 — Validation dette technique

Avant de clôturer :
- [ ] Pas de code mort ajouté
- [ ] Pas de `console.log` / `print()` oubliés
- [ ] Les normes du projet sont respectées (BEM, design tokens, pas de Tailwind inline)
- [ ] Les templates existants sont suivis
- [ ] Pas de workarounds non-documentés
