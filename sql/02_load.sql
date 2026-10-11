-- Load the CSV files written by etl/build_tables.py (psql meta-commands).
-- Run from the repository root, after sql/01_schema.sql:
--   psql -v ON_ERROR_STOP=1 -d festivals -f sql/01_schema.sql -f sql/02_load.sql
-- HEADER MATCH (PostgreSQL 15+) makes the load fail if a file's columns do not
-- match the table. Parents are loaded before children, so every foreign key is
-- checked as rows arrive.

\copy region FROM 'build/tables/region.csv' WITH (FORMAT csv, HEADER MATCH, ENCODING 'UTF8')
\copy departement FROM 'build/tables/departement.csv' WITH (FORMAT csv, HEADER MATCH, ENCODING 'UTF8')
\copy commune FROM 'build/tables/commune.csv' WITH (FORMAT csv, HEADER MATCH, ENCODING 'UTF8')
\copy adresse FROM 'build/tables/adresse.csv' WITH (FORMAT csv, HEADER MATCH, ENCODING 'UTF8')
\copy categorie FROM 'build/tables/categorie.csv' WITH (FORMAT csv, HEADER MATCH, ENCODING 'UTF8')
\copy sous_categorie FROM 'build/tables/sous_categorie.csv' WITH (FORMAT csv, HEADER MATCH, ENCODING 'UTF8')
\copy organisation FROM 'build/tables/organisation.csv' WITH (FORMAT csv, HEADER MATCH, ENCODING 'UTF8')
\copy festival FROM 'build/tables/festival.csv' WITH (FORMAT csv, HEADER MATCH, ENCODING 'UTF8')

-- Association tables: not loadable in 2024 (duplicate keys), loaded since the ETL fix.
\copy festival_categorie FROM 'build/tables/festival_categorie.csv' WITH (FORMAT csv, HEADER MATCH, ENCODING 'UTF8')
\copy festival_organisation FROM 'build/tables/festival_organisation.csv' WITH (FORMAT csv, HEADER MATCH, ENCODING 'UTF8')
\copy festival_commune FROM 'build/tables/festival_commune.csv' WITH (FORMAT csv, HEADER MATCH, ENCODING 'UTF8')
\copy festival_adresse FROM 'build/tables/festival_adresse.csv' WITH (FORMAT csv, HEADER MATCH, ENCODING 'UTF8')

ANALYZE;
