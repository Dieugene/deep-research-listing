"""
Level 4: Regulatory objectives and justifications.

Per-jurisdiction Parallel API deep research (text output, processor=pro),
followed by LLM post-processing into structured JSON (level4.json)
and validation (level4_validation.json).

Steps:
  parallel    — Launch Parallel API tasks, poll, save 4A_raw.json
  postprocess — LLM structured extraction + translation → level4.json
  validate    — Content validation → level4_validation.json
  all         — Run all three steps
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional, Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from pipeline.config import (
    LLM_SMART_MODEL,
    COUNTRIES_DIR,
    LEVEL4_STATE_FILE,
    LEVEL4_LOG_FILE,
    PILOT_JURISDICTIONS,
    PILOT_VENUES,
    VENUE_BY_KEY,
    get_country_level1_dir,
    get_country_level4_dir,
)
from pipeline.storage import load_json, save_json, now_iso
from pipeline.logging_setup import get_logger

logger = get_logger("level4", LEVEL4_LOG_FILE)


# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------

def _get_llm(model: str = LLM_SMART_MODEL) -> ChatOpenAI:
    return ChatOpenAI(model=model, api_key=os.environ["OPENAI_API_KEY"], temperature=0)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class Problem(BaseModel):
    description: str = ""
    description_ru: str = ""
    articulated_by: str = ""
    period: str = ""
    source: str = ""


class Contradiction(BaseModel):
    objective_a: str = ""
    objective_b: str = ""
    resolution: str = ""
    resolution_ru: str = ""
    period: str = ""
    source: str = ""


class ParameterAsTool(BaseModel):
    parameter_description: str = ""
    parameter_description_ru: str = ""
    problem_addressed: str = ""
    calibration_debate: str = ""
    period: str = ""
    source: str = ""


class Reform(BaseModel):
    description: str = ""
    description_ru: str = ""
    driver: str = ""
    opposition: str = ""
    year: str = ""
    source: str = ""


class Level4Result(BaseModel):
    jurisdiction: str = ""
    problems: list[Problem] = []
    contradictions: list[Contradiction] = []
    parameters_as_tools: list[ParameterAsTool] = []
    reforms: list[Reform] = []
    sources_summary: list[str] = []


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_level4_prompt(
    jurisdiction_en: str,
    regulator_name: str,
    regulator_type: str,
    venue_names: list[str],
    supranational_flag: bool,
    supranational_framework: Optional[str],
) -> str:
    """Build the Level 4 Parallel API prompt from jurisdiction_card data."""

    venues_str = "; ".join(venue_names) if venue_names else "—"
    supranational_note = ""
    if supranational_flag and supranational_framework:
        supranational_note = f"\nSupranational framework: {supranational_framework}"

    return f"""Jurisdiction: {jurisdiction_en}
Securities regulator: {regulator_name} ({regulator_type}){supranational_note}
Main trading venues: {venues_str}


Research the regulatory policy debate around securities listing and admission to trading in {jurisdiction_en}. Focus on substance — problems identified, conflicts between objectives, and how regulatory parameters were used to address them.

A. REGULATORY PROBLEMS DISCUSSED

What problems related to listing and admission to trading have been discussed in {jurisdiction_en} — both at the official level (regulator statements, consultation papers, legislative reviews, regulatory impact assessments) and in public/analytical discourse (industry associations, academic research, market commentary)?

For each problem identified:
- What was the problem (e.g., declining IPO numbers, insufficient investor protection, regulatory burden on SMEs, low liquidity of secondary market, capital flight to competing venues)
- Who articulated it (regulator, exchange, industry body, academic, government)
- Approximate period (years/decade — precision to the year is sufficient, greater detail not needed)
- Source (document, publication)

B. REGULATORY CONTRADICTIONS AND PRIORITIES

What contradictions between regulatory objectives have been identified or debated?

Examples of contradiction types (not exhaustive — find what actually exists in this jurisdiction):
- Investor protection vs attracting issuers (stricter rules protect investors but deter listings)
- Market quality vs market development (high thresholds ensure quality but exclude smaller companies)
- National competitiveness vs international harmonisation (differentiation vs convergence)
- Public market access vs investor sophistication (retail participation vs professional-only segments)

