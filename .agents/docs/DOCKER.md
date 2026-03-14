# Lancer le projet en Docker (local)

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) et Docker Compose
- Aucune installation de Node, Python ou PostgreSQL nécessaire sur la machine

## Démarrer toute la stack

À la racine du projet :

```bash
docker compose up -d
```

Services exposés :

| Service    | URL                    | Description        |
|-----------|------------------------|--------------------|
| Frontend  | http://localhost:4200  | App Angular (nginx)|
| API       | http://localhost:8555  | Backend FastAPI    |
| PostgreSQL| localhost:5432         | Base `croo_digital_experience` |

Comptes par défaut (seed) : **admin@croo.digital** / **Admin123!**

## Démarrer uniquement backend + base

Sans le frontend en conteneur (par exemple si vous lancez le frontend en local avec `ng serve`) :

```bash
docker compose up -d db api
```

Puis dans `frontend/` : `npm install && npm start`. L’app sur http://localhost:4200 appellera l’API sur http://localhost:8555.

## Commandes utiles

```bash
# Voir les logs
docker compose logs -f

# Reconstruire après modification du code
docker compose up -d --build

# Arrêter et supprimer les conteneurs
docker compose down

# Supprimer aussi les volumes (données PostgreSQL)
docker compose down -v
```

## Variables d’environnement

Les valeurs par défaut sont dans `docker-compose.yml`. Pour les surcharger, créez un fichier `.env` à la racine (voir `backend/.env.example` pour les clés optionnelles : Groq, Serper, etc.).

## Dépannage

- **Frontend build en Docker** : le build Angular produit dans `dist/frontend/browser`. Si votre version d’Angular utilise un autre chemin, adaptez la ligne `COPY` dans `frontend/Dockerfile`.
- **API ne démarre pas** : vérifier que PostgreSQL est bien healthy : `docker compose ps` puis `docker compose logs db`.
- **CORS** : les origines autorisées incluent `http://localhost:4200` et `http://localhost`. Pour un autre domaine, modifier `CORS_ORIGINS` dans `docker-compose.yml`.

### Rendu UI différent entre machines (éléments manquants)

Si la page d'accueil (login) ou le dashboard n'affiche pas le même visuel sur un autre poste :

1. **Largeur d'écran** : le panneau hero (gauche) de la page login s'affiche à partir de **768px** de largeur. En dessous, seul le formulaire est visible. Vérifier que la fenêtre du navigateur est assez large ou zoom à 100 %.

2. **Ressources CDN** : l'UI charge des polices et icônes depuis internet (Font Awesome, Google Fonts, Plotly). Si le réseau bloque ces domaines (proxy, firewall, VPN), les icônes et graphiques peuvent manquer. F12 → Network pour voir les requêtes en erreur.

3. **Logo** : `croo-logo.png` et `favicon.ico` sont dans `frontend/public/`. Si le logo ne s'affiche pas, reconstruire : `docker compose up -d --build frontend`.
