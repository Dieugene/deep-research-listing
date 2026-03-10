# Level 3: Сбор данных по ячейкам — пилот (LSE, AQSE, HKEX)

## Что нужно сделать

Реализовать Level 3 пайплайна: запустить Parallel Deep Research задачи для каждой ячейки (cell_id × тип запроса), дождаться результатов, сохранить сырые JSON.

**Scope Task 003:** только runner (запуск + polling + сохранение сырых результатов). LLM-постобработка (маппинг на словарь параметров П01–П23) — отдельная задача.

## Зачем

Собрать фактические данные о требованиях к листингу по каждой ячейке. Результаты используются в Streamlit viewer и последующей пакетной LLM-постобработке.

## Acceptance Criteria

- [ ] AC-1: Для каждой ячейки запущены Parallel-задачи типов 3A, 3B, 3C (всегда) и 3D (если `secondary_admission_applicable=True`)
- [ ] AC-2: Процессор — `core` для всех типов запросов (решение по пилоту: $0.025/запрос)
- [ ] AC-3: Каждая задача запускается с JSON-схемой соответствующего типа (см. раздел "Схемы выхода")
- [ ] AC-4: Сырые результаты сохранены в `03_data/countries/{name_ru}/level_3/{venue_key}/{cell_id}/3A_raw.json` (и 3B, 3C, 3D аналогично)
- [ ] AC-5: State-файл `04_logs/level3_state.json` — изолирован от level1/level2, позволяет перезапустить с места сбоя
- [ ] AC-6: Идемпотентность: повторный запуск пропускает уже выполненные задачи
- [ ] AC-7: Логи в `04_logs/level3_YYYYMMDD.log`
- [ ] AC-8: CLI: `--step launch`, `--step poll`, `--step all`
- [ ] AC-9: `implementation_01.md` создан

## Входные данные

Промпты уже сгенерированы на Level 2. Пути хранятся прямо в `cells_list.json` каждой площадки:
- `03_data/countries/Великобритания/level_2/LSE/cells_list.json`
- `03_data/countries/Великобритания/level_2/Aquis_Stock_Exchange/cells_list.json`
- `03_data/countries/Гонконг/level_2/HKEX/cells_list.json`

**Структура ячейки из cells_list.json:**
```json
{
  "cell_id": "GB_LSE_escc_equity",
  "venue_key": "LSE",
  "tier": "Equity Shares – Commercial Companies (ESCC)",
  "instrument_class": "equity",
  "secondary_admission_applicable": false,
  "prompts": {
    "3A": "D:\\_workspace\\deep-research-listing\\03_data\\prompts\\level_3\\GB_LSE_escc_equity_3A.txt",
    "3B": "D:\\_workspace\\deep-research-listing\\03_data\\prompts\\level_3\\GB_LSE_escc_equity_3B.txt",
    "3C": "D:\\_workspace\\deep-research-listing\\03_data\\prompts\\level_3\\GB_LSE_escc_equity_3C.txt",
    "3D": null
  }
}
```

**Полный список ячеек по площадкам:**

### LSE (11 ячеек, jurisdiction_ru = "Великобритания")

| cell_id | tier | instrument_class | 3D? |
|---------|------|-----------------|-----|
| GB_LSE_escc_equity | Equity Shares – Commercial Companies (ESCC) | equity | нет |
| GB_LSE_closedended_investment_funds_fund | Closed-Ended Investment Funds | fund | нет |
| GB_LSE_equity_shares_shell_companies_equity | Equity Shares – Shell Companies | equity | нет |
| GB_LSE_equity_shares_transition_equity | Equity Shares – Transition | equity | нет |
| GB_LSE_equity_shares_international_co_equity | Equity Shares – International Commercial Companies Secondary Listing | equity | да |
| GB_LSE_sfs_fund | Specialist Fund Segment (SFS) | fund | нет |
| GB_LSE_aim_equity | AIM | equity | да |
| GB_LSE_aim_fund | AIM | fund | да |
| GB_LSE_psm_bond | Professional Securities Market (PSM) | bond | да |
| GB_LSE_psm_depositary_receipt | Professional Securities Market (PSM) | depositary_receipt | да |
| GB_LSE_ism_bond | International Securities Market (ISM) | bond | нет |