For each contradiction found:
- Which objectives conflicted
- How was the trade-off resolved (which objective was prioritised, what compromise was reached)
- Approximate period
- Source

C. REGULATORY PARAMETERS AS TOOLS

Which specific listing parameters (thresholds, requirements, procedures) were explicitly discussed as instruments for addressing the identified problems?

Do not list all listing rules — only those where there is evidence in regulatory documents or public discourse that the parameter was DELIBERATELY CHOSEN or CALIBRATED to address a specific problem or achieve a specific objective.

For each:
- Which parameter (e.g., free float threshold, market cap minimum, sponsor requirement, lock-up period)
- What problem it was intended to address
- Was the calibration debated (e.g., "25% vs 10% free float — arguments for and against")
- Approximate period of the discussion/decision
- Source

D. REFORMS AND THEIR DRIVERS

What significant reforms of the listing/admission framework have occurred in {jurisdiction_en} in the last 10–15 years?

For each reform:
- What changed (briefly — the current rules are already collected separately)
- What problem or objective drove the reform
- Was there opposition or alternative proposals
- Approximate year
- Source (consultation paper, explanatory memorandum, parliamentary record)


Preferred sources (in order of priority):
1. Consultation papers and regulatory impact assessments by {regulator_name}
2. Explanatory memoranda to legislation
3. Strategic documents and annual reports of {regulator_name} and main venues
4. Parliamentary / legislative committee records
5. Industry body publications
6. Academic research on capital market regulation in {jurisdiction_en}
7. Regulator speeches and public statements

Do NOT rely on generic descriptions of listing rules. The rules themselves are already collected. This query is about the REASONING and DEBATE behind the rules.

For all findings — note the approximate time period (decade or specific years). Regulatory objectives and priorities change over time. Capturing this evolution is important.

