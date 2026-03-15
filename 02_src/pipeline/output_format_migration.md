# Raw Output Format Migration: Saving Full Parallel Output

## Summary

All raw files produced by Parallel API tasks now save the **full** `output.model_dump()` instead of just `output.content`.
This preserves `basis` — the list of `FieldBasis` objects containing citations (URL, title, excerpts) for each field.

---

## New Format (all files written after this migration)

```json
{
  "<metadata>": "...",
  "retrieved_at": "...",
  "parallel_output": {
    "content": { ... },
    "basis": [
      {
        "field": "field_name",
        "reasoning": "...",
        "citations": [
          {"url": "https://...", "title": "Doc title", "excerpts": ["..."]}
        ],
        "confidence": "high"
      }
    ]
  }
}
```

- `content` is a **dict** for JSON-schema queries (1B, 1C, 2A, 3A/3B/3C/3D, 3P) or a **string** for text queries (1A, 4A).
- `basis` is always a list (may be empty if Parallel did not return citations).

---

## Old Formats (still on disk — readers handle all of them)

| File     | Old format                                                                 |
|----------|----------------------------------------------------------------------------|
| 1A       | `{"jurisdiction": ..., "query": "1A", "content": "<str>", "retrieved_at": ...}` |
| 1B / 1C  | `{"jurisdiction": ..., **content_fields, "retrieved_at": ...}` (dict spread at top level) |
| 2A       | `{"venue_key": ..., "venue_name_english": ..., "retrieved_at": ..., **content_fields}` |
| 3A/3B/3C | `{"cell_id": ..., "venue_key": ..., "query_type": ..., "retrieved_at": ..., "content": {...}}` |
| 4A       | `{"jurisdiction": ..., "raw_text": "<str>", "retrieved_at": ...}` |
| 3P       | Content dict saved directly as the file (no wrapper) |

---

## Files Changed

### Writers (now save `parallel_output` wrapper)

| File | Function |
|------|----------|
| `02_src/pipeline/parallel_runner.py` | `poll_until_done`, `poll_all` — pass `output.model_dump()` to save_fn |
| `02_src/level_1/jurisdiction_runner.py` | `_save_fn_1a`, `_save_fn_1b`, `_save_fn_1c` |
| `02_src/level_2/venue_runner.py` | `_make_save_fn` |
| `02_src/level_3/cell_runner.py` | `_make_save_fn` |
| `02_src/level_4/level4_runner.py` | `_make_save_fn` (inside `run_level4_parallel`) |
| `02_src/level_3/phase2_runner.py` | `_make_save_fn` (inside `run_3p_execute`) |

### Readers (backward-compatible — handle both old and new formats)

| File | Location | Strategy |
|------|----------|----------|
| `02_src/level_1/jurisdiction_runner.py` | `_extract_text_content()` helper, used in `launch_all_1c` | Check `parallel_output` key first, fall back to `content` |
| `02_src/level_1/postprocess.py` | `_load_content()`, 1A reader in `process_jurisdiction` | New: `parallel_output.content`; old: `content` key; really old: dict spread |
| `02_src/level_2/postprocess.py` | `_extract_parallel_content()` helper, used in `_load_venue_inputs` | New: `parallel_output.content`; old: dict spread minus meta keys |
| `02_src/level_3/postprocess_l3.py` | Content extraction inside `run_postprocess_l3` | Check `parallel_output` key, fall back to `content` |
| `02_src/level_4/level4_runner.py` | `run_level4_postprocess` | New: `parallel_output.content`; old: `raw_text` or `content` |
| `02_src/level_3/phase2_runner.py` | `three_p_raw` loading in `run_new_pass2` | New: extract `parallel_output.content`; old: strip metadata keys |

---

## Backward Compatibility Notes

- All readers listed above handle **all old formats** on disk without migration.
- **No existing files need to be re-processed** — old files are read correctly via format detection.
- The only behavioral change: new files written from now on will contain the `basis` field with citation data.

---

## Nuances Discovered During Implementation

1. **`level_2/postprocess.py` — `raw_2a` passed as full JSON to LLM prompt**: In `_build_venue_prompt`, the entire `raw_2a` dict is serialized to JSON and injected into the LLM prompt. With the new format, this would have caused the LLM to see the `parallel_output` wrapper instead of the actual research content. Fixed by extracting content in `_load_venue_inputs` via `_extract_parallel_content()` before returning `raw_2a`.

2. **`phase2_runner.py` — `3P_raw.json` was raw content dict**: Unlike all other raw files, the 3P save function previously wrote `content` (a plain dict) directly as the entire JSON file, with no metadata wrapper. The new format adds a `{"group_id": ..., "retrieved_at": ..., "parallel_output": ...}` wrapper. The reader strips metadata keys when reading old format files.

3. **`1A` text output**: The `1A` query uses `output_schema=None` (text output), so `content` is a string. The `_extract_text_content` and `_load_content` helpers explicitly handle this case.

4. **`level_1/jurisdiction_runner.py` — unused import**: `save_raw_query` was imported and used only in the old `_save_fn_1a`. After refactoring, `_save_fn_1a` uses `save_json` directly. The `save_raw_query` import remains in the file but is no longer called — it can be removed in a future cleanup pass.