LSE итого: 11 ячеек × 3 типа = 33 задачи + 5 ячеек с 3D = 38 задач.

### Aquis_Stock_Exchange (12 ячеек, jurisdiction_ru = "Великобритания")

| cell_id | tier | instrument_class | 3D? |
|---------|------|-----------------|-----|
| GB_Aquis_Stock_Exchange_aqse_main_market_equity | AQSE Main Market | equity | да |
| GB_Aquis_Stock_Exchange_aqse_main_market_bond | AQSE Main Market | bond | да |
| GB_Aquis_Stock_Exchange_aqse_main_market_fund | AQSE Main Market | fund | да |
| GB_Aquis_Stock_Exchange_aqse_main_market_depositary_receipt | AQSE Main Market | depositary_receipt | да |
| GB_Aquis_Stock_Exchange_aquis_stock_exchange_growth_ma_equity | Aquis Stock Exchange – Growth Market – Access | equity | да |
| GB_Aquis_Stock_Exchange_aquis_stock_exchange_growth_ma_bond | Aquis Stock Exchange – Growth Market – Access | bond | да |
| GB_Aquis_Stock_Exchange_aquis_stock_exchange_growth_ma_fund | Aquis Stock Exchange – Growth Market – Access | fund | да |
| GB_Aquis_Stock_Exchange_aquis_stock_exchange_growth_ma_depositary_receipt | Aquis Stock Exchange – Growth Market – Access | depositary_receipt | да |
| GB_Aquis_Stock_Exchange_aquis_stock_exchange_growth_ma_equity | Aquis Stock Exchange – Growth Market – Apex | equity | да |
| GB_Aquis_Stock_Exchange_aquis_stock_exchange_growth_ma_bond | Aquis Stock Exchange – Growth Market – Apex | bond | да |
| GB_Aquis_Stock_Exchange_aquis_stock_exchange_growth_ma_fund | Aquis Stock Exchange – Growth Market – Apex | fund | да |
| GB_Aquis_Stock_Exchange_aquis_stock_exchange_growth_ma_depositary_receipt | Aquis Stock Exchange – Growth Market – Apex | depositary_receipt | да |

> **Замечание:** в cells_list.json для AQSE есть дублирующиеся cell_id между тирами Access и Apex (например, `GB_Aquis_Stock_Exchange_aquis_stock_exchange_growth_ma_equity` встречается дважды с разными `tier`). При итерации использовать индекс позиции или составной ключ `{cell_id}_{index}` для task_key, чтобы избежать коллизий в state-файле. Рекомендуется: `{cell_id}_{query_type}_{i}` где `i` — порядковый номер ячейки в списке.

AQSE итого: 12 ячеек × 3 типа = 36 задач + 12 ячеек с 3D = 48 задач.

### HKEX (5 ячеек, jurisdiction_ru = "Гонконг")

| cell_id | tier | instrument_class | 3D? |
|---------|------|-----------------|-----|
| HK_HKEX__equity | 主板 | equity | да |
| HK_HKEX__bond | 主板 | bond | да |
| HK_HKEX__fund | 主板 | fund | да |
| HK_HKEX__depositary_receipt | 主板 | depositary_receipt | да |
| HK_HKEX__equity | 創業板 | equity | нет |

> **Замечание:** в HKEX тоже есть дублирующийся cell_id `HK_HKEX__equity` (主板 и 創業板). Применить ту же стратегию уникального task_key с индексом.

HKEX итого: 5 ячеек × 3 типа = 15 задач + 4 ячейки с 3D = 19 задач.

**Итого задач Parallel: 38 + 48 + 19 = 105** (в task brief указано 96, но фактический подсчёт по cells_list.json даёт 105; использовать фактические данные из файлов).

## Структура файлов

