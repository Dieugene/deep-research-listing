# Task 004: Streamlit Viewer (L1 + L2 + L3 raw data)

## Что нужно сделать

Реализовать минимальный Streamlit viewer для просмотра сырых данных пайплайна:
- L1: карточки юрисдикций (jurisdiction_card.json)
- L2: карточки площадок (venue_card.json) и списки ячеек (cells_list.json)
- L3: сырые результаты Parallel Deep Research (3A/3B/3C/3D_raw.json) — если собраны

Это "лоскутный" инструмент для команды исследователей. Не финальный веб-интерфейс (он по спеке требует PostgreSQL, D3.js, 4 режима — это будущие задачи). Задача — удобно смотреть то, что уже собрано.

## Зачем

Данные L3 собираются сейчас. Нужен инструмент для мониторинга прогресса и просмотра результатов по мере их появления.

## Acceptance Criteria

- [ ] AC-1: Streamlit app запускается командой `venv\Scripts\streamlit run 02_src\viewer\app.py` из корня проекта
- [ ] AC-2: Sidebar — выбор юрисдикции (Великобритания / Гонконг) и площадки (LSE / Aquis_Stock_Exchange / HKEX)
- [ ] AC-3: Вкладка "Площадка" — key info из venue_card.json: название, оператор, тип, secondary_listing, список тиров/сегментов
- [ ] AC-4: Вкладка "Ячейки" — таблица cells_list.json с индикацией статуса L3 по каждому типу (3A/3B/3C/3D): done / pending / not started
- [ ] AC-5: При выборе ячейки — раскрытие результатов: для каждого доступного типа (3A/3B/3C/3D) показать содержимое raw JSON (поле `content`) в удобочитаемом виде
- [ ] AC-6: Вкладка "Юрисдикция" — ключевые поля из jurisdiction_card.json (название, правовая семья, регулятор, архитектура допуска)
- [ ] AC-7: Корректная работа при отсутствии L3 данных (ячейки отображаются со статусом "not started")
- [ ] AC-8: `implementation_01.md` создан

## Входные данные

### L1 — jurisdiction_card.json

Путь: `03_data/countries/{name_ru}/level_1/jurisdiction_card.json`

Пример полей (Великобритания):
```json
{
  "jurisdiction": "United Kingdom",
  "jurisdiction_ru": "Великобритания",
  ...
}
```

### L2 — venue_card.json

Путь: `03_data/countries/{name_ru}/level_2/{venue_key}/venue_card.json`

Ключевые поля:
```json
{
  "venue_key": "LSE",
  "venue_name_english": "London Stock Exchange",
  "venue_name_ru": "Лондонская фондовая биржа",
  "jurisdiction_ru": "Великобритания",
  "venue_type": "other",
  "operator": "London Stock Exchange plc",
  "secondary_listing_regime": true,
  "tiers": [
    {
      "tier_name": "Equity Shares – Commercial Companies (ESCC)",
      "tier_name_ru": "Акции – коммерческие компании (ESCC)",
      "segment_type": "listing_tier",
      "instrument_classes": ["equity"],
      "secondary_admission_applicable": false
    }
  ]
}
```

### L2 — cells_list.json

Путь: `03_data/countries/{name_ru}/level_2/{venue_key}/cells_list.json`

```json
[
  {
    "cell_id": "GB_LSE_escc_equity",
    "venue_key": "LSE",
    "tier": "Equity Shares – Commercial Companies (ESCC)",
    "instrument_class": "equity",
    "secondary_admission_applicable": false,
    "prompts": {
      "3A": "D:\\_workspace\\deep-research-listing\\03_data\\prompts\\level_3\\GB_LSE_escc_equity_3A.txt",
      "3B": "...",
      "3C": "...",
      "3D": null
    }
  }
]
```

### L3 — raw JSON (если собраны)

Путь: `03_data/countries/{name_ru}/level_3/{venue_key}/{cell_id}/{type}_raw.json`

Для ячеек с дублирующимися cell_id (AQSE, HKEX) Developer Level 3 сохранял в папку `{cell_id}_{i}/` (с 0-based индексом).

