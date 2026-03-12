# Диагностический replay-скрипт для анализа сетевых ошибок.
# Не требует основного кода проекта.
#
# Что нужно для запуска:
#   pip install python-dotenv langchain-openai langchain-core
#   Положить рядом: .env (с OPENAI_API_KEY и опционально OPENAI_BASE_URL)
#   Положить рядом: папку diag_prompts/ с .txt файлами промптов
#
# Запуск:
#   python network_diag_replay.py

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Load .env from the same directory as this script
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=_SCRIPT_DIR / ".env")

# ---------------------------------------------------------------------------
# Pydantic models (duplicated from phase2_runner — no project imports)
# ---------------------------------------------------------------------------

class ParameterEntry(BaseModel):
    parameter_id: str        # "П01", "П22", or "ADDITIONAL_1" etc.
    parameter_name: str
    status: str              # "found" | "not_applicable" | "data_not_found"
    description: str         # 6-question text; empty string if not found/not applicable
    note: str = ""           # brief explanation for not_applicable; empty otherwise


class Pass1Result(BaseModel):
    group_id: str
    instrument_class: str
    parameters: list[ParameterEntry]
    additional_parameters: list[ParameterEntry]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # --- Environment info ---
    base_url = os.environ.get("OPENAI_BASE_URL", "(not set — using OpenAI default)")
    api_key_raw = os.environ.get("OPENAI_API_KEY", "")
    api_key_masked = api_key_raw[:10] + "..." if len(api_key_raw) >= 10 else "(short/missing)"

    print("=" * 70)
    print("DIAG REPLAY: Phase 2 Pass 1 — from saved prompts")
    print("=" * 70)
    print(f"OPENAI_BASE_URL : {base_url}")
    print(f"OPENAI_API_KEY  : {api_key_masked}")
    print(f"LLM model       : gpt-5")
    print("=" * 70)
    print()

    # --- Load prompts from diag_prompts/ ---
    prompts_dir = _SCRIPT_DIR / "diag_prompts"
    if not prompts_dir.exists():
        print(f"[ERROR] Prompt directory not found: {prompts_dir}")
        return

    prompt_files = sorted(prompts_dir.glob("*.txt"))
    if not prompt_files:
        print(f"[ERROR] No .txt files found in: {prompts_dir}")
        return

    work_items = []
    for pf in prompt_files:
        group_id = pf.stem
        prompt_text = pf.read_text(encoding="utf-8")
        work_items.append({"group_id": group_id, "prompt": prompt_text})
        print(f"[LOADED] {pf.name}  ({len(prompt_text)} chars)")

    print(f"\nLoaded {len(work_items)} prompts. Starting batch call...")
    print(f"max_concurrency=50, return_exceptions=True")
    print()

    # --- LLM / chain ---
    llm = ChatOpenAI(model="gpt-5", api_key=os.environ["OPENAI_API_KEY"], temperature=0)
    chain = llm.with_structured_output(Pass1Result, method="function_calling")

    # --- Batch call ---
    prompts = [item["prompt"] for item in work_items]

    t_start = time.perf_counter()
    results = chain.batch(
        [[HumanMessage(content=p)] for p in prompts],
        config={"max_concurrency": 50},
        return_exceptions=True,
    )
    t_elapsed = time.perf_counter() - t_start

    print(f"Batch call finished in {t_elapsed:.2f}s")
    print()

    # --- Report results ---
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)

    for item, result in zip(work_items, results):
        group_id = item["group_id"]
        if isinstance(result, Exception):
            exc_type = type(result).__name__
            print(f"[FAIL]  {group_id}")
            print(f"        Exception type : {exc_type}")
            print(f"        Message        : {result}")
        else:
            n_params = len(result.parameters)
            n_add = len(result.additional_parameters)
            print(f"[OK]    {group_id}")
            print(f"        parameters={n_params}  additional={n_add}")
        print()

    print(f"Total wall time: {t_elapsed:.2f}s")
    print("Done.")


if __name__ == "__main__":
    main()
