"""
Task 008: L3 Matrix Builder 4x5

Builds a 4x5 matrix (lifecycle phases x regulatory content types) from
3A/3B/3C raw JSON files for each L3 cell.

Matrix dimensions:
  Rows (phases): G07_1 (admission), G07_2 (maintenance), G07_3 (suspension), G07_4 (removal)
  Cols (content): D01_requirements, D02_procedures, D03_monitoring, D04_sanctions, D05_disclosure
"""
import datetime
import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from pipeline.config import COUNTRIES_DIR, LOGS_DIR, LLM_FAST_MODEL
from pipeline.logging_setup import get_logger

logger = get_logger(
    "matrix_builder",
    LOGS_DIR / f"matrix_{datetime.date.today()}.log",
)

# ---------------------------------------------------------------------------
# Pydantic models for LLM structured output
# ---------------------------------------------------------------------------

class SanctionsDistribution(BaseModel):
    G07_2: Optional[str] = None
    G07_3: Optional[str] = None
    G07_4: Optional[str] = None


class AdditionalFinding(BaseModel):
    text: str
    phase: str       # G07_1|G07_2|G07_3|G07_4|UNKNOWN
    content_type: str  # D01|D02|D03|D04|D05|UNKNOWN
    source_query: str  # 3A|3B|3C


class LLMMatrixOutput(BaseModel):
    sanctions: SanctionsDistribution
    monitoring_suspension: Optional[str] = None
    additional_findings: list[AdditionalFinding] = []


# ---------------------------------------------------------------------------
# Content type key map
# ---------------------------------------------------------------------------

_CONTENT_KEY_MAP = {
    "D01": "D01_requirements",
    "D02": "D02_procedures",
    "D03": "D03_monitoring",
    "D04": "D04_sanctions",
    "D05": "D05_disclosure",
}

_PHASE_KEY_MAP = {
    "G07_1": "G07_1",
    "G07_2": "G07_2",
    "G07_3": "G07_3",
    "G07_4": "G07_4",
}

# Values that mean "not applicable" — skip this field entirely
_NA_VALUES = {"", "not applicable", "n/a", "н/д"}


def _is_na(description: str) -> bool:
    """Return True if description represents a not-applicable value."""
    return description.strip().lower() in _NA_VALUES


def _extract_content_item(
    description: str,
    source: str,
    subtitle: str,
    origin_field: str,
    description_ru: str = "",
) -> dict | None:
    """
    Returns content item dict or None if description is empty/n/a.

    Content item schema:
      {"subtitle": "...", "description": "...", "description_ru": "...",
       "source": "...", "origin_field": "..."}
    """
    if not description or _is_na(description):
        return None
    item = {
        "subtitle": subtitle,
        "description": description.strip(),
        "source": source.strip() if source else "",
        "origin_field": origin_field,
    }
    if description_ru:
        item["description_ru"] = description_ru.strip()
    return item


def _empty_matrix() -> dict:
    """Return blank 4x5 matrix structure with default null cells for N/A positions."""
    phases = ["G07_1", "G07_2", "G07_3", "G07_4"]
    content_types = ["D01_requirements", "D02_procedures", "D03_monitoring", "D04_sanctions", "D05_disclosure"]

    # Cells that are null by default (not applicable)
    null_cells = {
        ("G07_1", "D03_monitoring"),
        ("G07_1", "D04_sanctions"),
        ("G07_4", "D03_monitoring"),
    }

    matrix = {}
    for phase in phases:
        matrix[phase] = {}
        for ct in content_types:
            if (phase, ct) in null_cells:
                matrix[phase][ct] = None
            else:
                matrix[phase][ct] = {"content": [], "citations": []}
    return matrix


def _get_field(data: dict, *keys: str) -> tuple[str, str, str]:
    """
    Safely navigate nested dict by key sequence.
    Returns (description, source, description_ru) tuple.
    """
    obj = data
    for k in keys:
        if not isinstance(obj, dict):
            return "", "", ""
        obj = obj.get(k, {})
    if not isinstance(obj, dict):
        return "", "", ""
    return obj.get("description", ""), obj.get("source", ""), obj.get("description_ru", "")