```
02_src/
  level_3/
    __init__.py
    cell_runner.py      # launch + poll Parallel задач
    run_level3.py       # оркестратор (CLI)

03_data/
  countries/
    Великобритания/
      level_3/
        LSE/
          GB_LSE_escc_equity/
            3A_raw.json
            3B_raw.json
            3C_raw.json
          GB_LSE_aim_equity/
            3A_raw.json
            3B_raw.json
            3C_raw.json
            3D_raw.json   # только если secondary_admission_applicable
        Aquis_Stock_Exchange/
          ...
    Гонконг/
      level_3/
        HKEX/
          ...

04_logs/
  level3_state.json
  level3_YYYYMMDD.log
```

## Технический контекст

**Окружение:**
- venv: `D:\_workspace\deep-research-listing\venv`
- Запуск: `cd 02_src && ..\venv\Scripts\python.exe -m level_3.run_level3 --step all`
- Стек: Python, Parallel SDK (`parallel-web`)

**Существующая инфраструктура (`02_src/pipeline/`):**

| Модуль | Назначение |
|--------|-----------|
| `parallel_runner.py` | `launch_task`, `poll_all`, `save_state`, `load_state` |
| `config.py` | `PILOT_VENUES`, `PROMPTS_LEVEL3_DIR`, `POLL_INTERVAL_SECONDS`, `LEVEL1_STATE_FILE`, `LEVEL2_STATE_FILE` |
| `logging_setup.py` | `get_logger(name, log_file)` |
| `storage.py` | `load_json`, `save_json`, `now_iso` |

**Паттерн запуска:** `02_src/level_2/venue_runner.py` — образец для `cell_runner.py`.

**Сигнатура `launch_task`:**
```python
launch_task(
    task_key: str,
    prompt: str,
    output_schema: Optional[Any],   # None | "auto" | dict (JSON-схема)
    state: dict,
    processor: str = PARALLEL_PROCESSOR,   # default "pro" в config, override "core"
    state_file: Optional[Path] = None,
)
```
Внутри: если `output_schema` — dict, передаёт `task_spec={"output_schema": {"type": "json", "json_schema": output_schema}}`.

**Важно:** `core` + JSON-схема (dict) — валидная комбинация согласно PyPI docs. `core` + `"auto"` — невалидно (вернёт 400). Всегда передавать `output_schema=<dict схемы>`, не `"auto"`.

**Константы, которые нужно добавить в `config.py`:**
```python
LEVEL3_STATE_FILE = LOGS_DIR / "level3_state.json"
LEVEL3_LOG_FILE   = LOGS_DIR / f"level3_{_today}.log"

def get_country_level3_dir(name_ru: str, venue_key: str) -> Path:
    """Return path to level_3 data dir for a venue."""
    return COUNTRIES_DIR / name_ru / "level_3" / venue_key
```

**Task key format:** `{cell_id}_{query_type}` — например `GB_LSE_escc_equity_3A`.
Для ячеек с дублирующимися cell_id: `{cell_id}_{query_type}_{i}` где `i` — 0-based индекс в списке cells.

## Схемы выхода (output_schema для Parallel)

Передавать как `dict` (не строку) в `launch_task(output_schema=SCHEMA_3A)`.

### 3A — Первичный допуск (processor: core)
```json
{
  "quantitative_requirements": {
    "free_float": { "description": "string", "source": "string" },
    "market_capitalisation": { "description": "string", "source": "string" },
    "shareholders_count": { "description": "string", "source": "string" },
    "share_price": { "description": "string", "source": "string" },
    "trading_volume": { "description": "string", "source": "string" },
    "issue_size": { "description": "string", "source": "string" }
  },
  "financial_requirements": {
    "financial_history": { "description": "string", "source": "string" },
    "profit_requirements": { "description": "string", "source": "string" },
    "assets_equity": { "description": "string", "source": "string" },
    "revenue": { "description": "string", "source": "string" },
    "working_capital": { "description": "string", "source": "string" }
  },
  "qualitative_requirements": {
    "corporate_governance": { "description": "string", "source": "string" },
    "auditor_standards": { "description": "string", "source": "string" }
  },
  "infrastructure": {
    "sponsor": { "description": "string", "source": "string" },
    "market_maker": { "description": "string", "source": "string" },
    "prospectus": { "description": "string", "source": "string" }
  },
  "restrictions": {
    "lock_up": { "description": "string", "source": "string" },
    "escrow": { "description": "string", "source": "string" }
  },
  "procedure": {
    "application_process": { "description": "string", "source": "string" },
    "timeline": { "description": "string", "source": "string" },
    "approval_decision": { "description": "string", "source": "string" }
  },
  "special_regimes": {
    "spac_modifications": { "description": "string", "source": "string" },
    "wvr_modifications": { "description": "string", "source": "string" },
    "foreign_issuer_modifications": { "description": "string", "source": "string" }
  },
  "additional_findings": { "description": "string", "source": "string" }
}
```

