"""
Task 021: L3 section description translation to Russian.

Adds `description_ru` field to all sections in 3A_raw.json, 3B_raw.json, 3C_raw.json.
Handles both FLAT (content.key.description) and NESTED (content.key.subkey.description)
section structures.

Idempotent at the section level: already-translated sections are skipped.
"""
import datetime
import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from pipeline.config import COUNTRIES_DIR, LOGS_DIR, LLM_FAST_MODEL
from pipeline.logging_setup import get_logger
from pipeline.source_classifier import _iter_l3_raw_files

logger = get_logger(
    "l3_translate",
    LOGS_DIR / f"l3_translate_{datetime.date.today()}.log",
)


# ---------------------------------------------------------------------------
# Pydantic model for structured LLM output
# ---------------------------------------------------------------------------

class TranslationEntry(BaseModel):
    key: str
    value: str

class SectionTranslations(BaseModel):
    translations: list[TranslationEntry]


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------

def _get_llm(model: str = LLM_FAST_MODEL):
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=model, api_key=os.environ["OPENAI_API_KEY"], temperature=0)


# ---------------------------------------------------------------------------
# JSON helpers (atomic write)
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> Optional[dict]:
    """Load JSON from path; return None if missing or empty."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return None


def _save_json(path: Path, data: dict) -> None:
    """Atomically write JSON to path using tempfile + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# FLAT vs NESTED detection
# ---------------------------------------------------------------------------

def _is_flat(val: dict) -> bool:
    """True if val is a dict with a string `description` at the top level."""
    return isinstance(val.get("description"), str)


def _is_nested(val: dict) -> bool:
    """True if val contains sub-dicts (NESTED format)."""
    return any(isinstance(v, dict) for v in val.values())


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _collect_untranslated(content: dict) -> dict[str, str]:
    """
    Walk the content dict and return {display_key: description_en} for all
    sections that have a `description` but no `description_ru` yet.

    FLAT  -> display_key = "admission_overview"
    NESTED -> display_key = "suspension.procedure"

    The key "tier_name" is excluded (it is a short label, not a description).
    """
    result: dict[str, str] = {}
    for key, val in content.items():
        if key == "tier_name":
            continue
        if not isinstance(val, dict):
            continue
        if _is_flat(val):
            if not val.get("description_ru") and val.get("description"):
                result[key] = val["description"]
        elif _is_nested(val):
            for subkey, subval in val.items():
                if not isinstance(subval, dict):
                    continue
                if isinstance(subval.get("description"), str):
                    if not subval.get("description_ru"):
                        result[f"{key}.{subkey}"] = subval["description"]
    return result


def _apply_translations(data: dict, translations) -> int:
    """
    Write `description_ru` values back into data["content"].
    translations: list[TranslationEntry] from SectionTranslations.
    Returns the number of sections updated.
    """
    content = data.get("content", {})
    updated = 0
    pairs = [(e.key, e.value) for e in translations]
    for display_key, ru_text in pairs:
        if "." in display_key:
            section_key, subkey = display_key.split(".", 1)
            section = content.get(section_key, {})
            subsection = section.get(subkey, {})
            if isinstance(subsection, dict):
                subsection["description_ru"] = ru_text
                updated += 1
        else:
            section = content.get(display_key, {})
            if isinstance(section, dict):
                section["description_ru"] = ru_text
                updated += 1
    return updated


def _build_prompt(sections: dict[str, str]) -> str:
    """Build the translation prompt for one file's untranslated sections."""
    sections_json = json.dumps(sections, ensure_ascii=False, indent=2)
    return (
        "You are translating securities regulation content from English to Russian.\n"
        'Return JSON {"translations": [{"key": "section_key", "value": "russian_text"}, ...]}.\n'
        "Translate each value to Russian. Do NOT translate the keys.\n"
        "Preserve proper nouns, regulatory acronyms (FCA, MiFID, UKLR, ASX, etc.), "
        "and legal terms.\n\n"
        f"Sections to translate:\n{sections_json}"
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_l3_translate(llm=None, jurisdictions: Optional[list[str]] = None) -> None:
    """
    Translate `description` fields in 3A/3B/3C_raw.json files to Russian,
    adding `description_ru` to each section.

    Parameters
    ----------
    llm : ChatOpenAI, optional
        LLM instance to use. If None, creates one using LLM_FAST_MODEL.
    jurisdictions : list[str], optional
        Country directory names (name_ru) to process. None = all jurisdictions.
    """
    from langchain_core.messages import HumanMessage

    if llm is None:
        llm = _get_llm(LLM_FAST_MODEL)

    chain = llm.with_structured_output(SectionTranslations)

    # ------------------------------------------------------------------
    # 1. Collect work items — files with at least one untranslated section
    # ------------------------------------------------------------------
    work_items: list[dict] = []

    for raw_path, label in _iter_l3_raw_files(jurisdictions):
        data = _load_json(raw_path)
        if not data:
            continue
        content = data.get("content", {})
        if not content:
            continue

        sections = _collect_untranslated(content)
        if not sections:
            logger.info("[SKIP] %s — all sections already have description_ru", label)
            continue

        work_items.append({
            "raw_path": raw_path,
            "label": label,
            "data": data,
            "sections": sections,
        })

    if not work_items:
        logger.info("No files need translation")
        return

    logger.info("Translating %d files", len(work_items))

    # ------------------------------------------------------------------
    # 2. Build prompts
    # ------------------------------------------------------------------
    prompts = [_build_prompt(item["sections"]) for item in work_items]

    # ------------------------------------------------------------------
    # 3. Batch translate (max_concurrency=50, return_exceptions=True)
    # ------------------------------------------------------------------
    results = chain.batch(
        [[HumanMessage(content=p)] for p in prompts],
        config={"max_concurrency": 50},
        return_exceptions=True,
    )

    # ------------------------------------------------------------------
    # 4. Apply translations and save atomically
    # ------------------------------------------------------------------
    for item, result in zip(work_items, results):
        label: str = item["label"]

        if isinstance(result, Exception):
            logger.error("[ERROR] %s: %s", label, result)
            continue

        n = _apply_translations(item["data"], result.translations or [])
        _save_json(item["raw_path"], item["data"])
        logger.info("[TRANSLATED] %s — %d sections translated", label, n)
