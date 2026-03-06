---
description: "Commiter avec lien vers ticket Zoho Desk"
---

# /zoho-commit — Commit lié à Zoho

// turbo-all

## Étapes

1. Vérifier l'état git :
```bash
git status --short
git diff --stat
```

2. Demander à l'utilisateur :
   - **Numéro de ticket Zoho** (ex: #12345)
   - **Type de commit** : feat, fix, docs, refactor, chore, test, perf, ci
   - **Service concerné** (prefix du commit)

3. Composer le message de commit :
```
[service] type: description courte

Ref: ZOHO-#XXXXX
```

4. Commiter :
```bash
git add -A
git commit -m "[service] type: description

Ref: ZOHO-#XXXXX"
```

5. Proposer de pousser :
```bash
git push origin $(git branch --show-current)
```