### 3B — Поддержание, приостановка, делистинг (processor: core)
```json
{
  "continuing_obligations": {
    "quantitative_thresholds": { "description": "string", "source": "string" },
    "qualitative_obligations": { "description": "string", "source": "string" },
    "periodic_reporting": { "description": "string", "source": "string" },
    "compliance_confirmation": { "description": "string", "source": "string" }
  },
  "suspension": {
    "grounds": { "description": "string", "source": "string" },
    "procedure": { "description": "string", "source": "string" },
    "disclosure": { "description": "string", "source": "string" },
    "duration_limits": { "description": "string", "source": "string" }
  },
  "delisting_compulsory": {
    "grounds": { "description": "string", "source": "string" },
    "procedure": { "description": "string", "source": "string" },
    "grace_period": { "description": "string", "source": "string" },
    "shareholder_protection": { "description": "string", "source": "string" },
    "disclosure": { "description": "string", "source": "string" }
  },
  "delisting_voluntary": {
    "conditions": { "description": "string", "source": "string" },
    "procedure": { "description": "string", "source": "string" },
    "shareholder_approval": { "description": "string", "source": "string" }
  },
  "terminology": {
    "delisting_local_term": "string",
    "suspension_local_term": "string",
    "source": "string"
  },
  "additional_findings": { "description": "string", "source": "string" }
}
```

### 3C — Мониторинг и enforcement (processor: core)
```json
{
  "monitoring_regime": {
    "responsible_body": { "description": "string", "source": "string" },
    "mechanisms": { "description": "string", "source": "string" },
    "sponsor_role": { "description": "string", "source": "string" },
    "issuer_reporting_to_exchange": { "description": "string", "source": "string" }
  },
  "sanctions": {
    "exchange_sanctions": { "description": "string", "source": "string" },
    "regulator_sanctions": { "description": "string", "source": "string" },
    "disciplinary_procedure": { "description": "string", "source": "string" },
    "publication_of_actions": { "description": "string", "source": "string" }
  },
  "enforcement_practice": {
    "recent_examples": { "description": "string", "source": "string" },
    "general_approach": { "description": "string", "source": "string" }
  },
  "additional_findings": { "description": "string", "source": "string" }
}
```

### 3D — Вторичный допуск (processor: core, только если secondary_admission_applicable=True)
```json
{
  "eligibility": {
    "qualifying_exchanges": { "description": "string", "source": "string" },
    "market_cap_threshold": { "description": "string", "source": "string" },
    "track_record": { "description": "string", "source": "string" }
  },
  "waivers_from_standard": { "description": "string", "source": "string" },
  "additional_requirements": { "description": "string", "source": "string" },
  "continuing_obligations_differences": { "description": "string", "source": "string" },
  "secondary_vs_dual_primary": { "description": "string", "source": "string" },
  "additional_findings": { "description": "string", "source": "string" }
}
```

## Порядок выполнения

