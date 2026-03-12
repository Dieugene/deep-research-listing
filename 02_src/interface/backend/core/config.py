"""
Backend configuration: paths to data directories.
Does NOT import from pipeline.* — paths computed independently.
"""
from pathlib import Path

# Resolve from: core/config.py -> core/ -> backend/ -> interface/ -> 02_src/ -> project root
ROOT_DIR = Path(__file__).resolve().parents[4]

DATA_DIR = ROOT_DIR / "03_data"
COUNTRIES_DIR = DATA_DIR / "countries"
LOGS_DIR = ROOT_DIR / "04_logs"

# CORS origins allowed by the API
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
]