def _add_item(matrix: dict, phase: str, ct_short: str, item: dict | None) -> None:
    """Add content item to matrix cell. Skips if item is None."""
    if item is None:
        return
    ct_key = _CONTENT_KEY_MAP.get(ct_short)
    if ct_key is None:
        return
    cell = matrix.get(phase, {}).get(ct_key)
    if cell is None:
        # Cell was null (N/A) — only add content if data exists (override null)
        matrix[phase][ct_key] = {"content": [item], "citations": []}
    else:
        cell["content"].append(item)


# ---------------------------------------------------------------------------
# 3A algorithmic mapping
# ---------------------------------------------------------------------------

_3A_MAPPING = [
    # (field_key, phase, content_type_short, subtitle)
    ("admission_overview",       "G07_1", "D01", "Режим допуска"),
    ("eligibility_requirements", "G07_1", "D01", "Требования к эмитенту"),
    ("instrument_requirements",  "G07_1", "D01", "Требования к инструменту"),
    ("sponsor_and_infrastructure","G07_1","D01", "Инфраструктура и спонсор"),
    ("restrictions_and_lock_ups","G07_1", "D01", "Ограничения и lock-up"),
    ("special_regimes",          "G07_1", "D01", "Специальные режимы"),
    ("procedure_and_timeline",   "G07_1", "D02", "Процедура допуска"),
    ("disclosure_at_admission",  "G07_1", "D05", "Раскрытие при допуске"),
    ("secondary_admission",      "G07_1", "D01", "Вторичный допуск"),
    # additional_findings -> LLM
]

# 3B: nested content structure
_3B_MAPPING = [
    # (parent_key, sub_key, phase, content_type_short, subtitle)
    ("continuing_obligations", "quantitative_thresholds",  "G07_2", "D01", "Количественные пороги"),
    ("continuing_obligations", "qualitative_obligations",  "G07_2", "D01", "Качественные обязательства"),
    ("continuing_obligations", "compliance_confirmation",  "G07_2", "D02", "Подтверждение соответствия"),
    ("continuing_obligations", "periodic_reporting",       "G07_2", "D05", "Периодическая отчётность"),
    ("suspension", "grounds",    "G07_3", "D01", "Основания приостановки"),
    ("suspension", "duration_limits", "G07_3", "D01", "Сроки приостановки"),
    ("suspension", "procedure",  "G07_3", "D02", "Процедура приостановки"),
    ("suspension", "disclosure", "G07_3", "D05", "Раскрытие при приостановке"),
    ("delisting_compulsory", "grounds",              "G07_4", "D01", "Основания принудительного исключения"),
    ("delisting_compulsory", "procedure",            "G07_4", "D02", "Процедура исключения"),
    ("delisting_compulsory", "grace_period",         "G07_4", "D02", "Переходный период"),
    ("delisting_compulsory", "shareholder_protection","G07_4","D02", "Защита акционеров"),
    ("delisting_compulsory", "disclosure",           "G07_4", "D05", "Раскрытие при исключении"),
    ("delisting_voluntary",  "conditions",           "G07_4", "D01", "Условия добровольного исключения"),
    ("delisting_voluntary",  "procedure",            "G07_4", "D02", "Процедура добровольного исключения"),
    ("delisting_voluntary",  "shareholder_approval", "G07_4", "D02", "Одобрение акционеров"),
    # terminology -> metadata
    # additional_findings -> LLM
]

# 3C: nested content structure (algorithmic subset)
_3C_ALGORITHMIC_MAPPING = [
    # (parent_key, sub_key, phase, content_type_short, subtitle)
    ("monitoring_regime", "responsible_body",           "G07_2", "D03", "Ответственный орган"),
    ("monitoring_regime", "mechanisms",                 "G07_2", "D03", "Механизмы контроля"),
    ("monitoring_regime", "sponsor_role",               "G07_2", "D03", "Роль спонсора"),
    ("monitoring_regime", "issuer_reporting_to_exchange","G07_2","D03", "Отчётность перед биржей"),
    # sanctions.exchange_sanctions  -> LLM (G07_2.D04 baseline, then LLM routes)
    # sanctions.regulator_sanctions -> LLM
    ("sanctions", "disciplinary_procedure",  "G07_2", "D04", "Дисциплинарная процедура"),
    ("sanctions", "publication_of_actions",  "G07_2", "D04", "Публикация решений"),
    ("enforcement_practice", "recent_examples",  "G07_2", "D04", "Практика применения"),
    ("enforcement_practice", "general_approach", "G07_2", "D04", "Общий подход к enforcement"),
    # additional_findings -> LLM
]


