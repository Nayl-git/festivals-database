-- Analysis queries.
-- Queries 1 to 3 are the ones written in May 2024 (report section 4.1), unchanged.
-- Queries 4 and 5 were ADDED after the course; they use the association tables
-- that could not be loaded in 2024.

-- Query 1 (2024): how are festivals spread across regions?
SELECT r.region, COUNT(f.id_festival) AS nombre_de_festivals
FROM festival f
JOIN commune c ON f.id_commune = c.id_commune
JOIN departement d ON c.id_departement = d.id_departement
JOIN region r ON d.id_region = r.id_region
GROUP BY r.region
ORDER BY nombre_de_festivals DESC;

-- Query 2 (2024): which organisations (EPCI, inter-municipal bodies) host the most festivals?
SELECT o.libelle_insee_epci AS organisation, COUNT(f.id_festival) AS nombre_de_festivals
FROM festival f
JOIN organisation o ON f.id_organisation = o.id_organisation
GROUP BY o.libelle_insee_epci
ORDER BY nombre_de_festivals DESC
LIMIT 5;

-- Query 3 (2024): how many sub-categories does each dominant discipline have?
SELECT c.discipline_dominante, COUNT(sc.id_sous_categorie) AS nombre_de_sous_categories
FROM sous_categorie sc
JOIN categorie c ON sc.id_categorie = c.id_categorie
GROUP BY c.discipline_dominante
ORDER BY nombre_de_sous_categories DESC;

-- Query 4 (ADDED): festivals per dominant discipline, through the association table.
SELECT c.discipline_dominante,
       COUNT(*) AS nombre_de_festivals,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS part_pct
FROM festival_categorie fc
JOIN categorie c ON fc.id_categorie = c.id_categorie
GROUP BY c.discipline_dominante
ORDER BY nombre_de_festivals DESC;

-- Query 5 (ADDED): festivals by decade of creation. The decade column was removed
-- to reach 3NF (it depends on the creation year), so it is derived here instead.
SELECT (CAST(f.date_creation AS INT) / 10) * 10 AS decennie,
       COUNT(*) AS nombre_de_festivals
FROM festival f
WHERE f.date_creation ~ '^[0-9]{4}$'
GROUP BY decennie
ORDER BY decennie;
