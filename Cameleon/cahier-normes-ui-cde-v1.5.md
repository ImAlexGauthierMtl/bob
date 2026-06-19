# Cahier de normes UI CDE v1.5

## Intention

Le thème CDE doit être uniforme de la connexion aux modules internes. Le style est inspiré des tableaux de bord de travail modernes: navigation calme, surfaces neutres, faible bruit visuel, composants compacts et états clairs.

## Sources de décision

- Slack, Samuel Sirois: choisir un theming compatible avec la stack frontend existante et juger les options selon maintenance active, popularité de la communauté et robustesse.
- Référence visuelle fournie: sidebar neutre, contenu centré, contrôles discrets, hiérarchie typographique sobre.
- Stack CDE actuelle: Angular 21, CSS de composants, tokens globaux dans `frontend/src/styles.css`.

## Tokens

| Élément | Standard |
| --- | --- |
| Fond applicatif | `--color-shell` pour la navigation et `--color-surface` pour le contenu |
| Surface principale | `--color-surface-raised` avec `--color-border` |
| Accent | `--color-accent` noir chaud, réservé aux actions primaires et états actifs |
| Rayon carte | `--radius-md`, maximum 8px |
| Ombre | `--shadow-sm` par défaut, `--shadow-md` pour menus flottants |
| Typographie | `--font-family`, graisse 400 à 600, aucun letter-spacing négatif |

## Composants réutilisables

| Composant | Classes actuelles | Règles |
| --- | --- | --- |
| Bouton primaire | `.btn.btn-accent` | Accent plein, hauteur stable, icône si utile |
| Bouton secondaire | `.btn.btn-outline` | Surface blanche, bordure neutre |
| Champ | `.input`, `input`, `select`, `textarea` | Rayon 8px, focus gris/noir doux |
| Carte | `.metric-card`, `.chart-card`, `.table-card`, `.settings-card`, `.content-card` | Surface blanche, bordure neutre, pas de gradient |
| Tableau | `.data-table` | En-tête sur fond neutre, hover gris léger |
| Badge | `.status-badge`, `.counter-badge`, `.result-tag` | Rayon 6px, texte sans tracking forcé |
| Navigation | `.sidebar__link`, `.settings-nav__link` | Icône + libellé, actif gris avec icône accent |
| Conversation | `.chat-page`, `.chat-message__bubble`, `.chat-input-wrap` | Colonne centrée, bulles sobres, composer fixe |

## Règles d'application

1. Une page doit utiliser les tokens globaux au lieu de valeurs hex locales, sauf pour un état métier précis.
2. Les cartes et panneaux ne doivent pas dépasser 8px de rayon.
3. Les gradients décoratifs sont retirés des surfaces principales.
4. Les titres de pages restent compacts et sans letter-spacing négatif.
5. La navigation principale contient les modules réels, dont `Conversation`.
6. La page login doit partager le même vocabulaire visuel que l'application connectée.
7. Les nouveaux écrans doivent réutiliser les classes globales avant de créer une variante locale.
8. Les captures de validation UI vont dans `captures/`, non suivies par Git.
9. Les boutons primaires sont noirs; le bleu n'est pas une couleur de thème CDE.

## À éviter

- Créer une page au style isolé du shell.
- Ajouter des cartes dans des cartes pour structurer une section.
- Utiliser un gradient comme identité principale d'un module.
- Réintroduire un écran login de type landing marketing.
- Multiplier les accents colorés hors statuts métier.
