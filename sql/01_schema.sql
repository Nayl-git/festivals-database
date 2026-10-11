-- French festivals database: table creation script (PostgreSQL).
-- Written in May 2024 for SAE 2.01 (report section 3.1) and kept as submitted:
-- 8 entity tables and 4 association tables. The only changes are these comments
-- and the removal of empty lines; the statements themselves are unchanged.

DROP TABLE IF EXISTS festival_adresse;
DROP TABLE IF EXISTS festival_organisation;
DROP TABLE IF EXISTS festival_commune;
DROP TABLE IF EXISTS festival_categorie;

DROP TABLE IF EXISTS organisation CASCADE;
DROP TABLE IF EXISTS festival CASCADE;
DROP TABLE IF EXISTS sous_categorie CASCADE;
DROP TABLE IF EXISTS categorie CASCADE;
DROP TABLE IF EXISTS adresse CASCADE;
DROP TABLE IF EXISTS commune CASCADE;
DROP TABLE IF EXISTS departement CASCADE;
DROP TABLE IF EXISTS region CASCADE;

-- Entity tables ---------------------------------------------------------------

CREATE TABLE region (
id_region INT PRIMARY KEY,
region VARCHAR
);

CREATE TABLE departement (
id_departement INT PRIMARY KEY,
departement VARCHAR,
id_region INT,
FOREIGN KEY (id_region) REFERENCES region(id_region)
);

CREATE TABLE commune (
id_commune INT PRIMARY KEY,
commune VARCHAR,
code_postal_commune VARCHAR,
code_insee_commune VARCHAR,
id_departement INT,
FOREIGN KEY (id_departement) REFERENCES departement(id_departement)
);

CREATE TABLE adresse (
id_adresse INT PRIMARY KEY,
numero_de_voie VARCHAR,
type_de_voie VARCHAR,
nom_de_la_voie VARCHAR,
complement_d_adresse VARCHAR,
geocodage VARCHAR,
id_commune INT,
FOREIGN KEY (id_commune) REFERENCES commune(id_commune)
);

CREATE TABLE categorie (
id_categorie INT PRIMARY KEY,
discipline_dominante VARCHAR
);

CREATE TABLE sous_categorie (
id_sous_categorie INT PRIMARY KEY,
sous_categorie_spectacle_vivant VARCHAR,
sous_categorie_musique VARCHAR,
sous_categorie_musique_cnm VARCHAR,
sous_categorie_cinema_audiovisuel VARCHAR,
sous_categorie_art_visuel_et_arts_numériques VARCHAR,
sous_categorie_livres_et_litterature VARCHAR,
id_categorie INT,
FOREIGN KEY (id_categorie) REFERENCES categorie(id_categorie)
);

CREATE TABLE organisation (
id_organisation INT PRIMARY KEY,
code_insee_epci VARCHAR,
libelle_insee_epci VARCHAR
);

CREATE TABLE festival (
id_festival INT PRIMARY KEY,
nom_festival VARCHAR,
e_mail VARCHAR,
date_creation VARCHAR,
site_web VARCHAR,
periode_principale_de_deroulement_du_festival VARCHAR,
id_commune INT,
id_adresse INT,
id_organisation INT,
FOREIGN KEY (id_adresse) REFERENCES adresse(id_adresse),
FOREIGN KEY (id_commune) REFERENCES commune(id_commune),
FOREIGN KEY (id_organisation) REFERENCES organisation(id_organisation)
);

-- Association tables ----------------------------------------------------------

CREATE TABLE festival_categorie (
id_festival INT,
id_categorie INT,
PRIMARY KEY (id_festival, id_categorie),
FOREIGN KEY (id_festival) REFERENCES festival(id_festival),
FOREIGN KEY (id_categorie) REFERENCES categorie(id_categorie)
);

CREATE TABLE festival_organisation (
id_festival INT,
id_organisation INT,
PRIMARY KEY (id_festival , id_organisation),
FOREIGN KEY (id_festival) REFERENCES festival(id_festival),
FOREIGN KEY (id_organisation) REFERENCES organisation(id_organisation)
);

CREATE TABLE festival_commune (
id_festival INTEGER NOT NULL,
id_commune INTEGER NOT NULL,
PRIMARY KEY (id_festival, id_commune),
FOREIGN KEY (id_festival) REFERENCES FESTIVAL(id_festival),
FOREIGN KEY (id_commune) REFERENCES COMMUNE(id_commune)
);

CREATE TABLE festival_adresse (
id_festival INTEGER NOT NULL,
id_adresse INTEGER NOT NULL,
PRIMARY KEY (id_festival, id_adresse),
FOREIGN KEY (id_festival) REFERENCES festival (id_festival),
FOREIGN KEY (id_adresse) REFERENCES adresse (id_adresse)
);
