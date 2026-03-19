"""
Catch-up script: enrich existing L3 cell directory files with parallel_output
and citations from _parallel_raw source files.

The original postprocess_l3 disaggregation only copied `content` into cell dirs,
dropping `parallel_output` (with basis/citations) and top-level `citations`.
This script back-fills those fields.

Idempotent: skips files that already have parallel_output.

Usage:
    cd D:\\_workspace\\deep-research-listing
    PYTHONIOENCODING=utf-8 venv/Scripts/python.exe 02_src/tools/run_l3_postprocess_enrich_catchup.py [--dry-run]
"""

import argparse
import io
import json
import os
import sys
import tempfile
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "02_src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline.config import COUNTRIES_DIR, INSTRUMENT_CLASSES  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_json_atomic(path: Path, data: dict) -> None:
    """Write JSON atomically via tempfile + os.replace."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, str(path))
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _parse_raw_filename(filename: str):
    """
    Parse _parallel_raw filename like
      'Australian_Securities_Exchange_equity_3A_raw.json'
    Returns (instrument_class, query_type) or None.
    """
    stem = filename
    if stem.endswith(".json"):
        stem = stem[:-5]
    if stem.endswith("_raw"):
        stem = stem[:-4]
    # Last part is query_type (3A/3B/3C)
    parts = stem.rsplit("_", 1)
    if len(parts) != 2:
        return None
    prefix, query_type = parts
    if query_type not in ("3A", "3B", "3C"):
        return None
    # Find instrument_class
    instrument_class = None
    for ic in sorted(INSTRUMENT_CLASSES, key=len, reverse=True):
        if prefix.endswith(f"_{ic}"):
            instrument_class = ic
            break
    if instrument_class is None:
        return None
    return instrument_class, query_type


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def enrich_cell_dirs(dry_run: bool = False) -> None:
    enriched = 0
    skipped = 0
    errors = 0

    for country_dir in sorted(COUNTRIES_DIR.iterdir()):
        if not country_dir.is_dir():
            continue
        l3 = country_dir / "level_3"
        if not l3.exists():
            continue

        for venue_dir in sorted(l3.iterdir()):
            if not venue_dir.is_dir():
                continue
            par_raw = venue_dir / "_parallel_raw"
            if not par_raw.exists():
                continue

            # Build index: (instrument_class, query_type) -> parallel_raw data
            par_index: dict[tuple[str, str], dict] = {}
            for pf in par_raw.glob("*_raw.json"):
                parsed = _parse_raw_filename(pf.name)
                if parsed is None:
                    continue
                ic, qt = parsed
                try:
                    pd = _load_json(pf)
                except Exception as e:
                    print(f"  ERROR reading {pf}: {e}")
                    errors += 1
                    continue
                par_index[(ic, qt)] = pd

            if not par_index:
                continue

            # Enrich cell dirs
            for cell_dir in sorted(venue_dir.iterdir()):
                if not cell_dir.is_dir() or cell_dir.name == "_parallel_raw":
                    continue
                for raw_name in ("3A_raw.json", "3B_raw.json", "3C_raw.json"):
                    cell_file = cell_dir / raw_name
                    if not cell_file.exists():
                        continue
                    try:
                        cell_data = _load_json(cell_file)
                    except Exception as e:
                        print(f"  ERROR reading {cell_file}: {e}")
                        errors += 1
                        continue

                    if cell_data.get("parallel_output"):
                        skipped += 1
                        continue

                    ic = cell_data.get("instrument_class", "")
                    qt = cell_data.get("query_type", "")
                    par_data = par_index.get((ic, qt))
                    if not par_data:
                        continue

                    cell_data["parallel_output"] = par_data.get("parallel_output", {})
                    citations = par_data.get("citations", [])
                    if citations:
                        cell_data["citations"] = citations

                    if dry_run:
                        print(f"  [DRY-RUN] Would enrich {cell_file}")
                    else:
                        _save_json_atomic(cell_file, cell_data)
                        print(f"  Enriched {cell_file}")
                    enriched += 1

    print(f"\nDone. Enriched: {enriched}, Skipped (already have parallel_output): {skipped}, Errors: {errors}")


def main():
    parser = argparse.ArgumentParser(description="Enrich L3 cell dirs with parallel_output + citations")
    parser.add_argument("--dry-run", action="store_true", help="Do not write files, just report")
    args = parser.parse_args()

    print("L3 Postprocess Enrich Catchup")
    print("=" * 50)
    enrich_cell_dirs(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
