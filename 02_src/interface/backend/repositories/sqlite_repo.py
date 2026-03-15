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
    JurisdictionCard,
    JurisdictionSummary,
    Level4Data,
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
from models.venue import CellInVenue, VenueCard

logger = logging.getLogger(__name__)


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
                sources=l4.get("sources"),
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

        return JurisdictionCard(
            name_ru=name_ru,
            name_en=card.get("jurisdiction", card.get("name_en", name_ru)),
            legal_family=card.get("legal_family"),
            regulator_name=card.get("regulator_name"),
            regulator_type=card.get("regulator_type"),
            admission_architecture=card.get("admission_architecture"),
            admission_architecture_ru=card.get("admission_architecture_ru"),
            listing_authority=card.get("listing_authority"),
            iso_code=JURISDICTION_ISO_CODES.get(name_ru),
            data_status=data_status,
            market_types=card.get("market_types", []),
            key_terms_mapping=card.get("key_terms_mapping", {}),
            supranational_flag=card.get("supranational_flag", False),
            supranational_framework=card.get("supranational_framework"),
            notes=card.get("notes"),
            notes_ru=card.get("notes_ru"),
            sources=card.get("sources"),
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

            cells_in_venue.append(
                CellInVenue(
                    cell_id=cid,
                    tier=tier,
                    instrument_class_key=iclass,
                    instrument_class_label=self._instrument_label(iclass),
                    has_admission_data=has_3a,
                    has_maintenance_data=has_3b,
                    has_enforcement_data=has_3c,
                    has_parameters=has_params,
                    validation_status=val_status,
                )
            )

        raw_type = vc.get("venue_type")
        return VenueCard(
            venue_key=vc.get("venue_key", venue_key),
            venue_name_english=vc.get("venue_name_english", venue_key),
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
            sources=vc.get("sources"),
            cells=cells_in_venue,
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
            instrument_class_key=iclass,
            instrument_class_label=self._instrument_label(iclass),
            validation_status=val_status,
            rows=rows,
        )

    # ------------------------------------------------------------------
    # Cells — Content
    # ------------------------------------------------------------------

    def get_cell_content(
        self, name_ru: str, venue_key: str, cell_id: str
    ) -> CellContent | None:
        cells = self._load_cells_list(name_ru, venue_key)
        cell_meta = next((c for c in cells if c.get("cell_id") == cell_id), None)

        raw_3a = self._load(f"{name_ru}/level_3/{venue_key}/{cell_id}/3A_raw.json")
        raw_3b = self._load(f"{name_ru}/level_3/{venue_key}/{cell_id}/3B_raw.json")
        raw_3c = self._load(f"{name_ru}/level_3/{venue_key}/{cell_id}/3C_raw.json")

        if raw_3a is None and raw_3b is None and raw_3c is None and cell_meta is None:
            return None

        iclass = (cell_meta or {}).get("instrument_class", "")
        tier = (cell_meta or {}).get("tier", "")

        val_3a = self._load(
            f"{name_ru}/level_3/{venue_key}/{cell_id}/3A_validation.json"
        )
        val_3b = self._load(
            f"{name_ru}/level_3/{venue_key}/{cell_id}/3B_validation.json"
        )
        val_3c = self._load(
            f"{name_ru}/level_3/{venue_key}/{cell_id}/3C_validation.json"
        )

        phases: list[PhaseContent] = [
            self._build_phase_content(
                "admission",
                "Первичный допуск",
                raw_3a,
                val_3a,
            ),
            self._build_phase_content(
                "maintenance",
                "Поддержание, приостановка и исключение",
                raw_3b,
                val_3b,
            ),
            self._build_phase_content(
                "enforcement",
                "Мониторинг и надзор",
                raw_3c,
                val_3c,
            ),
        ]

        return CellContent(
            cell_id=cell_id,
            venue_key=venue_key,
            tier=tier,
            instrument_class_key=iclass,
            instrument_class_label=self._instrument_label(iclass),
            phases=phases,
        )

    def _build_phase_content(
        self,
        phase_key: str,
        phase_label: str,
        raw: dict | None,
        validation: dict | None,
    ) -> PhaseContent:
        val_status = "unknown"
        if validation:
            raw_status = validation.get("validation_status", "unknown")
            val_status = (
                raw_status.lower() if isinstance(raw_status, str) else "unknown"
            )

        if raw is None:
            return PhaseContent(
                phase_key=phase_key,
                phase_label=phase_label,
                has_data=False,
                validation_status=val_status,
                sections=[],
            )

        content_dict = raw.get("content", {})
        sections: list[ContentSection] = []

        for key, value in content_dict.items():
            if not isinstance(value, dict):
                continue
            description = value.get("description", "")
            if not description or description.strip().lower() in (
                "",
                "not applicable",
                "н/д",
                "n/a",
            ):
                continue
            source = value.get("source") or None
            section_label = SECTION_LABELS.get(key, key)
            sections.append(
                ContentSection(
                    section_key=key,
                    section_label=section_label,
                    text=description,
                    source=source,
                )
            )

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
                )
            )

        return CellParameters(
            cell_id=cell_id,
            venue_key=venue_key,
            tier=tier,
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

        for name_ru in self._list_jurisdiction_names():
            for venue_key in self._list_venue_keys(name_ru):
                cells = self._load_cells_list(name_ru, venue_key)
                for cell in cells:
                    ik = cell.get("instrument_class_key", "")
                    if not ik:
                        continue
                    cell_id = cell.get("cell_id", "")
                    pass2 = self._load_pass2(name_ru, venue_key, cell_id)
                    if not pass2 or not pass2.get("parameter_values"):
                        continue
                    instrument_counts[ik] += 1
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
                    if cell.get("instrument_class_key") != instrument_class_key:
                        continue
                    cell_id = cell.get("cell_id", "")
                    tier = cell.get("tier", "")

                    pass2 = self._load_pass2(name_ru, venue_key, cell_id)
                    if not pass2:
                        continue

                    param_values: dict[str, str] = {}
                    for pv in pass2.get("parameter_values", []):
                        if pv.get("lifecycle_phase_key") != phase_key:
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
