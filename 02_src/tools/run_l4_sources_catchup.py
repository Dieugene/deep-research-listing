"""
Catch-up script: re-process L4 record sources for jurisdictions that may have missed
the Step 3 enrichment in the main pipeline (e.g., if run_pipeline.py was halted early).

Usage:
    cd 02_src
    python tools/run_l4_sources_catchup.py

Processes all jurisdictions in COUNTRIES_DIR.
"""
import sys
from pathlib import Path

# Ensure project src is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.level4_postprocess import process_level4_record_sources
from pipeline.logging_setup import get_logger
from pipeline.config import LOGS_DIR

import datetime

logger = get_logger(
    "l4_sources_catchup",
    LOGS_DIR / f"l4_sources_catchup_{datetime.date.today()}.log"
)


def main() -> None:
    """Re-process all jurisdictions for L4 record sources."""
    logger.info("========== L4 Sources Catch-up Start ==========")
    logger.info("Processing all jurisdictions for record sources enrichment")

    try:
        # None = process all jurisdictions from COUNTRIES_DIR
        process_level4_record_sources(jurisdictions=None)
        logger.info("========== L4 Sources Catch-up Complete ==========")
    except Exception as e:
        logger.error("========== L4 Sources Catch-up FAILED ==========")
        logger.error("Error: %s", e)
        raise


if __name__ == "__main__":
    main()
