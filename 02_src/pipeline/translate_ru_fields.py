"""
Task 022: Translate missing _ru fields to Russian.

Four functions:
  A. translate_jurisdiction_notes  — notes -> notes_ru in jurisdiction_card.json (L1)
  B. translate_phase2_fields       — tier_ru + ADDITIONAL param_label_ru in pass2_ru.json (Phase 2)
  C. translate_level4_fields       — reforms + ptools _ru fields in level4.json (L4)
  D. normalize_param_ids           — Latin P01 -> Cyrillic П01 in pass2_ru.json (no LLM)

All LLM functions are idempotent: they skip records where _ru fields are already filled.
All writes use atomic tempfile + os.replace.
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

logger = get_logger(
    "translate_ru_fields",
    LOGS_DIR / f"translate_ru_fields_{datetime.date.today()}.log",
)


# ---------------------------------------------------------------------------
# Pydantic models for structured LLM output
# ---------------------------------------------------------------------------

class TextTranslation(BaseModel):
    translation: str


class ReformTranslation(BaseModel):
    driver_ru: str
    opposition_ru: str


class PToolTranslation(BaseModel):
    problem_addressed_ru: str
    calibration_debate_ru: str


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------

def _get_llm(model: str = LLM_FAST_MODEL):
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=model, api_key=os.environ["OPENAI_API_KEY"], temperature=0)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> Optional[dict]:
    """Load JSON from path; return None if missing, unreadable, or empty."""
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
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


def _is_filled(value) -> bool:
    """Return True if value is a non-empty, non-None string."""
    return isinstance(value, str) and bool(value.strip())


# ---------------------------------------------------------------------------
# A. translate_jurisdiction_notes
# ---------------------------------------------------------------------------

def translate_jurisdiction_notes(llm=None, jurisdictions: Optional[list[str]] = None) -> None:
    """
    Translate `notes` -> `notes_ru` in jurisdiction_card.json for each jurisdiction.

    Idempotent: skips jurisdictions where notes_ru is already filled.
    jurisdictions: list of name_ru; None = process all.
    llm: LangChain LLM instance; created internally if None.
    """
    from langchain_core.messages import HumanMessage

    if llm is None:
        llm = _get_llm()

    chain = llm.with_structured_output(TextTranslation)

    # Collect pending work
    pending: list[dict] = []  # {name_ru, path, data, notes}

    for country_dir in sorted(COUNTRIES_DIR.iterdir()):
        if not country_dir.is_dir():
            continue
        if jurisdictions and country_dir.name not in jurisdictions:
            continue

        card_path = country_dir / "level_1" / "jurisdiction_card.json"
        data = _load_json(card_path)
        if data is None:
            logger.warning("[SKIP] %s — jurisdiction_card.json not found or unreadable", country_dir.name)
            continue

        notes = data.get("notes", "")
        if not _is_filled(notes):
            logger.info("[SKIP] %s — notes field is empty", country_dir.name)
            continue

        if _is_filled(data.get("notes_ru")):
            logger.info("[SKIP] %s — notes_ru already filled", country_dir.name)
            continue

        pending.append({
            "name_ru": country_dir.name,
            "path": card_path,
            "data": data,
            "notes": notes,
        })

    if not pending:
        logger.info("No jurisdictions need notes_ru translation")
        return

    logger.info("Translating notes_ru for %d jurisdiction(s)", len(pending))

    prompts = [
        (
            "Translate the following securities regulation text from English to Russian.\n"
            "Preserve proper nouns, regulatory acronyms, and legal terms.\n"
            "Return ONLY the Russian translation.\n\n"
            f"Text to translate:\n{item['notes']}"
        )
        for item in pending
    ]

    results = chain.batch(
        [[HumanMessage(content=p)] for p in prompts],
        config={"max_concurrency": 50},
        return_exceptions=True,
    )

    for item, result in zip(pending, results):
        if isinstance(result, Exception):
            logger.error("[ERROR] %s — notes_ru translation failed: %s", item["name_ru"], result)
            continue
        item["data"]["notes_ru"] = result.translation
        try:
            _save_json(item["path"], item["data"])
            logger.info("[UPDATED] %s — notes_ru written", item["name_ru"])
        except Exception as e:
            logger.error("[ERROR] %s — failed to save jurisdiction_card.json: %s", item["name_ru"], e)

    logger.info("translate_jurisdiction_notes complete")


# ---------------------------------------------------------------------------
# B. translate_phase2_fields (merged: tier_names + additional_param_labels)
# ---------------------------------------------------------------------------

def translate_phase2_fields(llm=None, jurisdictions: Optional[list[str]] = None) -> None:
    """
    Translate Phase 2 fields in pass2_ru.json (single directory walk):
      - tier_name (from 3A_raw.json) -> tier_ru
      - ADDITIONAL parameter_name -> param_label_ru

    Uses a single walk over COUNTRIES_DIR/*/level_3/*/cell_*/ and reads
    each pass2_ru.json once.  Two LLM batch calls (same TextTranslation schema,
    different prompt templates).  Each modified file is saved once at the end.

    Idempotent: skips fields that are already filled.
    jurisdictions: list of name_ru; None = process all.
    llm: LangChain LLM instance; created internally if None.
    """
    from langchain_core.messages import HumanMessage

    if llm is None:
        llm = _get_llm()

    chain = llm.with_structured_output(TextTranslation)

    # file_map: path_key -> {pass2_path, pass2_data, cell_id}
    # Ensures tier and param results write to the same in-memory dict
    file_map: dict[str, dict] = {}

    tier_pending: list[dict] = []   # {path_key, tier_name}
    param_pending: list[dict] = []  # {path_key, param_idx, param_name}

    for country_dir in sorted(COUNTRIES_DIR.iterdir()):
        if not country_dir.is_dir():
            continue
        if jurisdictions and country_dir.name not in jurisdictions:
            continue

        l3_dir = country_dir / "level_3"
        if not l3_dir.exists():
            continue

        for venue_dir in sorted(l3_dir.iterdir()):
            if not venue_dir.is_dir():
                continue
            for cell_dir in sorted(venue_dir.iterdir()):
                if not cell_dir.is_dir():
                    continue

                pass2_path = cell_dir / "pass2_ru.json"
                if not pass2_path.exists():
                    continue

                pass2_data = _load_json(pass2_path)
                if pass2_data is None:
                    continue

                path_key = str(pass2_path)

                # Register in file_map (shared between tier and param)
                if path_key not in file_map:
                    file_map[path_key] = {
                        "pass2_path": pass2_path,
                        "pass2_data": pass2_data,
                        "cell_id": cell_dir.name,
                    }

                # --- Tier: check if tier_ru needs translation ---
                if not _is_filled(pass2_data.get("tier_ru")):
                    raw_path = cell_dir / "3A_raw.json"
                    raw_data = _load_json(raw_path)
                    if raw_data is not None:
                        content = raw_data.get("content", {})
                        tier_name = content.get("tier_name", "") if isinstance(content, dict) else ""
                        if _is_filled(tier_name):
                            tier_pending.append({
                                "path_key": path_key,
                                "tier_name": tier_name,
                            })

                # --- ADDITIONAL params: check param_label_ru ---
                params = pass2_data.get("parameter_values", [])
                for idx, param in enumerate(params):
                    param_id = param.get("parameter_id", "")
                    if not param_id.startswith("ADDITIONAL"):
                        continue
                    if _is_filled(param.get("param_label_ru")):
                        continue
                    param_name = param.get("parameter_name", "")
                    if not _is_filled(param_name):
                        continue

                    param_pending.append({
                        "path_key": path_key,
                        "param_idx": idx,
                        "param_name": param_name,
                    })

    # --- Batch 1: tier translations ---
    if tier_pending:
        logger.info("Translating tier_ru for %d cell(s)", len(tier_pending))

        tier_prompts = [
            (
                "Translate the following securities instrument tier name from English to Russian.\n"
                "This is a short label (1-5 words) used as a page heading in a regulatory database.\n"
                "Preserve proper nouns and regulatory acronyms.\n"
                "Return ONLY the Russian translation.\n\n"
                f"Tier name: {item['tier_name']}"
            )
            for item in tier_pending
        ]

        tier_results = chain.batch(
            [[HumanMessage(content=p)] for p in tier_prompts],
            config={"max_concurrency": 50},
            return_exceptions=True,
        )

        for item, result in zip(tier_pending, tier_results):
            if isinstance(result, Exception):
                cell_id = file_map[item["path_key"]]["cell_id"]
                logger.error("[ERROR] %s — tier_ru translation failed: %s", cell_id, result)
                continue
            file_map[item["path_key"]]["pass2_data"]["tier_ru"] = result.translation
    else:
        logger.info("No cells need tier_ru translation")

    # --- Batch 2: ADDITIONAL param label translations ---
    if param_pending:
        logger.info("Translating param_label_ru for %d ADDITIONAL parameter(s)", len(param_pending))

        param_prompts = [
            (
                "Translate the following securities listing parameter name from English to Russian.\n"
                "This is a short label (1-6 words) for a regulatory parameter.\n"
                "Preserve proper nouns and regulatory acronyms.\n"
                "Return ONLY the Russian translation.\n\n"
                f"Parameter name: {item['param_name']}"
            )
            for item in param_pending
        ]

        param_results = chain.batch(
            [[HumanMessage(content=p)] for p in param_prompts],
            config={"max_concurrency": 50},
            return_exceptions=True,
        )

        for item, result in zip(param_pending, param_results):
            if isinstance(result, Exception):
                logger.error(
                    "[ERROR] param_label_ru translation failed for '%s': %s",
                    item["param_name"], result,
                )
                continue
            path_key = item["path_key"]
            params = file_map[path_key]["pass2_data"].get("parameter_values", [])
            params[item["param_idx"]]["param_label_ru"] = result.translation
    else:
        logger.info("No ADDITIONAL params need param_label_ru translation")

    # --- Save all modified files once ---
    # A file is modified if any tier or param result was written to it
    modified_paths: set[str] = set()
    for item in tier_pending:
        modified_paths.add(item["path_key"])
    for item in param_pending:
        modified_paths.add(item["path_key"])

    for path_key in modified_paths:
        file_info = file_map[path_key]
        try:
            _save_json(file_info["pass2_path"], file_info["pass2_data"])
            logger.info("[UPDATED] %s — phase2 fields written", file_info["cell_id"])
        except Exception as e:
            logger.error("[ERROR] %s — failed to save pass2_ru.json: %s", file_info["cell_id"], e)

    logger.info("translate_phase2_fields complete")


# ---------------------------------------------------------------------------
# C. translate_level4_fields (merged: reforms + ptools)
# ---------------------------------------------------------------------------

def translate_level4_fields(llm=None, jurisdictions: Optional[list[str]] = None) -> None:
    """
    Translate Level 4 fields in level4.json (single directory walk):
      - reforms[].driver/opposition -> driver_ru/opposition_ru
      - parameters_as_tools[].problem_addressed/calibration_debate -> _ru

    Uses a single walk over COUNTRIES_DIR/*/level_4/level4.json and reads
    each file once.  Two LLM batch calls (different Pydantic schemas).
    Each modified file is saved once at the end.

    Idempotent: skips fields that are already filled.
    jurisdictions: list of name_ru; None = process all.
    llm: LangChain LLM instance; created internally if None.
    """
    from langchain_core.messages import HumanMessage

    if llm is None:
        llm = _get_llm()

    reform_chain = llm.with_structured_output(ReformTranslation)
    ptool_chain = llm.with_structured_output(PToolTranslation)

    # jurisdiction_data: name_ru -> (l4_path, data)
    jurisdiction_data: dict[str, tuple[Path, dict]] = {}

    reform_pending: list[dict] = []
    ptool_pending: list[dict] = []

    for country_dir in sorted(COUNTRIES_DIR.iterdir()):
        if not country_dir.is_dir():
            continue
        if jurisdictions and country_dir.name not in jurisdictions:
            continue

        l4_path = country_dir / "level_4" / "level4.json"
        data = _load_json(l4_path)
        if data is None:
            continue

        name_ru = country_dir.name
        jurisdiction_data[name_ru] = (l4_path, data)

        # --- Reforms ---
        reforms = data.get("reforms", [])
        for idx, reform in enumerate(reforms):
            driver = reform.get("driver", "")
            opposition = reform.get("opposition", "")
            driver_ru_filled = _is_filled(reform.get("driver_ru"))
            opposition_ru_filled = _is_filled(reform.get("opposition_ru"))

            if driver_ru_filled and opposition_ru_filled:
                continue
            if not _is_filled(driver) and not _is_filled(opposition):
                continue

            reform_pending.append({
                "name_ru": name_ru,
                "reform_idx": idx,
                "driver": driver if not driver_ru_filled else "",
                "opposition": opposition if not opposition_ru_filled else "",
                "driver_ru_filled": driver_ru_filled,
                "opposition_ru_filled": opposition_ru_filled,
            })

        # --- Parameters as tools ---
        ptools = data.get("parameters_as_tools", [])
        for idx, ptool in enumerate(ptools):
            problem = ptool.get("problem_addressed", "")
            calibration = ptool.get("calibration_debate", "")
            problem_ru_filled = _is_filled(ptool.get("problem_addressed_ru"))
            calibration_ru_filled = _is_filled(ptool.get("calibration_debate_ru"))

            if problem_ru_filled and calibration_ru_filled:
                continue
            if not _is_filled(problem) and not _is_filled(calibration):
                continue

            ptool_pending.append({
                "name_ru": name_ru,
                "ptool_idx": idx,
                "problem": problem if not problem_ru_filled else "",
                "calibration": calibration if not calibration_ru_filled else "",
                "problem_ru_filled": problem_ru_filled,
                "calibration_ru_filled": calibration_ru_filled,
            })

    # --- Batch 1: reforms translations ---
    modified_jurisdictions: set[str] = set()

    if reform_pending:
        logger.info("Translating reforms fields for %d reform(s)", len(reform_pending))

        reform_prompts = [
            (
                "Translate the following securities regulation reform fields from English to Russian.\n"
                "Preserve proper nouns, regulatory acronyms, and legal terms.\n"
                "Return a JSON object with driver_ru and opposition_ru fields.\n"
                "If a field is empty, return an empty string for it.\n\n"
                f"driver: {item['driver']}\n"
                f"opposition: {item['opposition']}"
            )
            for item in reform_pending
        ]

        reform_results = reform_chain.batch(
            [[HumanMessage(content=p)] for p in reform_prompts],
            config={"max_concurrency": 50},
            return_exceptions=True,
        )

        for item, result in zip(reform_pending, reform_results):
            if isinstance(result, Exception):
                logger.error(
                    "[ERROR] %s reform[%d] — translation failed: %s",
                    item["name_ru"], item["reform_idx"], result,
                )
                continue

            _, data = jurisdiction_data[item["name_ru"]]
            reform = data["reforms"][item["reform_idx"]]

            if not item["driver_ru_filled"] and _is_filled(item["driver"]):
                reform["driver_ru"] = result.driver_ru
            if not item["opposition_ru_filled"] and _is_filled(item["opposition"]):
                reform["opposition_ru"] = result.opposition_ru

            modified_jurisdictions.add(item["name_ru"])
    else:
        logger.info("No reforms need driver_ru/opposition_ru translation")

    # --- Batch 2: ptools translations ---
    if ptool_pending:
        logger.info("Translating ptools fields for %d record(s)", len(ptool_pending))

        ptool_prompts = [
            (
                "Translate the following securities regulation parameter fields from English to Russian.\n"
                "Preserve proper nouns, regulatory acronyms, and legal terms.\n"
                "Return a JSON object with problem_addressed_ru and calibration_debate_ru fields.\n"
                "If a field is empty, return an empty string for it.\n\n"
                f"problem_addressed: {item['problem']}\n"
                f"calibration_debate: {item['calibration']}"
            )
            for item in ptool_pending
        ]

        ptool_results = ptool_chain.batch(
            [[HumanMessage(content=p)] for p in ptool_prompts],
            config={"max_concurrency": 50},
            return_exceptions=True,
        )

        for item, result in zip(ptool_pending, ptool_results):
            if isinstance(result, Exception):
                logger.error(
                    "[ERROR] %s ptool[%d] — translation failed: %s",
                    item["name_ru"], item["ptool_idx"], result,
                )
                continue

            _, data = jurisdiction_data[item["name_ru"]]
            ptool = data["parameters_as_tools"][item["ptool_idx"]]

            if not item["problem_ru_filled"] and _is_filled(item["problem"]):
                ptool["problem_addressed_ru"] = result.problem_addressed_ru
            if not item["calibration_ru_filled"] and _is_filled(item["calibration"]):
                ptool["calibration_debate_ru"] = result.calibration_debate_ru

            modified_jurisdictions.add(item["name_ru"])
    else:
        logger.info("No parameters_as_tools need problem_addressed_ru/calibration_debate_ru translation")

    # --- Save all modified files once ---
    for name_ru in modified_jurisdictions:
        l4_path, data = jurisdiction_data[name_ru]
        try:
            _save_json(l4_path, data)
            logger.info("[UPDATED] %s — level4 fields written", name_ru)
        except Exception as e:
            logger.error("[ERROR] %s — failed to save level4.json: %s", name_ru, e)

    logger.info("translate_level4_fields complete")


# ---------------------------------------------------------------------------
# D. normalize_param_ids
# ---------------------------------------------------------------------------

def normalize_param_ids(jurisdictions: Optional[list[str]] = None) -> None:
    """
    Normalize parameter_id from Latin P-prefix to Cyrillic П-prefix in pass2_ru.json.

    Rule: if param_id starts with Latin 'P' and the remainder is all digits,
    replace 'P' with Cyrillic 'П'. e.g., P01 -> П01.
    ADDITIONAL_* parameters are not touched.

    Algorithmic (no LLM). Idempotent.
    jurisdictions: list of name_ru; None = process all.
    """
    updated_files = 0
    updated_params = 0

    for country_dir in sorted(COUNTRIES_DIR.iterdir()):
        if not country_dir.is_dir():
            continue
        if jurisdictions and country_dir.name not in jurisdictions:
            continue

        l3_dir = country_dir / "level_3"
        if not l3_dir.exists():
            continue

        for venue_dir in sorted(l3_dir.iterdir()):
            if not venue_dir.is_dir():
                continue
            for cell_dir in sorted(venue_dir.iterdir()):
                if not cell_dir.is_dir():
                    continue

                pass2_path = cell_dir / "pass2_ru.json"
                if not pass2_path.exists():
                    continue

                pass2_data = _load_json(pass2_path)
                if pass2_data is None:
                    continue

                changed = False
                params = pass2_data.get("parameter_values", [])

                for param in params:
                    param_id = param.get("parameter_id", "")
                    # Check for Latin P followed by digits only
                    if (
                        isinstance(param_id, str)
                        and param_id.startswith("P")
                        and not param_id.startswith("ADDITIONAL")
                        and param_id[1:].isdigit()
                    ):
                        new_id = "\u041f" + param_id[1:]  # П + digits
                        param["parameter_id"] = new_id
                        changed = True
                        updated_params += 1

                    # Also normalize linkages list entries
                    linkages = param.get("linkages", [])
                    if isinstance(linkages, list):
                        new_linkages = []
                        for link in linkages:
                            if (
                                isinstance(link, str)
                                and link.startswith("P")
                                and not link.startswith("ADDITIONAL")
                                and link[1:].isdigit()
                            ):
                                new_linkages.append("\u041f" + link[1:])
                                changed = True
                                updated_params += 1
                            else:
                                new_linkages.append(link)
                        param["linkages"] = new_linkages

                if changed:
                    try:
                        _save_json(pass2_path, pass2_data)
                        updated_files += 1
                        logger.info("[UPDATED] %s — param_ids normalized", cell_dir.name)
                    except Exception as e:
                        logger.error("[ERROR] %s — failed to save pass2_ru.json: %s", cell_dir.name, e)

    if updated_files == 0:
        logger.info("normalize_param_ids: no files needed normalization")
    else:
        logger.info(
            "normalize_param_ids complete: %d file(s) updated, %d param id(s) normalized",
            updated_files, updated_params
        )
