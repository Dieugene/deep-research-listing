# Task 024: Excerpt Cleanup - Implementation Report

## Files Created

- `02_src/pipeline/excerpt_cleaner.py` - Core cleanup module
- `02_src/tools/run_excerpt_cleanup_catchup.py` - Standalone catchup script

## Files Modified

- `02_src/run_pipeline.py` - Added excerpt cleanup integration:
  - L1 Step 12 (after source classification, before translations)
  - L2 Step 8 (after source classification, before level complete)
  - L3 Step 9 (after citation type classification, before matrix build)
  - L4 Step 6 (after source classification, before translations)

## Implementation Details

### clean_excerpt()
- Applies 4 regex rules in a convergence loop (max 5 iterations, typically 1-2)
- Handles cascading patterns (e.g., mid-text removal exposing a leading date prefix)

### clean_excerpts_in_file()
- Recursive JSON walker finds all lists named `excerpts` containing strings
- Atomic write only if changes detected

### run_excerpt_cleanup()
- Scans L1 (jurisdiction_card, 1A, 1B, 1C), L2 (venue_card), L3 (3A/3B/3C_raw in both phase 1 cell dirs and phase 2 _parallel_raw/), L4 (level4, 4A_raw)
- Per-file logging, aggregate summary

## Test Results (Full Catchup Run)

- **554 files scanned**
- **242 files updated**
- **4,402 excerpts cleaned**
- Second run: 0 files updated, 0 excerpts cleaned (fully idempotent)
