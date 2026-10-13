#!/usr/bin/env bash
# Sauvegarde horodatée de la base veloville au format custom (pg_dump -Fc).
# La connexion est lue dans .env. Le script s'arrête avec un code non nul si
# la sauvegarde échoue ou si le fichier produit est vide.
set -euo pipefail

racine="$(cd "$(dirname "$0")/.." && pwd)"
cd "$racine"

if [[ ! -f .env ]]; then
  echo "Fichier .env introuvable à la racine du projet." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL est absente." >&2
  exit 1
fi

mkdir -p sauvegardes
fichier="${racine}/sauvegardes/veloville_$(date +%Y%m%d_%H%M%S).dump"

echec() {
  rm -f "$fichier"
  echo "$1" >&2
  exit 1
}

if command -v pg_dump >/dev/null 2>&1; then
  url="$(python3 -c 'import os; print(os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1))')"
  pg_dump --dbname="$url" --format=custom --file="$fichier" || echec "pg_dump a échoué."
else
  docker compose exec -T db pg_dump -U veloville -d veloville --format=custom > "$fichier" \
    || echec "pg_dump via Docker a échoué."
fi

if [[ ! -s "$fichier" ]]; then
  echec "La sauvegarde est vide."
fi

echo "$fichier"
