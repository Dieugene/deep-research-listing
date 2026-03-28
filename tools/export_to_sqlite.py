"""
Listing Research — JSON → SQLite export

Walk all .json files under 03_data/countries/ and load them into a single
SQLite database.  Idempotent — safe to re-run when new jurisdictions are added.

Usage:
    python tools/export_to_sqlite.py [--db PATH] [--data PATH]

Defaults (relative to the project root, i.e. the parent of this script's dir):
    --db   02_src/interface/listing_research.db
    --data 03_data/countries
"""

import argparse
import io
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Reconfigure stdout/stderr to UTF-8 so non-ASCII paths print correctly on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Resolve project root: this script lives in <project_root>/tools/
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

DEFAULT_DB = PROJECT_ROOT / "02_src" / "interface" / "listing_research.db"
DEFAULT_DATA = PROJECT_ROOT / "03_data" / "countries"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
DDL = """
CREATE TABLE IF NOT EXISTS json_files (
    path     TEXT PRIMARY KEY,
    content  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

PROGRESS_EVERY = 50


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export all JSON files from the countries data directory into SQLite."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        metavar="PATH",
        help=f"Path to the output SQLite database (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA,
        metavar="PATH",
        help=f"Root directory to scan for .json files (default: {DEFAULT_DATA})",
    )
    return parser.parse_args()


def format_bytes(n: int) -> str:
    """Return a human-readable file size string."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def collect_json_files(data_dir: Path) -> list[Path]:
    """Return all .json files under data_dir, sorted for deterministic order."""
    return sorted(data_dir.rglob("*.json"))


def run_export(data_dir: Path, db_path: Path) -> int:
    """
    Main export logic.

    Returns:
        0 on success, 1 on fatal error.
    """
    print("Listing Research -- JSON -> SQLite export")
    print(f"Data dir : {data_dir}")
    print(f"DB       : {db_path}")
    print()

    # Validate data directory
    if not data_dir.exists():
        print(f"ERROR: Data directory does not exist: {data_dir}", file=sys.stderr)
        return 1
    if not data_dir.is_dir():
        print(f"ERROR: Data path is not a directory: {data_dir}", file=sys.stderr)
        return 1

    # Ensure DB parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Collect files first so we can show total count
    print("Scanning...")
    all_files = collect_json_files(data_dir)

    # Also include institutional data files (shared across jurisdictions)
    institutional_dir = data_dir.parent / "institutional"
    if institutional_dir.is_dir():
        inst_files = sorted(institutional_dir.glob("*.json"))
        if inst_files:
            print(f"  + {len(inst_files)} institutional files from {institutional_dir}")
            all_files.extend(inst_files)

    total = len(all_files)
    if total == 0:
        print("No .json files found — nothing to do.")
        return 0

    # Open DB connection and apply schema
    try:
        con = sqlite3.connect(db_path)
    except sqlite3.Error as exc:
        print(f"ERROR: Cannot open database {db_path}: {exc}", file=sys.stderr)
        return 1

    try:
        with con:
            con.executescript(DDL)
            # Remove stale rows so renamed/deleted files don't linger
            con.execute("DELETE FROM json_files")

        # Track counts
        processed = 0
        upserted = 0
        skipped = 0

        for idx, file_path in enumerate(all_files, start=1):
            # Compute relative path with forward slashes
            try:
                rel = file_path.relative_to(data_dir)
            except ValueError:
                try:
                    rel = file_path.relative_to(data_dir.parent)
                except ValueError:
                    print(
                        f"WARNING: Cannot compute relative path for {file_path} — skipping.",
                        file=sys.stderr,
                    )
                    skipped += 1
                    continue

            rel_str = rel.as_posix()  # always forward slashes

            # Read file content
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                print(
                    f"WARNING: Cannot read {rel_str} ({exc}) — skipping.",
                    file=sys.stderr,
                )
                skipped += 1
                continue

            # Upsert into DB
            try:
                with con:
                    con.execute(
                        "INSERT OR REPLACE INTO json_files (path, content) VALUES (?, ?)",
                        (rel_str, content),
                    )
                upserted += 1
            except sqlite3.Error as exc:
                print(
                    f"WARNING: DB error for {rel_str} ({exc}) — skipping.",
                    file=sys.stderr,
                )
                skipped += 1
                continue

            processed += 1

            # Progress report
            if processed % PROGRESS_EVERY == 0:
                print(f"  [{processed}/{total}] {rel_str}")

        # Write meta
        exported_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        with con:
            con.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("exported_at", exported_at),
            )
            con.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("file_count", str(upserted)),
            )

        # DB size
        db_size_bytes = db_path.stat().st_size

        print()
        print("Done.")
        print(f"  Files processed : {processed}")
        if skipped:
            print(f"  Skipped (errors): {skipped}")
        print(f"  Inserted/updated: {upserted}")
        print(f"  DB size         : {format_bytes(db_size_bytes)}")
        print(f"  Exported at     : {exported_at}")

    except Exception as exc:  # pylint: disable=broad-except
        print(f"ERROR: Unexpected error during export: {exc}", file=sys.stderr)
        return 1
    finally:
        con.close()

    return 0


def main() -> None:
    args = parse_args()
    sys.exit(run_export(data_dir=args.data.resolve(), db_path=args.db.resolve()))


if __name__ == "__main__":
    main()