```
1. Прочитать cells_list.json для всех трёх площадок:
   - 03_data/countries/Великобритания/level_2/LSE/cells_list.json
   - 03_data/countries/Великобритания/level_2/Aquis_Stock_Exchange/cells_list.json
   - 03_data/countries/Гонконг/level_2/HKEX/cells_list.json

2. Для каждой ячейки (с учётом уникальности task_key через индекс):
   × каждый применимый тип запроса (3A, 3B, 3C всегда; 3D если secondary_admission_applicable=True):
     a. Прочитать промпт из файла по пути из cells_list.json["prompts"][type]
     b. launch_task(
            task_key=f"{cell_id}_{query_type}",   # или с индексом если cell_id дублируется
            prompt=<содержимое файла>,
            output_schema=SCHEMA_3A|3B|3C|3D,     # dict, не строка
            processor="core",
            state=state,
            state_file=LEVEL3_STATE_FILE,
        )

3. poll_all(tasks_to_poll, state, state_file=LEVEL3_STATE_FILE)
   - tasks_to_poll: список (task_key, save_fn) для всех запущенных задач

4. save_fn(content) для каждой задачи:
   - Сохранить в: 03_data/countries/{jurisdiction_ru}/level_3/{venue_key}/{cell_id}/{type}_raw.json
   - Формат файла:
     {
       "cell_id": "...",
       "venue_key": "...",
       "query_type": "3A",
       "retrieved_at": "<ISO timestamp>",
       "content": <dict от Parallel>
     }
```

## Существующий код для reference

**`02_src/pipeline/parallel_runner.py`** — функции:
- `launch_task(task_key, prompt, output_schema, state, processor, state_file)` — запуск задачи с идемпотентностью
- `poll_all(tasks_to_poll, state, state_file)` — поллинг списка задач до завершения
- `load_state(state_file)` — загрузка state dict с диска
- `save_state(state, state_file)` — сохранение state dict на диск

**`02_src/pipeline/config.py`** — текущие константы:
- `PROMPTS_LEVEL3_DIR = DATA_DIR / "prompts" / "level_3"` (уже есть)
- `COUNTRIES_DIR = DATA_DIR / "countries"`
- `POLL_INTERVAL_SECONDS = 60`
- `PILOT_VENUES` — список dict с `venue_key`, `name_ru`, `venue_name_english`
- `LEVEL1_STATE_FILE`, `LEVEL2_STATE_FILE` — образец для добавления `LEVEL3_STATE_FILE`

**`02_src/pipeline/logging_setup.py`:**
- `get_logger(name, log_file=None)` — возвращает logger с файловым и консольным хендлером

**`02_src/pipeline/storage.py`:**
- `load_json(path)` — загрузка JSON, None если файл не существует
- `save_json(path, data)` — сохранение JSON (создаёт директории)
- `now_iso()` — текущее время в ISO формате

**`02_src/level_2/venue_runner.py`** — образец для `cell_runner.py`:
- Паттерн `load_state` / `save_state` через `state_file` override
- Паттерн `_make_save_fn(venue)` — фабрика функций сохранения для `poll_all`
- CLI через `argparse` с `--launch` / `--poll`

## Примечания и подводные камни

1. **Дублирующиеся cell_id в AQSE и HKEX.** В cells_list.json у AQSE восемь ячеек имеют одинаковые cell_id (Access и Apex тиры используют один и тот же cell_id, отличаясь только полем `tier`). У HKEX `HK_HKEX__equity` встречается дважды. Task key в state-файле должен быть уникальным — использовать `{cell_id}_{query_type}_{i}` или prefixed вариант.

2. **Промпты уже существуют.** Не генерировать промпты — только читать из путей в cells_list.json.

3. **Процессор строго `"core"`.** Не использовать дефолт `PARALLEL_PROCESSOR` из config (он равен `"pro"`). Передавать `processor="core"` явно в каждый вызов `launch_task`.

4. **output_schema = dict, не "auto".** `core` + `"auto"` вернёт 400. Передавать конкретную схему в виде dict.

5. **State-файл изолирован.** `LEVEL3_STATE_FILE = LOGS_DIR / "level3_state.json"` — добавить в config.py, не смешивать с level1/level2 state.

6. **Сохранение сырого content.** `poll_all` возвращает `content` — это уже dict (Parallel возвращает JSON согласно переданной схеме). Обернуть в метаданные и сохранить через `save_json`.

7. **Создание директорий.** `save_json` из `storage.py` создаёт директории автоматически (`path.parent.mkdir(parents=True, exist_ok=True)`).
