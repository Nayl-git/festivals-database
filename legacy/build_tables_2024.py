"""Original 2024 load-file generator (report section 3.2), kept for reference.

This is the script submitted in May 2024, transcribed from the report. Only three
things differ from the original: the comments are translated into English, the
two hard-coded local Windows paths are replaced by command-line arguments, and
the trailing notebook expression is replaced by a print. It is NOT used by the
pipeline: see etl/build_tables.py for the corrected version.

It expected the CSV export of the Ministry of Culture's former open-data portal,
whose headers were snake_case field names (e.g. ``region_principale_de_deroulement``).
The data.gouv.fr file used today has human-readable headers instead. An export
with the expected headers is archived at
https://web.archive.org/web/20221231065612/https://data.culture.gouv.fr/explore/dataset/festivals-global-festivals-_-pl/download?format=csv

Known problems (fixed in etl/build_tables.py):
- every table gets one row per CSV row (``generate_ids`` numbers rows, it does not
  deduplicate), so ``region`` holds 7,000+ rows instead of 22;
- foreign keys are numbered separately, from the *distinct* values, so a foreign
  key value points to an unrelated row of the referenced table;
- association tables use the source ``identifiant`` column, which is not unique,
  so their composite primary keys get duplicates and the load fails;
- missing values are written as the string ``'null'`` instead of SQL NULL.

Usage: python legacy/build_tables_2024.py <export.csv> <output_dir>
"""

import os
import sys

import pandas as pd

# Path to the downloaded CSV file
csv_file_path = sys.argv[1]

# Read the CSV file with the semicolon separator
data = pd.read_csv(csv_file_path, sep=";")

# Replace missing values with 'null'
data = data.fillna("null")

# Tables and their columns
tables_columns = {
    "region": ["region_principale_de_deroulement"],
    "departement": ["departement_principal_de_deroulement", "region_principale_de_deroulement"],
    "commune": [
        "commune_principale_de_deroulement",
        "code_postal_de_la_commune_principale_de_deroulement",
        "code_insee_commune",
        "departement_principal_de_deroulement",
    ],
    "adresse": [
        "numero_de_voie",
        "type_de_voie_rue_avenue_boulevard_etc",
        "nom_de_la_voie",
        "complement_d_adresse_facultatif",
        "geocodage_xy",
        "commune_principale_de_deroulement",
    ],
    "categorie": ["discipline_dominante"],
    "sous_categorie": [
        "sous_categorie_spectacle_vivant",
        "sous_categorie_musique",
        "sous_categorie_musique_cnm",
        "sous_categorie_cinema_et_audiovisuel",
        "sous_categorie_arts_visuels_et_arts_numeriques",
        "sous_categorie_livre_et_litterature",
        "discipline_dominante",
    ],
    "festival": [
        "nom_du_festival",
        "adresse_e_mail",
        "annee_de_creation_du_festival",
        "site_internet_du_festival",
        "commune_principale_de_deroulement",
        "periode_principale_de_deroulement_du_festival",
        "adresse_postale",
        "code_insee_epci_collage_en_valeur",
    ],
    "organisation": ["code_insee_epci_collage_en_valeur", "libelle_epci_collage_en_valeur"],
    "festival_categorie": ["identifiant", "discipline_dominante"],
    "festival_organisation": ["identifiant", "code_insee_epci_collage_en_valeur"],
    "festival_commune": ["identifiant", "commune_principale_de_deroulement"],
    "festival_adresse": ["identifiant", "adresse_postale"],
}

# Foreign keys
foreign_keys = {
    "departement": {"id_region": "region_principale_de_deroulement"},
    "commune": {"id_departement": "departement_principal_de_deroulement"},
    "adresse": {"id_commune": "commune_principale_de_deroulement"},
    "sous_categorie": {"id_categorie": "discipline_dominante"},
    "festival": {
        "id_commune": "commune_principale_de_deroulement",
        "id_adresse": "adresse_postale",
        "id_organisation": "code_insee_epci_collage_en_valeur",
    },
    "festival_categorie": {"id_festival": "identifiant", "id_categorie": "discipline_dominante"},
    "festival_organisation": {
        "id_festival": "identifiant",
        "id_organisation": "code_insee_epci_collage_en_valeur",
    },
    "festival_commune": {"id_festival": "identifiant", "id_commune": "commune_principale_de_deroulement"},
    "festival_adresse": {"id_festival": "identifiant", "id_adresse": "adresse_postale"},
}

# Output directory
output_dir = sys.argv[2]
if not os.path.exists(output_dir):
    os.makedirs(output_dir)


# Generate identifiers
def generate_ids(df, table):
    id_column_name = f"id_{table}"
    df.insert(0, id_column_name, range(1, len(df) + 1))
    return df


# Validate and format integer columns
def validate_and_format_integers(df, columns):
    for col in columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna("null").astype(str)
    return df


# Create the TXT files with their foreign keys
for table, columns in tables_columns.items():
    # Check that the columns exist in the CSV file
    existing_columns = [col for col in columns if col in data.columns]
    if not existing_columns:
        continue

    if table in ["festival_categorie", "festival_organisation", "festival_commune", "festival_adresse"]:
        # For these tables, keep only the foreign keys
        df = data[existing_columns].copy()
    else:
        # Add the auto-incremented 'id_<table>' column
        df = data[existing_columns].copy()
        df = generate_ids(df, table)

        # Validate and format integer columns
        integer_columns = [col for col in df.columns if "id_" in col]
        df = validate_and_format_integers(df, integer_columns)

    # Add the foreign keys
    if table in foreign_keys:
        for fk, ref_col in foreign_keys[table].items():
            if ref_col in data.columns:
                ref_data = data[[ref_col]].drop_duplicates().reset_index(drop=True)
                ref_data = generate_ids(ref_data, fk.replace("id_", ""))
                try:
                    df = df.merge(ref_data, how="left", left_on=ref_col, right_on=ref_col)
                    df = df.rename(columns={f'id_{fk.replace("id_", "")}': fk})
                    df = df.drop(columns=[ref_col])
                except KeyError:
                    print(f"KeyError: '{ref_col}' not found in DataFrame. Skipping this merge.")

    # Write the complete data to a TXT file
    output_file = os.path.join(output_dir, f"{table}.txt")
    df.to_csv(output_file, sep="\t", index=False)

# List the created files
output_files = os.listdir(output_dir)
print(output_files)