# ---------------------------------------------------------------------------
# Citation field -> matrix cell mapping
# ---------------------------------------------------------------------------

_CITATION_FIELD_MAP = {
    # 3A fields (all phase G07_1)
    "admission_overview": ("G07_1", "D01"),
    "eligibility_requirements": ("G07_1", "D01"),
    "instrument_requirements": ("G07_1", "D01"),
    "sponsor_and_infrastructure": ("G07_1", "D01"),
    "restrictions_and_lock_ups": ("G07_1", "D01"),
    "special_regimes": ("G07_1", "D01"),
    "procedure_and_timeline": ("G07_1", "D02"),
    "disclosure_at_admission": ("G07_1", "D05"),
    "secondary_admission": ("G07_1", "D01"),
    "common_requirements": ("G07_1", "D01"),  # venue-level common reqs
    "tiers": ("G07_1", "D01"),                # tier structure info
    # 3B parent fields
    "continuing_obligations": ("G07_2", "D01"),
    "suspension": ("G07_3", "D01"),
    "delisting_compulsory": ("G07_4", "D01"),
    "delisting_voluntary": ("G07_4", "D01"),
    "common_obligations": ("G07_2", "D01"),   # venue-level common obligations
    "terminology": ("G07_2", "D01"),          # terminology definitions
    # 3C parent fields
    "monitoring_regime": ("G07_2", "D03"),
    "sanctions": ("G07_2", "D04"),
    "enforcement_practice": ("G07_2", "D04"),
    "common_monitoring": ("G07_2", "D03"),    # venue-level common monitoring
    # Generic / other
    "content": ("G07_1", "D01"),              # catch-all content field
}

# Default cells for additional_findings by source file
_AF_DEFAULTS = {
    "3A": ("G07_1", "D01"),
    "3B": ("G07_2", "D01"),
    "3C": ("G07_2", "D04"),
}


def _distribute_citations(
    matrix: dict, raw_3a: dict, raw_3b: dict, raw_3c: dict,
) -> None:
    """Distribute citations from 3A/3B/3C raw files into matrix cells."""
    for raw_data, default_source in [(raw_3a, "3A"), (raw_3b, "3B"), (raw_3c, "3C")]:
        citations = raw_data.get("citations", [])
        for citation in citations:
            field = citation.get("field", "")

            # Look up matrix cell for this field
            if field in _CITATION_FIELD_MAP:
                phase, ct_short = _CITATION_FIELD_MAP[field]
            elif field == "additional_findings":
                phase, ct_short = _AF_DEFAULTS[default_source]
            else:
                # Fallback: determine phase from source file
                phase_fallback = {"3A": "G07_1", "3B": "G07_2", "3C": "G07_2"}
                ct_fallback = {"3A": "D01", "3B": "D01", "3C": "D04"}
                phase = phase_fallback.get(default_source, "G07_1")
                ct_short = ct_fallback.get(default_source, "D01")
                logger.info("Citation field '%s' not in map — fallback to %s/%s", field, phase, ct_short)

            ct_key = _CONTENT_KEY_MAP.get(ct_short)
            if ct_key is None:
                continue

            cell = matrix.get(phase, {}).get(ct_key)
            if cell is None:
                # Cell was null (N/A) -- create it with citations
                matrix[phase][ct_key] = {"content": [], "citations": [citation]}
            else:
                if "citations" not in cell:
                    cell["citations"] = []
                cell["citations"].append(citation)


