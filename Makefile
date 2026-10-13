.DEFAULT_GOAL := help

.PHONY: help installer env up schema comptes import recharger api front test sauvegarde sante down

help: ## Affiche les commandes
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

installer: ## Crée le venv Python 3.12 et installe les dépendances
	uv venv --python 3.12
	uv pip install -r requirements.txt

env: ## Copie .env.example vers .env s'il n'existe pas
	@test -f .env || cp .env.example .env
	@echo "Renseigner JWT_SECRET et COMPTE_MOT_DE_PASSE dans .env"

up: ## Démarre PostgreSQL et attend qu'il réponde
	docker compose up -d --wait

schema: ## Recrée les tables (les données sont supprimées)
	docker compose exec -T db psql -U veloville -d veloville < sql/schema.sql

comptes: ## Charge les comptes exploitant01 et direction01
	docker compose exec -T db psql -U veloville -d veloville < sql/comptes.sql

import: ## Importe les trois CSV
	uv run python scripts/importer.py

recharger: up schema comptes import ## Recrée la base, charge les comptes et importe

api: ## Lance l'API sur le port 8000
	uv run uvicorn api.main:app --port 8000

front: ## Lance le front Streamlit
	uv run streamlit run front/app.py

test: ## Lance pytest et la couverture de api/services
	uv run pytest --cov=api/services --cov-report=term-missing

sauvegarde: ## Écrit un pg_dump horodaté dans sauvegardes/
	bash scripts/sauvegarde.sh

sante: ## Appelle GET /sante
	@curl -fsS http://127.0.0.1:8000/sante
	@echo

down: ## Arrête PostgreSQL
	docker compose down
