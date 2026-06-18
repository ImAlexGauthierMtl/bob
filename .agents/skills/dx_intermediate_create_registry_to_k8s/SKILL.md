---
name: dx_intermediate_create_registry_to_k8s
description: Crée le câblage Harbor → K8s — instructions pour créer le projet Harbor et le robot account (étapes manuelles UI), bootstrap des variables HARBOR_*, vérification du job provision-registry-access et du serviceAccountName dans les values. La logique vit dans le repo CI/CD central — la skill produit les éléments projet et la table des variables.
metadata:
  reference: § 7.4
---

# dx_intermediate_create_registry_to_k8s

## Étapes manuelles (Harbor UI) — à documenter pour l'humain

1. Créer le **projet Harbor** (1:1 avec le projet GitLab)
2. Configurer : auto-scan on push, severity gate HIGH/CRITICAL, auto-sign Cosign, retention purge non-signées > 30j
3. Créer le **robot account** `robot$<projet>+ci` :
   permissions push + pull + scan:read + scan:create + artifact:read

## Bootstrap variables (CLI)

```bash
glab variable set HARBOR_URL         --value "harbor.tools.thesmartcrew.com"
glab variable set HARBOR_PROJECT     --value "<projet>"
glab variable set HARBOR_ROBOT_USER  --value 'robot$<projet>+ci' --protected
glab variable set HARBOR_ROBOT_TOKEN --value "<token>" --protected --masked
```

## Côté projet

- Vérifier que les values Helm ne hardcodent pas le registry : l'image est
  passée par le pipeline (`${HARBOR_URL}/${HARBOR_PROJECT}/<api>:<sha>`)
- Lancer `provision-registry-access:<env>` (manuel, idempotent) sur chaque env
- Vérifier `serviceAccountName: harbor-registry-deployer` dans le rendu

## Anti-patterns

1. Stocker `HARBOR_ROBOT_TOKEN` sans `--protected --masked`
2. Réutiliser un robot account entre projets (1 robot par projet)
3. Pull par `$CI_JOB_TOKEN` au runtime (ImagePullBackOff après scale)
4. Recréer des variables `DEPLOY_TOKEN_*` (n'existent plus)
5. Oublier la rotation 90j du robot token
