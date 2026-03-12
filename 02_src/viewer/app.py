"""
Streamlit viewer for Deep Research pipeline data (L1 + L2 + L3).
No LLM calls — pure file-based viewer.

Run from project root:
    venv\\Scripts\\streamlit run 02_src\\viewer\\app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from pipeline.config import PILOT_VENUES
from viewer.data_loader import (
    get_l3_status,
    load_cells_list,
    load_jurisdiction_card,
    load_l3_result,
    load_level3_state,
    load_venue_card,
    load_pass2_data,
    load_cell_validation_status,
    load_level4_data,
    load_level4_validation,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Deep Research Viewer",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("Deep Research — Listing Requirements Viewer")

# ---------------------------------------------------------------------------
# Sidebar — venue selector
# ---------------------------------------------------------------------------
VENUE_OPTIONS = {
    f"{v['venue_key']} ({v['name_ru']})": (v["name_ru"], v["venue_key"])
    for v in PILOT_VENUES
}

selected_label = st.sidebar.selectbox("Площадка", list(VENUE_OPTIONS.keys()))
name_ru, venue_key = VENUE_OPTIONS[selected_label]

# ---------------------------------------------------------------------------
# Status symbol helpers
# ---------------------------------------------------------------------------
STATUS_ICON = {
    "done": "✅",
    "pending": "⏳",
    "not started": "⬜",
    "n/a": "—",
}

QUERY_TYPES = ["3A", "3B", "3C"]

# ---------------------------------------------------------------------------
# Load data (cached per session to avoid re-reading on every widget interaction)
# ---------------------------------------------------------------------------


@st.cache_data(ttl=30)
def _load_all(name_ru: str, venue_key: str):
    jurisdiction_card = load_jurisdiction_card(name_ru)
    venue_card = load_venue_card(name_ru, venue_key)
    cells = load_cells_list(name_ru, venue_key) or []
    state = load_level3_state()
    return jurisdiction_card, venue_card, cells, state


jurisdiction_card, venue_card, cells, state = _load_all(name_ru, venue_key)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_jurisdiction, tab_venue, tab_cells = st.tabs(["Юрисдикция", "Площадка", "Ячейки"])


# ===========================================================================
# Tab: Юрисдикция
# ===========================================================================
with tab_jurisdiction:
    if not jurisdiction_card:
        st.info("Данные по юрисдикции не собраны (jurisdiction_card.json не найден)")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Юрисдикция", jurisdiction_card.get("jurisdiction_ru", name_ru))
            st.metric(
                "Правовая семья",
                jurisdiction_card.get("legal_family", "—").replace("_", " ").title(),
            )
            st.metric("Регулятор", jurisdiction_card.get("regulator_name", "—"))
            st.metric(
                "Тип регулятора",
                jurisdiction_card.get("regulator_type", "—").replace("_", " ").title(),
            )
        with col2:
            supranational = jurisdiction_card.get("supranational_flag", False)
            st.metric("Наднациональный режим", "Да" if supranational else "Нет")
            if supranational and jurisdiction_card.get("supranational_framework"):
                st.caption(jurisdiction_card["supranational_framework"])

        st.divider()

        arch_ru = jurisdiction_card.get("admission_architecture_ru") or jurisdiction_card.get(
            "admission_architecture"
        )
        if arch_ru:
            st.subheader("Архитектура допуска")
            st.write(arch_ru)

        listing_auth = jurisdiction_card.get("listing_authority")
        if listing_auth:
            st.subheader("Листинговый орган")
            st.write(listing_auth)

        market_types = jurisdiction_card.get("market_types", [])
        if market_types:
            st.subheader("Типы рынков")
            for mt in market_types:
                st.markdown(f"- {mt}")

        notes = jurisdiction_card.get("notes")
        if notes:
            with st.expander("Примечания"):
                st.write(notes)

        venues_list = jurisdiction_card.get("venues", [])
        if venues_list:
            with st.expander(f"Площадки в юрисдикции ({len(venues_list)})"):
                for v in venues_list:
                    tiers_str = ", ".join(v.get("tiers", []))
                    st.markdown(
                        f"**{v.get('name_english', '?')}** `{v.get('type', '?')}`  \n"
                        f"Уровни листинга: {tiers_str or '—'}"
                    )

        with st.expander("Полный JSON (jurisdiction_card)"):
            st.json(jurisdiction_card, expanded=False)

        # Level 4: Regulatory objectives
        st.divider()
        level4_data = load_level4_data(name_ru)
        level4_val = load_level4_validation(name_ru)

        _L4_VAL_ICONS = {"green": "🟢", "yellow": "🟡", "red": "🔴", "unknown": "⬜"}
        l4_status = (level4_val or {}).get("validation_status", "unknown")
        l4_icon = _L4_VAL_ICONS.get(l4_status, "⬜")

        st.subheader(f"{l4_icon} Регуляторные цели и обоснования")

        if not level4_data:
            st.info("level4.json не найден — Level 4 не выполнен для данной юрисдикции.")
        else:
            # Problems
            problems = level4_data.get("problems", [])
            with st.expander(f"Проблемы ({len(problems)})", expanded=False):
                if not problems:
                    st.caption("Не найдено")
                for p in problems:
                    st.markdown(f"**{p.get('description_ru') or p.get('description', '?')}**")
                    cols = st.columns(3)
                    cols[0].caption(f"Кто: {p.get('articulated_by', '—')}")
                    cols[1].caption(f"Период: {p.get('period', '—')}")
                    cols[2].caption(f"Источник: {p.get('source', '—')}")
                    st.divider()

            # Contradictions
            contradictions = level4_data.get("contradictions", [])
            with st.expander(f"Противоречия целей ({len(contradictions)})", expanded=False):
                if not contradictions:
                    st.caption("Не найдено")
                for c in contradictions:
                    st.markdown(f"**{c.get('objective_a', '?')}** ↔ **{c.get('objective_b', '?')}**")
                    resolution = c.get('resolution_ru') or c.get('resolution', '')
                    if resolution:
                        st.write(resolution)
                    cols = st.columns(2)
                    cols[0].caption(f"Период: {c.get('period', '—')}")
                    cols[1].caption(f"Источник: {c.get('source', '—')}")
                    st.divider()

            # Parameters as tools
            params_tools = level4_data.get("parameters_as_tools", [])
            with st.expander(f"Параметры как инструменты политики ({len(params_tools)})", expanded=False):
                if not params_tools:
                    st.caption("Не найдено")
                for pt in params_tools:
                    desc_ru = pt.get('parameter_description_ru') or pt.get('parameter_description', '?')
                    st.markdown(f"**{desc_ru}**")
                    problem = pt.get('problem_addressed', '')
                    if problem:
                        st.write(f"Проблема: {problem}")
                    debate = pt.get('calibration_debate', '')
                    if debate:
                        st.caption(f"Дискуссия о калибровке: {debate}")
                    cols = st.columns(2)
                    cols[0].caption(f"Период: {pt.get('period', '—')}")
                    cols[1].caption(f"Источник: {pt.get('source', '—')}")
                    st.divider()

            # Reforms
            reforms = level4_data.get("reforms", [])
            with st.expander(f"Реформы ({len(reforms)})", expanded=False):
                if not reforms:
                    st.caption("Не найдено")
                for r in reforms:
                    st.markdown(f"**{r.get('description_ru') or r.get('description', '?')}**")
                    driver = r.get('driver', '')
                    if driver:
                        st.write(f"Драйвер: {driver}")
                    opposition = r.get('opposition', '')
                    if opposition:
                        st.caption(f"Оппозиция: {opposition}")
                    cols = st.columns(2)
                    cols[0].caption(f"Год: {r.get('year', '—')}")
                    cols[1].caption(f"Источник: {r.get('source', '—')}")
                    st.divider()

            # Sources summary
            sources = level4_data.get("sources_summary", [])
            if sources:
                with st.expander(f"Источники ({len(sources)})", expanded=False):
                    for s in sources:
                        st.markdown(f"- {s}")


# ===========================================================================
# Tab: Площадка
# ===========================================================================
with tab_venue:
    if not venue_card:
        st.info("venue_card.json не найден")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Площадка",
                venue_card.get("venue_name_ru")
                or venue_card.get("venue_name_english", venue_key),
            )
            st.metric("Оператор", venue_card.get("operator", "—"))
            st.metric(
                "Тип площадки",
                str(venue_card.get("venue_type", "—")).replace("_", " ").title(),
            )
            secondary = venue_card.get("secondary_listing_regime", False)
            st.metric("Вторичный листинг", "Да" if secondary else "Нет")
            listing_arch = venue_card.get("listing_architecture")
            if listing_arch:
                st.metric("Архитектура листинга", listing_arch.replace("_", " ").title())
            if venue_card.get("issuer_eligibility_separate") is not None:
                st.metric(
                    "Раздельный допуск эмитента и инструмента",
                    "Да" if venue_card["issuer_eligibility_separate"] else "Нет",
                )
                st.caption(f"Кто проводит: {venue_card.get('issuer_eligibility_authority', '—')}")
                st.caption(f"Основание: {venue_card.get('issuer_eligibility_legal_basis', '—')}")

        with col2:
            tiers = venue_card.get("tiers", [])
            if tiers:
                st.subheader(f"Уровни листинга ({len(tiers)})")
                tiers_df = pd.DataFrame(
                    [
                        {
                            "Уровень листинга": t.get("tier_name_ru") or t.get("tier_name", "—"),
                            "Тип": t.get("segment_type", "—"),
                            "Инструменты": ", ".join(t.get("instrument_classes", [])),
                            "Вторичный": "Да" if t.get("secondary_admission_applicable") else "Нет",
                        }
                        for t in tiers
                    ]
                )
                st.dataframe(tiers_df, use_container_width=True, hide_index=True)

        segments = venue_card.get("segments", [])
        if segments:
            st.subheader(f"Тематические сегменты ({len(segments)})")
            segs_df = pd.DataFrame(
                [
                    {
                        "Сегмент": s.get("segment_name_ru") or s.get("segment_name", "—"),
                        "Генерирует ячейку": "Да" if s.get("generates_cell") else "Нет",
                        "Главы правил": ", ".join((s.get("rulebook_chapters") or {}).keys()) or "—",
                    }
                    for s in segments
                ]
            )
            st.dataframe(segs_df, use_container_width=True, hide_index=True)

        instrument_coverage = venue_card.get("instrument_coverage", [])
        if instrument_coverage:
            st.subheader(f"Инструменты и режимы допуска ({len(instrument_coverage)})")
            cov_rows = []
            for ic in instrument_coverage:
                modifiers = ic.get("modifiers") or []
                cov_rows.append(
                    {
                        "Класс": ic.get("instrument_class", "—"),
                        "Режим": ic.get("regime_name_ru") or ic.get("regime_name") or "—",
                        "Путь": (ic.get("admission_path") or "listing").replace("_", " "),
                        "Особый режим": "Да" if ic.get("distinct_regime") else "Нет",
                        "Вторичный": "Да" if ic.get("secondary_admission_applicable") else "Нет",
                        "Legacy": "Да" if ic.get("legacy") else "Нет",
                        "Модификаторы": ", ".join(modifiers) if modifiers else "—",
                    }
                )
            cov_df = pd.DataFrame(cov_rows)
            st.dataframe(cov_df, use_container_width=True, hide_index=True)

        if venue_card.get("secondary_listing_description"):
            with st.expander("Описание вторичного листинга"):
                st.write(venue_card["secondary_listing_description"])

        if venue_card.get("key_rulebook_references"):
            with st.expander("Ключевые источники"):
                st.write(venue_card["key_rulebook_references"])

        if venue_card.get("notes_ru") or venue_card.get("notes"):
            with st.expander("Примечания"):
                st.write(venue_card.get("notes_ru") or venue_card.get("notes", ""))

        with st.expander("Полный JSON (venue_card)"):
            st.json(venue_card, expanded=False)


# ===========================================================================
# Tab: Ячейки
# ===========================================================================
with tab_cells:
    if not cells:
        st.info("cells_list.json не найден или список пуст")
    else:
        # ------------------------------------------------------------------
        # Build status table
        # ------------------------------------------------------------------
        rows = []
        for i, cell in enumerate(cells):
            cell_id = cell.get("cell_id", f"cell_{i}")
            row = {
                "cell_id": cell_id,
                "Уровень листинга": cell.get("tier", "—"),
                "Инструмент": cell.get("instrument_class", "—"),
                "Вторичный": "Да" if cell.get("secondary_admission_applicable") else "Нет",
            }
            for qt in QUERY_TYPES:
                status = get_l3_status(
                    name_ru, venue_key, cell_id, qt, cell_index=i, state=state
                )
                row[qt] = STATUS_ICON[status]
            rows.append(row)

        status_df = pd.DataFrame(rows)

        st.subheader(f"Ячейки площадки {venue_key} ({len(cells)})")

        # Legend
        st.caption(
            "Статусы: "
            + " ".join(f"{v} {k}" for k, v in STATUS_ICON.items())
        )

        st.dataframe(
            status_df.drop(columns=["cell_id"]),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        # ------------------------------------------------------------------
        # Cell detail selector
        # ------------------------------------------------------------------
        cell_labels = [
            f"[{i}] {c.get('tier', '?')} / {c.get('instrument_class', '?')}"
            for i, c in enumerate(cells)
        ]
        selected_idx = st.selectbox("Выберите ячейку для просмотра", range(len(cells)), format_func=lambda i: cell_labels[i])

        selected_cell = cells[selected_idx]
        cell_id = selected_cell.get("cell_id", f"cell_{selected_idx}")

        st.subheader(f"Ячейка: {cell_id}")
        meta_cols = st.columns(4)
        meta_cols[0].metric("Уровень листинга", selected_cell.get("tier", "—"))
        meta_cols[1].metric("Инструмент", selected_cell.get("instrument_class", "—"))
        meta_cols[2].metric(
            "Вторичный",
            "Да" if selected_cell.get("secondary_admission_applicable") else "Нет",
        )

        st.divider()

        # ------------------------------------------------------------------
        # L3 results per query type
        # ------------------------------------------------------------------
        for qt in QUERY_TYPES:
            status = get_l3_status(
                name_ru, venue_key, cell_id, qt, cell_index=selected_idx, state=state
            )
            icon = STATUS_ICON[status]

            if status == "done":
                result = load_l3_result(
                    name_ru, venue_key, cell_id, qt, cell_index=selected_idx
                )
                with st.expander(f"{icon} {qt} — готово", expanded=False):
                    if result:
                        retrieved = result.get("retrieved_at", "")
                        if retrieved:
                            st.caption(f"Получено: {retrieved}")
                        content = result.get("content")
                        if content is not None:
                            if isinstance(content, (dict, list)):
                                st.json(content)
                            else:
                                st.write(content)
                        else:
                            st.json(result, expanded=True)
                    else:
                        st.warning("Файл найден, но не удалось загрузить содержимое.")
            elif status == "pending":
                st.markdown(f"{icon} **{qt}** — в очереди / выполняется")
            else:
                st.markdown(f"{icon} **{qt}** — не запущено")

        st.divider()
        st.subheader("Параметры (Pass 2)")

        # Load pass2 data and validation status
        pass2_data = load_pass2_data(name_ru, venue_key, cell_id)
        val_status = load_cell_validation_status(name_ru, venue_key, cell_id)

        # Validation status indicator
        _VAL_COLORS = {"green": "🟢", "yellow": "🟡", "red": "🔴", "unknown": "⬜"}
        val_icon = _VAL_COLORS.get(val_status, "⬜")
        if val_status == "yellow":
            st.caption(f"{val_icon} Статус данных: источники не верифицированы")
        elif val_status == "red":
            st.caption(f"{val_icon} Статус данных: данные не получены")
        elif val_status == "green":
            st.caption(f"{val_icon} Статус данных: верифицировано")
        else:
            st.caption(f"{val_icon} Статус данных: неизвестен")

        if not pass2_data:
            if val_status == "red":
                st.warning("Данные для этой ячейки не были получены (RED).")
            else:
                st.info("pass2.json не найден — ячейка ещё не обработана.")
        else:
            param_values = pass2_data.get("parameter_values", [])

            if not param_values:
                st.info("Нет параметров в pass2.json")
            else:
                # Filters
                filter_cols = st.columns(3)

                all_statuses = sorted(set(pv.get("status", "not_found") for pv in param_values))
                all_phases = sorted(set(pv.get("lifecycle_phase", "") for pv in param_values if pv.get("lifecycle_phase")))

                status_filter = filter_cols[0].selectbox(
                    "Статус", ["все"] + all_statuses, key=f"status_filter_{cell_id}"
                )
                phase_filter = filter_cols[1].selectbox(
                    "Фаза ЖЦ", ["все"] + all_phases, key=f"phase_filter_{cell_id}"
                )

                # Apply filters
                filtered = [
                    pv for pv in param_values
                    if (status_filter == "все" or pv.get("status") == status_filter)
                    and (phase_filter == "все" or pv.get("lifecycle_phase") == phase_filter)
                ]

                # Status icon for parameter
                def _param_status_icon(status: str) -> str:
                    return {"found": "✅", "not_applicable": "⬜", "not_found": "❌"}.get(status, "❓")

                # Separate standard params (П-prefix) from CANDIDATE_XX and ADDITIONAL_X
                standard_params = [p for p in filtered if p.get("parameter_id", "").startswith(("П", "П-D"))]
                candidate_params = [p for p in filtered if p.get("parameter_id", "").startswith("CANDIDATE")]
                other_params = [p for p in filtered if p not in standard_params and p not in candidate_params]

                st.caption(f"Показано: {len(filtered)} из {len(param_values)} параметров")

                def _render_param_block(pv_list: list[dict]) -> None:
                    for pv in pv_list:
                        param_id = pv.get("parameter_id", "?")
                        param_name = pv.get("parameter_name", "")
                        status = pv.get("status", "not_found")
                        phase = pv.get("lifecycle_phase", "")
                        value = pv.get("value", "")
                        icon = _param_status_icon(status)

                        # Header: ID | name | value (truncated) | phase | status icon
                        header = f"{icon} **{param_id}** — {param_name}"
                        if phase:
                            header += f" `{phase}`"

                        with st.expander(header, expanded=False):
                            if value:
                                st.markdown(f"**Значение:** {value}")

                            methodology = pv.get("calculation_methodology", "")
                            if methodology:
                                st.markdown(f"**Методика расчёта:** {methodology}")

                            alternatives = pv.get("alternatives", "")
                            if alternatives:
                                st.markdown(f"**Альтернативы:** {alternatives}")

                            variations = pv.get("variations", "")
                            if variations:
                                st.markdown(f"**Вариации:** {variations}")

                            linkages = pv.get("linkages", [])
                            if linkages:
                                st.markdown(f"**Связки:** {', '.join(linkages)}")

                            source = pv.get("source", "")
                            if source:
                                st.markdown(f"**Источник:** `{source}`")

                            note = pv.get("note", "")
                            if note:
                                st.caption(f"Примечание: {note}")

                            if pv.get("drill_down_applied"):
                                st.caption("🔍 Применена доразведка (3P)")

                _render_param_block(standard_params + other_params)

                if candidate_params:
                    st.divider()
                    st.caption("**Параметры вне словаря (кандидаты)**")
                    _render_param_block(candidate_params)
