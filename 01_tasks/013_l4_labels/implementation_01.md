# Task 013: L4 Timeline Labels + articulated_by Normalization

## Status: DONE

## Changes made

### 1. `02_src/pipeline/level4_postprocess.py` — 2 new functions added

**`process_level4_labels(jurisdictions, llm)`**
- Collects all records missing `label` across `problems`, `contradictions`, `parameters_as_tools`, `reforms`
- Selects source text per section: `resolution_ru`/`resolution` for contradictions, `parameter_description_ru`/`parameter_description` for parameters_as_tools, `description_ru`/`description` for others
- Batch LLM call via `langchain_openai.ChatOpenAI` (gpt-5-mini, max_concurrency=50)
- Truncates result to 35 chars; writes back idempotently
- Atomic save via `_save_json_atomic` (temp file + `os.replace`)

**`process_level4_articulated_by(jurisdictions)`**
- Normalizes `articulated_by` field using `_ARTICULATED_BY_MAP`
- Enum: `government`, `regulator`, `academic`, `market_participants`, `exchange`
- Maps `industry` → `market_participants`
- Logs warning for unknown values; skips them
- Atomic save

**Helper functions added:**
- `_get_record_text(record, section_name)` — text selection logic
- `_load_level4(name_ru)` — load with error handling
- `_save_json_atomic(path, data)` — atomic write via temp + os.replace

### 2. `02_src/run_pipeline.py` — L4 Step 4 added

After L4 Step 3 (Enrich record sources), added:
```
--- L4 Step 4: Labels and articulated_by ---
```
Calls `process_level4_labels` and `process_level4_articulated_by` with the current jurisdiction batch.

### 3. `02_src/tools/run_l4_labels_catchup.py` — NEW

Standalone catch-up script for existing level4.json files.
Run: `python 02_src/tools/run_l4_labels_catchup.py`

## Design decisions

- `_ARTICULATED_BY_VALID` set used for O(1) membership check to detect already-normalized values
- LLM created internally if not passed (uses `LLM_FAST_MODEL` from config)
- All saves are atomic to prevent partial writes on error
- Both functions handle missing `level4.json` gracefully (log + skip)
