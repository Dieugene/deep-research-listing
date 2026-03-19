# Task 024: Excerpt Cleanup

## Problem

Excerpts in `sources[]` and `citations[]` across all JSON files contain Google snippet artifacts from the Parallel API:

- **Leading date prefixes**: `"Mon DD, YYYY -- "` (English month names, em-dash/en-dash/hyphen)
- **Trailing `"...Read more"` / `"...Read more"`**: Google snippet truncation markers
- **Mid-text snippet joins**: `"...Read more"` followed by optional date prefix, then next snippet

### Scale

- `...Read more` / `...Read more`: ~1951 occurrences across 203 files
- Date prefix: ~817 occurrences across 173 files
- Affects ALL levels: L1, L2, L3 (Phase 1 + Phase 2), L4

## Cleanup Rules

Applied in order, looping until stable:

1. **Mid-text join**: `...Read more` + optional whitespace + optional date prefix -> `" ... "`
2. **Trailing**: `...Read more` at end of string -> remove
3. **Leading date**: `^Mon DD, YYYY -- ` -> remove
4. **Strip** leading/trailing whitespace

## Deliverables

1. `02_src/pipeline/excerpt_cleaner.py` - Core module with `clean_excerpt()`, `clean_excerpts_in_file()`, `run_excerpt_cleanup()`
2. `02_src/tools/run_excerpt_cleanup_catchup.py` - Standalone catchup script
3. Integration into `02_src/run_pipeline.py` at each level (L1 Step 12, L2 Step 8, L3 Step 9, L4 Step 6)

## Requirements

- Purely algorithmic, no LLM calls
- Recursive walker finds all `excerpts[]` arrays anywhere in JSON structure
- Atomic writes (tempfile + os.replace)
- Idempotent: skip files with no changes
- ASCII-safe print output (Windows cp1251 compatibility)
