# Journal des versions

## [1.0.0] - 2026-10-13

### Ajouté
- Résultats de la campagne de recette du 13/10/2026 et procès-verbal.
- README, schéma de données, procédure de déploiement, matrice des droits.
- Script `scripts/sauvegarde.sh` (pg_dump au format custom).

### Corrigé
- Aucune correction de code : les dix cas sont OK.

## [0.2.0] - 2026-10-13

### Ajouté
- Schéma PostgreSQL rejouable, règles de fiabilisation et import idempotent.
- API FastAPI : authentification JWT, stations, trajets, incidents, trois indicateurs.
- Front Streamlit : connexion et trois écrans tabulaires.
- Tests unitaires et d'intégration. Couverture de `api/services` : 99 %.

## [0.1.0] - 2026-10-07

### Ajouté
- Initialisation du projet à partir du squelette fourni.