Precision: year or period (e.g., "2015–2018", "post-GFC", "following the 2024 reform"). Do not attempt month-level dating."""


# ---------------------------------------------------------------------------
# Prompt data extraction from jurisdiction_card
# ---------------------------------------------------------------------------

def _get_jurisdiction_prompt_data(name_ru: str) -> Optional[dict]:
    """
    Load jurisdiction_card and extract data needed for prompt.
    Returns dict with keys: jurisdiction_en, regulator_name, regulator_type,
    venue_names, supranational_flag, supranational_framework.
    """
    card = load_json(get_country_level1_dir(name_ru) / "jurisdiction_card.json")
    if not card:
        logger.warning("No jurisdiction_card.json for %s", name_ru)
        return None

    # Jurisdiction English name — look up from PILOT_JURISDICTIONS by name_ru
    jur_config = next((j for j in PILOT_JURISDICTIONS if j["name_ru"] == name_ru), None)
    if not jur_config:
        logger.warning("No PILOT_JURISDICTIONS entry for %s", name_ru)
        return None

    jurisdiction_en = jur_config["name_en"]

    # Venue names from PILOT_VENUES filtered by jurisdiction
    pilot_venue_keys = jur_config.get("venues", [])
    venue_names = [
        VENUE_BY_KEY[vk]["venue_name_english"]
        for vk in pilot_venue_keys
        if vk in VENUE_BY_KEY
    ]

    return {
        "jurisdiction_en": jurisdiction_en,
        "regulator_name": card.get("regulator_name", "Securities Regulator"),
        "regulator_type": card.get("regulator_type", ""),
        "venue_names": venue_names,
        "supranational_flag": card.get("supranational_flag", False),
        "supranational_framework": card.get("supranational_framework"),
    }


# ---------------------------------------------------------------------------
# Step 1: Launch Parallel API tasks + poll
# ---------------------------------------------------------------------------

def run_level4_parallel() -> None:
    """
    For each pilot jurisdiction: launch Parallel API deep research task (text output, pro).
    Launch all tasks first, then poll all concurrently.
    Idempotency: skip if 4A_raw.json already exists.
    """
    from pipeline.parallel_runner import launch_task, poll_all, load_state as pr_load_state

    logger.info("Starting Level 4 Parallel API research")

    state_file = LEVEL4_STATE_FILE
    state = pr_load_state(state_file)

    tasks_to_poll: list[tuple[str, Any]] = []
    skipped = 0

    # Pass 1: launch all tasks
    seen_name_ru: set[str] = set()
    for jur in PILOT_JURISDICTIONS:
        name_ru = jur["name_ru"]
        if name_ru in seen_name_ru:
            continue
        seen_name_ru.add(name_ru)

        level4_dir = get_country_level4_dir(name_ru)
        raw_path = level4_dir / "4A_raw.json"

        if raw_path.exists():
            logger.info("[SKIP] 4A_raw.json already exists for %s", name_ru)
            skipped += 1
            continue

        prompt_data = _get_jurisdiction_prompt_data(name_ru)
        if not prompt_data:
            logger.warning("[SKIP] Could not build prompt for %s", name_ru)
            skipped += 1
            continue

        prompt = _build_level4_prompt(**prompt_data)

        task_key = f"level4_{name_ru}"
        try:
            launch_task(
                task_key=task_key,
                prompt=prompt,
                output_schema=None,   # text output
                state=state,
                processor="pro",
                state_file=state_file,
            )
        except Exception as exc:
            logger.error("[ERROR] Failed to launch task for %s: %s", name_ru, exc)
            continue

        def _make_save_fn(save_path: Path, jurisdiction: str):
            def save_fn(content) -> Path:
                # text output: content is a string
                text = content if isinstance(content, str) else str(content)
                level4_dir_local = save_path.parent
                level4_dir_local.mkdir(parents=True, exist_ok=True)
                save_json(save_path, {"jurisdiction": jurisdiction, "raw_text": text, "retrieved_at": now_iso()})
                return save_path
            return save_fn

        tasks_to_poll.append((task_key, _make_save_fn(raw_path, prompt_data["jurisdiction_en"])))

    if not tasks_to_poll:
        logger.info("No Level 4 tasks to poll (all skipped or already done). Skipped: %d", skipped)
        return

    logger.info("Launched %d tasks — polling all concurrently", len(tasks_to_poll))

    poll_results = poll_all(tasks_to_poll, state, state_file)

    completed = sum(1 for v in poll_results.values() if v is not None)
    failed = len(poll_results) - completed

    for task_key, content in poll_results.items():
        jur_name = task_key.removeprefix("level4_")
        if content is not None:
            logger.info("[SAVED] 4A_raw.json for %s", jur_name)
        else:
            entry = state["tasks"].get(task_key, {})
            if entry.get("status") == "done":
                completed += 1
                failed -= 1
                logger.info("[ALREADY_DONE] %s", jur_name)
            else:
                logger.error("[ERROR] Level 4 parallel failed for %s", jur_name)

    logger.info(
        "Level 4 parallel complete: %d completed, %d skipped, %d failed",
        completed, skipped, failed,
    )


# ---------------------------------------------------------------------------
# Step 2: LLM post-processing → level4.json
# ---------------------------------------------------------------------------

_POSTPROCESS_SYSTEM_PROMPT = """You are an expert analyst in regulatory policy and securities market regulation.

You will receive a Deep Research report about securities listing regulation in a specific jurisdiction.

Your task: STRUCTURE and TRANSLATE the report. NOT summarize, NOT compress.

CRITICAL RULES:
1. DO NOT compress or simplify. If the source material contains detailed explanation, preserve the full detail.
   - Bad: "FCA reduced free float requirement."
   - Good: "FCA reduced the minimum free float threshold from 25% to 10% for equity shares (commercial companies) as part of the 2024 UKLR reform, explicitly prioritising competitiveness over ex-ante structural investor protections. The change was contested by the Investment Association, which argued that lower free float reduces liquidity and increases governance risk."
2. DO NOT invent content. If the source material is sparse on a topic, the output should reflect that sparseness — do not fill gaps.
3. `description` and `description_ru` fields must be FULL PARAGRAPHS, not one-liners. Include: what the problem/reform/contradiction was, who articulated it, what the evidence was, and what was at stake.
4. `source` field: write the FULL citation — document title AND URL. A REFERENCES LOOKUP TABLE will be provided. Look up numbered references like [1], [2] and replace with: "Document Title — https://url". Multiple sources: separate with "; ".
   - Bad source: "[3] [7]"
   - Good source: "PS21/22: Primary Market Effectiveness Review — http://www.fca.org.uk/publication/policy/ps21-22.pdf; Capital markets reform in the UK — https://www.davispolk.com/insights/client-update/capital-markets-reform-uk"
