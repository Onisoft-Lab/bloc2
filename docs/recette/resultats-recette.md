# Résultats de recette - VéloVille V1

Campagne du 13/10/2026 sur l'arbre de travail (contenu prévu pour le tag `v1.0.0`). Python 3.12.11, PostgreSQL 16 (image `postgres:16-alpine`), API sur le port 8000, front Streamlit 1.65 sur le port 8501. Base chargée par `sql/schema.sql`, `sql/comptes.sql` et `scripts/importer.py`.

Les jetons ne sont pas recopiés. `exploitant01` a reçu un jeton de 160 caractères, `direction01` un jeton de 157 caractères, `token_type` = `bearer`.

## REC-01 - Import idempotent

Deux exécutions consécutives de `uv run python scripts/importer.py`.

Sortie identique les deux fois :

```
stations.csv : 120 lues, 120 retenues, 0 rejetées, 0 doublons
trajets.csv : 2030 lues, 2002 retenues, 16 rejetées, 12 doublons
incidents.csv : 180 lues, 177 retenues, 3 rejetées, 0 doublons
Base : station=120 trajet=2002 incident=177
```

Après la seconde exécution :

```
 stations | trajets | incidents
----------+---------+-----------
      120 |    2002 |       177
```

Statut : **OK**

## REC-02 - Rejets journalisés et cohérence des volumes

Journal `docs/journal-import.csv`, 190 lignes de données, colonnes `fichier`, `identifiant`, `colonne`, `valeur`, `motif`, `decision`.

| Fichier | Lignes CSV | Retenues (base) | Rejets | Doublons | Égalité |
|---|---:|---:|---:|---:|---|
| stations.csv | 120 | 120 | 0 | 0 | 120 |
| trajets.csv | 2 030 | 2 002 | 16 | 12 | 2 030 |
| incidents.csv | 180 | 177 | 3 | 0 | 180 |

Les normalisations (10 trajets, 124 incidents) et les 25 avertissements sont des lignes de journal supplémentaires. Elles ne comptent pas dans l'équation.

Requête d'arrivée orpheline : `count` = 0.

Statut : **OK**

## REC-03 - Connexion acceptée

`POST /auth/login`

- `exploitant01` : 200, `role` = `exploitant`, `token_type` = `bearer`, jeton non vide.
- `direction01` : 200, `role` = `direction`, `token_type` = `bearer`, jeton non vide.

Statut : **OK**

## REC-04 - Connexion refusée

- `exploitant01` / mot de passe `mauvais` : 401 `{"detail":"Identifiants invalides"}`
- `inconnu` / mot de passe du compte de démonstration : 401 `{"detail":"Identifiants invalides"}`

Message identique dans les deux cas.

Statut : **OK**

## REC-05 - Route protégée sans jeton

- `GET /stations` sans en-tête : 401 `{"detail":"Jeton absent, invalide ou expire"}`
- `GET /stations` avec `Authorization: Bearer jeton.invalide.xyz` : 401, même message. Un jeton modifié d'un caractère donne le même 401.
- `GET /sante` sans en-tête : 200 `{"statut":"ok"}`

Statut : **OK**

## REC-06 - Rôle direction refusé sur la modification d'un incident

Incident `I2026-0002`, statut de départ `ouvert`.

1. `PUT /incidents/I2026-0002/statut` `{"statut":"en_cours"}` avec le jeton direction : 403 `{"detail":"Acces reserve au role exploitant"}`.
2. Statut en base : toujours `ouvert`.
3. Même appel avec le jeton exploitant : 200, corps avec `"statut":"en_cours"` et `"date_resolution":null`.
4. Statut en base : `en_cours`.
5. Second appel identique : 422 `{"detail":"Transition de statut non autorisee"}`.

La ligne a été remise à `ouvert` et `date_resolution` nulle après le cas, pour laisser la base dans l'état de l'import. Contrôle : `statut = ouvert`, `resolution_vide = t`.

Statut : **OK**

## REC-07 - Pagination

Jeton direction.

1. `GET /stations?taille_page=50&page=1` : 200, `total` = 120, `page` = 1, `taille_page` = 50, 50 résultats, premier `station_id` = `S001`.
2. `GET /stations?taille_page=50&page=3` : 200, `total` = 120, 20 résultats.
3. `GET /stations?commune=Lille&taille_page=100` : 200, `total` = 46, 46 résultats, seule commune `Lille`, premier nom `Lille - Gare`.
4. `GET /stations?page=0` : 422, `loc` = `query.page`, `greater_than_equal` 1.
5. `GET /stations?taille_page=101` : 422, `loc` = `query.taille_page`, `less_than_equal` 100.

Statut : **OK**

## REC-08 - Station introuvable

- `GET /stations/S001` : 200, `station_id` = `S001`, `nom` = `Lille - Gare`.
- `GET /stations/S999` : 404 `{"detail":"Station introuvable"}`.

Statut : **OK**

## REC-09 - Cohérence de l'indicateur « activité par jour »

`GET /indicateurs/activite-par-jour?date_debut=2026-08-24&date_fin=2026-08-30` : 200.

