"""Build one CSV file per table of sql/01_schema.sql from the raw festivals CSV.

Corrected version of the 2024 script (legacy/build_tables_2024.py). Same idea:
read the open-data file with pandas, split it into the tables of the relational
model and write load files for PostgreSQL. What changed:

- every entity table is deduplicated on a natural key (region name, department
  name, INSEE commune code, street address, discipline, sub-category values,
  EPCI code), so ``region`` has 22 rows instead of one row per festival;
- each table gets its identifiers once, and foreign keys reuse that same mapping,
  so a foreign key always points to the right row;
- festivals get their own surrogate key (one per source row), so the association
  tables have unique composite keys and can be loaded;
- identifiers are deterministic: dimension ids follow the sorted natural key,
  festival ids follow the order of the source file;
- missing values stay empty (SQL NULL) instead of the string 'null';
- light cleaning: INSEE and postal codes that lost their leading zero are padded,
  '0' INSEE codes and spreadsheet errors ('#N/A', '#REF!') are treated as
  missing, '01/01/YYYY 00:00' years become 'YYYY'.

Usage: python etl/build_tables.py [--input data/festivals-global-festivals-pl.csv.gz]
                                   [--output build/tables]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "festivals-global-festivals-pl.csv.gz"
DEFAULT_OUTPUT = ROOT / "build" / "tables"

# data.gouv.fr header -> field name used by the 2024 scripts (the snake_case names
# of the Ministry of Culture's former export). Files that already use the
# snake_case names are accepted as they are.
COLUMNS = {
    "Nom du festival": "nom_du_festival",
    "Envergure territoriale": "envergure_territoriale",
    "Région principale de déroulement": "region_principale_de_deroulement",
    "Département principal de déroulement": "departement_principal_de_deroulement",
    "Commune principale de déroulement": "commune_principale_de_deroulement",
    "Code postal (de la commune principale de déroulement)": ("code_postal_de_la_commune_principale_de_deroulement"),
    "Code Insee commune": "code_insee_commune",
    "Code Insee EPCI": "code_insee_epci_collage_en_valeur",
    "Libellé EPCI": "libelle_epci_collage_en_valeur",
    "Numéro de voie": "numero_de_voie",
    "Type de voie (rue, Avenue, boulevard, etc.)": "type_de_voie_rue_avenue_boulevard_etc",
    "Nom de la voie": "nom_de_la_voie",
    "Adresse postale": "adresse_postale",
    "Complément d'adresse (facultatif)": "complement_d_adresse_facultatif",
    "Site internet du festival": "site_internet_du_festival",
    "Adresse e-mail": "adresse_e_mail",
    "Décennie de création du festival": "decennie_de_creation_du_festival",
    "Année de création du festival": "annee_de_creation_du_festival",
    "Discipline dominante": "discipline_dominante",
    "Sous-catégorie spectacle vivant": "sous_categorie_spectacle_vivant",
    "Sous-catégorie musique": "sous_categorie_musique",
    "Sous-catégorie Musique CNM": "sous_categorie_musique_cnm",
    "Sous-catégorie cinéma et audiovisuel": "sous_categorie_cinema_et_audiovisuel",
    "Sous-catégorie arts visuels et arts numériques": "sous_categorie_arts_visuels_et_arts_numeriques",
    "Sous-catégorie livre et littérature": "sous_categorie_livre_et_litterature",
    "Période principale de déroulement du festival": "periode_principale_de_deroulement_du_festival",
    "Identifiant Agence A": "identifiant_agence_a",
    "Identifiant": "identifiant",
    "Géocodage xy": "geocodage_xy",
    "identifiant CNM": "identifiant_cnm",
}

# Source columns -> sous_categorie table columns (names as in sql/01_schema.sql).
SUBCATEGORY_COLUMNS = {
    "sous_categorie_spectacle_vivant": "sous_categorie_spectacle_vivant",
    "sous_categorie_musique": "sous_categorie_musique",
    "sous_categorie_musique_cnm": "sous_categorie_musique_cnm",
    "sous_categorie_cinema_et_audiovisuel": "sous_categorie_cinema_audiovisuel",
    "sous_categorie_arts_visuels_et_arts_numeriques": "sous_categorie_art_visuel_et_arts_numériques",
    "sous_categorie_livre_et_litterature": "sous_categorie_livres_et_litterature",
}

ADDRESS_COLUMNS = [
    "numero_de_voie",
    "type_de_voie_rue_avenue_boulevard_etc",
    "nom_de_la_voie",
    "complement_d_adresse_facultatif",
]

SPREADSHEET_ERRORS = ["#N/A", "#REF!"]

# Load order (parents before children), used by tests and sql/02_load.sql.
TABLES = [
    "region",
    "departement",
    "commune",
    "adresse",
    "categorie",
    "sous_categorie",
    "organisation",
    "festival",
    "festival_categorie",
    "festival_organisation",
    "festival_commune",
    "festival_adresse",
]


def read_raw(path: Path) -> pd.DataFrame:
    """Read the raw CSV (';'-separated, possibly gzipped) as text, with snake_case headers."""
    df = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    # The data.gouv.fr file starts with two byte-order marks; utf-8-sig removes one.
    df.columns = [c.lstrip("\ufeff").strip() for c in df.columns]
    df = df.rename(columns=COLUMNS)
    # The published snapshot has no e-mail column (removed for privacy by scripts/download_data.py).
    missing = sorted(set(COLUMNS.values()) - set(df.columns) - {"adresse_e_mail"})
    if missing:
        raise ValueError(f"unexpected file format, missing columns: {missing}")
    # Trim every cell; empty strings become missing values.
    df = df.apply(lambda s: s.str.strip()).replace("", pd.NA)
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    # Spreadsheet error markers left in the source file mean "no value".
    df = df.replace(SPREADSHEET_ERRORS, pd.NA)

    def pad(value: object, width: int) -> object:
        if isinstance(value, str) and value.isdigit() and len(value) == width - 1:
            return value.zfill(width)
        return value

    insee = df["code_insee_commune"].where(df["code_insee_commune"] != "0")
    df["code_insee_commune"] = insee.map(lambda v: pad(v, 5))
    postal = "code_postal_de_la_commune_principale_de_deroulement"
    df[postal] = df[postal].map(lambda v: pad(v, 5))
    year = "annee_de_creation_du_festival"
    df[year] = df[year].str.replace(r"^01/01/(\d{4}) 00:00$", r"\1", regex=True)
    return df


def mode(values: pd.Series) -> object:
    """Most frequent non-missing value; ties broken alphabetically (deterministic)."""
    counts = values.dropna().value_counts()
    if counts.empty:
        return pd.NA
    best = counts.max()
    return sorted(counts[counts == best].index)[0]


def number(keys: pd.Series) -> dict:
    """Map each distinct non-missing key to 1..n in sorted order."""
    distinct = sorted(keys.dropna().unique())
    return {key: i for i, key in enumerate(distinct, start=1)}


def build_tables(raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df = clean(raw).reset_index(drop=True)
    tables: dict[str, pd.DataFrame] = {}

    # region
    region_ids = number(df["region_principale_de_deroulement"])
    tables["region"] = pd.DataFrame({"id_region": list(region_ids.values()), "region": list(region_ids.keys())})

    # departement (its region is the most frequent one among its festivals)
    dep_col = "departement_principal_de_deroulement"
    dep_ids = number(df[dep_col])
    dep_region = df.groupby(dep_col)["region_principale_de_deroulement"].agg(mode)
    tables["departement"] = pd.DataFrame(
        {
            "id_departement": list(dep_ids.values()),
            "departement": list(dep_ids.keys()),
            "id_region": [region_ids.get(dep_region[d]) for d in dep_ids],
        }
    )

    # commune: keyed on the INSEE code. A row without a code but whose name and
    # department match a known commune gets that commune's code; other rows that
    # still name a commune are keyed on "name|department".
    name_col = "commune_principale_de_deroulement"
    known = df.dropna(subset=["code_insee_commune", name_col])
    by_name = known.groupby([name_col, dep_col], dropna=False)["code_insee_commune"].agg(mode)
    filled = [
        insee if pd.notna(insee) else by_name.get((name, dep), pd.NA) if pd.notna(name) else pd.NA
        for insee, name, dep in zip(df["code_insee_commune"], df[name_col], df[dep_col], strict=True)
    ]
    df["code_insee_commune"] = filled
    df["commune_key"] = [
        insee if pd.notna(insee) else (f"{name}|{dep}" if pd.notna(name) else pd.NA)
        for insee, name, dep in zip(df["code_insee_commune"], df[name_col], df[dep_col], strict=True)
    ]
    commune_ids = number(df["commune_key"])
    grouped = df.dropna(subset=["commune_key"]).groupby("commune_key")
    communes = grouped.agg(
        commune=(name_col, mode),
        code_postal_commune=("code_postal_de_la_commune_principale_de_deroulement", mode),
        code_insee_commune=("code_insee_commune", mode),
        departement=(dep_col, mode),
    )
    tables["commune"] = pd.DataFrame(
        {
            "id_commune": [commune_ids[k] for k in communes.index],
            "commune": communes["commune"].values,
            "code_postal_commune": communes["code_postal_commune"].values,
            "code_insee_commune": communes["code_insee_commune"].values,
            "id_departement": [dep_ids.get(d) for d in communes["departement"]],
        }
    ).sort_values("id_commune")
    df["id_commune"] = df["commune_key"].map(commune_ids)

    # adresse: street fields + commune; rows without any street field have no address.
    has_address = df[ADDRESS_COLUMNS].notna().any(axis=1)
    df["adresse_key"] = pd.Series(pd.NA, index=df.index, dtype=object)
    df.loc[has_address, "adresse_key"] = (
        df.loc[has_address, ADDRESS_COLUMNS + ["commune_key"]].fillna("").astype(str).agg("\x1f".join, axis=1)
    )
    adresse_ids = number(df["adresse_key"])
    grouped = df.dropna(subset=["adresse_key"]).groupby("adresse_key")
    addresses = grouped.agg(
        numero_de_voie=("numero_de_voie", "first"),
        type_de_voie=("type_de_voie_rue_avenue_boulevard_etc", "first"),
        nom_de_la_voie=("nom_de_la_voie", "first"),
        complement_d_adresse=("complement_d_adresse_facultatif", "first"),
        geocodage=("geocodage_xy", mode),
        id_commune=("id_commune", "first"),
    )
    addresses.insert(0, "id_adresse", [adresse_ids[k] for k in addresses.index])
    tables["adresse"] = addresses.reset_index(drop=True).sort_values("id_adresse")
    df["id_adresse"] = df["adresse_key"].map(adresse_ids)

    # categorie
    categorie_ids = number(df["discipline_dominante"])
    tables["categorie"] = pd.DataFrame(
        {"id_categorie": list(categorie_ids.values()), "discipline_dominante": list(categorie_ids.keys())}
    )
    df["id_categorie"] = df["discipline_dominante"].map(categorie_ids)

    # sous_categorie: distinct, non-empty combinations of the six sub-category
    # columns, attached to their dominant discipline.
    sub_src = list(SUBCATEGORY_COLUMNS)
    subs = df.loc[df[sub_src].notna().any(axis=1), sub_src + ["discipline_dominante"]].drop_duplicates()
    subs = subs.assign(_key=subs.fillna("").astype(str).agg("\x1f".join, axis=1)).sort_values("_key")
    tables["sous_categorie"] = pd.concat(
        [
            pd.DataFrame({"id_sous_categorie": range(1, len(subs) + 1)}),
            subs[sub_src].rename(columns=SUBCATEGORY_COLUMNS).reset_index(drop=True),
            pd.DataFrame({"id_categorie": subs["discipline_dominante"].map(categorie_ids).values}),
        ],
        axis=1,
    )

    # organisation (EPCI), keyed on its code; label = most frequent spelling.
    epci = "code_insee_epci_collage_en_valeur"
    organisation_ids = number(df[epci])
    labels = df.groupby(epci)["libelle_epci_collage_en_valeur"].agg(mode)
    tables["organisation"] = pd.DataFrame(
        {
            "id_organisation": list(organisation_ids.values()),
            "code_insee_epci": list(organisation_ids.keys()),
            "libelle_insee_epci": [labels.get(k) for k in organisation_ids],
        }
    )
    df["id_organisation"] = df[epci].map(organisation_ids)

    # festival: one row per source row. The source "identifiant" is not unique,
    # so festivals get their own surrogate key (source row order).
    df["id_festival"] = range(1, len(df) + 1)
    tables["festival"] = pd.DataFrame(
        {
            "id_festival": df["id_festival"],
            "nom_festival": df["nom_du_festival"],
            # The published snapshot has no e-mail column (privacy): the column stays empty.
            "e_mail": df["adresse_e_mail"] if "adresse_e_mail" in df else "",
            "date_creation": df["annee_de_creation_du_festival"],
            "site_web": df["site_internet_du_festival"],
            "periode_principale_de_deroulement_du_festival": df["periode_principale_de_deroulement_du_festival"],
            "id_commune": df["id_commune"],
            "id_adresse": df["id_adresse"],
            "id_organisation": df["id_organisation"],
        }
    )

    # association tables: one row per (festival, linked entity), duplicates removed.
    for table, column in [
        ("festival_categorie", "id_categorie"),
        ("festival_organisation", "id_organisation"),
        ("festival_commune", "id_commune"),
        ("festival_adresse", "id_adresse"),
    ]:
        links = df[["id_festival", column]].dropna().drop_duplicates()
        tables[table] = links.sort_values(["id_festival", column]).reset_index(drop=True)

    # Integer columns as nullable integers (no '1.0' in the CSV files).
    for name, table in tables.items():
        for col in table.columns:
            if col.startswith("id_"):
                table[col] = pd.array(table[col], dtype="Int64")
        tables[name] = table.reset_index(drop=True)
    return {name: tables[name] for name in TABLES}


def write_tables(tables: dict[str, pd.DataFrame], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(output / f"{name}.csv", index=False, encoding="utf-8", lineterminator="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    raw = read_raw(args.input)
    tables = build_tables(raw)
    write_tables(tables, args.output)
    print(f"{len(raw)} source rows -> {args.output}")
    for name, table in tables.items():
        print(f"  {name:<22} {len(table):>6} rows")


if __name__ == "__main__":
    main()