5. Extract ALL entries — do not skip any problem, contradiction, parameter discussion, or reform found in the text.
6. `articulated_by`: use one of: regulator / exchange / industry / academic / government
7. `period` and `year`: keep as-is (e.g. "2015–2018", "post-GFC", "2024")
"""


def _parse_references(raw_text: str) -> dict[str, str]:
    """
    Parse numbered references from the References section of the raw text.
    Returns {ref_number_str: "Title — URL"}.
    """
    import re
    refs: dict[str, str] = {}

    # Find the references section
    for marker in ["## References", "## Sources", "## Bibliography"]:
        idx = raw_text.rfind(marker)
        if idx != -1:
            refs_text = raw_text[idx:]
            break
    else:
        return refs

    # Match lines like: 1. *Title*. https://... or 1. Title — https://...
    pattern = re.compile(
        r'^\s*(\d+)\.\s+\*?([^\n*]+?)\*?\.\s+(https?://\S+)',
        re.MULTILINE,
    )
    for m in pattern.finditer(refs_text):
        num, title, url = m.group(1), m.group(2).strip(), m.group(3).strip()
        refs[num] = f"{title} — {url}"

    # Also try simpler format: 1. Title. URL or 1. *Title*. URL
    if not refs:
        pattern2 = re.compile(r'^\s*(\d+)\.\s+(.+?)(https?://\S+)', re.MULTILINE)
        for m in pattern2.finditer(refs_text):
            num, title, url = m.group(1), m.group(2).strip().rstrip('—').strip(), m.group(3).strip()
            refs[num] = f"{title} — {url}"

    return refs


def _build_postprocess_prompt(raw_text: str, jurisdiction_en: str) -> str:
    refs = _parse_references(raw_text)
    refs_table = ""
    if refs:
        lines = [f"[{num}]: {citation}" for num, citation in sorted(refs.items(), key=lambda x: int(x[0]))]
        refs_table = "\n\nREFERENCES LOOKUP TABLE (use these to resolve [1], [2], etc. in the text):\n" + "\n".join(lines)

    return f"""Extract ALL structured entries from the following Deep Research report about {jurisdiction_en}.

INSTRUCTIONS:
- description / description_ru: full paragraphs with complete detail — do not compress
- source: resolve numbered refs like [1] using the REFERENCES LOOKUP TABLE — write "Title — URL"
- Translate description_ru, resolution_ru, parameter_description_ru, description_ru to Russian
- Keep source, period, year in original language
- Extract every problem, contradiction, parameter discussion, and reform found in the text{refs_table}