Структура файла:
```json
{
  "cell_id": "GB_LSE_escc_equity",
  "venue_key": "LSE",
  "query_type": "3A",
  "retrieved_at": "2026-03-06T...",
  "content": { ... }
}
```

### Маппинг venues

```python
PILOT_VENUES = [
    {"venue_key": "LSE",                  "name_ru": "Великобритания"},
    {"venue_key": "Aquis_Stock_Exchange",  "name_ru": "Великобритания"},
    {"venue_key": "HKEX",                  "name_ru": "Гонконг"},
]
```

## Структура файлов

```
02_src/
  viewer/
    __init__.py
    app.py          # точка входа Streamlit
    data_loader.py  # загрузка L1/L2/L3 данных из файлов
```

## Технический контекст

**Окружение:**
- venv: `D:\_workspace\deep-research-listing\venv`
- Запуск: `venv\Scripts\streamlit run 02_src\viewer\app.py` (из корня проекта)
- Streamlit должен быть установлен: `venv\Scripts\pip install streamlit`

**Существующая инфраструктура:**
- `02_src/pipeline/config.py` — COUNTRIES_DIR, PILOT_VENUES и функции `get_country_level2_dir`, `get_country_level3_dir`
- `02_src/pipeline/storage.py` — `load_json(path)` (возвращает None если файл не существует)

**sys.path**: добавлять `str(Path(__file__).resolve().parents[1])` перед pipeline-импортами (как в level_2, level_3 модулях).

## Детали реализации

### data_loader.py

```python
def load_jurisdiction_card(name_ru: str) -> dict | None
def load_venue_card(name_ru: str, venue_key: str) -> dict | None
def load_cells_list(name_ru: str, venue_key: str) -> list | None
def load_l3_result(name_ru: str, venue_key: str, cell_id: str, query_type: str, cell_index: int = 0) -> dict | None
    # cell_index нужен для ячеек с дублирующимися cell_id (AQSE/HKEX)
    # Пробует сначала path/{cell_id}/{type}_raw.json
    # Если не найден — пробует path/{cell_id}_{cell_index}/{type}_raw.json
def get_l3_status(name_ru: str, venue_key: str, cell_id: str, query_type: str, cell_index: int = 0) -> str
    # Возвращает "done" | "not started"
    # "done" = файл существует
    # "not started" = файл не существует
    # "pending" = определяется из level3_state.json (если task_key в state и status != "done")
def load_level3_state() -> dict
    # Загружает 04_logs/level3_state.json
```

### app.py — структура

```python
# Sidebar: выбор юрисдикции → площадки
# Три вкладки: "Юрисдикция" | "Площадка" | "Ячейки"

# Вкладка "Юрисдикция":
#   - Ключевые поля из jurisdiction_card.json в виде st.metric / st.json

# Вкладка "Площадка":
#   - venue_name, operator, venue_type, secondary_listing_regime
#   - Таблица тиров (tier_name_ru, instrument_classes, secondary_admission_applicable)

# Вкладка "Ячейки":
#   - st.dataframe с колонками: cell_id, tier, instrument_class, 3A, 3B, 3C, 3D
#   - Цветовые индикаторы статуса: ✅ done / ⏳ pending / ⬜ not started
#   - selectbox или radio для выбора ячейки
#   - При выборе ячейки — st.expander для каждого типа с доступным content
```

### Статус L3

Логика определения статуса для отображения в таблице:
1. Файл `{type}_raw.json` существует → "done" (✅)
2. В `level3_state.json` есть task_key с `status != "done"` → "pending" (⏳)
3. Иначе → "not started" (⬜)

Task key для поиска в state: `{cell_id}_{query_type}` или `{cell_id}_{query_type}_{i}` для дублей.

## Примечания

1. **Дублирующиеся cell_id в AQSE и HKEX**: при итерации по cells_list.json использовать enumerate для получения индекса `i`. При загрузке L3 данных пробовать оба варианта путей.
2. **Streamlit не нужен в requirements.txt** — просто `pip install streamlit` в venv. Добавь в README или в комментарий команду установки.
3. **Нет LLM-вызовов** в этой задаче — чистый просмотрщик файлов.
4. **Отсутствие данных** — корректно обрабатывать: `load_json` возвращает None, показывать "данные не собраны" вместо ошибки.
