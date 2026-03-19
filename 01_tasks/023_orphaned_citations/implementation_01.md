# Task 023: Orphaned citations — implementation report

## Status: DONE

---

## Changes made

### 1. `02_src/pipeline/sources.py` — modified

**New imports added** (lines 10–11):
- `import os`
- `import tempfile`

**New function: `_save_json_atomic(path, data)`**
Writes JSON atomically via `tempfile.mkstemp` + `os.replace`. On failure the
temp file is cleaned up and the original file is left intact. Used exclusively
by `remove_orphaned_citations`.

**New function: `_is_empty_section(section_value) -> bool`**
Returns `True` when a content section has no meaningful description:
- value is not a dict
- value has no `"description"` key → treated as nested section; empty only
  when ALL sub-keys are empty (recursive)
- `description` is missing, None, or not a string
- `description` stripped+lowercased is one of:
  `""`, `"none"`, `"n/a"`, `"n/a."`, `"not applicable"`, `"not applicable."`

**New function: `_filter_citations_by_content(citations, content) -> list`**
Iterates the citations list and drops any entry whose `field` maps to an
empty section according to `_is_empty_section`. Citations with no `field`,
or whose field is absent from `content`, are kept.

**Modified: `_add_citations_to_raw_file`** (pipeline-level prevention)
After `extract_sources_from_raw`, applies `_filter_citations_by_content`
against `raw_data["content"]` before writing. Logs the number of filtered
citations when non-zero. This prevents orphaned citations from ever being
written during normal pipeline runs.

**New function: `remove_orphaned_citations(jurisdictions=None)`**
Catchup/cleanup function placed at the bottom of the module:
- Imports `_iter_l3_raw_files` from `pipeline.source_classifier` as a local
  import (avoids potential circular import at module load time).
- Iterates all `3A/3B/3C_raw.json` files (Phase 1 per-cell + Phase 2
  `_parallel_raw`) for the given jurisdictions (or all if `None`).
- Skips files without `citations` or `content`.
- Calls `_filter_citations_by_content`; if `removed > 0`, writes with
  `_save_json_atomic` and logs `[UPDATED] label — N orphaned citation(s)
  removed (M remaining)`.
- Skips files where `removed == 0` (idempotent).
- Logs aggregate summary at completion: files scanned / updated / citations
  removed.

---

### 2. `02_src/tools/run_orphaned_citations_catchup.py` — created

CLI catchup script:
- Bootstrap: adds `02_src` to `sys.path` (same pattern as other catchup tools).
- Forces UTF-8 stdout on Windows.
- `argparse` with optional `--jurisdiction NAME_RU [NAME_RU ...]` flag to
  limit scope.
- Calls `remove_orphaned_citations(jurisdictions=...)` and prints `Done.`.

Usage:
```
# All jurisdictions
venv\Scripts\python.exe 02_src/tools/run_orphaned_citations_catchup.py

# Single jurisdiction
venv\Scripts\python.exe 02_src/tools/run_orphaned_citations_catchup.py --jurisdiction "Россия"

# Multiple jurisdictions
venv\Scripts\python.exe 02_src/tools/run_orphaned_citations_catchup.py --jurisdiction "Россия" "Германия"
```

---

## Acceptance Criteria — status

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | `remove_orphaned_citations(jurisdictions=None)` in `sources.py` | DONE |
| AC-2 | Scans all `3A/3B/3C_raw.json`, finds citations for empty-description sections | DONE |
| AC-3 | Such citations are removed from `citations[]` | DONE |
| AC-4 | Idempotent — files with 0 orphaned citations are not touched | DONE |
| AC-5 | `_filter_citations_by_content` integrated into `_add_citations_to_raw_file` | DONE |
| AC-6 | Catchup script `02_src/tools/run_orphaned_citations_catchup.py` created | DONE |
| AC-7 | Logging: count of removed citations per file | DONE |

---

## Design decisions

- **`_save_json` kept as-is** — it is used by existing Level 1/2/3/4 code
  paths; replacing it would change behaviour for all callers. Instead,
  `_save_json_atomic` was added as a new, separate function and is used only
  by `remove_orphaned_citations`.
- **Pipeline fix preferred over run_pipeline.py step** — per task brief the
  preferred approach is to integrate filtering directly into
  `_add_citations_to_raw_file`, which removes the need for a separate Step 6b
  in `run_pipeline.py`. `run_pipeline.py` is therefore unchanged.
- **Local import of `_iter_l3_raw_files`** — deferred to function body to
  avoid any circular-import risk at module load time (both modules import from
  `pipeline.config`).
- **Nested section handling** — `_is_empty_section` handles one level of
  nesting: if a section dict has no `"description"` key, it recurses over its
  values. This covers the data shapes seen in existing raw files.
