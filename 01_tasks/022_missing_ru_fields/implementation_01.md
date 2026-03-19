# Task 022: Implementation Report

## Status: Done

## Files Created / Modified

| Action | File |
|--------|------|
| CREATED | `02_src/pipeline/translate_ru_fields.py` |
| MODIFIED | `02_src/run_pipeline.py` |
| CREATED | `02_src/tools/run_missing_ru_catchup.py` |

---

## 1. `02_src/pipeline/translate_ru_fields.py`

New module with 6 functions:

### A. `translate_jurisdiction_notes(llm, jurisdictions=None)`
- Reads `jurisdiction_card.json` for each jurisdiction
- Translates `notes` → `notes_ru` using `TextTranslation` Pydantic model
- Idempotent: skips if `notes_ru` already filled

### B. `translate_tier_names(llm, jurisdictions=None)`
- Iterates all `level_3/<venue>/<cell>/` directories
- Reads `content.tier_name` from `3A_raw.json`
- Writes `tier_ru` into `pass2_ru.json` at top level
- Idempotent: skips cells where `tier_ru` already filled

### C. `translate_additional_param_labels(llm, jurisdictions=None)`
- Iterates all `pass2_ru.json` files
- Finds parameters where `parameter_id` starts with `"ADDITIONAL"`
- Translates `parameter_name` → `param_label_ru` using `TextTranslation`
- Idempotent: skips params where `param_label_ru` already filled
- Atomic save once per file (collects all changes then writes)

### D. `translate_reforms_fields(llm, jurisdictions=None)`
- Reads `level4.json` for each jurisdiction
- Translates `reforms[].driver` + `reforms[].opposition` as a pair using `ReformTranslation`
- Writes `driver_ru` and `opposition_ru` back to reforms
- Idempotent: skips reforms where both `_ru` fields are already filled

### E. `translate_ptools_fields(llm, jurisdictions=None)`
- Reads `level4.json` for each jurisdiction
- Translates `parameters_as_tools[].problem_addressed` + `.calibration_debate` as a pair using `PToolTranslation`
- Writes `problem_addressed_ru` and `calibration_debate_ru` back
- Idempotent: skips records where both `_ru` fields are already filled

### F. `normalize_param_ids(jurisdictions=None)` — no LLM
- Iterates all `pass2_ru.json` files
- Replaces Latin `P` prefix with Cyrillic `П` in `parameter_id` when remainder is all digits (e.g. `P01` → `П01`)
- Also normalizes `linkages` list entries with the same rule
- `ADDITIONAL_*` params not touched
- Idempotent

### Pydantic Models
- `TextTranslation(translation: str)` — single-field translations
- `ReformTranslation(driver_ru: str, opposition_ru: str)` — reform pairs
- `PToolTranslation(problem_addressed_ru: str, calibration_debate_ru: str)` — ptools pairs

### Patterns used
- LLM batch: `chain.batch([[HumanMessage(content=p)] for p in prompts], config={"max_concurrency": 50}, return_exceptions=True)`
- Atomic write: `tempfile.mkstemp + os.replace` (same pattern as `l3_translate.py`, `source_classifier.py`)
- Logger: `get_logger("translate_ru_fields", LOGS_DIR / f"translate_ru_fields_{date}.log")`

---

## 2. `02_src/run_pipeline.py` — changes

### `run_level1()` — Step 12 added (after Step 11 Classify source types):
```
--- L1 Step 12: Translate jurisdiction notes ---
```
Creates `ChatOpenAI(LLM_FAST_MODEL)` inline, calls `translate_jurisdiction_notes` with current batch jurisdictions.

### `run_phase2()` — 3 steps added (after Section keys):
```
--- Phase 2 Step: Translate tier names ---
--- Phase 2 Step: Translate ADDITIONAL param labels ---
--- Phase 2 Step: Normalize param IDs ---
```
Creates one `ChatOpenAI(LLM_FAST_MODEL)` instance shared by the two LLM steps. `normalize_param_ids` called without LLM. Both LLM steps use `jurisdictions=None` (Phase 2 runs on all data).

### `run_level4()` — Steps 6 and 7 added (after Step 5 Classify source types):
```
--- L4 Step 6: Translate reforms fields ---
--- L4 Step 7: Translate ptools fields ---
```
Creates one `ChatOpenAI(LLM_FAST_MODEL)` instance shared by both steps. Both use current batch jurisdictions list.

---

## 3. `02_src/tools/run_missing_ru_catchup.py`

Standalone script that runs all 6 functions against the full dataset:
1. `translate_jurisdiction_notes(llm)`
2. `translate_tier_names(llm)`
3. `translate_additional_param_labels(llm)`
4. `normalize_param_ids()` — no llm
5. `translate_reforms_fields(llm)`
6. `translate_ptools_fields(llm)`

Uses `load_dotenv` from project root `.env`. Sets sys.path to `02_src`.

---

## Acceptance Criteria Status

- [x] AC-1: `translate_ru_fields.py` created with all 6 functions
- [x] AC-2: `run_pipeline.py` — functions integrated in run_level1, run_phase2, run_level4
- [x] AC-3: `run_missing_ru_catchup.py` created
- [x] AC-4: All functions idempotent (check `_is_filled` before adding to batch)
- [x] AC-5: LLM functions use `chain.batch` with `max_concurrency=50`, `return_exceptions=True`