def build_matrix_algorithmic(raw_3a: dict, raw_3b: dict, raw_3c: dict) -> dict:
    """
    Build matrix from deterministic field mappings.
    Returns partial matrix (dict) — LLM fields not yet applied.
    """
    matrix = _empty_matrix()

    # --- 3A fields ---
    content_3a = raw_3a.get("content", {})
    for field_key, phase, ct_short, subtitle in _3A_MAPPING:
        field_data = content_3a.get(field_key, {})
        if not isinstance(field_data, dict):
            continue
        desc = field_data.get("description", "")
        src = field_data.get("source", "")
        desc_ru = field_data.get("description_ru", "")
        item = _extract_content_item(desc, src, subtitle, field_key, description_ru=desc_ru)
        _add_item(matrix, phase, ct_short, item)

    # --- 3B fields ---
    content_3b = raw_3b.get("content", {})
    for parent_key, sub_key, phase, ct_short, subtitle in _3B_MAPPING:
        desc, src, desc_ru = _get_field(content_3b, parent_key, sub_key)
        item = _extract_content_item(desc, src, subtitle, f"{parent_key}.{sub_key}", description_ru=desc_ru)
        _add_item(matrix, phase, ct_short, item)

    # --- 3C algorithmic fields ---
    content_3c = raw_3c.get("content", {})
    for parent_key, sub_key, phase, ct_short, subtitle in _3C_ALGORITHMIC_MAPPING:
        desc, src, desc_ru = _get_field(content_3c, parent_key, sub_key)
        item = _extract_content_item(desc, src, subtitle, f"{parent_key}.{sub_key}", description_ru=desc_ru)
        _add_item(matrix, phase, ct_short, item)

    # --- Distribute citations ---
    _distribute_citations(matrix, raw_3a, raw_3b, raw_3c)

    return matrix


def build_matrix_llm_inputs(raw_3a: dict, raw_3b: dict, raw_3c: dict) -> dict:
    """
    Collect inputs needed for the LLM prompt for a single cell.
    Returns dict with all relevant text fields.
    """
    content_3a = raw_3a.get("content", {})
    content_3b = raw_3b.get("content", {})
    content_3c = raw_3c.get("content", {})

    # additional_findings from each query
    af_3a_data = content_3a.get("additional_findings", {})
    af_3b_data = content_3b.get("additional_findings", {})
    af_3c_data = content_3c.get("additional_findings", {})

    def _flat_field(data: dict) -> tuple[str, str, str]:
        if not isinstance(data, dict):
            return "", "", ""
        return data.get("description", ""), data.get("source", ""), data.get("description_ru", "")

    af_3a_desc, af_3a_src, af_3a_desc_ru = _flat_field(af_3a_data)
    af_3b_desc, af_3b_src, af_3b_desc_ru = _flat_field(af_3b_data)
    af_3c_desc, af_3c_src, af_3c_desc_ru = _flat_field(af_3c_data)

    # sanctions
    exchange_sanctions_desc, exchange_sanctions_src, _ = _get_field(content_3c, "sanctions", "exchange_sanctions")
    regulator_sanctions_desc, regulator_sanctions_src, _ = _get_field(content_3c, "sanctions", "regulator_sanctions")

    # monitoring_regime combined text
    monitoring_parts = []
    for sub_key in ["responsible_body", "mechanisms", "sponsor_role", "issuer_reporting_to_exchange"]:
        desc, _, _ = _get_field(content_3c, "monitoring_regime", sub_key)
        if desc:
            monitoring_parts.append(desc)
    monitoring_combined = " | ".join(monitoring_parts)
    monitoring_sources = []
    for sub_key in ["responsible_body", "mechanisms", "sponsor_role", "issuer_reporting_to_exchange"]:
        _, src, _ = _get_field(content_3c, "monitoring_regime", sub_key)
        if src:
            monitoring_sources.append(src)

    return {
        "exchange_sanctions": exchange_sanctions_desc,
        "exchange_sanctions_source": exchange_sanctions_src,
        "regulator_sanctions": regulator_sanctions_desc,
        "regulator_sanctions_source": regulator_sanctions_src,
        "monitoring_combined": monitoring_combined,
        "monitoring_sources": monitoring_sources,
        "af_3a": af_3a_desc,
        "af_3a_source": af_3a_src,
        "af_3a_desc_ru": af_3a_desc_ru,
        "af_3b": af_3b_desc,
        "af_3b_source": af_3b_src,
        "af_3b_desc_ru": af_3b_desc_ru,
        "af_3c": af_3c_desc,
        "af_3c_source": af_3c_src,
        "af_3c_desc_ru": af_3c_desc_ru,
    }


