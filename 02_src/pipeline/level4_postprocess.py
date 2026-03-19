"""
Post-process level4.json: parse source strings and enrich with excerpts from top-level sources array.

For each record in problems, contradictions, parameters_as_tools, reforms:
- Parse the source string using em-dash separator: "Title — URL; Title — URL"
- Add sources[] list with {url, title, excerpts} for each entry
- Preserve original source field (idempotent: skip if sources[] already exists)
"""
import json
from pathlib import Path
from typing import Optional

from pipeline.config import COUNTRIES_DIR, LOGS_DIR, get_country_level4_dir
from pipeline.logging_setup import get_logger

import datetime

logger = get_logger(
    "level4_postprocess",
    LOGS_DIR / f"level4_postprocess_{datetime.date.today()}.log"
)


def _parse_source_entry(entry: str) -> dict:
    """
    Parse a single 'Title — URL' string into {url, title}.

    Separator: ' — ' (space + em dash + space)
    Handles:
      - 'Title — URL' -> {url, title}
      - URLs without titles (fallback)
      - Non-URL entries (fallback)
    """
    sep = " \u2014 "  # em dash with spaces
    entry = entry.strip()

    if sep in entry:
        # Split from right to handle titles with em dashes
        title, url = entry.rsplit(sep, 1)
        return {"url": url.strip(), "title": title.strip()}
    elif entry.startswith("http"):
        # Fallback: no title, just URL
        return {"url": entry, "title": entry}
    else:
        # Fallback: non-URL string
        return {"url": "", "title": entry}


def _parse_source_string(source_str: str) -> list[dict]:
    """
    Parse 'Title — URL; Title — URL' string into list of {url, title} dicts.

    Separator between entries: '; ' (semicolon + space)
    """
    if not source_str or not source_str.strip():
        return []

    entries = source_str.split("; ")
    return [_parse_source_entry(e) for e in entries if e.strip()]


def _enrich_with_top_sources(
    parsed: list[dict], top_sources: list[dict]
) -> list[dict]:
    """
    Add excerpts from top-level sources[] by URL match.

    Args:
        parsed: list of {url, title} dicts (from _parse_source_string)
        top_sources: top-level sources[] array with {url, title, field, excerpts}

    Returns:
        list of {url, title, excerpts} dicts
    """
    # Build URL lookup from top-level sources
    top_by_url = {s.get("url", ""): s for s in top_sources}

    result = []
    for entry in parsed:
        url = entry.get("url", "")
        title = entry.get("title", "")

        # Look up excerpts from top-level source
        top = top_by_url.get(url, {})
        excerpts = top.get("excerpts", [])

        result.append({
            "url": url,
            "title": title,
            "excerpts": excerpts
        })

    return result


def _process_section(
    section: list[dict],
    source_key: str,
    top_sources: list[dict]
) -> int:
    """
    Process a single section (problems, contradictions, parameters_as_tools, reforms).

    Args:
        section: list of record dicts
        source_key: field name containing source string (e.g., "source")
        top_sources: top-level sources[] array

    Returns:
        count of records enriched
    """
    count = 0
    for record in section:
        # Skip if already has non-empty sources[]
        if record.get("sources") and len(record.get("sources", [])) > 0:
            continue

        source_str = record.get(source_key, "")
        if not source_str:
            # No source to parse
            record["sources"] = []
            count += 1
            continue

        # Parse and enrich
        parsed = _parse_source_string(source_str)
        enriched = _enrich_with_top_sources(parsed, top_sources)
        record["sources"] = enriched
        count += 1

    return count


