-- Original 2024 population script (report section 3.2), kept for reference.
-- The local Windows paths of the original are replaced by relative paths to the
-- folder written by legacy/build_tables_2024.py. Not used by the pipeline: see
-- sql/02_load.sql.

\COPY region FROM 'textes/region.txt' delimiter E'\t' csv HEADER encoding 'UTF8';

\COPY departement FROM 'textes/departement.txt' delimiter E'\t' csv HEADER encoding 'UTF8';

\COPY commune FROM 'textes/commune.txt' delimiter E'\t' csv HEADER encoding 'UTF8';

\COPY adresse FROM 'textes/adresse.txt' delimiter E'\t' csv HEADER encoding 'UTF8';

\COPY categorie FROM 'textes/categorie.txt' delimiter E'\t' csv HEADER encoding 'UTF8';

\COPY sous_categorie FROM 'textes/sous_categorie.txt' delimiter E'\t' csv HEADER encoding 'UTF8';

\COPY organisation FROM 'textes/organisation.txt' delimiter E'\t' csv HEADER encoding 'UTF8';

\COPY festival FROM 'textes/festival.txt' delimiter E'\t' csv HEADER encoding 'UTF8';

-- The report notes that the association-table part "causes errors" (duplicate
-- keys) and set it aside; these four commands were never run successfully in 2024.

\COPY festival_categorie FROM 'textes/festival_categorie.txt' delimiter E'\t' csv HEADER encoding 'UTF8';

\COPY festival_organisation FROM 'textes/festival_organisation.txt' delimiter E'\t' csv HEADER encoding 'UTF8';

\COPY festival_commune FROM 'textes/festival_commune.txt' delimiter E'\t' csv HEADER encoding 'UTF8';

\COPY festival_adresse FROM 'textes/festival_adresse.txt' delimiter E'\t' csv HEADER encoding 'UTF8';
