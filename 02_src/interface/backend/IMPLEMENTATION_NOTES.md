# Backend Implementation Notes

## Created Files

```
02_src/interface/backend/
  __init__.py
  main.py                          FastAPI app, CORS, routers, health check
  dependencies.py                  Singleton get_repository() DI
  requirements.txt                 fastapi, uvicorn[standard], pydantic>=2
  core/
    __init__.py
    config.py                      ROOT_DIR / DATA_DIR / COUNTRIES_DIR / CORS_ORIGINS
    labels.py                      All display label dicts + SECTION_LABELS
  repositories/
    __init__.py
    base.py                        DataRepository Protocol
    file_repo.py                   FileDataRepository — full implementation
  models/
    __init__.py
    common.py                      ValidationStatus, MatrixCellStatus enums
    jurisdiction.py                JurisdictionSummary, JurisdictionCard, VenueInJurisdiction, Level4Data
    venue.py                       VenueCard, CellInVenue
    cell.py                        MatrixView, MatrixRow, MatrixColumn, CellContent, PhaseContent, ContentSection
    parameter.py                   ParameterValue, CellParameters, ParameterSummary, ParameterComparison, ParameterComparisonEntry
  routers/
    __init__.py
    jurisdictions.py               GET /api/jurisdictions/, GET /api/jurisdictions/{name_ru}
    venues.py                      GET /api/venues/{venue_key}
    cells.py                       GET /api/cells/{cell_id}/matrix|content|parameters
    parameters.py                  GET /api/parameters/, GET /api/parameters/{parameter_id}
```

## How to Start

```bash
cd 02_src/interface/backend
# Activate venv first, then:
uvicorn main:app --reload --port 8000
```

Interactive docs: http://localhost:8000/docs

## Key Design Decisions

### Path Resolution
`core/config.py` resolves ROOT_DIR independently as `Path(__file__).resolve().parents[4]`
(core/ -> backend/ -> interface/ -> 02_src/ -> project root). Does not import from `pipeline.*`.

### L3 File Location
All L3 files (3A/3B/3C raw, validation, pass2) are expected in:
```
level_3/{venue_key}/{cell_id}/
```
The `_parallel_raw/` subfolder (named by instrument class, not cell_id) is **not** scanned —
it is used by the pipeline internals only. All pipeline-processed cells have their own
cell_id-named folder.

### Venue Lookup by venue_key
`get_venue(venue_key)` scans all jurisdiction directories for a `level_2/{venue_key}` subfolder.
This avoids importing PILOT_VENUES from pipeline config and works for any jurisdiction on disk.

### Empty / Missing Sections
In `get_cell_content`, sections with empty, "not applicable", or "н/д" descriptions are
silently skipped. Frontend receives only sections with real content.

### Parameter Comparison Returns None if No "found" Entries
`get_parameter_comparison` returns `None` (→ HTTP 404) if the parameter_id exists but has
no entries with `status="found"` anywhere. This is intentional.

### Matrix text_volume
`text_volume` in `MatrixColumn` is the `len(json.dumps(raw_data))` of the corresponding
raw JSON (3A, 3B, or 3C). Used by the frontend for colour-intensity rendering.
Columns mapped to NOT_APPLICABLE always have text_volume=0.

### Level4 fields
`Level4Data.parameters_as_tools` and `Level4Data.reforms` are returned as raw dicts
(from level4.json top-level keys). The spec did not prescribe typed sub-models for these.

## Known Limitations / Notes

1. **`get_cell_matrix` / `get_cell_content` with unknown cell_id**: If `cell_id` is not in
   `cells_list.json` but the folder exists on disk, the matrix/content endpoints still attempt
   to load data. `instrument_class` and `tier` will be empty strings in that case.

2. **URL-encoding of Russian jurisdiction names**: FastAPI path parameters URL-decode
   automatically. Clients should URL-encode Cyrillic names, e.g.
   `GET /api/jurisdictions/%D0%92%D0%B5%D0%BB%D0%B8%D0%BA%D0%BE%D0%B1%D1%80%D0%B8%D1%82%D0%B0%D0%BD%D0%B8%D1%8F`

3. **No caching**: The repository reads files on every request. For production use,
   add an in-memory LRU cache or use FastAPI's `@lru_cache` on heavy methods.

4. **`get_all_parameters` is O(jurisdictions × venues × cells)**: It iterates all files
   on every call. Suitable for the current pilot dataset size; add caching for scale.

5. **Россия jurisdiction**: Russia has level_1 data (1A/1B) but no level_2 or level_3.
   It will appear in `GET /api/jurisdictions/` with `venue_count=0` and `has_full_data=false`.
