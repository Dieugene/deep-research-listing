"""
Join fragmented excerpts using LLM.

Parallel API sometimes returns excerpts fragmented line-by-line (especially
from PDFs and HTML tables). This module detects fragmented excerpt lists and
uses an LLM to reconstruct coherent text blocks.

Operates on derived citations[]/sources[] only -- basis stays as the original
Parallel API response (immutable audit trail).
"""
import datetime
import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from pipeline.config import COUNTRIES_DIR, LOGS_DIR, LLM_FAST_MODEL
from pipeline.logging_setup import get_logger

logger = get_logger(
    "excerpt_joiner",
    LOGS_DIR / f"excerpt_joiner_{datetime.date.today()}.log",
)

# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def _is_fragmented(excerpts: list[str], min_count: int = 10, max_avg_len: int = 80) -> bool:
    """Return True if excerpts look like fragmented PDF/table lines."""
    if len(excerpts) < min_count:
        return False
    avg_len = sum(len(e) for e in excerpts) / len(excerpts)
    return avg_len < max_avg_len


# ---------------------------------------------------------------------------
# Pydantic model for structured output
# ---------------------------------------------------------------------------

class JoinedExcerpts(BaseModel):
    text: str  # The reconstructed text


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """\
The following text fragments were extracted line-by-line from a PDF or web page.
They are fragments of one continuous passage. Reconstruct the original text
by joining the fragments into coherent paragraphs or sections.

Preserve the original text exactly -- do not rephrase, summarize, or add content.
Only join fragments that belong together. Keep numbered lists and bullet points
as they are, but join them with their content.

If the text contains distinct sections (e.g., different regulatory topics),
return them as separate blocks separated by \\n\\n.

Fragments:
{fragments}

Return the reconstructed text."""


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("File not found: %s", path)
        return None
    except json.JSONDecodeError as exc:
        logger.error("JSON decode error in %s: %s", path, exc)
        return None


def _save_json(path: Path, data) -> None:
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


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _collect_fragmented_sources(data, path: Path) -> list[dict]:
    """
    Walk a JSON structure and collect references to source/citation objects
    whose excerpts are fragmented.

    Returns list of dicts:
        {obj: <the dict>, excerpts: <list[str]>, location: <str>}
    """
    results = []

    def _scan_list(items: list, location: str):
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            excerpts = item.get("excerpts")
            if not isinstance(excerpts, list):
                continue
            # Skip already joined
            if item.get("excerpts_joined"):
                continue
            # Filter to string excerpts only
            str_excerpts = [e for e in excerpts if isinstance(e, str)]
            if _is_fragmented(str_excerpts):
                results.append({
                    "obj": item,
                    "excerpts": str_excerpts,
                    "location": f"{location}[{i}]",
                })

    if isinstance(data, dict):
        # Top-level sources[]
        if "sources" in data and isinstance(data["sources"], list):
            _scan_list(data["sources"], "sources")
        # Top-level citations[]
        if "citations" in data and isinstance(data["citations"], list):
            _scan_list(data["citations"], "citations")
        # Nested: records[].sources[]
        if "records" in data and isinstance(data["records"], list):
            for ri, rec in enumerate(data["records"]):
                if isinstance(rec, dict) and "sources" in rec and isinstance(rec["sources"], list):
                    _scan_list(rec["sources"], f"records[{ri}].sources")

    return results


