"""Download the pinned raw dataset and store it as data/festivals-global-festivals-pl.csv.gz.

Source: "Liste des festivals en France", Ministère de la Culture, on data.gouv.fr
(https://www.data.gouv.fr/datasets/liste-des-festivals-en-france), Licence Ouverte 2.0.
The downloaded file is checked against its SHA-256 so the snapshot stays reproducible; pass
--url and --no-check to try a newer upload. The contact e-mail column is removed before the
snapshot is written: it is not needed by the project and some addresses are personal.

Usage: python scripts/download_data.py [--url URL] [--no-check]
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import re
import urllib.request
from pathlib import Path

URL = (
    "https://static.data.gouv.fr/resources/liste-des-festivals-en-france/"
    "20250827-132958/festivals-global-festivals-pl.csv"
)
SHA256 = "d7289702cd5fc5f6ecb53d6b11dea499c06b2c61a836cc59f5a2fc1fb1734c27"
TARGET = Path(__file__).resolve().parents[1] / "data" / "festivals-global-festivals-pl.csv.gz"
BOM = "﻿"

# Contact e-mails of the festivals, some of them personal: never stored in this repository.
# Some e-mails were also typed in other columns (mostly the website one): they are erased too.
PRIVATE_COLUMNS = ("Adresse e-mail",)
EMAIL = re.compile(r"[\w.+-]+\s*@\s*[\w-]+(?:\.[\w-]+)+")  # spaces around @: typing mistakes


def scrub(value: str) -> str:
    """Erase e-mail addresses from a cell; a cell left with only a URL scheme becomes empty.
    Cells without an e-mail address are returned unchanged."""
    if not EMAIL.search(value):
        return value
    cleaned = EMAIL.sub("", value).strip(" ,;")
    return "" if cleaned in ("", "http://", "https://") else cleaned


def drop_columns(content: bytes, names: tuple[str, ...]) -> bytes:
    """Same CSV without the given columns and without any e-mail address (UTF-8, `;`-separated,
    byte-order marks removed)."""
    text = content.decode("utf-8").lstrip(BOM)
    rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=";"))
    keep = [i for i, name in enumerate(rows[0]) if name.lstrip(BOM) not in names]
    if len(keep) == len(rows[0]):
        raise SystemExit(f"columns not found: {names}")
    out = io.StringIO(newline="")
    writer = csv.writer(out, delimiter=";", lineterminator="\n")
    writer.writerow([rows[0][i].lstrip(BOM) for i in keep])
    for row in rows[1:]:
        writer.writerow([scrub(row[i]) for i in keep])
    return out.getvalue().encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=URL)
    parser.add_argument("--no-check", action="store_true", help="skip the SHA-256 check")
    args = parser.parse_args()

    request = urllib.request.Request(args.url, headers={"User-Agent": "festivals-database/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        content = response.read()
    digest = hashlib.sha256(content).hexdigest()
    if not args.no_check and digest != SHA256:
        raise SystemExit(f"checksum mismatch: got {digest}, expected {SHA256}")

    content = drop_columns(content, PRIVATE_COLUMNS)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    # mtime=0 and no file name: the same CSV always gives the same .gz bytes.
    with open(TARGET, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
        gz.write(content)
    print(f"downloaded sha256 {digest}; {len(content):,} bytes without {', '.join(PRIVATE_COLUMNS)} -> {TARGET}")


if __name__ == "__main__":
    main()
