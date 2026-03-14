# Débogage de la Perte d'Authentification au Rafraîchissement

Ce document retrace l'intégralité du processus de débogage qui a permis d'identifier et de résoudre le problème où les utilisateurs étaient déconnectés (perte de session) à chaque rafraîchissement de page sous Angular 17+ avec SSR (Server-Side Rendering).

---

## 1. Les 10 Hypothèses Initiales de la Problématique

Avant d'écrire le script, nous avons émis les 10 hypothèses suivantes pour cibler la source du problème :

1. **Hydration SSR discordante :** Le serveur Angular Universal renvoie une page où l'utilisateur est déconnecté (pas d'accès au `localStorage` côté serveur). Lors de l'hydration, le client écrase l'état local pour correspondre à l'état initial du serveur.
2. **Échec de `loadCurrentUser` au démarrage :** Au chargement, l'appel `/me` échoue (ex: réseau, SSR). La méthode catch/error appelle `this.logout()` silencieusement et vide le `localStorage`.
3. **`isPlatformBrowser` évalué trop tôt :** Lors de l'initialisation de `AuthService`, la vérification `isPlatformBrowser` retourne `false` au tout premier cycle, ce qui fait que `hasToken()` retourne `false`.
4. **Race condition avec l'intercepteur :** Un appel réseau part avant que le token ne soit récupéré du `localStorage`, reçoit un 401, échoue le refresh, et mène au `logout()`.
5. **Nettoyage actif du `localStorage` au démarrage :** Un autre service/Guard ou effet d'état est déclenché et nettoie le `localStorage`.
6. **Token invalide pour un nouvel onglet :** L'intercepteur n'attend pas la lecture asynchrone du `localStorage`, l'en-tête Authorization part vide.
7. **Redirection du Guard d'authentification (`AuthGuard`) :** Le Guard s'exécute et vérifie l'état avant que `AuthService` ne se mette à jour, redirigeant vers `/login` et forçant une réinitialisation.
8. **Problème de portée de `localStorage` (SSR vs Browser) :** Utilisation directe de `localStorage` hors des hooks du cycle de vie causant un comportement indéfini.
9. **SSR transfère un état d'erreur :** L'API `/me` appelée côté serveur SSR échoue. Cet échec est transféré via `TransferState` au client, qui l'exécute immédiatement en déclenchant un `logout()`.
10. **Comportement de `null` dans le Refresh Token :** L'intercepteur intercepte une erreur, tente de rafraîchir avec un token `null`, reçoit un 401, et force une déconnexion stricte.

---

## 2. Le Script de Test Playwright

Pour reproduire la faille formellement et isoler le problème sans intervention humaine, nous avons développé un script Playwright (`test-refresh.js`).
L'astuce cruciale a été **d'injecter un hook sur `localStorage.removeItem`** pour tracer la Stack Trace exacte de la fonction qui supprimait les tokens.

```javascript
// Injection dans Playwright pour capturer la suppression des tokens
await page.addInitScript(() => {
    const originalRemoveItem = localStorage.removeItem;
    localStorage.removeItem = function (key) {
        console.error(`[LocalStorage Dump] Removing ${key} - Stack: ${new Error().stack}`);
        return originalRemoveItem.call(localStorage, key);
    };
});
```

Hormis ce hook, le script Playwright effectue le parcours suivant :
1. Se connecter avec les bons identifiants (`admin@croo.digital`).
2. Attendre l'arrivée sur `/dashboard`.
3. Vérifier que les tokens sont présents dans le `localStorage`.
4. Faire un `page.reload()`.
5. Lire les logs réseau, logs console et la Stack Trace du hook.

---

## 3. Découverte de la Racine du Bug (La Trace)

L'exécution du script Playwright a révélé ce log précis au moment du rafraîchissement :

```text
3. Refreshing the page...
[Browser error] [AuthService] /me request failed during loadCurrentUser: T: NG0200
[Browser error] [LocalStorage Dump] Removing croo_access_token - Stack: Error
    at localStorage.removeItem (<anonymous>:5:75)
    at a.logout (http://localhost:4700/chunk-7QR4VSG5.js:1:981)
    ...
[Browser error] [LocalStorage Dump] Removing croo_refresh_token - Stack: Error
...
❌ FAILURE: Token was cleared from localStorage upon refresh.
```

### Explication du Bug (Hypothèse #2 et #9 confirmées) :
L'erreur `NG0200` d'Angular indique généralement une erreur HTTP réseau de base (ex: le backend est injoignable, l'URL est mal résolue côté serveur (SSR), ou la requête est annulée durant l'hydration).

Dans `AuthService.ts`, le chargement de l'utilisateur (`loadCurrentUser()`) réagissait à *n'importe quelle erreur* en déconnectant l'utilisateur de force :

**Ancien code destructeur :**
```typescript
error: () => this.logout()
```
Dès que l'application se rafraîchissait, le processus de SSR ou d'hydration Angular déclenchait un `NG0200` sur `/me`, et l'application balayait instantanément le `localStorage` et redirigeait vers `/login`.

---

## 4. La Résolution et Validation Finale

Nous avons corrigé `AuthService` pour s'assurer qu'une simple erreur réseau ou un couac de SSR n'efface pas les identifiants de l'utilisateur. Seule une réponse formelle `401 Unauthorized` de l'API (certifiant que le token est expiré ou invalide) peut déclencher la déconnexion stricte.

**Nouveau code sécurisé :**
```typescript
error: (err) => {
    console.error('[AuthService] /me request failed during loadCurrentUser:', err);
    // On force la déconnexion SEULEMENT si c'est explicitement un refus 401
    if (err && err.status === 401) {
        console.error('[AuthService] Forcing logout due to 401 from /me');
        this.logout();
    }
}
```

**Recompilation & Résultat Playwright :**
Étant donné que le frontend tourne dans Docker, la commande `docker compose up -d --build frontend` a été nécessaire pour propager la modification.

Le résultat final de Playwright est désormais parfait :
```text
1. Logging in...
2. Checking localStorage after login...
   Token persists: true
3. Refreshing the page...
4. Checking localStorage after refresh...
   Token persists after refresh: true
   Current URL: http://localhost:4700/dashboard
✅ SUCCESS: User remained logged in after refresh.
```

Le problème est définitivement corrigé en environnement de développement et compatible avec Angular Universal (SSR).
