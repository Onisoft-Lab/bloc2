# Procédure de déploiement

Poste vierge jusqu'à `GET /sante`, puis sauvegarde et restauration. Les commandes partent de la racine du dépôt.

## 1. Outils

Installer Python 3.12, UV, Docker et Docker Compose. PostgreSQL n'a pas besoin d'être installé sur l'hôte : le script de sauvegarde appelle `pg_dump` du PATH s'il existe, sinon `docker compose exec`.

## 2. Environnement Python

```bash
uv venv --python 3.12
uv pip install -r requirements.txt
```

Équivalent sans UV : `python3.12 -m venv .venv`, activer le venv, puis `pip install -r requirements.txt`.

## 3. Secrets

```bash
cp .env.example .env
```

Renseigner dans `.env` :

- `JWT_SECRET` : chaîne aléatoire longue, par exemple la sortie de `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Ne pas la coller dans un fichier versionné.
- `COMPTE_MOT_DE_PASSE` : `Formation2026!` (comptes de démonstration, voir le README).

`DATABASE_URL`, `JWT_ALGORITHM`, `JWT_EXPIRATION_MINUTES`, `API_URL` et `API_TIMEOUT_SECONDES` peuvent rester aux valeurs de l'exemple.

## 4. Base

```bash
docker compose up -d
docker compose exec -T db psql -U veloville -d veloville < sql/schema.sql
docker compose exec -T db psql -U veloville -d veloville < sql/comptes.sql
uv run python scripts/importer.py
uv run python scripts/importer.py
```

La seconde exécution doit afficher les mêmes volumes et laisser la base à 120 stations, 2 002 trajets, 177 incidents.

## 5. Contrôle

```bash
uv run pytest --cov=api/services --cov-report=term-missing
uv run uvicorn api.main:app --port 8000
```

Dans un autre terminal :

```bash
curl -s http://127.0.0.1:8000/sante
```

Réponse attendue : `{"statut":"ok"}`.

Front :

```bash
uv run streamlit run front/app.py
```

Ouvrir l'adresse affichée et se connecter avec `exploitant01` ou `direction01`.

## 6. Sauvegarde

```bash
bash scripts/sauvegarde.sh
```

Le script lit `DATABASE_URL` dans `.env`, crée `sauvegardes/` et écrit `sauvegardes/veloville_AAAAMMJJ_HHMMSS.dump` au format custom (`pg_dump -Fc`). Il affiche le chemin du fichier. Il s'arrête avec un code non nul, et supprime le fichier, si `pg_dump` échoue ou si le fichier est vide. Le dossier `sauvegardes/` est ignoré par Git.

Contrôle du contenu, sans client sur l'hôte :

```bash
docker compose exec -T db pg_restore --list < sauvegardes/veloville_AAAAMMJJ_HHMMSS.dump
```

Une sauvegarde de contrôle a été produite le 13/10/2026 : `sauvegardes/veloville_20261013_091329.dump`.

## 7. Restauration

Sur une base déjà créée par `sql/schema.sql` (le format custom ne recrée pas le rôle ni la base) :

```bash
docker compose exec -T db pg_restore -U veloville -d veloville --clean --if-exists < sauvegardes/veloville_AAAAMMJJ_HHMMSS.dump
```

Avec un client sur l'hôte, remplacer le préfixe SQLAlchemy de l'URL puis :

```bash
pg_restore --dbname="postgresql://veloville:veloville@localhost:5432/veloville" --clean --if-exists sauvegardes/veloville_AAAAMMJJ_HHMMSS.dump
```

Recharger ensuite n'est pas nécessaire : le dump contient les données. Vérifier `GET /sante` et un `SELECT count(*) FROM station` à 120.