Report text:
{raw_text}
"""


def run_level4_postprocess(llm: ChatOpenAI) -> None:
    """
    For each jurisdiction with 4A_raw.json: run LLM structured extraction + translation.
    Saves level4.json.
    Idempotency: skip if level4.json already exists.
    """
    logger.info("Starting Level 4 post-processing")

    work_items: list[dict] = []

    seen_name_ru: set[str] = set()
    for jur in PILOT_JURISDICTIONS:
        name_ru = jur["name_ru"]
        if name_ru in seen_name_ru:
            continue
        seen_name_ru.add(name_ru)

        level4_dir = get_country_level4_dir(name_ru)
        raw_path = level4_dir / "4A_raw.json"
        level4_path = level4_dir / "level4.json"

        if level4_path.exists():
            logger.info("[SKIP] level4.json already exists for %s", name_ru)
            continue

        if not raw_path.exists():
            logger.info("[SKIP] No 4A_raw.json for %s — run parallel step first", name_ru)
            continue

        raw_data = load_json(raw_path)
        if not raw_data:
            logger.warning("4A_raw.json empty for %s — skipping", name_ru)
            continue

        raw_text = raw_data.get("raw_text", "")
        jurisdiction_en = raw_data.get("jurisdiction", jur["name_en"])

        work_items.append({
            "name_ru": name_ru,
            "jurisdiction_en": jurisdiction_en,
            "level4_path": level4_path,
            "prompt": _build_postprocess_prompt(raw_text, jurisdiction_en),
        })

    if not work_items:
        logger.info("No Level 4 post-processing needed — all done or no raw data found")
        return

    logger.info("Running Level 4 post-processing batch for %d jurisdictions", len(work_items))

    chain = llm.with_structured_output(Level4Result)

    results = chain.batch(
        [
            [SystemMessage(content=_POSTPROCESS_SYSTEM_PROMPT), HumanMessage(content=item["prompt"])]
            for item in work_items
        ],
        config={"max_concurrency": 50},
        return_exceptions=True,
    )

    completed = 0
    failed = 0

    for item, result in zip(work_items, results):
        name_ru: str = item["name_ru"]
        level4_path: Path = item["level4_path"]

        if isinstance(result, Exception):
            logger.error("[ERROR] Post-processing failed for %s: %s", name_ru, result)
            failed += 1
            continue

        level4_result: Level4Result = result
        level4_result.jurisdiction = item["jurisdiction_en"]

        level4_path.parent.mkdir(parents=True, exist_ok=True)
        save_json(level4_path, level4_result.model_dump())

        logger.info(
            "[SAVED] level4.json for %s — %d problems, %d contradictions, %d params, %d reforms",
            name_ru,
            len(level4_result.problems),
            len(level4_result.contradictions),
            len(level4_result.parameters_as_tools),
            len(level4_result.reforms),
        )
        completed += 1

    logger.info("Level 4 post-processing complete: %d completed, %d failed", completed, failed)


# ---------------------------------------------------------------------------
# Step 3: Validation → level4_validation.json
# ---------------------------------------------------------------------------

def run_level4_validate() -> None:
    """
    Validate level4.json for each jurisdiction.
    Saves level4_validation.json.
    Idempotency: skip if level4_validation.json already exists.

    Validation logic:
      GREEN  — all four sections non-empty
      YELLOW — at least two sections non-empty
      RED    — fewer than two sections non-empty (essentially empty result)
    """
    logger.info("Starting Level 4 validation")

    seen_name_ru: set[str] = set()
    for jur in PILOT_JURISDICTIONS:
        name_ru = jur["name_ru"]
        if name_ru in seen_name_ru:
            continue
        seen_name_ru.add(name_ru)

        level4_dir = get_country_level4_dir(name_ru)
        level4_path = level4_dir / "level4.json"
        validation_path = level4_dir / "level4_validation.json"

        if validation_path.exists():
            logger.info("[SKIP] level4_validation.json already exists for %s", name_ru)
            continue

        if not level4_path.exists():
            logger.info("[SKIP] No level4.json for %s — run postprocess step first", name_ru)
            continue

        data = load_json(level4_path)
        if not data:
            save_json(validation_path, {
                "jurisdiction": name_ru,
                "validation_status": "red",
                "notes": "level4.json is empty or unreadable",
            })
            continue

        sections = {
            "problems": len(data.get("problems", [])),
            "contradictions": len(data.get("contradictions", [])),
            "parameters_as_tools": len(data.get("parameters_as_tools", [])),
            "reforms": len(data.get("reforms", [])),
        }
        non_empty = sum(1 for v in sections.values() if v > 0)

        if non_empty == 4:
            status = "green"
        elif non_empty >= 2:
            status = "yellow"
        else:
            status = "red"

        notes = f"sections: {sections}"

        save_json(validation_path, {
            "jurisdiction": name_ru,
            "validation_status": status,
            "section_counts": sections,
            "notes": notes,
        })

        logger.info(
            "[VALIDATED] %s — status=%s, non_empty_sections=%d/4",
            name_ru, status, non_empty,
        )

    logger.info("Level 4 validation complete")


# ---------------------------------------------------------------------------
# Run all steps
# ---------------------------------------------------------------------------

def run_level4_all(llm: ChatOpenAI) -> None:
    """Run all Level 4 steps: parallel → postprocess → validate."""
    logger.info("========== Level 4 Start ==========")
    logger.info("--- Step 1: Parallel API research ---")
    run_level4_parallel()
    logger.info("--- Step 2: LLM post-processing ---")
    run_level4_postprocess(llm=llm)
    logger.info("--- Step 3: Validation ---")
    run_level4_validate()
    logger.info("========== Level 4 Complete ==========")