def _build_llm_prompt(cell_id: str, venue_key: str, inputs: dict) -> str:
    """Build the LLM prompt string for a cell."""
    return f"""You are analyzing regulatory content for a securities exchange listing cell.
Cell: {cell_id}, Venue: {venue_key}

TASK 1 - Sanctions phase routing:
The following sanctions text describes enforcement measures. For each distinct sanction type,
determine its primary lifecycle phase:
- G07_2 (maintenance): sanctions for ongoing compliance breaches (fines, censures, etc.)
- G07_3 (suspension): suspension of trading as a measure or during investigation
- G07_4 (removal): compulsory delisting/cancellation as ultimate sanction

Exchange sanctions text: {inputs['exchange_sanctions']}
Regulator sanctions text: {inputs['regulator_sanctions']}

TASK 2 - Monitoring during suspension:
Does the following monitoring text explicitly mention monitoring *during a suspension period*?
If yes, extract that specific fragment (verbatim or paraphrased). If no, return null.
Monitoring text: {inputs['monitoring_combined']}

TASK 3 - Additional findings routing:
Route each additional_findings text to the appropriate matrix cell.
3A additional_findings: {inputs['af_3a']}
3B additional_findings: {inputs['af_3b']}
3C additional_findings: {inputs['af_3c']}

Return JSON:
{{
  "sanctions": {{
    "G07_2": "text | null",
    "G07_3": "text | null",
    "G07_4": "text | null"
  }},
  "monitoring_suspension": "text | null",
  "additional_findings": [
    {{"text": "...", "phase": "G07_1|G07_2|G07_3|G07_4", "content_type": "D01|D02|D03|D04|D05", "source_query": "3A|3B|3C"}}
  ]
}}

Rules:
- If a sanctions text doesn't clearly fit G07_3 or G07_4, assign to G07_2
- For additional_findings, if unable to determine -> return {{"text": "...", "phase": "UNKNOWN", "content_type": "UNKNOWN", "source_query": "..."}}
- UNKNOWN items are not added to the matrix
- Keep phase and content_type codes exactly as shown"""


def apply_llm_output(matrix: dict, llm_output: LLMMatrixOutput, llm_inputs: dict) -> dict:
    """
    Apply LLM routing results to the algorithmic matrix.
    Returns updated matrix (modified in-place).
    """
    # Build combined source for sanctions
    sanctions_source_parts = []
    if llm_inputs.get("exchange_sanctions_source"):
        sanctions_source_parts.append(llm_inputs["exchange_sanctions_source"])
    if llm_inputs.get("regulator_sanctions_source"):
        sanctions_source_parts.append(llm_inputs["regulator_sanctions_source"])
    sanctions_source = "; ".join(s for s in sanctions_source_parts if s)

    # 1. Sanctions routing
    sanctions = llm_output.sanctions
    for phase_key, text in [("G07_2", sanctions.G07_2), ("G07_3", sanctions.G07_3), ("G07_4", sanctions.G07_4)]:
        if text:
            item = _extract_content_item(
                description=text,
                source=sanctions_source,
                subtitle="Санкции (биржа + регулятор)",
                origin_field="sanctions_llm_routed",
            )
            _add_item(matrix, phase_key, "D04", item)

    # 2. Monitoring during suspension
    if llm_output.monitoring_suspension:
        monitoring_source = "; ".join(s for s in llm_inputs.get("monitoring_sources", []) if s)
        item = _extract_content_item(
            description=llm_output.monitoring_suspension,
            source=monitoring_source,
            subtitle="Мониторинг при приостановке",
            origin_field="monitoring_regime_suspension",
        )
        _add_item(matrix, "G07_3", "D03", item)

    # 3. Additional findings (skip UNKNOWN)
    for af in llm_output.additional_findings:
        if af.phase == "UNKNOWN" or af.content_type == "UNKNOWN":
            continue
        # Determine source and description_ru for this finding
        source_map = {
            "3A": llm_inputs.get("af_3a_source", ""),
            "3B": llm_inputs.get("af_3b_source", ""),
            "3C": llm_inputs.get("af_3c_source", ""),
        }
        desc_ru_map = {
            "3A": llm_inputs.get("af_3a_desc_ru", ""),
            "3B": llm_inputs.get("af_3b_desc_ru", ""),
            "3C": llm_inputs.get("af_3c_desc_ru", ""),
        }
        src = source_map.get(af.source_query, "")
        desc_ru = desc_ru_map.get(af.source_query, "")
        item = _extract_content_item(
            description=af.text,
            source=src,
            subtitle="Дополнительные находки",
            origin_field=f"additional_findings_{af.source_query}",
            description_ru=desc_ru,
        )
        _add_item(matrix, af.phase, af.content_type, item)

    return matrix


