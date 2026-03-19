"""
Task 014: Source type classification.
Adds type field (legislation/rulebook/government/consultation/research/other)
to source objects based on URL domain analysis.

Task 020: L3 citation type classification + "Fetched web page" title fix.
"""
import json
import os
import tempfile
import urllib.parse
import urllib.request
from html.parser import HTMLParser
import datetime
from pathlib import Path
from typing import Optional

from pipeline.config import COUNTRIES_DIR, LOGS_DIR
from pipeline.logging_setup import get_logger

logger = get_logger(
    "source_classifier",
    LOGS_DIR / f"source_classifier_{datetime.date.today()}.log"
)

_DOMAIN_TYPE_MAP = {
    # Legislation — official law databases
    "legislation.gov.uk": "legislation",
    "www.legislation.gov.uk": "legislation",
    "www.gesetze-im-internet.de": "legislation",
    "www.elegislation.gov.hk": "legislation",
    "www.legifrance.gouv.fr": "legislation",
    "sso.agc.gov.sg": "legislation",
    "www5.austlii.edu.au": "legislation",
    "www.austlii.edu.au": "legislation",
    "www.legislation.gov.au": "legislation",
    "eur-lex.europa.eu": "legislation",
    "assets.publishing.service.gov.uk": "government",

    # Rulebook — regulator handbooks and exchange listing rules
    "handbook.fca.org.uk": "rulebook",
    "rulebook.sgx.com": "rulebook",
    "docs.londonstockexchange.com": "rulebook",
    "en-rules.hkex.com.hk": "rulebook",
    "eservices.mas.gov.sg": "rulebook",

    # Exchange sites — listed because of listing rules → rulebook
    "www.euronext.com": "rulebook",
    "live.euronext.com": "rulebook",
    "www.asx.com.au": "rulebook",
    "www2.asx.com.au": "rulebook",
    "www.hkex.com.hk": "rulebook",
    "www.sgx.com": "rulebook",
    "www.deutsche-boerse.com": "rulebook",
    "www.cashmarket.deutsche-boerse.com": "rulebook",
    "live.deutsche-boerse.com": "rulebook",
    "cdn.cboe.com": "rulebook",
    "www.cboe.com": "rulebook",
    "www.londonstockexchange.com": "rulebook",
    "www.nsx.com.au": "rulebook",
    "ssx.sydney": "rulebook",
    "aquis.eu": "rulebook",
    "www.aquis.eu": "rulebook",
    "aqx-web-prod-s3-public-read.s3.eu-west-2.amazonaws.com": "rulebook",

    # Government/Regulatory bodies
    "www.fca.org.uk": "government",
    "www.bafin.de": "government",
    "www.mas.gov.sg": "government",
    "www.sfc.hk": "government",
    "www.asic.gov.au": "government",
    "download.asic.gov.au": "government",
    "asic.gov.au": "government",
    "www.amf-france.org": "government",
    "www.gov.uk": "government",
    "hmrc.gov.uk": "government",
    "www.hmrc.gov.uk": "government",
    "www.sec.gov": "government",
    "www.esma.europa.eu": "government",
    "esma.europa.eu": "government",

    # Research — international organizations, academia
    "www.oecd.org": "research",
    "data.worldbank.org": "research",
    "www.worldbank.org": "research",
    "www.bis.org": "research",
    "www.imf.org": "research",
    "imf.org": "research",
}


def classify_source_url(url: str) -> str:
    """
    Classify a source URL into: legislation/rulebook/government/consultation/research/other.
    Returns string type.

    Steps:
    1. Domain-based classification (primary) using _DOMAIN_TYPE_MAP.
    2. Path-based overrides (consultation, handbook).
    3. .gov. / .gov TLD pattern fallback.
    4. Default → "other".
    """
    if not url:
        return "other"

    parsed = urllib.parse.urlparse(url)
    netloc = parsed.netloc.lower()

    # Strip www. prefix to get a normalized domain for secondary lookup
    netloc_no_www = netloc.lstrip("www.") if netloc.startswith("www.") else netloc

    # Step 1: Domain-based classification — try exact netloc first, then www.-stripped
    source_type = _DOMAIN_TYPE_MAP.get(netloc) or _DOMAIN_TYPE_MAP.get(netloc_no_www)

    # Step 2: Path-based overrides
    path_lower = parsed.path.lower()
    query_lower = parsed.query.lower()
    full_path = path_lower + ("?" + query_lower if query_lower else "")

    if "consultation" in full_path:
        source_type = "consultation"
    elif "handbook" in full_path and source_type == "government":
        source_type = "rulebook"

    if source_type is not None:
        return source_type

    # Step 3: .gov. or .gov TLD patterns
    if ".gov." in netloc or netloc.endswith(".gov"):
        return "government"

    # Step 4: Default
    return "other"


