"""
FastAPI application entry point for the Listing Requirements API.

Start the server:
    cd 02_src/interface/backend
    uvicorn main:app --reload --port 8000

Or from project root:
    venv/Scripts/uvicorn 02_src.interface.backend.main:app --reload
"""
import logging
import sys
from pathlib import Path

# Ensure the backend package is importable when run directly
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import CORS_ORIGINS
from routers import cells, jurisdictions, parameters, venues

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Listing Requirements API",
    version="1.0",
    description=(
        "REST API for accessing structured data about securities listing requirements "
        "across jurisdictions (UK, Hong Kong). Backed by pipeline output files."
    ),
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(jurisdictions.router, prefix="/api")
app.include_router(venues.router, prefix="/api")
app.include_router(cells.router, prefix="/api")
app.include_router(parameters.router, prefix="/api")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["meta"])
def health():
    """Simple liveness probe."""
    return {"status": "ok", "version": "1.0"}
