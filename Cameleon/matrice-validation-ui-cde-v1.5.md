# Matrice de validation UI CDE v1.5

| ID | Règle | Méthode | Preuve attendue | Statut |
| --- | --- | --- | --- | --- |
| UI-01 | Login et application utilisent les mêmes tokens | Inspecter `styles.css`, `login.css`, `layout.css` | Couleurs, rayons et champs basés sur variables globales | Validé |
| UI-02 | Le menu `Conversation` existe | Ouvrir `/dashboard`, vérifier sidebar | Entrée `Conversation` active vers `/conversation` | Validé |
| UI-03 | Ancien accès `/chat` reste compatible | Ouvrir `/chat` | Redirection vers `/conversation` | Validé |
| UI-04 | Cartes et panneaux principaux ont rayon <= 8px | Inspecter CSS et captures | `--radius-md` ou moins sur cartes | Validé |
| UI-05 | Titres sans tracking négatif | Recherche CSS | Aucun `letter-spacing` négatif restant | Validé |
| UI-06 | Gradients décoratifs retirés du login, layout, settings et conversation | Inspecter CSS ciblés | Aucune surface principale en gradient | Validé |
| UI-07 | Composants réutilisables documentés | Lire cahier de normes | Table des composants présente | Validé |
| UI-08 | Dashboard lisible dans le nouveau shell | Capture navigateur | Pas de chevauchement, cartes cohérentes | Validé |
| UI-09 | Conversation respecte la référence sans la copier | Capture navigateur | Sidebar neutre, colonne centrée, composer compact | Validé |
| UI-10 | Settings ne porte plus un thème séparé | Capture navigateur | Panneau latéral neutre, carte Bob normalisée | Validé |
| UI-11 | Build Angular valide | Lancer build frontend | Compilation réussie | Validé avec avertissements existants |
| UI-12 | Captures conservées hors Git | Vérifier `captures/` | PNG présents, non suivis | Validé |

## Parcours de test local

1. `http://localhost:4700/login`
2. Connexion avec un compte local valide.
3. `http://localhost:4700/dashboard`
4. `http://localhost:4700/conversation`
5. `http://localhost:4700/settings`
6. `http://localhost:4700/contacts`

## Critères d'acceptation

- Aucune page clé ne revient au thème noir/orange pleine surface.
- Les états actifs sont sobres et identifiables.
- La navigation et le login donnent l'impression d'un même produit.
- Les nouvelles règles sont assez concrètes pour guider les prochaines pages sans nouvelle décision graphique.
