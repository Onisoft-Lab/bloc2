# Schéma de données

Base `veloville`, PostgreSQL 16. Le script [sql/schema.sql](../sql/schema.sql) supprime les tables puis les recrée. Après un rejeu, il faut recharger [sql/comptes.sql](../sql/comptes.sql) et relancer l'import.

## Modèle logique

```
station (station_id)
   |
   +--< trajet.station_depart
   +--< trajet.station_arrivee   (nullable)
   +--< incident.station_id      (nullable)

utilisateur est isolée : elle ne référence aucune donnée métier.
```

| Table | Clé | Rôle |
|---|---|---|
| station | `station_id` | Point de retrait et de dépôt |
| trajet | `trajet_id` | Course d'un vélo entre deux stations |
| incident | `incident_id` | Signalement sur un vélo ou une station |
| utilisateur | `id_utilisateur` | Compte `exploitant` ou `direction` |

## Contraintes portées par le schéma

- `station.capacite > 0`
- `trajet.duree_secondes > 0`
- `trajet.type_usager` parmi `abonne`, `occasionnel`
- `trajet.station_depart` obligatoire et présente dans `station`
- `trajet.station_arrivee` nulle ou présente dans `station`
- `incident.cible` parmi `velo`, `station`
- `incident.statut` parmi `ouvert`, `en_cours`, `resolu`
- `incident_cible_coherente` : un vélo a `velo_id` et pas de station ; une station a `station_id` et pas de vélo
- `incident_resolution_coherente` : `date_resolution` est renseignée si et seulement si le statut est `resolu`, et elle est postérieure ou égale au signalement
- `utilisateur.role` parmi `exploitant`, `direction`
- `usager_ref` reste nullable : le contrat ne demande pas de contrôle d'abonné en base

Index : commune, horodatage de départ, stations de départ et d'arrivée, statut, date de signalement.

## Règles de gestion

Elles sont appliquées par [api/services/fiabilisation.py](../api/services/fiabilisation.py) avant l'insertion. Le schéma empêche ensuite qu'une ligne invalide entre par un autre chemin.

| Règle | Contrôle | Sort d'une ligne en défaut |
|---|---|---|
| RG1 | Identifiant de station obligatoire et déjà connu pour un trajet ou un incident | Rejet |
| RG2 | Station d'arrivée renseignée mais inconnue (`S999` dans le jeu) | Rejet |
| RG3 | Station d'arrivée vide | Conservée, `station_arrivee` nulle |
| RG4 | Durée nulle ou négative | Rejet |
| RG5 | `occasionnel` avec une référence, ou référence mal formée | Rejet. Abonné sans référence : conservé, avec avertissement |
| RG6 | Cible incohérente (vélo sans identifiant, station avec un vélo, identifiant de vélo invalide) | Rejet |
| RG7 | Statut hors `ouvert` / `en_cours` / `resolu` après normalisation | Rejet |
| RG8 | Date de résolution antérieure au signalement | Rejet. Technicien absent sur `en_cours` ou `resolu` : avertissement, ligne conservée |

Les dates `JJ/MM/AAAA HH:MM` et les `velo_id` en minuscules sont normalisés puis importés. Un doublon strict (même ligne déjà traitée, y compris une ligne déjà rejetée) est écarté comme doublon, pas comme second rejet.

## Volumes après import

Mesurés le 13/10/2026, identiques après une seconde exécution.

| Fichier | Lignes CSV | Retenues | Rejetées | Doublons |
|---|---:|---:|---:|---:|
| stations.csv | 120 | 120 | 0 | 0 |
| trajets.csv | 2 030 | 2 002 | 16 | 12 |
| incidents.csv | 180 | 177 | 3 | 0 |

Journal : 16 rejets et 12 doublons de trajets, 10 normalisations de trajets, 3 rejets d'incidents, 124 normalisations de statut, 25 avertissements de technicien. Lille : 46 stations. `S001` : « Lille - Gare ».
