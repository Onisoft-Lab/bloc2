# VéloVille

Plateforme de restitution des données du service de vélos en libre-service VéloVille (Hauts-de-France). Une API FastAPI lit une base PostgreSQL. Un front Streamlit affiche des tableaux : stations, incidents, indicateurs. Les graphiques sont hors périmètre.

## Prérequis

- Python 3.12
- [UV](https://docs.astral.sh/uv/) pour créer l'environnement
- Docker, pour PostgreSQL

`requirements.txt` reste installable avec `pip` si UV n'est pas disponible.

## Installation

```bash
uv venv --python 3.12
uv pip install -r requirements.txt
cp .env.example .env
```

Dans `.env`, renseigner `JWT_SECRET` avec une valeur aléatoire longue. Ne jamais commiter `.env`.

Les comptes de démonstration sont `exploitant01` (rôle `exploitant`) et `direction01` (rôle `direction`). Mot de passe : `Formation2026!`. Le recopier dans `COMPTE_MOT_DE_PASSE` pour que pytest puisse se connecter. Cette valeur ne figure que dans `sql/comptes.sql` (commentaire et empreinte bcrypt) et dans la documentation.

## Base de données

PostgreSQL 16 tourne dans Docker. Le port publié est 5432 et l'URL du contrat ne change pas :

`postgresql+psycopg://veloville:veloville@localhost:5432/veloville`

```bash
docker compose up -d
docker compose exec -T db psql -U veloville -d veloville < sql/schema.sql
docker compose exec -T db psql -U veloville -d veloville < sql/comptes.sql
```

Le détail d'un poste vierge, la sauvegarde et la restauration sont dans [docs/procedure-deploiement.md](docs/procedure-deploiement.md).

## Import

```bash
uv run python scripts/importer.py
```

L'import est idempotent (`ON CONFLICT DO NOTHING`). Une seconde exécution réécrit le journal et ne change pas les volumes en base.

Le journal est [docs/journal-import.csv](docs/journal-import.csv). Le squelette ignore les fichiers `journal_rejets*`, d'où ce nom. Colonnes : fichier, identifiant, colonne, valeur, motif, décision (`rejet`, `normalisation`, `doublon`, `avertissement`).

Pour chaque CSV, lignes lues = retenues + rejetées + doublons. Une normalisation ou un avertissement est une ligne de journal en plus, pas un quatrième sort.

| Fichier | Lues | Retenues | Rejetées | Doublons |
|---|---:|---:|---:|---:|
| stations.csv | 120 | 120 | 0 | 0 |
| trajets.csv | 2 030 | 2 002 | 16 | 12 |
| incidents.csv | 180 | 177 | 3 | 0 |

Trajets rejetés : 9 durées nulles ou négatives, 7 arrivées `S999`. Les 12 doublons stricts écartent la seconde occurrence, y compris `T480596` déjà rejeté pour la durée. 23 arrivées vides sont conservées. 6 `velo_id` en minuscules et 4 dates `JJ/MM/AAAA HH:MM` sont normalisés puis importés. Une cinquième date mal formée est sur une ligne déjà rejetée pour `S999` : seul le rejet est journalisé.

Incidents rejetés (date de résolution antérieure au signalement) : `I2026-0028`, `I2026-0124`, `I2026-0178`. Les statuts hétérogènes sont ramenés à `ouvert`, `en_cours` ou `resolu`. Un technicien absent sur un incident `en_cours` ou `resolu` produit un avertissement, la ligne est conservée.

Contrôles : 46 stations à Lille, `S001` se nomme « Lille - Gare », aucune arrivée renseignée ne pointe vers une station absente.

Le modèle et les règles RG1 à RG8 sont décrits dans [docs/schema-donnees.md](docs/schema-donnees.md).

## Lancement

```bash
uv run uvicorn api.main:app --port 8000
uv run streamlit run front/app.py
```

`GET /sante` répond `{"statut": "ok"}` sans jeton. Les autres routes exigent `Authorization: Bearer`. La matrice des droits est dans [docs/matrice-roles-droits.md](docs/matrice-roles-droits.md).

## Tests

```bash
uv run pytest --cov=api/services --cov-report=term-missing
```

27 tests passent. Couverture de `api/services` : 99 % (278 instructions, 2 non couvertes dans `indicateurs.py` : conversion d'un horodatage déjà de type datetime, et moyenne de délai absente). Seuil demandé : 60 %.

## Écoresponsabilité

- Les listes sont paginées côté serveur. `taille_page` est plafonnée à 100.
- Le front ne se rafraîchit pas tout seul.
- La liste des communes est mise en cache une heure (`st.cache_data`).
- Les indicateurs sont des agrégations SQL, pas un parcours des lignes dans l'application.
- Aucune dépendance au-delà de ce que les trois briques (API, import, front, tests) utilisent.

## Limites connues

- La purge des trajets de plus de 13 mois n'est pas livrée.
- Il n'y a pas d'écran de gestion des comptes.
- `GET /trajets` renvoie encore `usager_ref` au rôle `direction`. Aucun écran ne l'affiche.
- Les données météo et l'anticipation de charge sont hors V1.

La campagne du 13/10/2026 est dans [docs/recette/resultats-recette.md](docs/recette/resultats-recette.md) : 10 cas sur 10 OK, recette prononcée, aucune fiche d'anomalie.
