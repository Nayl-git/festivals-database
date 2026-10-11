"""Checks on the tables produced by etl/build_tables.py from the pinned snapshot."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from etl.build_tables import DEFAULT_INPUT, TABLES, build_tables, read_raw, write_tables

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "sql" / "01_schema.sql").read_text(encoding="utf-8")

PRIMARY_KEYS = {
    "region": ["id_region"],
    "departement": ["id_departement"],
    "commune": ["id_commune"],
    "adresse": ["id_adresse"],
    "categorie": ["id_categorie"],
    "sous_categorie": ["id_sous_categorie"],
    "organisation": ["id_organisation"],
    "festival": ["id_festival"],
    "festival_categorie": ["id_festival", "id_categorie"],
    "festival_organisation": ["id_festival", "id_organisation"],
    "festival_commune": ["id_festival", "id_commune"],
    "festival_adresse": ["id_festival", "id_adresse"],
}

# (child table, column, parent table) for every FOREIGN KEY of sql/01_schema.sql
FOREIGN_KEYS = [
    ("departement", "id_region", "region"),
    ("commune", "id_departement", "departement"),
    ("adresse", "id_commune", "commune"),
    ("sous_categorie", "id_categorie", "categorie"),
    ("festival", "id_adresse", "adresse"),
    ("festival", "id_commune", "commune"),
    ("festival", "id_organisation", "organisation"),
    ("festival_categorie", "id_festival", "festival"),
    ("festival_categorie", "id_categorie", "categorie"),
    ("festival_organisation", "id_festival", "festival"),
    ("festival_organisation", "id_organisation", "organisation"),
    ("festival_commune", "id_festival", "festival"),
    ("festival_commune", "id_commune", "commune"),
    ("festival_adresse", "id_festival", "festival"),
    ("festival_adresse", "id_adresse", "adresse"),
]

# Row counts for the pinned snapshot (data.gouv.fr upload of 2025-08-27).
EXPECTED_ROWS = {
    "region": 22,
    "departement": 110,
    "commune": 3114,
    "adresse": 4224,
    "categorie": 6,
    "sous_categorie": 1735,
    "organisation": 1046,
    "festival": 7283,
    "festival_categorie": 7283,
    "festival_organisation": 7247,
    "festival_commune": 7264,
    "festival_adresse": 4345,
}


def schema_columns() -> dict[str, list[str]]:
    """Column names of each CREATE TABLE in sql/01_schema.sql, in order."""
    columns = {}
    for name, body in re.findall(r"CREATE TABLE (\w+) \((.*?)\n\);", SCHEMA, flags=re.S):
        lines = [line.strip() for line in body.strip().splitlines()]
        columns[name] = [
            line.split()[0] for line in lines if line and not line.startswith(("PRIMARY KEY", "FOREIGN KEY"))
        ]
    return columns


@pytest.fixture(scope="session")
def raw() -> pd.DataFrame:
    return read_raw(DEFAULT_INPUT)


@pytest.fixture(scope="session")
def tables(raw, tmp_path_factory) -> dict[str, pd.DataFrame]:
    """Build the tables, write them, and read the CSV files back as PostgreSQL would."""
    out = tmp_path_factory.mktemp("tables")
    write_tables(build_tables(raw), out)
    return {
        name: pd.read_csv(out / f"{name}.csv", dtype=str, keep_default_na=False).replace("", pd.NA) for name in TABLES
    }


def as_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series).astype("Int64")


def test_snapshot_shape(raw):
    # 30 columns in the source, minus the contact e-mail column removed for privacy.
    assert raw.shape == (7283, 29)


def test_snapshot_has_no_email_address(raw):
    assert not any("mail" in column.lower() for column in raw.columns)
    email = r"[\w.+-]+\s*@\s*[\w-]+(?:\.[\w-]+)+"
    for column in raw.columns:
        assert not raw[column].astype(str).str.contains(email, regex=True).any(), column


def test_every_table_matches_the_schema(tables):
    columns = schema_columns()
    assert list(columns) == TABLES
    for name in TABLES:
        assert list(tables[name].columns) == columns[name], name


@pytest.mark.parametrize("name", TABLES)
def test_row_counts(tables, name):
    assert len(tables[name]) == EXPECTED_ROWS[name]


def test_no_festival_lost(raw, tables):
    festival = tables["festival"]
    assert len(festival) == len(raw)
    assert sorted(festival["nom_festival"]) == sorted(raw["nom_du_festival"])
    # every festival keeps its discipline
    assert set(as_int(tables["festival_categorie"]["id_festival"])) == set(as_int(festival["id_festival"]))


@pytest.mark.parametrize("name", TABLES)
def test_primary_key_unique_and_not_null(tables, name):
    key = tables[name][PRIMARY_KEYS[name]]
    assert key.notna().all().all()
    assert not key.duplicated().any()


@pytest.mark.parametrize(("child", "column", "parent"), FOREIGN_KEYS)
def test_foreign_keys_resolve(tables, child, column, parent):
    values = set(as_int(tables[child][column]).dropna())
    parent_ids = set(as_int(tables[parent][PRIMARY_KEYS[parent][0]]))
    assert values, f"{child}.{column} is empty"
    assert values <= parent_ids, sorted(values - parent_ids)[:10]


@pytest.mark.parametrize(
    ("table", "column"),
    [
        ("festival_organisation", "id_organisation"),
        ("festival_commune", "id_commune"),
        ("festival_adresse", "id_adresse"),
    ],
)
def test_association_tables_agree_with_festival(tables, table, column):
    festival = tables["festival"][["id_festival", column]].dropna()
    expected = set(map(tuple, festival.apply(as_int).to_numpy().tolist()))
    actual = set(map(tuple, tables[table][["id_festival", column]].apply(as_int).to_numpy().tolist()))
    assert actual == expected


@pytest.mark.parametrize(
    ("table", "column"),
    [
        ("region", "region"),
        ("departement", "departement"),
        ("categorie", "discipline_dominante"),
        ("organisation", "code_insee_epci"),
        ("commune", "code_insee_commune"),
    ],
)
def test_entities_are_deduplicated(tables, table, column):
    values = tables[table][column].dropna()
    assert not values.duplicated().any()


def test_no_literal_null_strings(tables):
    for name, table in tables.items():
        assert not (table == "null").any().any(), name


def test_codes_are_cleaned(tables):
    insee = tables["commune"]["code_insee_commune"].dropna()
    assert insee.str.fullmatch(r"[0-9AB]{5}").all()
    assert not (tables["commune"]["code_postal_commune"] == "#N/A").any()
    # 1,043 of the 1,046 EPCI codes are 9-digit SIREN numbers; the other three are
    # kept as published ("ZZZZZZZZZ" = no EPCI, plus two malformed codes).
    assert tables["organisation"]["code_insee_epci"].str.fullmatch(r"\d{9}").sum() == 1043


def test_duplicate_source_identifiers_do_not_break_keys(raw):
    # The 2024 association tables were keyed on the source "identifiant",
    # which is not unique: this is what made their load fail.
    assert raw["identifiant"].duplicated().sum() == 13
    sample = raw.head(3).copy()
    sample["identifiant"] = "FEST_DUPLICATE"
    built = build_tables(sample)
    assert len(built["festival"]) == 3
    for name in ["festival_categorie", "festival_organisation", "festival_commune", "festival_adresse"]:
        assert not built[name].duplicated().any()


def test_dimension_ids_do_not_depend_on_row_order(raw):
    first = build_tables(raw)
    shuffled = build_tables(raw.sample(frac=1, random_state=0))
    for name in ["region", "departement", "commune", "adresse", "categorie", "sous_categorie", "organisation"]:
        pd.testing.assert_frame_equal(first[name], shuffled[name], check_index_type=False)


def test_build_is_deterministic(raw, tmp_path):
    write_tables(build_tables(raw), tmp_path / "a")
    write_tables(build_tables(raw), tmp_path / "b")
    for name in TABLES:
        assert (tmp_path / "a" / f"{name}.csv").read_bytes() == (tmp_path / "b" / f"{name}.csv").read_bytes()
