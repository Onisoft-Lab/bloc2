# Matrice des rôles et des droits

Deux rôles : `exploitant` et `direction`. Le jeton est un JWT HS256. Le corps contient `sub` (identifiant), `role` et `exp`. L'expiration est `JWT_EXPIRATION_MINUTES` (60 par défaut). Un jeton absent, invalide ou expiré répond 401 avec `{"detail": "Jeton absent, invalide ou expire"}`.

| Route | Anonyme | exploitant | direction | Refus |
|---|---|---|---|---|
| GET /sante | 200 | 200 | 200 | - |
| POST /auth/login | 200 si les identifiants sont bons, sinon 401 | identique | identique | 401 `Identifiants invalides` |
| GET /stations | 401 | 200 | 200 | 401 |
| GET /stations/{id} | 401 | 200 ou 404 | 200 ou 404 | 401, ou 404 `Station introuvable` |
| GET /trajets | 401 | 200 | 200 | 401 |
| GET /incidents | 401 | 200 | 200 | 401 |
| PUT /incidents/{id}/statut | 401 | 200, 404 ou 422 | 403 | 403 `Acces reserve au role exploitant` |
| GET /indicateurs/activite-par-jour | 401 | 200 | 200 | 401 |
| GET /indicateurs/stations-actives | 401 | 200 | 200 | 401 |
| GET /indicateurs/incidents-par-statut | 401 | 200 | 200 | 401 |

`page` hors de 1 et plus, ou `taille_page` hors de 1 à 100, répondent 422 avant le contrôle de rôle dès que le jeton est valide. Une transition de statut interdite répond 422 `Transition de statut non autorisee`. Un incident inconnu répond 404 `Incident introuvable`.

Transitions autorisées : `ouvert` vers `en_cours`, `ouvert` vers `resolu`, `en_cours` vers `resolu`. Le passage à `resolu` renseigne `date_resolution` si elle est vide.

Le front affiche le formulaire de changement de statut au seul rôle `exploitant`. Le rôle `direction` voit le texte « La modification des incidents est réservée aux exploitants. » et n'envoie pas de PUT.

## Données sensibles

| Donnée | Où elle vit | Ce qui est évité |
|---|---|---|
| Mot de passe | Empreinte bcrypt en base. Clair uniquement dans `.env` (non versionné) pour les tests, et dans la documentation des comptes de démonstration | Pas de mot de passe en clair en base, pas de secret JWT dans Git |
| JWT_SECRET | `.env` seulement | `.env.example` laisse la valeur vide |
| Jeton | Mémoire de session Streamlit, en-tête `Authorization` | Jamais affiché à l'écran |
| usager_ref | Colonne `trajet`, renvoyée par GET /trajets | Absente de tous les écrans. Le rôle direction la reçoit encore dans le JSON : limite connue, pas un masquage côté API |
