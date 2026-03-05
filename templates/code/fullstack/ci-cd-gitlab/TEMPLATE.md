# Template: CI/CD GitLab

> Pipeline `.gitlab-ci.yml` avec stages lint/test/build/deploy.

## Fichier

`.gitlab-ci.yml`

```yaml
stages:
  - lint
  - test
  - build
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.pip-cache"
  NPM_CACHE_DIR: "$CI_PROJECT_DIR/.npm-cache"
  DOCKER_REGISTRY: "$CI_REGISTRY"

# ═══════════ LINT ═══════════
lint:backend:
  stage: lint
  image: python:3.11-slim
  script:
    - pip install ruff mypy
    - ruff check apis/
    - mypy apis/ --ignore-missing-imports
  cache:
    key: pip-cache
    paths: [.pip-cache]

lint:frontend:
  stage: lint
  image: node:20-alpine
  script:
    - cd frontend && npm ci --cache $NPM_CACHE_DIR
    - npx ng lint
  cache:
    key: npm-cache
    paths: [.npm-cache]

# ═══════════ TEST ═══════════
test:backend:
  stage: test
  image: python:3.11-slim
  services:
    - postgres:16-alpine
  variables:
    DATABASE_URL: "postgresql://test:test@postgres:5432/test"
    POSTGRES_USER: test
    POSTGRES_PASSWORD: test
    POSTGRES_DB: test
  script:
    - pip install -r apis/auth-api/requirements.txt
    - cd apis/auth-api && pytest --tb=short -q
  artifacts:
    reports:
      junit: apis/auth-api/test-results.xml

test:frontend:
  stage: test
  image: node:20-alpine
  script:
    - cd frontend && npm ci --cache $NPM_CACHE_DIR
    - npx ng test --watch=false --browsers=ChromeHeadless
  cache:
    key: npm-cache
    paths: [.npm-cache]

# ═══════════ BUILD ═══════════
.build_api: &build_api
  stage: build
  image: docker:24
  services: [docker:24-dind]
  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $CI_REGISTRY/$CI_PROJECT_PATH/$API_NAME:$CI_COMMIT_SHA apis/$API_NAME/
    - docker push $CI_REGISTRY/$CI_PROJECT_PATH/$API_NAME:$CI_COMMIT_SHA
  only: [main, develop]

build:auth-api:
  <<: *build_api
  variables:
    API_NAME: auth-api

build:frontend:
  stage: build
  image: docker:24
  services: [docker:24-dind]
  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $CI_REGISTRY/$CI_PROJECT_PATH/frontend:$CI_COMMIT_SHA frontend/
    - docker push $CI_REGISTRY/$CI_PROJECT_PATH/frontend:$CI_COMMIT_SHA
  only: [main, develop]

# ═══════════ DEPLOY ═══════════
deploy:staging:
  stage: deploy
  image: alpine/helm:3.14
  script:
    - helm upgrade --install $CI_PROJECT_NAME deploy/helm/ --set image.tag=$CI_COMMIT_SHA -n staging
  environment:
    name: staging
  only: [develop]

deploy:production:
  stage: deploy
  image: alpine/helm:3.14
  script:
    - helm upgrade --install $CI_PROJECT_NAME deploy/helm/ --set image.tag=$CI_COMMIT_SHA -n production
  environment:
    name: production
  only: [main]
  when: manual
```
