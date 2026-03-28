"""
SQLiteDataRepository — reads pipeline output from a SQLite database and returns typed API models.

The database has one key table:
    json_files(path TEXT PRIMARY KEY, content TEXT NOT NULL)

where `path` is relative to COUNTRIES_DIR with forward slashes, e.g.:
    "Великобритания/level_1/jurisdiction_card.json"

All JSON is loaded into memory at startup (dataset is small).
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from core.jurisdiction_meta import JURISDICTION_ISO_CODES, JURISDICTION_MARKET_TYPE
from core.labels import (
    CONTENT_TYPE_LABELS,
    INSTRUMENT_CLASS_LABELS,
    LIFECYCLE_PHASE_LABELS,
    PARAMETER_STATUS_LABELS,
    SECTION_LABELS,
    VENUE_TYPE_LABELS,
)
from models.cell import (
    CellContent,
    ContentSection,
    MatrixCellStatus,
    MatrixColumn,
    MatrixRow,
    MatrixView,
    PhaseContent,
)
from models.jurisdiction import (
    InstitutionalMetric,
    InstitutionalMetrics,
    InvestorProtection,
    JurisdictionCard,
    JurisdictionSummary,
    Level4Data,
    SimilarJurisdiction,
    VenueInJurisdiction,
)
from models.instrument import InstrumentComparison, InstrumentRegime, InstrumentSummary
from models.parameter import (
    CellParameters,
    ParameterComparison,
    ParameterComparisonEntry,
    ParameterSummary,
    ParameterValue,
)
from models.venue import CellInVenue, ParamPill, VenueCard

logger = logging.getLogger(__name__)


def _normalize_sources(data: dict) -> list[dict] | None:
    """Normalizes source/sources field: returns list or None."""
    sources = data.get("sources")
    if isinstance(sources, list):
        return sources
    source_str = data.get("source")
    if isinstance(source_str, str) and source_str.strip():
        return [{"url": source_str, "title": source_str, "field": "", "excerpts": []}]
    return None


# ---------------------------------------------------------------------------
# Institutional data helpers
# ---------------------------------------------------------------------------

# Reverse mapping: iso_code → name_ru
_ISO_TO_NAME_RU: dict[str, str] = {v: k for k, v in JURISDICTION_ISO_CODES.items()}


def _build_institutional_metrics(raw: dict) -> InstitutionalMetrics:
    """Convert raw metrics dict from JSON into InstitutionalMetrics model."""
    def _metric(key: str) -> InstitutionalMetric | None:
        d = raw.get(key)
        if not isinstance(d, dict):
            return None
        return InstitutionalMetric(
            value=d.get("value"),
            year=d.get("year"),
            percentile=d.get("percentile"),
        )

    ip_raw = raw.get("investor_protection")
    ip: InvestorProtection | None = None
    if isinstance(ip_raw, dict):
        def _ipval(key: str) -> float | None:
            v = ip_raw.get(key)
            if isinstance(v, dict):
                return v.get("value")
            return v if isinstance(v, (int, float)) else None
        ip = InvestorProtection(
            disclosure=_ipval("disclosure"),
            director_liability=_ipval("director_liability"),
            shareholder_suits=_ipval("shareholder_suits"),
            composite=_ipval("composite"),
        )

    return InstitutionalMetrics(
        rule_of_law=_metric("rule_of_law"),
        regulatory_quality=_metric("regulatory_quality"),
        political_stability=_metric("political_stability"),
        wgi_composite=_metric("wgi_composite"),
        market_cap_gdp_pct=_metric("market_cap_gdp_pct"),
        investor_protection=ip,
    )


def _build_similar_jurisdictions(similar_list: list[dict]) -> list[SimilarJurisdiction]:
    """Convert raw similar list from JSON into list of SimilarJurisdiction models."""
    result: list[SimilarJurisdiction] = []
    for item in similar_list:
        iso = item.get("iso_code", "")
        result.append(SimilarJurisdiction(
            iso_code=iso,
            name_en=item.get("name_en", ""),
            name_ru=_ISO_TO_NAME_RU.get(iso),
            score=item.get("score"),
            common_traits=item.get("common_traits", []),
        ))
    return result


# ---------------------------------------------------------------------------
# Matrix JSON helpers
# ---------------------------------------------------------------------------

_MATRIX_ROW_MAP: dict[str, str] = {
    "G07_1": "admission",
    "G07_2": "continuing",
    "G07_3": "suspension",
    "G07_4": "delisting",
}

_MATRIX_COL_MAP: dict[str, str] = {
    "D01_requirements": "requirements",
    "D02_procedures": "procedures",
    "D03_monitoring": "monitoring",
    "D04_sanctions": "sanctions",
    "D05_disclosure": "disclosure",
}


def _build_matrix_from_json_sqlite(
    matrix_data: dict,
    cell_id: str,
    venue_key: str,
    tier: str,
    tier_ru: str | None,
    iclass: str,
    val_status: str,
) -> MatrixView:
    """Build a MatrixView from a matrix.json dict."""
    F = MatrixCellStatus.FILLED
    N = MatrixCellStatus.NOT_FILLED
    X = MatrixCellStatus.NOT_APPLICABLE

    matrix_cells = matrix_data.get("matrix", {})
    rows: list[MatrixRow] = []

    for row_idx, (row_code, row_key) in enumerate(sorted(_MATRIX_ROW_MAP.items()), start=1):
        row_data = matrix_cells.get(row_code, {})
        columns: list[MatrixColumn] = []
        for col_idx, (col_code, col_key) in enumerate(sorted(_MATRIX_COL_MAP.items()), start=1):
            cell_data = row_data.get(col_code) if isinstance(row_data, dict) else None

            snippet = None
            snippet_hint = None

            if cell_data is None:
                status = X
                text_volume = 0
            else:
                content = cell_data.get("content")
                if content is None:
                    status = X
                    text_volume = 0
                elif isinstance(content, list) and len(content) == 0:
                    status = N
                    text_volume = 0
                else:
                    status = F
                    items = [i for i in (content if isinstance(content, list) else []) if isinstance(i, dict)]
                    text_volume = sum(len(i.get("description", "")) for i in items)
                    if items:
                        first_desc = items[0].get("description_ru") or items[0].get("description", "")
                        snippet = first_desc[:150].rsplit(" ", 1)[0] + "…" if len(first_desc) > 150 else first_desc
                        subtitles = [i.get("subtitle", "") for i in items if i.get("subtitle")]
                        snippet_hint = " · ".join(subtitles[:3]) if subtitles else None

            columns.append(
                MatrixColumn(
                    col_index=col_idx,
                    col_key=col_key,
                    col_label=CONTENT_TYPE_LABELS.get(col_key, col_key),
                    status=status,
                    text_volume=text_volume,
                    snippet=snippet if status == F else None,
                    snippet_hint=snippet_hint if status == F else None,
                )
            )

        rows.append(
            MatrixRow(
                row_index=row_idx,
                row_key=row_key,
                row_label=LIFECYCLE_PHASE_LABELS.get(row_key, row_key),
                columns=columns,
            )
        )

    return MatrixView(
        cell_id=cell_id,
        venue_key=venue_key,
        tier=tier,
        tier_ru=tier_ru,
        instrument_class_key=iclass,
        instrument_class_label=INSTRUMENT_CLASS_LABELS.get(iclass, iclass),
        validation_status=val_status,
        rows=rows,
    )


class SQLiteDataRepository:
    """
    Reads listing-requirements data from a SQLite database (json_files table)
    and returns typed Pydantic models for the REST API.

    All files are loaded into memory at construction time.
    """

    def __init__(self, db_path: str) -> None:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        self._files: dict[str, Any] = {}
        for (path, content) in conn.execute("SELECT path, content FROM json_files"):
            try:
                self._files[path] = json.loads(content)
            except Exception:
                pass
        conn.close()
        logger.info(
            "SQLiteDataRepository: loaded %d files from %s", len(self._files), db_path
        )

        # Load institutional data from SQLite (or empty if not exported yet)
        self._inst_metrics: dict[str, dict] = {}
        self._similar: dict[str, dict] = {}
        metrics_data = self._load("institutional/institutional_metrics.json")
        if isinstance(metrics_data, list):
            for item in metrics_data:
                iso = item.get("iso_code")
                if iso:
                    self._inst_metrics[iso] = item.get("metrics", {})
        similar_data = self._load("institutional/similar_jurisdictions.json")
        if isinstance(similar_data, list):
            for item in similar_data:
                iso = item.get("iso_code")
                if iso:
                    self._similar[iso] = {
                        "cluster_label": item.get("cluster_label"),
                        "similar": item.get("similar", []),
                    }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self, relative_path: str) -> Any:
        """Load JSON dict by relative path (forward slashes from COUNTRIES_DIR)."""
        return self._files.get(relative_path)

    def _list_jurisdiction_names(self) -> list[str]:
        """Return sorted list of jurisdiction name_ru values (top-level directories)."""
        seen: set[str] = set()
        for path in self._files:
            top = path.split("/")[0]
            seen.add(top)
        return sorted(seen)

    def _list_venue_keys(self, name_ru: str) -> list[str]:
        """Return sorted list of venue_key values for a jurisdiction."""
        prefix = f"{name_ru}/level_2/"
        keys: set[str] = set()
        for path in self._files:
            if path.startswith(prefix):
                parts = path[len(prefix):].split("/")
                if parts:
                    keys.add(parts[0])
        return sorted(keys)

    def _load_cells_list(self, name_ru: str, venue_key: str) -> list[dict]:
        """Load cells list for a venue, handling both plain list and envelope formats."""
        path = f"{name_ru}/level_2/{venue_key}/cells_list.json"
        data = self._load(path)
        if data is None:
            logger.warning("cells_list.json not found: %s", path)
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "cells" in data:
            return data["cells"]
        return []

    def _load_pass2(self, name_ru: str, venue_key: str, cell_id: str) -> dict | None:
        """Load pass2 data; prefers pass2_ru.json, falls back to pass2.json."""
        for filename in ("pass2_ru.json", "pass2.json"):
            data = self._load(f"{name_ru}/level_3/{venue_key}/{cell_id}/{filename}")
            if data is not None:
                logger.debug("Loaded pass2 (%s) for cell %s", filename, cell_id)
                return data
        logger.warning(
            "No pass2 file found for cell %s in %s/%s", cell_id, name_ru, venue_key
        )
        return None

    def _cell_validation_status(
        self, name_ru: str, venue_key: str, cell_id: str
    ) -> str:
        """
        Aggregate validation status from 3A/3B/3C validation files.
        Worst-case: red > yellow > green. Returns 'unknown' if no validation files exist.
        """
        statuses: list[str] = []
        for qt in ("3A", "3B", "3C"):
            val = self._load(
                f"{name_ru}/level_3/{venue_key}/{cell_id}/{qt}_validation.json"
            )
            if val:
                raw = val.get("validation_status", "unknown")
                statuses.append(raw.lower() if isinstance(raw, str) else "unknown")
        if not statuses:
            return "unknown"
        if "red" in statuses:
            return "red"
        if "yellow" in statuses:
            return "yellow"
        if all(s == "green" for s in statuses):
            return "green"
        return "unknown"

    def _get_cell_param_pills(
        self, name_ru: str, venue_key: str, cell_id: str
    ) -> tuple[list[ParamPill], list[ParamPill], list[ParamPill]]:
        pass2 = self._load_pass2(name_ru, venue_key, cell_id)
        if not pass2:
            return [], [], []

        params = pass2.get("parameter_values", [])
        if not params and "parameters" in pass2:
            params = pass2["parameters"]

        adm: list[ParamPill] = []
        maint: list[ParamPill] = []
        enf: list[ParamPill] = []

        for p in params:
            status = p.get("status", p.get("validation_status", ""))
            if status not in ("found", "Найдено", "extracted"):
                continue
            phase = p.get("lifecycle_phase_key", p.get("lifecycle_phase", p.get("phase", "")))
            code = str(p.get("param_id", p.get("parameter_id", p.get("id", ""))))
            label = str(p.get("param_label_ru", p.get("param_label", p.get("parameter_name", p.get("label", "")))))
            value = str(p.get("value", p.get("param_value", "")))
            if not value or value in ("N/A", "—", "-", "null", "None"):
                continue
            pill = ParamPill(param_id=code, label=label, value_short=value[:40])
            if phase == "admission":
                adm.append(pill)
            elif phase == "continuing":
                maint.append(pill)
            elif phase in ("suspension", "delisting", "enforcement"):
                enf.append(pill)

        return adm[:3], maint[:3], enf[:3]

    def _load_parallel_raw_citations(
        self, name_ru: str, venue_key: str, instrument_class: str, query_type: str
    ) -> list[dict]:
        """Load citations from _parallel_raw file for a venue+instrument+query combination."""
        if not name_ru or not venue_key or not instrument_class:
            return []
        filename = f"{venue_key}_{instrument_class}_{query_type}_raw.json"
        rel_path = f"{name_ru}/level_3/{venue_key}/_parallel_raw/{filename}"
        data = self._load(rel_path)
        if data and isinstance(data.get("citations"), list):
            return data["citations"]
        return []

    def _find_jurisdiction_for_venue(self, venue_key: str) -> str | None:
        """Scan all jurisdiction names to find which one contains this venue_key."""
        for name_ru in self._list_jurisdiction_names():
            if f"{name_ru}/level_2/{venue_key}/venue_card.json" in self._files:
                return name_ru
        return None

    # ------------------------------------------------------------------
    # Pure label helpers
    # ------------------------------------------------------------------

    def _venue_type_label(self, raw_type: str | None) -> str:
        if raw_type is None:
            return ""
        return VENUE_TYPE_LABELS.get(raw_type, raw_type)

    def _instrument_label(self, key: str) -> str:
        return INSTRUMENT_CLASS_LABELS.get(key, key)

    def _lifecycle_label(self, key: str) -> str:
        return LIFECYCLE_PHASE_LABELS.get(key, key)

    def _param_status_label(self, status: str) -> str:
        return PARAMETER_STATUS_LABELS.get(status, status)

    # ------------------------------------------------------------------
    # Jurisdictions
    # ------------------------------------------------------------------

    def get_jurisdictions(self) -> list[JurisdictionSummary]:
        result: list[JurisdictionSummary] = []
        for name_ru in self._list_jurisdiction_names():
            card = self._load(f"{name_ru}/level_1/jurisdiction_card.json")

            name_en: str = name_ru  # fallback
            legal_family: str | None = None
            listing_authority: str | None = None
            if card:
                name_en = card.get("jurisdiction", card.get("name_en", name_ru))
                legal_family = card.get("legal_family")
                listing_authority = card.get("listing_authority")

            venue_keys = self._list_venue_keys(name_ru)
            venue_count = len(venue_keys)

            has_level1 = f"{name_ru}/level_1/jurisdiction_card.json" in self._files
            has_level2 = bool(venue_keys)
            # Check if any level_3 file exists for this jurisdiction
            level3_prefix = f"{name_ru}/level_3/"
            has_level3 = any(p.startswith(level3_prefix) for p in self._files)
            has_full_data = has_level1 and has_level2 and has_level3

            has_level4 = f"{name_ru}/level_4/level4.json" in self._files

            if has_full_data:
                data_status = "full"
            elif venue_count > 0:
                data_status = "partial"
            else:
                data_status = "empty"

            result.append(
                JurisdictionSummary(
                    name_ru=name_ru,
                    name_en=name_en,
                    legal_family=legal_family,
                    venue_count=venue_count,
                    has_level4=has_level4,
                    has_full_data=has_full_data,
                    iso_code=JURISDICTION_ISO_CODES.get(name_ru),
                    market_type=JURISDICTION_MARKET_TYPE.get(name_ru),
                    data_status=data_status,
                    listing_authority=listing_authority,
                )
            )
        return sorted(result, key=lambda j: j.name_ru)

    def get_jurisdiction(self, name_ru: str) -> JurisdictionCard | None:
        card = self._load(f"{name_ru}/level_1/jurisdiction_card.json")
        if card is None:
            logger.warning("jurisdiction_card.json missing for %s", name_ru)
            return None

        # Build venue list
        # Load venues_list.json to get research_priority per venue
        venues_list_data = self._load(f"{name_ru}/level_1/venues_list.json")
        priority_lookup: dict[str, str] = {}
        vl_venues = (venues_list_data or {}).get("venues", []) if isinstance(venues_list_data, dict) else (venues_list_data or [])
        for v in vl_venues:
            vname = v.get("name_english", "")
            if vname:
                priority_lookup[vname] = v.get("research_priority", "primary")

        venues_in_card: list[VenueInJurisdiction] = []
        for venue_key in self._list_venue_keys(name_ru):
            vc = self._load(f"{name_ru}/level_2/{venue_key}/venue_card.json")
            venue_name_en = venue_key
            venue_name_ru = venue_key
            raw_venue_type = None
            if vc:
                venue_name_en = vc.get("venue_name_english", venue_key)
                venue_name_ru = vc.get("venue_name_ru") or venue_name_en
                raw_venue_type = vc.get("venue_type")

            cells = self._load_cells_list(name_ru, venue_key)
            cell_count = len(cells)

            venues_in_card.append(
                VenueInJurisdiction(
                    venue_key=venue_key,
                    name=venue_name_en,
                    name_ru=venue_name_ru,
                    venue_type=self._venue_type_label(raw_venue_type),
                    cell_count=cell_count,
                    research_priority=priority_lookup.get(venue_name_en, "primary"),
                )
            )

        # Level 4 data
        level4_data: Level4Data | None = None
        l4 = self._load(f"{name_ru}/level_4/level4.json")
        if l4:
            l4_val = self._load(f"{name_ru}/level_4/level4_validation.json")
            val_status = "unknown"
            if l4_val:
                raw = l4_val.get("validation_status", "unknown")
                val_status = raw.lower() if isinstance(raw, str) else "unknown"
            level4_data = Level4Data(
                problems=l4.get("problems", []),
                contradictions=l4.get("contradictions", []),
                parameters_as_tools=l4.get("parameters_as_tools", []),
                reforms=l4.get("reforms", []),
                validation_status=val_status,
                sources=_normalize_sources(l4),
            )

        venue_keys_for_status = self._list_venue_keys(name_ru)
        has_level1 = f"{name_ru}/level_1/jurisdiction_card.json" in self._files
        level3_prefix = f"{name_ru}/level_3/"
        has_level3 = any(p.startswith(level3_prefix) for p in self._files)
        has_full_data = has_level1 and bool(venue_keys_for_status) and has_level3
        if has_full_data:
            data_status = "full"
        elif bool(venue_keys_for_status):
            data_status = "partial"
        else:
            data_status = "empty"

        # Institutional data
        iso_code = JURISDICTION_ISO_CODES.get(name_ru)
        inst_metrics: InstitutionalMetrics | None = None
        cluster_label: str | None = None
        similar_jurisdictions: list[SimilarJurisdiction] = []
        if iso_code:
            raw_metrics = self._inst_metrics.get(iso_code)
            if raw_metrics:
                inst_metrics = _build_institutional_metrics(raw_metrics)
            sim_data = self._similar.get(iso_code)
            if sim_data:
                cluster_label = sim_data.get("cluster_label")
                similar_jurisdictions = _build_similar_jurisdictions(sim_data.get("similar", []))

        return JurisdictionCard(
            name_ru=name_ru,
            name_en=card.get("jurisdiction", card.get("name_en", name_ru)),
            legal_family=card.get("legal_family"),
            regulator_name=card.get("regulator_name"),
            regulator_type=card.get("regulator_type"),
            admission_architecture=card.get("admission_architecture"),
            admission_architecture_ru=card.get("admission_architecture_ru"),
            listing_authority=card.get("listing_authority"),
            listing_authority_short=card.get("listing_authority_short"),
            iso_code=iso_code,
            market_type=card.get("market_type"),
            data_status=data_status,
            market_types=card.get("market_types") or [],
            key_terms_mapping=card.get("key_terms_mapping") or {},
            supranational_flag=card.get("supranational_flag") or False,
            supranational_framework=card.get("supranational_framework"),
            notes=card.get("notes"),
            notes_ru=card.get("notes_ru"),
            sources=_normalize_sources(card),
            institutional_metrics=inst_metrics,
            cluster_label=cluster_label,
            similar_jurisdictions=similar_jurisdictions,
            venues=venues_in_card,
            level4=level4_data,
        )

    # ------------------------------------------------------------------
    # Venues
    # ------------------------------------------------------------------

    def get_venue(self, venue_key: str) -> VenueCard | None:
        name_ru = self._find_jurisdiction_for_venue(venue_key)
        if name_ru is None:
            logger.warning("Could not find jurisdiction for venue_key=%s", venue_key)
            return None

        vc = self._load(f"{name_ru}/level_2/{venue_key}/venue_card.json")
        if vc is None:
            logger.warning(
                "venue_card.json not found for %s/%s", name_ru, venue_key
            )
            return None

        cells = self._load_cells_list(name_ru, venue_key)
        cells_in_venue: list[CellInVenue] = []
        for cell in cells:
            cid = cell.get("cell_id", "")
            iclass = cell.get("instrument_class", "")
            tier = cell.get("tier", "")

            has_3a = f"{name_ru}/level_3/{venue_key}/{cid}/3A_raw.json" in self._files
            has_3b = f"{name_ru}/level_3/{venue_key}/{cid}/3B_raw.json" in self._files
            has_3c = f"{name_ru}/level_3/{venue_key}/{cid}/3C_raw.json" in self._files

            has_params = (
                f"{name_ru}/level_3/{venue_key}/{cid}/pass2_ru.json" in self._files
                or f"{name_ru}/level_3/{venue_key}/{cid}/pass2.json" in self._files
            )

            val_status = self._cell_validation_status(name_ru, venue_key, cid)
            p_adm, p_maint, p_enf = self._get_cell_param_pills(name_ru, venue_key, cid)

            cell_pass2 = self._load_pass2(name_ru, venue_key, cid)
            cell_tier_ru = cell_pass2.get("tier_ru") if cell_pass2 else None

            cells_in_venue.append(
                CellInVenue(
                    cell_id=cid,
                    tier=tier,
                    tier_ru=cell_tier_ru,
                    instrument_class_key=iclass,
                    instrument_class_label=self._instrument_label(iclass),
                    has_admission_data=has_3a,
                    has_maintenance_data=has_3b,
                    has_enforcement_data=has_3c,
                    has_parameters=has_params,
                    validation_status=val_status,
                    params_admission=p_adm,
                    params_maintenance=p_maint,
                    params_enforcement=p_enf,
                )
            )

        # Load venues_list.json to get research_priority
        venues_list_data = self._load(f"{name_ru}/level_1/venues_list.json")
        venue_priority = "primary"
        venue_name_en = vc.get("venue_name_english", venue_key)
        vl_venues2 = (venues_list_data or {}).get("venues", []) if isinstance(venues_list_data, dict) else (venues_list_data or [])
        for v in vl_venues2:
            if v.get("name_english") == venue_name_en:
                venue_priority = v.get("research_priority", "primary")
                break

        raw_type = vc.get("venue_type")
        return VenueCard(
            venue_key=vc.get("venue_key", venue_key),
            venue_name_english=venue_name_en,
            venue_name_local=vc.get("venue_name_local"),
            venue_name_ru=vc.get("venue_name_ru"),
            jurisdiction_ru=vc.get("jurisdiction_ru", name_ru),
            jurisdiction_en=vc.get("jurisdiction"),
            venue_type=self._venue_type_label(raw_type),
            operator=vc.get("operator"),
            secondary_listing_regime=vc.get("secondary_listing_regime", False),
            listing_architecture=vc.get("listing_architecture"),
            tiers=vc.get("tiers", []),
            segments=vc.get("segments", []),
            instrument_coverage=vc.get("instrument_coverage", []),
            notes=vc.get("notes"),
            notes_ru=vc.get("notes_ru"),
            sources=_normalize_sources(vc),
            cells=cells_in_venue,
            research_priority=venue_priority,
        )

    # ------------------------------------------------------------------
    # Cells — Matrix
    # ------------------------------------------------------------------

    def get_cell_matrix(
        self, name_ru: str, venue_key: str, cell_id: str
    ) -> MatrixView | None:
        cells = self._load_cells_list(name_ru, venue_key)
        cell_meta = next((c for c in cells if c.get("cell_id") == cell_id), None)
        if cell_meta is None:
            logger.warning(
                "cell_id=%s not found in cells_list for %s/%s",
                cell_id,
                name_ru,
                venue_key,
            )
            cell_meta = {}

        iclass = cell_meta.get("instrument_class", "")
        tier = cell_meta.get("tier", "")

        pass2 = self._load_pass2(name_ru, venue_key, cell_id)
        tier_ru = pass2.get("tier_ru") if pass2 else None

        # Try matrix.json first
        matrix_data = self._load(
            f"{name_ru}/level_3/{venue_key}/{cell_id}/matrix.json"
        )
        if matrix_data:
            val_status = self._cell_validation_status(name_ru, venue_key, cell_id)
            return _build_matrix_from_json_sqlite(
                matrix_data, cell_id, venue_key, tier, tier_ru, iclass, val_status,
            )

        raw_3a = self._load(f"{name_ru}/level_3/{venue_key}/{cell_id}/3A_raw.json")
        raw_3b = self._load(f"{name_ru}/level_3/{venue_key}/{cell_id}/3B_raw.json")
        raw_3c = self._load(f"{name_ru}/level_3/{venue_key}/{cell_id}/3C_raw.json")

        if raw_3a is None and raw_3b is None and raw_3c is None and not cell_meta:
            return None

        has_3a = raw_3a is not None
        has_3b = raw_3b is not None
        has_3c = raw_3c is not None

        vol_3a = len(json.dumps(raw_3a, ensure_ascii=False)) if has_3a else 0
        vol_3b = len(json.dumps(raw_3b, ensure_ascii=False)) if has_3b else 0
        vol_3c = len(json.dumps(raw_3c, ensure_ascii=False)) if has_3c else 0

        F = MatrixCellStatus.FILLED
        N = MatrixCellStatus.NOT_FILLED
        X = MatrixCellStatus.NOT_APPLICABLE

        def col(
            col_index: int,
            col_key: str,
            status: MatrixCellStatus,
            volume: int,
        ) -> MatrixColumn:
            return MatrixColumn(
                col_index=col_index,
                col_key=col_key,
                col_label=CONTENT_TYPE_LABELS.get(col_key, col_key),
                status=status,
                text_volume=volume,
            )

        rows: list[MatrixRow] = [
            # Row 1: admission (3A)
            MatrixRow(
                row_index=1,
                row_key="admission",
                row_label=LIFECYCLE_PHASE_LABELS["admission"],
                columns=[
                    col(1, "requirements", F if has_3a else N, vol_3a),
                    col(2, "procedures",   F if has_3a else N, vol_3a),
                    col(3, "monitoring",   X, 0),
                    col(4, "sanctions",    X, 0),
                    col(5, "disclosure",   F if has_3a else N, vol_3a),
                ],
            ),
            # Row 2: continuing (3B requirements/procedures/disclosure + 3C monitoring/sanctions)
            MatrixRow(
                row_index=2,
                row_key="continuing",
                row_label=LIFECYCLE_PHASE_LABELS["continuing"],
                columns=[
                    col(1, "requirements", F if has_3b else N, vol_3b),
                    col(2, "procedures",   F if has_3b else N, vol_3b),
                    col(3, "monitoring",   F if has_3c else N, vol_3c),
                    col(4, "sanctions",    F if has_3c else N, vol_3c),
                    col(5, "disclosure",   F if has_3b else N, vol_3b),
                ],
            ),
            # Row 3: suspension (3B requirements/procedures/sanctions + 3C monitoring)
            MatrixRow(
                row_index=3,
                row_key="suspension",
                row_label=LIFECYCLE_PHASE_LABELS["suspension"],
                columns=[
                    col(1, "requirements", F if has_3b else N, vol_3b),
                    col(2, "procedures",   F if has_3b else N, vol_3b),
                    col(3, "monitoring",   F if has_3c else N, vol_3c),
                    col(4, "sanctions",    F if has_3b else N, vol_3b),
                    col(5, "disclosure",   X, 0),
                ],
            ),
            # Row 4: delisting (3B requirements/procedures/sanctions, no monitoring/disclosure)
            MatrixRow(
                row_index=4,
                row_key="delisting",
                row_label=LIFECYCLE_PHASE_LABELS["delisting"],
                columns=[
                    col(1, "requirements", F if has_3b else N, vol_3b),
                    col(2, "procedures",   F if has_3b else N, vol_3b),
                    col(3, "monitoring",   X, 0),
                    col(4, "sanctions",    F if has_3b else N, vol_3b),
                    col(5, "disclosure",   X, 0),
                ],
            ),
        ]

        val_status = self._cell_validation_status(name_ru, venue_key, cell_id)

        return MatrixView(
            cell_id=cell_id,
            venue_key=venue_key,
            tier=tier,
            tier_ru=tier_ru,
            instrument_class_key=iclass,
            instrument_class_label=self._instrument_label(iclass),
            validation_status=val_status,
            rows=rows,
        )

    # ------------------------------------------------------------------
    # Cells — Content
    # ------------------------------------------------------------------

    def _build_phases_from_matrix(
        self,
        matrix_data: dict,
        name_ru: str = "",
        venue_key: str = "",
        instrument_class: str = "",
    ) -> list[PhaseContent]:
        """Build PhaseContent list from matrix.json (preferred over 3A/3B/3C).

        Citations are loaded from _parallel_raw/ files (keyed by venue+instrument+query)
        because matrix.json cells no longer carry citations.
        """
        matrix = matrix_data.get("matrix", {})
        metadata = matrix_data.get("metadata", {})
        val_status = (metadata.get("validation_status") or "unknown").lower()

        # --- Load citations from _parallel_raw/ files -------------------------
        cit_3a = self._load_parallel_raw_citations(name_ru, venue_key, instrument_class, "3A")
        cit_3b = self._load_parallel_raw_citations(name_ru, venue_key, instrument_class, "3B")
        cit_3c = self._load_parallel_raw_citations(name_ru, venue_key, instrument_class, "3C")

        # Map matrix row codes to the relevant citation pools
        _ROW_CITATIONS: dict[str, list[dict]] = {
            "G07_1": cit_3a,
            "G07_2": cit_3b + cit_3c,
            "G07_3": cit_3b,
            "G07_4": cit_3b,
        }

        # Phase mapping: 3 display phases from 4 matrix rows
        PHASE_MAP = [
            ("admission", "Первичный допуск", ["G07_1"]),
            ("maintenance", "Поддержание", ["G07_2", "G07_3"]),
            ("delisting", "Исключение", ["G07_4"]),
        ]

        COL_ORDER = [
            ("D01_requirements", "Требования"),
            ("D02_procedures", "Процедуры"),
            ("D03_monitoring", "Мониторинг и надзор"),
            ("D04_sanctions", "Санкции"),
            ("D05_disclosure", "Раскрытие информации"),
        ]

        phases = []
        for phase_key, phase_label, row_codes in PHASE_MAP:
            sections = []

            # Collect all citations for this display phase (union of row codes)
            phase_citations: list[dict] = []
            for rc in row_codes:
                phase_citations.extend(_ROW_CITATIONS.get(rc, []))

            for row_code in row_codes:
                row_data = matrix.get(row_code, {})
                if not isinstance(row_data, dict):
                    continue

                for col_code, col_label in COL_ORDER:
                    cell = row_data.get(col_code)
                    if cell is None or not isinstance(cell, dict):
                        continue

                    # Build sections from content items
                    content_items = cell.get("content", [])
                    if not isinstance(content_items, list):
                        continue

                    for item in content_items:
                        if not isinstance(item, dict):
                            continue
                        text = item.get("description_ru") or item.get("description", "")
                        if not text or text.strip().lower() in ("", "not applicable", "н/д", "n/a"):
                            continue

                        origin = item.get("origin_field", "")
                        subtitle = item.get("subtitle", "")
                        section_key = f"{row_code}.{col_code}.{origin}" if origin else f"{row_code}.{col_code}.{subtitle}"

                        sections.append(ContentSection(
                            section_key=section_key,
                            section_label=subtitle or SECTION_LABELS.get(origin, origin),
                            text=text,
                            source=item.get("source") or None,
                            citations=[],
                        ))

            phases.append(PhaseContent(
                phase_key=phase_key,
                phase_label=phase_label,
                has_data=bool(sections),
                validation_status=val_status,
                sections=sections,
                citations=phase_citations,
            ))

        return phases

    def get_cell_content(
        self, name_ru: str, venue_key: str, cell_id: str
    ) -> CellContent | None:
        cells = self._load_cells_list(name_ru, venue_key)
        cell_meta = next((c for c in cells if c.get("cell_id") == cell_id), None)

        iclass = (cell_meta or {}).get("instrument_class", "")
        tier = (cell_meta or {}).get("tier", "")

        pass2 = self._load_pass2(name_ru, venue_key, cell_id)
        tier_ru = pass2.get("tier_ru") if pass2 else None

        # Try matrix.json first (preferred — has description_ru + citations)
        matrix_data = self._load(
            f"{name_ru}/level_3/{venue_key}/{cell_id}/matrix.json"
        )
        if matrix_data:
            phases = self._build_phases_from_matrix(
                matrix_data,
                name_ru=name_ru,
                venue_key=venue_key,
                instrument_class=iclass,
            )
            return CellContent(
                cell_id=cell_id,
                venue_key=venue_key,
                tier=tier,
                tier_ru=tier_ru,
                instrument_class_key=iclass,
                instrument_class_label=self._instrument_label(iclass),
                phases=phases,
            )

        # Fallback to 3A/3B/3C raw files
        raw_3a = self._load(f"{name_ru}/level_3/{venue_key}/{cell_id}/3A_raw.json")
        raw_3b = self._load(f"{name_ru}/level_3/{venue_key}/{cell_id}/3B_raw.json")
        raw_3c = self._load(f"{name_ru}/level_3/{venue_key}/{cell_id}/3C_raw.json")

        if raw_3a is None and raw_3b is None and raw_3c is None and cell_meta is None:
            return None

        val_3a = self._load(
            f"{name_ru}/level_3/{venue_key}/{cell_id}/3A_validation.json"
        )
        val_3b = self._load(
            f"{name_ru}/level_3/{venue_key}/{cell_id}/3B_validation.json"
        )
        val_3c = self._load(
            f"{name_ru}/level_3/{venue_key}/{cell_id}/3C_validation.json"
        )

        citations_3a = raw_3a.get("citations", []) if raw_3a else []
        citations_3b = raw_3b.get("citations", []) if raw_3b else []
        citations_3c = raw_3c.get("citations", []) if raw_3c else []

        # Build all 3B sections, then split by delisting prefixes
        all_3b_sections = self._build_sections_from_raw(raw_3b, citations_3b) if raw_3b else []

        DELISTING_PREFIXES = ("delisting_compulsory", "delisting_voluntary")
        maintenance_sections = [s for s in all_3b_sections if not s.section_key.startswith(DELISTING_PREFIXES)]
        delisting_3b_sections = [s for s in all_3b_sections if s.section_key.startswith(DELISTING_PREFIXES)]

        # Build 3C sections
        all_3c_sections = self._build_sections_from_raw(raw_3c, citations_3c) if raw_3c else []

        # Extract validation statuses
        val_3b_status = self._extract_validation_status(val_3b)
        val_3c_status = self._extract_validation_status(val_3c)

        phases: list[PhaseContent] = [
            self._build_phase_content(
                "admission",
                "Первичный допуск",
                raw_3a,
                val_3a,
                citations_3a,
            ),
            PhaseContent(
                phase_key="maintenance",
                phase_label="Поддержание",
                has_data=bool(maintenance_sections),
                validation_status=val_3b_status,
                sections=maintenance_sections,
            ),
            PhaseContent(
                phase_key="delisting",
                phase_label="Исключение",
                has_data=bool(delisting_3b_sections) or bool(all_3c_sections),
                validation_status=val_3c_status,
                sections=delisting_3b_sections + all_3c_sections,
            ),
        ]

        return CellContent(
            cell_id=cell_id,
            venue_key=venue_key,
            tier=tier,
            tier_ru=tier_ru,
            instrument_class_key=iclass,
            instrument_class_label=self._instrument_label(iclass),
            phases=phases,
        )

    @staticmethod
    def _extract_validation_status(validation: dict | None) -> str:
        """Extract validation status string from a validation dict."""
        if not validation:
            return "unknown"
        raw_status = validation.get("validation_status", "unknown")
        return raw_status.lower() if isinstance(raw_status, str) else "unknown"

    def _build_sections_from_raw(
        self,
        raw: dict | None,
        raw_citations: list[dict] | None = None,
    ) -> list[ContentSection]:
        """Build a list of ContentSection from a raw 3x JSON dict (content key)."""
        if raw is None:
            return []

        content_dict = raw.get("content", {})
        all_citations: list[dict] = raw_citations if raw_citations is not None else []
        sections: list[ContentSection] = []

        for key, value in content_dict.items():
            if not isinstance(value, dict):
                continue

            # Check if this is a FLAT section (has "description" key)
            if "description" in value:
                description = value.get("description_ru") or value.get("description", "")
                if not description or description.strip().lower() in (
                    "",
                    "not applicable",
                    "\u043d/\u0434",
                    "n/a",
                ):
                    continue
                source = value.get("source") or None
                section_label = SECTION_LABELS.get(key, key)
                section_citations = [c for c in all_citations if isinstance(c, dict) and c.get("field") == key]
                sections.append(
                    ContentSection(
                        section_key=key,
                        section_label=section_label,
                        text=description,
                        source=source,
                        citations=section_citations,
                    )
                )
                continue

            # Check if this is a NESTED section (no "description", but sub-values have "description")
            has_nested = any(
                isinstance(sv, dict) and "description" in sv
                for sv in value.values()
            )
            if not has_nested:
                continue

            parent_key = key
            parent_label = SECTION_LABELS.get(parent_key, parent_key)
            for sub_key, sub_value in value.items():
                if not isinstance(sub_value, dict) or "description" not in sub_value:
                    continue
                nested_desc = sub_value.get("description_ru") or sub_value.get("description", "")
                if not nested_desc or nested_desc.strip().lower() in (
                    "",
                    "not applicable",
                    "\u043d/\u0434",
                    "n/a",
                ):
                    continue
                compound_key = f"{parent_key}.{sub_key}"
                nested_label = SECTION_LABELS.get(compound_key, f"{parent_label} \u2192 {sub_key}")
                nested_source = sub_value.get("source") or None
                nested_citations = [
                    c for c in all_citations
                    if isinstance(c, dict) and c.get("field") in (compound_key, sub_key)
                ]
                sections.append(
                    ContentSection(
                        section_key=compound_key,
                        section_label=nested_label,
                        text=nested_desc,
                        source=nested_source,
                        citations=nested_citations,
                    )
                )

        return sections

    def _build_phase_content(
        self,
        phase_key: str,
        phase_label: str,
        raw: dict | None,
        validation: dict | None,
        raw_citations: list[dict] | None = None,
    ) -> PhaseContent:
        val_status = self._extract_validation_status(validation)
        sections = self._build_sections_from_raw(raw, raw_citations)

        return PhaseContent(
            phase_key=phase_key,
            phase_label=phase_label,
            has_data=bool(sections),
            validation_status=val_status,
            sections=sections,
        )

    # ------------------------------------------------------------------
    # Parameters — cell
    # ------------------------------------------------------------------

    def get_cell_parameters(
        self, name_ru: str, venue_key: str, cell_id: str
    ) -> CellParameters | None:
        cells = self._load_cells_list(name_ru, venue_key)
        cell_meta = next((c for c in cells if c.get("cell_id") == cell_id), {})

        data = self._load_pass2(name_ru, venue_key, cell_id)
        if data is None:
            return None

        iclass = cell_meta.get("instrument_class", "")
        tier = cell_meta.get("tier", "")

        params: list[ParameterValue] = []
        for raw_p in data.get("parameter_values", []):
            phase_key = raw_p.get("lifecycle_phase", "")
            status = raw_p.get("status", "")
            params.append(
                ParameterValue(
                    parameter_id=raw_p.get("parameter_id", ""),
                    parameter_name=raw_p.get("parameter_name", ""),
                    lifecycle_phase_key=phase_key,
                    lifecycle_phase_label=self._lifecycle_label(phase_key),
                    value=raw_p.get("value", ""),
                    calculation_methodology=raw_p.get("calculation_methodology")
                    or None,
                    alternatives=raw_p.get("alternatives") or None,
                    variations=raw_p.get("variations") or None,
                    linkages=raw_p.get("linkages", []),
                    source=raw_p.get("source") or None,
                    status=status,
                    status_label=self._param_status_label(status),
                    drill_down_applied=raw_p.get("drill_down_applied", False),
                    note=raw_p.get("note") or None,
                    section_keys=raw_p.get("section_keys", []),
                )
            )

        tier_ru = data.get("tier_ru")

        return CellParameters(
            cell_id=cell_id,
            venue_key=venue_key,
            tier=tier,
            tier_ru=tier_ru,
            instrument_class_label=self._instrument_label(iclass),
            parameters=params,
        )

    # ------------------------------------------------------------------
    # Parameters — global summary and comparison
    # ------------------------------------------------------------------

    def get_all_parameters(self) -> list[ParameterSummary]:
        """
        Iterate over all jurisdictions -> venues -> cells -> pass2 files.
        Count unique parameter_id occurrences (only status="found" entries).
        """
        counts: dict[str, int] = {}
        names: dict[str, str] = {}

        for name_ru in self._list_jurisdiction_names():
            for venue_key in self._list_venue_keys(name_ru):
                cells = self._load_cells_list(name_ru, venue_key)
                for cell in cells:
                    cid = cell.get("cell_id", "")
                    data = self._load_pass2(name_ru, venue_key, cid)
                    if data is None:
                        continue
                    for raw_p in data.get("parameter_values", []):
                        if raw_p.get("status") != "found":
                            continue
                        pid = raw_p.get("parameter_id", "")
                        if not pid:
                            continue
                        counts[pid] = counts.get(pid, 0) + 1
                        if pid not in names:
                            names[pid] = raw_p.get("parameter_name", pid)

        return sorted(
            [
                ParameterSummary(
                    parameter_id=pid,
                    parameter_name=names.get(pid, pid),
                    occurrence_count=cnt,
                )
                for pid, cnt in counts.items()
            ],
            key=lambda p: p.parameter_id,
        )

    def get_parameter_comparison(
        self, parameter_id: str
    ) -> ParameterComparison | None:
        """
        Find all cells across all jurisdictions that have the given parameter_id
        with status="found", and return a comparison object.
        """
        entries: list[ParameterComparisonEntry] = []
        param_name: str = parameter_id

        for name_ru in self._list_jurisdiction_names():
            for venue_key in self._list_venue_keys(name_ru):
                vc = self._load(f"{name_ru}/level_2/{venue_key}/venue_card.json")
                venue_name = venue_key
                if vc:
                    venue_name = vc.get("venue_name_english", venue_key)

                cells = self._load_cells_list(name_ru, venue_key)
                for cell in cells:
                    cid = cell.get("cell_id", "")
                    iclass = cell.get("instrument_class", "")
                    tier = cell.get("tier", "")

                    data = self._load_pass2(name_ru, venue_key, cid)
                    if data is None:
                        continue

                    for raw_p in data.get("parameter_values", []):
                        if raw_p.get("parameter_id") != parameter_id:
                            continue
                        if raw_p.get("status") != "found":
                            continue

                        if param_name == parameter_id:
                            param_name = raw_p.get("parameter_name", parameter_id)

                        phase_key = raw_p.get("lifecycle_phase", "")
                        entries.append(
                            ParameterComparisonEntry(
                                jurisdiction_ru=name_ru,
                                venue_key=venue_key,
                                venue_name=venue_name,
                                cell_id=cid,
                                tier=tier,
                                instrument_class_key=iclass,
                                instrument_class_label=self._instrument_label(iclass),
                                lifecycle_phase_key=phase_key,
                                lifecycle_phase_label=self._lifecycle_label(phase_key),
                                value=raw_p.get("value", ""),
                                source=raw_p.get("source") or None,
                            )
                        )

        if not entries:
            return None

        return ParameterComparison(
            parameter_id=parameter_id,
            parameter_name=param_name,
            entries=entries,
        )

    # ------------------------------------------------------------------
    # Instruments — summary and comparison
    # ------------------------------------------------------------------

    def get_instrument_summaries(self) -> list[InstrumentSummary]:
        """Return summary stats for each instrument class across all venues."""
        from collections import defaultdict
        from repositories.file_repo import INSTRUMENT_CLASS_LABELS, INSTRUMENT_ORDER

        instrument_params: dict[str, dict[str, tuple[str, int]]] = defaultdict(dict)
        instrument_counts: dict[str, int] = defaultdict(int)
        instrument_jurisdictions: dict[str, set] = defaultdict(set)

        for name_ru in self._list_jurisdiction_names():
            for venue_key in self._list_venue_keys(name_ru):
                cells = self._load_cells_list(name_ru, venue_key)
                for cell in cells:
                    ik = cell.get("instrument_class_key") or cell.get("instrument_class", "")
                    if not ik:
                        continue
                    cell_id = cell.get("cell_id", "")
                    pass2 = self._load_pass2(name_ru, venue_key, cell_id)
                    if not pass2 or not pass2.get("parameter_values"):
                        continue
                    instrument_counts[ik] += 1
                    instrument_jurisdictions[ik].add(name_ru)
                    for pv in pass2["parameter_values"]:
                        if pv.get("status") != "found":
                            continue
                        pid = pv.get("parameter_id", "")
                        pname = pv.get("parameter_name", "")
                        if pid:
                            prev = instrument_params[ik].get(pid, (pname, 0))
                            instrument_params[ik][pid] = (pname, prev[1] + 1)

        result = []
        for ik in INSTRUMENT_ORDER:
            if ik not in instrument_counts and ik not in instrument_params:
                continue
            params_sorted = sorted(
                instrument_params.get(ik, {}).items(),
                key=lambda x: -x[1][1]
            )[:5]
            top_params = [
                ParameterSummary(
                    parameter_id=pid,
                    parameter_name=name,
                    occurrence_count=count,
                )
                for pid, (name, count) in params_sorted
            ]
            result.append(InstrumentSummary(
                instrument_class_key=ik,
                instrument_class_label=INSTRUMENT_CLASS_LABELS.get(ik, ik),
                regime_count=instrument_counts.get(ik, 0),
                jurisdiction_count=len(instrument_jurisdictions.get(ik, set())),
                top_parameters=top_params,
            ))
        return result

    def get_instrument_comparison(
        self, instrument_class_key: str, phase_key: str
    ) -> InstrumentComparison:
        """Return all regimes for an instrument class with parameter values for given phase."""
        from repositories.file_repo import INSTRUMENT_CLASS_LABELS, PHASE_LABELS

        regimes: list[InstrumentRegime] = []
        param_counts: dict[str, tuple[str, int]] = {}

        for name_ru in self._list_jurisdiction_names():
            jcard = self._load(f"{name_ru}/level_1/jurisdiction_card.json")
            legal_family = jcard.get("legal_family") if jcard else None

            for venue_key in self._list_venue_keys(name_ru):
                vcard = self._load(f"{name_ru}/level_2/{venue_key}/venue_card.json")
                if not vcard:
                    continue
                venue_name = vcard.get("venue_name_english") or venue_key
                raw_vtype = vcard.get("venue_type", "")
                venue_type = raw_vtype  # keep as-is; label mapping optional

                cells = self._load_cells_list(name_ru, venue_key)
                for cell in cells:
                    if (cell.get("instrument_class_key") or cell.get("instrument_class", "")) != instrument_class_key:
                        continue
                    cell_id = cell.get("cell_id", "")
                    tier = cell.get("tier", "")

                    pass2 = self._load_pass2(name_ru, venue_key, cell_id)
                    if not pass2:
                        continue

                    param_values: dict[str, str] = {}
                    for pv in pass2.get("parameter_values", []):
                        pv_phase = pv.get("lifecycle_phase_key") or pv.get("lifecycle_phase", "")
                        if pv_phase != phase_key:
                            continue
                        if pv.get("status") != "found":
                            continue
                        pid = pv.get("parameter_id", "")
                        pname = pv.get("parameter_name", "")
                        val = str(pv.get("value", ""))
                        if pid:
                            param_values[pid] = val
                            prev = param_counts.get(pid, (pname, 0))
                            param_counts[pid] = (pname, prev[1] + 1)

                    validation_status = self._cell_validation_status(
                        name_ru, venue_key, cell_id
                    )
                    regimes.append(InstrumentRegime(
                        cell_id=cell_id,
                        venue_key=venue_key,
                        venue_name=venue_name,
                        venue_type=venue_type,
                        jurisdiction_ru=name_ru,
                        legal_family=legal_family,
                        tier=tier,
                        validation_status=validation_status,
                        parameter_values=param_values,
                    ))

        parameters = [
            ParameterSummary(
                parameter_id=pid,
                parameter_name=name,
                occurrence_count=count,
            )
            for pid, (name, count) in sorted(
                param_counts.items(), key=lambda x: -x[1][1]
            )
        ]

        return InstrumentComparison(
            instrument_class_key=instrument_class_key,
            instrument_class_label=INSTRUMENT_CLASS_LABELS.get(
                instrument_class_key, instrument_class_key
            ),
            phase_key=phase_key,
            phase_label=PHASE_LABELS.get(phase_key, phase_key),
            parameters=parameters,
            regimes=regimes,
        )