def run_excerpt_joiner(
    llm=None,
    jurisdictions: Optional[list[str]] = None,
) -> None:
    """
    Scan all files with citations/sources, find fragmented excerpts,
    join them via LLM, mark with excerpts_joined=True.
    """
    logger.info("=== Excerpt joiner: start (jurisdictions=%s) ===", jurisdictions)

    if llm is None:
        llm = ChatOpenAI(
            model=LLM_FAST_MODEL,
            api_key=os.environ["OPENAI_API_KEY"],
            temperature=0,
        )

    chain = llm.with_structured_output(JoinedExcerpts)

    # Discover jurisdiction directories
    if jurisdictions is None:
        juris_dirs = sorted(d for d in COUNTRIES_DIR.iterdir() if d.is_dir())
    else:
        juris_dirs = [
            COUNTRIES_DIR / name for name in jurisdictions
            if (COUNTRIES_DIR / name).is_dir()
        ]

    # Phase 1: collect all fragmented sources across all files
    # Each entry: {path, obj, excerpts, location}
    all_pending: list[dict] = []
    # Track which files have pending items (path -> data)
    file_data: dict[str, tuple[Path, object]] = {}

    for juris_dir in juris_dirs:
        name_ru = juris_dir.name

        # Build list of files to scan
        files_to_scan: list[Path] = []

        # L1
        l1_dir = juris_dir / "level_1"
        if l1_dir.exists():
            for fname in ["jurisdiction_card.json"]:
                fpath = l1_dir / fname
                if fpath.exists():
                    files_to_scan.append(fpath)

        # L2
        l2_dir = juris_dir / "level_2"
        if l2_dir.exists():
            for venue_dir in sorted(l2_dir.iterdir()):
                if not venue_dir.is_dir():
                    continue
                fpath = venue_dir / "venue_card.json"
                if fpath.exists():
                    files_to_scan.append(fpath)

        # L3: _parallel_raw/*_raw.json
        l3_dir = juris_dir / "level_3"
        if l3_dir.exists():
            for venue_dir in sorted(l3_dir.iterdir()):
                if not venue_dir.is_dir():
                    continue
                parallel_raw_dir = venue_dir / "_parallel_raw"
                if parallel_raw_dir.exists():
                    for raw_path in sorted(parallel_raw_dir.glob("*_raw.json")):
                        files_to_scan.append(raw_path)

        # L4
        l4_dir = juris_dir / "level_4"
        if l4_dir.exists():
            fpath = l4_dir / "level4.json"
            if fpath.exists():
                files_to_scan.append(fpath)

        # Scan each file
        for fpath in files_to_scan:
            data = _load_json(fpath)
            if data is None:
                continue

            found = _collect_fragmented_sources(data, fpath)
            if found:
                path_key = str(fpath)
                file_data[path_key] = (fpath, data)
                for item in found:
                    item["path_key"] = path_key
                    all_pending.append(item)

    if not all_pending:
        logger.info("=== Excerpt joiner: no fragmented excerpts found ===")
        return

    logger.info(
        "Found %d fragmented source(s) across %d file(s)",
        len(all_pending), len(file_data),
    )

    # Phase 2: build prompts and run LLM batch
    prompts = []
    for item in all_pending:
        fragments_text = "\n".join(item["excerpts"])
        prompt = _PROMPT_TEMPLATE.format(fragments=fragments_text)
        prompts.append(prompt)

    logger.info("Running LLM batch for %d prompts...", len(prompts))

    results = chain.batch(
        [[HumanMessage(content=p)] for p in prompts],
        config={"max_concurrency": 50},
        return_exceptions=True,
    )

    # Phase 3: apply results
    joined_count = 0
    error_count = 0
    files_to_save: set[str] = set()

    for item, result in zip(all_pending, results):
        if isinstance(result, Exception):
            logger.error(
                "LLM error for %s %s: %s",
                item["path_key"], item["location"], result,
            )
            error_count += 1
            continue

        joined_text = result.text.strip()
        if not joined_text:
            logger.warning(
                "Empty LLM result for %s %s -- skipping",
                item["path_key"], item["location"],
            )
            error_count += 1
            continue

        # Replace excerpts with joined text (as single-element list)
        item["obj"]["excerpts"] = [joined_text]
        item["obj"]["excerpts_joined"] = True
        joined_count += 1
        files_to_save.add(item["path_key"])

    # Phase 4: save modified files
    saved_count = 0
    for path_key in files_to_save:
        fpath, data = file_data[path_key]
        _save_json(fpath, data)
        saved_count += 1
        logger.info("[SAVED] %s", fpath)

    logger.info(
        "=== Excerpt joiner: done -- %d joined, %d errors, %d files saved ===",
        joined_count, error_count, saved_count,
    )
