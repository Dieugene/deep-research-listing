"""
Backend configuration: paths to data directories.
Does NOT import from pipeline.* — paths computed independently.
"""
from pathlib import Path

# Resolve from: core/config.py -> core/ -> backend/ -> interface/ -> 02_src/ -> project root
# In Docker the app lives at /app so only 2 parent levels exist; fall back to /app.
_parents = Path(__file__).resolve().parents
ROOT_DIR = _parents[4] if len(_parents) > 4 else _parents[-1]

DATA_DIR = ROOT_DIR / "03_data"
COUNTRIES_DIR = DATA_DIR / "countries"
LOGS_DIR = ROOT_DIR / "04_logs"

# CORS origins allowed by the API
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
]

import os
# Path to SQLite database. If set, backend uses SQLiteDataRepository instead of FileDataRepository.
DB_PATH: str | None = os.environ.get("DB_PATH")