| Jour | nb_trajets API | nb_trajets SQL |
|---|---:|---:|
| 2026-08-24 | 329 | 329 |
| 2026-08-25 | 311 | 311 |
| 2026-08-26 | 306 | 306 |
| 2026-08-27 | 300 | 300 |
| 2026-08-28 | 315 | 315 |
| 2026-08-29 | 219 | 219 |
| 2026-08-30 | 222 | 222 |

Somme : 2 002. `GET /trajets?date_debut=2026-08-24&date_fin=2026-08-30` : `total` = 2 002.

Indicateurs relevés en complément, hors critère de ce cas : `incidents-par-statut` donne `en_cours` 46, `ouvert` 55, `resolu` 76, délai 129,4 h. `stations-actives?limite=10` place `S094` Marcq-en-Baroeul - Grand Place en tête (22 départs, 27 arrivées).

Statut : **OK**

## REC-10 - Front : état vide et état d'erreur

Compte `direction01` dans le navigateur.

1. Écran Stations, page 7 (dernière page réelle : 6) : « Aucun résultat pour ces critères. », « Page 7 sur 6 », bouton suivant désactivé. Pas d'erreur.
2. API arrêtée, écran Stations rechargé : « L'API est injoignable. Vérifiez qu'elle est démarrée. » Aucune trace Python.
3. Écran Indicateurs dans le même état : le même message, le formulaire de période reste affiché, aucune trace.
4. API redémarrée, écran Stations rechargé : « 120 stations au total », « Page 1 sur 6 », première ligne `S001` / Lille - Gare.

Contrôles d'écran hors de ce cas, même session : connexion exploitant puis direction, barre latérale avec identifiant et rôle, jeton non affiché, déconnexion, tableau d'incidents (177), formulaire de statut visible seulement pour l'exploitant, message « La modification des incidents est réservée aux exploitants. » pour la direction, indicateurs 2 002 trajets / 10 stations actives / délai 129,4. Une navigation directe vers Stations sans session affiche « Veuillez vous connecter » et n'appelle pas l'API.

Statut : **OK**

## Synthèse

| Cas | Date | Version testée | Statut | Preuve | Anomalie |
|---|---|---|---|---|---|
| REC-01 | 13/10/2026 | arbre de travail, tag prévu v1.0.0 | OK | deux imports, comptages SQL | - |
| REC-02 | 13/10/2026 | idem | OK | journal et requête orpheline à 0 | - |
| REC-03 | 13/10/2026 | idem | OK | deux 200, rôles exploitant et direction | - |
| REC-04 | 13/10/2026 | idem | OK | deux 401, message identique | - |
| REC-05 | 13/10/2026 | idem | OK | 401 sans jeton et jeton invalide, 200 sur /sante | - |
| REC-06 | 13/10/2026 | idem | OK | 403, 200, 422, ligne restaurée | - |
| REC-07 | 13/10/2026 | idem | OK | enveloppe, Lille = 46, deux 422 | - |
| REC-08 | 13/10/2026 | idem | OK | S001 et 404 S999 | - |
| REC-09 | 13/10/2026 | idem | OK | 7 jours identiques au SQL, somme = total trajets | - |
| REC-10 | 13/10/2026 | idem | OK | état vide, API arrêtée, retour du tableau | - |

10 cas exécutés sur 10. 10 OK, 0 KO, 0 NT. 0 anomalie ouverte, 0 corrigée. Le dossier `docs/recette/anomalies/` ne contient pas de fiche.

## Axes d'amélioration

1. Purger les trajets de plus de 13 mois. Le sujet le prévoit, le script n'est pas livré.
2. Créer et désactiver les comptes hors de l'IHM actuelle. Les deux comptes viennent de `sql/comptes.sql`.
3. Masquer `usager_ref` dans `GET /trajets` pour le rôle `direction`. L'API le renvoie encore. Aucun écran ne l'affiche.
4. Reporter les données météo et l'anticipation de charge, explicitement hors V1.

---

# Procès-verbal de recette - VéloVille V1

## 1. Identification

Application VéloVille, version de travail du 13/10/2026 destinée au tag `v1.0.0`. Campagne menée le 13/10/2026. Environnement : poste de développement, Python 3.12.11, PostgreSQL 16 via Docker Compose, FastAPI et Streamlit du `requirements.txt`. Participant : développeur.

## 2. Périmètre recetté

REC-01 à REC-10, dans l'ordre du plan. Rien n'a été laissé non testé dans ce périmètre. La purge des trajets, la gestion des comptes et le masquage de `usager_ref` ne font pas partie des cas.

## 3. Résultats de la campagne

10 cas prévus, 10 exécutés : 10 OK, 0 KO, 0 NT. Anomalies : 0 ouverte, 0 corrigée.

## 4. Réserves bloquantes

Néant.

## 5. Réserves non bloquantes

Néant au titre de la recette. Les quatre axes ci-dessus sont des suites de produit, pas des écarts aux cas REC-01 à REC-10.

## 6. Décision

Recette **PRONONCÉE**. Les dix cas produisent le résultat attendu par le plan, sur l'application réelle, et la base est revenue à l'état de l'import après le cas qui modifiait un incident.

## 7. Signatures

Pour le commanditaire - 

Pour le développeur - développeur, le 13/10/2026.
