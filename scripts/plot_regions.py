"""Draw docs/festivals_per_region.png (query 1) from the CSV files of etl/build_tables.py.

Same joins as query 1 of sql/03_queries.sql (festival -> commune -> departement ->
region), done with pandas so no database is needed.

Usage: python scripts/plot_regions.py [--tables build/tables] [--output docs/festivals_per_region.png]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

SURFACE = "#fcfcfb"
BAR = "#2a78d6"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"


def festivals_per_region(tables: Path) -> pd.Series:
    read = lambda name: pd.read_csv(tables / f"{name}.csv")  # noqa: E731
    joined = (
        read("festival")
        .merge(read("commune"), on="id_commune")
        .merge(read("departement"), on="id_departement")
        .merge(read("region"), on="id_region")
    )
    return joined.groupby("region")["id_festival"].count().sort_values()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tables", type=Path, default=ROOT / "build" / "tables")
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "festivals_per_region.png")
    args = parser.parse_args()

    counts = festivals_per_region(args.tables)
    fig, ax = plt.subplots(figsize=(8, 6.4), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    bars = ax.barh(counts.index, counts.values, height=0.62, color=BAR, zorder=2)
    for bar, value in zip(bars, counts.values, strict=True):
        ax.text(
            bar.get_width() + 12,
            bar.get_y() + bar.get_height() / 2,
            f"{value:,}",
            va="center",
            ha="left",
            fontsize=8.5,
            color=INK_SECONDARY,
        )
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color("#c3c2b7")
    ax.tick_params(axis="x", colors=MUTED, labelsize=8.5, length=0)
    ax.tick_params(axis="y", colors=INK, labelsize=9, length=0)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.set_xlim(0, counts.max() * 1.12)
    fig.suptitle("Festivals per region", x=0.02, ha="left", fontsize=13, color=INK, fontweight="bold")
    fig.text(
        0.02,
        0.925,
        f"{counts.sum():,} festivals located through their commune · data.gouv.fr, upload of 27 Aug 2025",
        ha="left",
        fontsize=9,
        color=INK_SECONDARY,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.935))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, facecolor=SURFACE, metadata={"Software": None})
    print(f"{args.output} ({counts.sum()} festivals, {len(counts)} regions)")


if __name__ == "__main__":
    main()