def process_level4_record_sources(jurisdictions: Optional[list[str]] = None) -> None:
    """
    For each level4.json: add sources[] to each record in problems/contradictions/
    parameters_as_tools/reforms. Idempotent: skips records that already have sources[].

    Args:
        jurisdictions: list of jurisdiction_ru names; if None, processes all
    """
    if jurisdictions is None:
        # Load all jurisdictions from COUNTRIES_DIR
        jurisdictions = [
            d.name for d in COUNTRIES_DIR.iterdir()
            if d.is_dir()
        ]

    logger.info("Processing %d jurisdiction(s) for L4 record sources", len(jurisdictions))

    for name_ru in jurisdictions:
        level4_dir = get_country_level4_dir(name_ru)
        level4_path = level4_dir / "level4.json"

        if not level4_path.exists():
            logger.warning("[SKIP] %s — level4.json not found", name_ru)
            continue

        try:
            with open(level4_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error("[ERROR] %s — failed to load: %s", name_ru, e)
            continue

        # Get top-level sources array for excerpts lookup
        top_sources = data.get("sources", [])

        # Process each section
        sections = {
            "problems": "source",
            "contradictions": "source",
            "parameters_as_tools": "source",
            "reforms": "source",
        }

        total_updated = 0
        for section_name, source_key in sections.items():
            section = data.get(section_name, [])
            if not section:
                continue

            count = _process_section(section, source_key, top_sources)
            total_updated += count

        # Check if any records were updated
        if total_updated == 0:
            logger.info("[SKIP] %s — all records already have sources[]", name_ru)
            continue

        # Save back to file
        try:
            with open(level4_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("[UPDATED] %s — %d records enriched", name_ru, total_updated)
        except Exception as e:
            logger.error("[ERROR] %s — failed to save: %s", name_ru, e)


# ---------------------------------------------------------------------------
# Task 013: Timeline labels and articulated_by normalization
# ---------------------------------------------------------------------------

_SECTIONS = ["problems", "contradictions", "parameters_as_tools", "reforms"]

_ARTICULATED_BY_VALID = {"government", "regulator", "academic", "market_participants", "exchange"}

_ARTICULATED_BY_MAP = {
    "government": "government",
    "regulator": "regulator",
    "academic": "academic",
    "market_participants": "market_participants",
    "exchange": "exchange",
    "industry": "market_participants",  # current non-standard value
}


def _get_record_text(record: dict, section_name: str) -> str:
    """Get the best text for label generation."""
    if section_name == "contradictions":
        return (record.get("resolution_ru") or record.get("resolution") or
                record.get("description_ru") or record.get("description") or "")
    elif section_name == "parameters_as_tools":
        return (record.get("parameter_description_ru") or
                record.get("parameter_description") or "")
    else:  # problems, reforms
        return record.get("description_ru") or record.get("description") or ""


def _load_level4(name_ru: str) -> tuple[Path, dict] | tuple[None, None]:
    """Load level4.json for a jurisdiction. Returns (path, data) or (None, None) on failure."""
    level4_dir = get_country_level4_dir(name_ru)
    level4_path = level4_dir / "level4.json"

    if not level4_path.exists():
        logger.warning("[SKIP] %s — level4.json not found", name_ru)
        return None, None

    try:
        with open(level4_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return level4_path, data
    except Exception as e:
        logger.error("[ERROR] %s — failed to load: %s", name_ru, e)
        return None, None


def _save_json_atomic(path: Path, data: dict) -> None:
    """Write JSON atomically: write to temp file then os.replace."""
    import os
    import tempfile

    tmp_path = path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        # Clean up temp file if replace failed
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def process_level4_labels(
    jurisdictions: list[str] | None = None,
    llm=None
) -> None:
    """
    Add label field (<=35 chars) to each record via LLM batch call.
    Idempotent: skips records that already have label.
    jurisdictions: list of name_ru; None = process all.
    llm: langchain LLM; created internally if None.
    """
    if jurisdictions is None:
        jurisdictions = [
            d.name for d in COUNTRIES_DIR.iterdir()
            if d.is_dir()
        ]

    logger.info("Processing %d jurisdiction(s) for L4 labels", len(jurisdictions))

    # Step 1: collect all (jurisdiction, path, data, section_name, record_index, text)
    # for records missing label
    pending = []  # list of (name_ru, path, data, section_name, record_idx)
    texts = []    # parallel list of texts to send to LLM

    jurisdiction_data: dict[str, tuple[Path, dict]] = {}

    for name_ru in jurisdictions:
        path, data = _load_level4(name_ru)
        if data is None:
            continue
        jurisdiction_data[name_ru] = (path, data)

        for section_name in _SECTIONS:
            section = data.get(section_name, [])
            for idx, record in enumerate(section):
                if record.get("label"):
                    continue  # already has label — skip
                text = _get_record_text(record, section_name)
                if not text:
                    continue  # no text to generate label from — skip
                pending.append((name_ru, section_name, idx))
                texts.append(text)

    if not pending:
        logger.info("No records need labels — all up to date")
        return

    logger.info("Generating labels for %d records via LLM batch", len(pending))

    # Step 2: create LLM if not passed
    if llm is None:
        from langchain_openai import ChatOpenAI
        from pipeline.config import LLM_FAST_MODEL
        llm = ChatOpenAI(model=LLM_FAST_MODEL, temperature=0)

    from langchain_core.messages import SystemMessage, HumanMessage

    system_msg = SystemMessage(
        content=(
            "Ты — краткий редактор. Сформируй метку ≤35 символов на русском языке, "
            "описывающую суть записи. Используй только существительные и глаголы. "
            "Верни ТОЛЬКО метку, ничего больше."
        )
    )

    # Step 3: batch LLM call
    inputs = [[system_msg, HumanMessage(content=text)] for text in texts]
    try:
        results = llm.batch(inputs, config={"max_concurrency": 50})
    except Exception as e:
        logger.error("LLM batch call failed: %s", e)
        return

    # Step 4: assign results back to records
    modified_jurisdictions: set[str] = set()

    for i, (name_ru, section_name, record_idx) in enumerate(pending):
        result = results[i]
        label = result.content.strip()[:35]
        if not label:
            continue

        _, data = jurisdiction_data[name_ru]
        data[section_name][record_idx]["label"] = label
        modified_jurisdictions.add(name_ru)

    # Step 5: save modified jurisdictions
    for name_ru in modified_jurisdictions:
        path, data = jurisdiction_data[name_ru]
        try:
            _save_json_atomic(path, data)
            logger.info("[UPDATED] %s — labels written", name_ru)
        except Exception as e:
            logger.error("[ERROR] %s — failed to save labels: %s", name_ru, e)

    logger.info("Labels generation complete: %d jurisdictions updated", len(modified_jurisdictions))


def process_level4_articulated_by(
    jurisdictions: list[str] | None = None
) -> None:
    """
    Normalize articulated_by to enum values.
    Idempotent: skips already-normalized records.
    jurisdictions: list of name_ru; None = process all.
    """
    if jurisdictions is None:
        jurisdictions = [
            d.name for d in COUNTRIES_DIR.iterdir()
            if d.is_dir()
        ]

    logger.info("Processing %d jurisdiction(s) for articulated_by normalization", len(jurisdictions))

    for name_ru in jurisdictions:
        path, data = _load_level4(name_ru)
        if data is None:
            continue

        total_updated = 0

        for section_name in _SECTIONS:
            section = data.get(section_name, [])
            for record in section:
                raw = record.get("articulated_by")
                if raw is None:
                    continue
                if raw in _ARTICULATED_BY_VALID:
                    continue  # already a valid enum value — skip
                normalized = _ARTICULATED_BY_MAP.get(raw)
                if normalized is None:
                    logger.warning(
                        "[WARN] %s — unknown articulated_by value '%s' in %s, skipping",
                        name_ru, raw, section_name
                    )
                    continue
                record["articulated_by"] = normalized
                total_updated += 1

        if total_updated == 0:
            logger.info("[SKIP] %s — all articulated_by already normalized", name_ru)
            continue

        try:
            _save_json_atomic(path, data)
            logger.info("[UPDATED] %s — %d articulated_by fields normalized", name_ru, total_updated)
        except Exception as e:
            logger.error("[ERROR] %s — failed to save: %s", name_ru, e)

    logger.info("articulated_by normalization complete")