def _load_json(path: Path) -> dict | None:
    """Load JSON from path, returning None on error."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("File not found: %s", path)
        return None
    except json.JSONDecodeError as exc:
        logger.error("JSON decode error in %s: %s", path, exc)
        return None


def _save_json(path: Path, data: dict) -> None:
    """Atomically write JSON to path (temp file + os.replace)."""
    content = json.dumps(data, ensure_ascii=False, indent=2)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def process_sources_in_data(data: dict) -> int:
    """
    Classify type for all items in data["sources"][].
    Returns count of sources updated.
    Idempotent: skips sources with existing non-empty type.
    """
    sources = data.get("sources")
    if not isinstance(sources, list):
        return 0

    updated = 0
    for source in sources:
        if not isinstance(source, dict):
            continue
        # Idempotency: skip if type already set and non-empty
        if source.get("type"):
            continue
        url = source.get("url", "")
        source["type"] = classify_source_url(url)
        updated += 1

    return updated


def process_source_types(jurisdictions: Optional[list[str]] = None) -> None:
    """
    Add type field to all sources in jurisdiction_card.json,
    venue_card.json, and level4.json.
    Idempotent.
    jurisdictions: list of name_ru; None = all.
    """
    if jurisdictions is None:
        # Discover all jurisdictions from COUNTRIES_DIR
        jurisdictions = [
            d.name for d in sorted(COUNTRIES_DIR.iterdir())
            if d.is_dir()
        ]

    for name_ru in jurisdictions:
        juris_dir = COUNTRIES_DIR / name_ru
        if not juris_dir.exists():
            logger.warning("Jurisdiction directory not found: %s — skipping", name_ru)
            continue

        # --- L1: jurisdiction_card.json ---
        l1_card = juris_dir / "level_1" / "jurisdiction_card.json"
        if l1_card.exists():
            data = _load_json(l1_card)
            if data is not None:
                count = process_sources_in_data(data)
                if count > 0:
                    _save_json(l1_card, data)
                    logger.info("[UPDATED] %s/jurisdiction_card — %d sources classified", name_ru, count)
                else:
                    logger.info("[SKIP] %s/jurisdiction_card — all sources already have type", name_ru)

        # --- L2: venue_card.json for each venue ---
        level2_dir = juris_dir / "level_2"
        if level2_dir.exists():
            for venue_dir in sorted(level2_dir.iterdir()):
                if not venue_dir.is_dir():
                    continue
                venue_card = venue_dir / "venue_card.json"
                if not venue_card.exists():
                    continue
                data = _load_json(venue_card)
                if data is None:
                    continue
                venue_key = data.get("venue_key", venue_dir.name)
                count = process_sources_in_data(data)
                if count > 0:
                    _save_json(venue_card, data)
                    logger.info("[UPDATED] %s/%s — %d sources classified", name_ru, venue_key, count)
                else:
                    logger.info("[SKIP] %s/%s — all sources already have type", name_ru, venue_key)

        # --- L4: level4.json ---
        l4_path = juris_dir / "level_4" / "level4.json"
        if l4_path.exists():
            data = _load_json(l4_path)
            if data is not None:
                count = process_sources_in_data(data)
                if count > 0:
                    _save_json(l4_path, data)
                    logger.info("[UPDATED] %s/level4 — %d sources classified", name_ru, count)
                else:
                    logger.info("[SKIP] %s/level4 — all sources already have type", name_ru)


# ---------------------------------------------------------------------------
# Task 020: L3 citation type classification
# ---------------------------------------------------------------------------

def _iter_l3_raw_files(jurisdictions: Optional[list[str]]):
    """
    Yield (raw_path, label) for all 3A/3B/3C_raw.json files under COUNTRIES_DIR.
    jurisdictions: list of country_dir.name (name_ru); None = all.
    label: human-readable identifier for logs, e.g. "GB/LSEG/cell_01/3A".
    """
    for country_dir in sorted(COUNTRIES_DIR.iterdir()):
        if not country_dir.is_dir():
            continue
        if jurisdictions is not None and country_dir.name not in jurisdictions:
            continue
        l3_root = country_dir / "level_3"
        if not l3_root.exists():
            continue
        for venue_dir in sorted(l3_root.iterdir()):
            if not venue_dir.is_dir():
                continue
            # Phase 2: _parallel_raw/*.json (may contain 3A/3B/3C in filename)
            parallel_raw_dir = venue_dir / "_parallel_raw"
            if parallel_raw_dir.exists():
                for raw_path in sorted(parallel_raw_dir.glob("*_raw.json")):
                    label = f"{country_dir.name}/{venue_dir.name}/_parallel_raw/{raw_path.name}"
                    yield raw_path, label
            # Phase 1: per-cell subdirectories
            cell_dirs = sorted(
                p for p in venue_dir.iterdir()
                if p.is_dir() and not p.name.startswith("_")
            )
            for cell_dir in cell_dirs:
                for qt in ("3A", "3B", "3C"):
                    raw_path = cell_dir / f"{qt}_raw.json"
                    if raw_path.exists():
                        label = f"{country_dir.name}/{venue_dir.name}/{cell_dir.name}/{qt}"
                        yield raw_path, label


def process_l3_citation_types(jurisdictions: Optional[list[str]] = None) -> None:
    """
    Add type field to all citations[] in 3A/3B/3C_raw.json files.
    Uses classify_source_url() to determine the type from the citation URL.
    Idempotent: skips citations that already have a non-empty type.
    jurisdictions: list of name_ru; None = all.
    """
    logger.info("=== L3 citation types: start (jurisdictions=%s) ===", jurisdictions)
    files_updated = 0
    files_skipped = 0

    for raw_path, label in _iter_l3_raw_files(jurisdictions):
        data = _load_json(raw_path)
        if data is None:
            continue

        citations = data.get("citations")
        if not isinstance(citations, list):
            logger.info("[SKIP] %s — no citations list", label)
            files_skipped += 1
            continue

        updated = 0
        for citation in citations:
            if not isinstance(citation, dict):
                continue
            # Idempotency: skip if type already set and non-empty
            if citation.get("type"):
                continue
            url = citation.get("url", "")
            citation["type"] = classify_source_url(url)
            updated += 1

        if updated > 0:
            _save_json(raw_path, data)
            logger.info("[UPDATED] %s — %d citations classified", label, updated)
            files_updated += 1
        else:
            logger.info("[SKIP] %s — already typed (%d citations)", label, len(citations))
            files_skipped += 1

    logger.info(
        "=== L3 citation types: done — %d files updated, %d skipped ===",
        files_updated, files_skipped,
    )


# ---------------------------------------------------------------------------
# Task 020: Fix "Fetched web page" titles
# ---------------------------------------------------------------------------

class _TitleParser(HTMLParser):
    """Minimal HTML parser that extracts <title> or og:title."""

    def __init__(self):
        super().__init__()
        self._in_title = False
        self.title = None

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            attrs_d = dict(attrs)
            if attrs_d.get("property") == "og:title" and self.title is None:
                self.title = attrs_d.get("content", "").strip() or None

    def handle_data(self, data):
        if self._in_title and self.title is None:
            self.title = data.strip() or None

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False


def _fetch_title(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch HTML from url and return page title, or None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read(65536).decode("utf-8", errors="replace")
        parser = _TitleParser()
        parser.feed(html)
        return parser.title
    except Exception:
        return None


def fix_fetched_web_page_titles(jurisdictions: Optional[list[str]] = None) -> None:
    """
    For all citations in 3A/3B/3C_raw.json where title == "Fetched web page"
    (case-insensitive), attempt to fetch the real page title via HTTP.
    Updates the citation in-place if a title is retrieved.
    Idempotent: only touches citations whose title is exactly the placeholder.
    jurisdictions: list of name_ru; None = all.
    """
    logger.info("=== L3 title fix: start (jurisdictions=%s) ===", jurisdictions)
    files_updated = 0
    files_skipped = 0

    for raw_path, label in _iter_l3_raw_files(jurisdictions):
        data = _load_json(raw_path)
        if data is None:
            continue

        citations = data.get("citations")
        if not isinstance(citations, list):
            files_skipped += 1
            continue

        # Collect citations that need fixing
        to_fix = [
            c for c in citations
            if isinstance(c, dict)
            and isinstance(c.get("title"), str)
            and c["title"].strip().lower() == "fetched web page"
        ]

        if not to_fix:
            logger.info("[SKIP] %s — no 'Fetched web page' titles", label)
            files_skipped += 1
            continue

        updated = 0
        for citation in to_fix:
            url = citation.get("url", "")
            new_title = _fetch_title(url)
            if new_title:
                citation["title"] = new_title
                updated += 1
            else:
                logger.warning("[TITLE-FETCH-FAIL] %s — could not resolve title for: %s", label, url)

        if updated > 0:
            _save_json(raw_path, data)
            logger.info("[UPDATED] %s — %d titles fixed (of %d placeholder)", label, updated, len(to_fix))
            files_updated += 1
        else:
            logger.info("[NO-CHANGE] %s — %d placeholder(s) but all fetch attempts failed", label, len(to_fix))
            files_skipped += 1

    logger.info(
        "=== L3 title fix: done — %d files updated, %d skipped/unchanged ===",
        files_updated, files_skipped,
    )