def _extract_metadata(raw_3a: dict, raw_3b: dict, matrix: dict) -> dict:
    """Extract cell metadata and compute validation fields."""
    content_3a = raw_3a.get("content", {})
    content_3b = raw_3b.get("content", {})

    # Tier name
    tier = (
        content_3a.get("tier_name")
        or raw_3a.get("tier_name_from_parallel")
        or raw_3b.get("tier_name_from_parallel")
        or ""
    )

    # Terminology from 3B
    terminology_raw = content_3b.get("terminology", {})
    terminology = {}
    if isinstance(terminology_raw, dict):
        for k, v in terminology_raw.items():
            if k != "source" and isinstance(v, str):
                terminology[k] = v

    # Validation: which phases have any content?
    phases_covered = []
    phases_not_covered = []
    for phase in ["G07_1", "G07_2", "G07_3", "G07_4"]:
        phase_data = matrix.get(phase, {})
        has_content = any(
            isinstance(cell, dict) and cell.get("content")
            for cell in phase_data.values()
        )
        if has_content:
            phases_covered.append(phase)
        else:
            phases_not_covered.append(phase)

    validation_status = "green" if phases_not_covered == [] else (
        "yellow" if len(phases_covered) >= 2 else "red"
    )

    return {
        "tier": tier,
        "terminology": terminology,
        "validation_status": validation_status,
        "phases_covered": phases_covered,
        "phases_not_covered": phases_not_covered,
    }


def build_matrix_for_cell(cell_dir: Path, llm_chain) -> dict:
    """
    Full pipeline for one cell: load 3A/3B/3C, algorithmic mapping, LLM, assemble.

    llm_chain: a langchain chain (llm.with_structured_output(LLMMatrixOutput))
    Returns the final matrix dict (not saved).
    """
    cell_id = cell_dir.name

    # Load raw files
    path_3a = cell_dir / "3A_raw.json"
    path_3b = cell_dir / "3B_raw.json"
    path_3c = cell_dir / "3C_raw.json"

    raw_3a = json.loads(path_3a.read_text(encoding="utf-8")) if path_3a.exists() else {}
    raw_3b = json.loads(path_3b.read_text(encoding="utf-8")) if path_3b.exists() else {}
    raw_3c = json.loads(path_3c.read_text(encoding="utf-8")) if path_3c.exists() else {}

    venue_key = raw_3a.get("venue_key") or raw_3b.get("venue_key") or raw_3c.get("venue_key") or ""
    instrument_class = raw_3a.get("instrument_class") or ""

    # Build algorithmic matrix
    matrix = build_matrix_algorithmic(raw_3a, raw_3b, raw_3c)

    # Collect LLM inputs
    llm_inputs = build_matrix_llm_inputs(raw_3a, raw_3b, raw_3c)

    # We return the llm_inputs together with matrix for batch processing
    return {
        "cell_id": cell_id,
        "venue_key": venue_key,
        "instrument_class": instrument_class,
        "matrix": matrix,
        "llm_inputs": llm_inputs,
        "raw_3a": raw_3a,
        "raw_3b": raw_3b,
        "raw_3c": raw_3c,
    }


def _assemble_output(
    cell_id: str,
    venue_key: str,
    instrument_class: str,
    matrix: dict,
    raw_3a: dict,
    raw_3b: dict,
) -> dict:
    """Assemble the final matrix.json structure."""
    meta = _extract_metadata(raw_3a, raw_3b, matrix)

    return {
        "cell_id": cell_id,
        "venue_key": venue_key,
        "tier": meta["tier"],
        "instrument_class": instrument_class,
        "matrix": matrix,
        "metadata": {
            "validation_status": meta["validation_status"],
            "phases_covered": meta["phases_covered"],
            "phases_not_covered": meta["phases_not_covered"],
            "terminology": meta["terminology"],
        },
    }


def _get_llm(model: str = LLM_FAST_MODEL):
    """Create and return a ChatOpenAI LLM instance."""
    import os
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=model, api_key=os.environ["OPENAI_API_KEY"], temperature=0)


