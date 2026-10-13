-- Schéma de la base veloville (PostgreSQL 14+).
-- Rejouable : les tables sont supprimées puis recréées.
-- Après un rejeu, réexécuter sql/comptes.sql et scripts/importer.py.

-- ---------------------------------------------------------------
-- 0. Nettoyage
-- ---------------------------------------------------------------

DROP TABLE IF EXISTS trajet CASCADE;
DROP TABLE IF EXISTS incident CASCADE;
DROP TABLE IF EXISTS utilisateur CASCADE;
DROP TABLE IF EXISTS station CASCADE;

-- ---------------------------------------------------------------
-- 1. Table station
-- ---------------------------------------------------------------

CREATE TABLE station (
    station_id VARCHAR(10) PRIMARY KEY,
    nom TEXT NOT NULL,
    commune TEXT NOT NULL,
    capacite INTEGER NOT NULL CHECK (capacite > 0),
    latitude NUMERIC(8, 5) NOT NULL,
    longitude NUMERIC(8, 5) NOT NULL,
    date_mise_en_service DATE NOT NULL
);

-- ---------------------------------------------------------------
-- 2. Table trajet
-- ---------------------------------------------------------------

CREATE TABLE trajet (
    trajet_id VARCHAR(12) PRIMARY KEY,
    velo_id VARCHAR(8) NOT NULL,
    depart_horodatage TIMESTAMP NOT NULL,
    station_depart VARCHAR(10) NOT NULL REFERENCES station (station_id),
    station_arrivee VARCHAR(10) REFERENCES station (station_id),
    duree_secondes INTEGER NOT NULL CHECK (duree_secondes > 0),
    type_usager VARCHAR(20) NOT NULL CHECK (type_usager IN ('abonne', 'occasionnel')),
    usager_ref VARCHAR(20)
);

-- ---------------------------------------------------------------
-- 3. Table incident
-- ---------------------------------------------------------------

CREATE TABLE incident (
    incident_id VARCHAR(12) PRIMARY KEY,
    date_signalement TIMESTAMP NOT NULL,
    cible VARCHAR(10) NOT NULL CHECK (cible IN ('velo', 'station')),
    velo_id VARCHAR(8),
    station_id VARCHAR(10) REFERENCES station (station_id),
    type_incident TEXT NOT NULL,
    statut VARCHAR(10) NOT NULL CHECK (statut IN ('ouvert', 'en_cours', 'resolu')),
    date_resolution TIMESTAMP,
    technicien TEXT,
    CONSTRAINT incident_cible_coherente CHECK (
        (cible = 'velo' AND velo_id IS NOT NULL AND station_id IS NULL)
        OR (cible = 'station' AND station_id IS NOT NULL AND velo_id IS NULL)
    ),
    CONSTRAINT incident_resolution_coherente CHECK (
        (
            statut = 'resolu'
            AND date_resolution IS NOT NULL
            AND date_resolution >= date_signalement
        )
        OR (statut <> 'resolu' AND date_resolution IS NULL)
    )
);

-- ---------------------------------------------------------------
-- 4. Table utilisateur
-- ---------------------------------------------------------------

CREATE TABLE utilisateur (
    id_utilisateur SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    mot_de_passe_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('exploitant', 'direction'))
);

-- ---------------------------------------------------------------
-- 5. Index utiles aux filtres et aux indicateurs
-- ---------------------------------------------------------------

CREATE INDEX idx_station_commune ON station (commune);
CREATE INDEX idx_trajet_depart ON trajet (depart_horodatage);
CREATE INDEX idx_trajet_station_depart ON trajet (station_depart);
CREATE INDEX idx_trajet_station_arrivee ON trajet (station_arrivee);
CREATE INDEX idx_incident_statut ON incident (statut);
CREATE INDEX idx_incident_signalement ON incident (date_signalement DESC);