def _iter_cell_dirs():
    """Yield all cell dirs that have 3A_raw.json."""
    for country_dir in COUNTRIES_DIR.iterdir():
        if not country_dir.is_dir():
            continue
        l3_dir = country_dir / "level_3"
        if not l3_dir.exists():
            continue
        for venue_dir in l3_dir.iterdir():
            if not venue_dir.is_dir():
                continue
            for cell_dir in venue_dir.iterdir():
                if not cell_dir.is_dir():
                    continue
                if (cell_dir / "3A_raw.json").exists():
                    yield cell_dir


def build_matrix_all(venues: list[str] | None = None, llm=None) -> None:
    """
    Iterate COUNTRIES_DIR, find all cell dirs, build matrix.json. Idempotent.

    If llm is None, creates one using LLM_FAST_MODEL.
    Collects all prompts first, batch-calls LLM, then assembles and saves.

    venues: optional list of venue_key strings to filter. None = all venues.
    """
    from langchain_core.messages import HumanMessage

    if llm is None:
        llm = _get_llm(LLM_FAST_MODEL)

    chain = llm.with_structured_output(LLMMatrixOutput)

    # --- Phase 1: Discover cells, build algorithmic matrices ---
    pending = []  # list of cell data dicts
    skipped = 0

    for cell_dir in _iter_cell_dirs():
        matrix_path = cell_dir / "matrix.json"
        if matrix_path.exists():
            logger.info("SKIP %s — matrix.json already exists", cell_dir.name)
            skipped += 1
            continue

        # Filter by venue if requested
        if venues is not None:
            # Determine venue_key from directory structure (parent of cell_dir)
            venue_key_from_path = cell_dir.parent.name
            if venue_key_from_path not in venues:
                continue

        try:
            cell_data = build_matrix_for_cell(cell_dir, chain)
            cell_data["cell_dir"] = cell_dir
            pending.append(cell_data)
        except Exception as exc:
            logger.error("Error loading cell %s: %s", cell_dir.name, exc, exc_info=True)

    logger.info(
        "Matrix builder: %d cells to process, %d skipped (already done)",
        len(pending),
        skipped,
    )

    if not pending:
        logger.info("No cells to process — done.")
        return

    # --- Phase 2: Batch LLM call ---
    prompts = [
        _build_llm_prompt(
            cell["cell_id"],
            cell["venue_key"],
            cell["llm_inputs"],
        )
        for cell in pending
    ]

    llm_results: list[LLMMatrixOutput | None] = [None] * len(pending)

    try:
        results = chain.batch(
            [[HumanMessage(content=p)] for p in prompts],
            config={"max_concurrency": 50},
        )
        for i, res in enumerate(results):
            llm_results[i] = res
        logger.info("LLM batch completed for %d cells", len(pending))
    except Exception as exc:
        logger.warning(
            "LLM batch call failed for all cells: %s. Saving algorithmic-only matrices.",
            exc,
        )

    # --- Phase 3: Apply LLM results, assemble, save ---
    saved = 0
    errors = 0

    for i, cell in enumerate(pending):
        cell_id = cell["cell_id"]
        cell_dir = cell["cell_dir"]
        matrix = cell["matrix"]
        llm_inputs = cell["llm_inputs"]

        llm_output = llm_results[i]

        if llm_output is not None:
            try:
                matrix = apply_llm_output(matrix, llm_output, llm_inputs)
            except Exception as exc:
                logger.warning(
                    "LLM matrix apply failed for cell %s: %s", cell_id, exc
                )
        else:
            logger.warning(
                "LLM matrix output missing for cell %s — saving algorithmic-only matrix",
                cell_id,
            )

        # Assemble final output
        try:
            output = _assemble_output(
                cell_id=cell_id,
                venue_key=cell["venue_key"],
                instrument_class=cell["instrument_class"],
                matrix=matrix,
                raw_3a=cell["raw_3a"],
                raw_3b=cell["raw_3b"],
            )

            matrix_path = cell_dir / "matrix.json"
            matrix_path.write_text(
                json.dumps(output, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("Saved matrix.json for %s", cell_id)
            saved += 1
        except Exception as exc:
            logger.error(
                "Failed to save matrix.json for %s: %s", cell_id, exc, exc_info=True
            )
            errors += 1

    logger.info(
        "Matrix builder complete: %d saved, %d errors, %d skipped",
        saved, errors, skipped,
    )
