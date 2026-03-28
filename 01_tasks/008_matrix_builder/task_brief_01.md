# Task 008: L3 Matrix Builder 4×5

## Что нужно сделать

Построить матрицу 4×5 (жизненные фазы × типы регулятивного содержания) из 3A/3B/3C raw JSON для каждой ячейки уровня 3.

1. **Создать `02_src/level_3/matrix_builder.py`** — алгоритмический маппинг + LLM-маппинг + сборка
2. **Интегрировать в `run_pipeline.py`** — новый шаг L3 Step 7 после Step 6 (Add citations)
3. **Создать catch-up скрипт** — `02_src/tools/run_matrix_catchup.py`

## Acceptance Criteria

- [ ] AC-1: `build_matrix_all()` создаёт `matrix.json` в директории каждой ячейки
- [ ] AC-2: `matrix.json` соответствует схеме из spec (разделы 5.3, 5.4)
- [ ] AC-3: Алгоритмический маппинг корректен по таблице раздела 3 ниже
- [ ] AC-4: LLM-маппинг (sanctions, monitoring, additional_findings) использует `LLM_FAST_MODEL`
- [ ] AC-5: Идемпотентность — пропускает ячейку если `matrix.json` уже существует
- [ ] AC-6: `run_pipeline.py` вызывает `build_matrix_all()` как L3 Step 7
- [ ] AC-7: Catch-up скрипт создан (не запускать)

## Контекст

### Структура данных на входе

**3A_raw.json** (`content` — плоский, 1 уровень):
```
content[field_key] = {"description": "...", "source": "url or text"}
```
Пример полей: `admission_overview`, `eligibility_requirements`, `instrument_requirements`, `sponsor_and_infrastructure`, `restrictions_and_lock_ups`, `special_regimes`, `procedure_and_timeline`, `disclosure_at_admission`, `secondary_admission`, `additional_findings`

Могут также присутствовать поля с суффиксом `_common` (например, `common_requirements_common`) — они не в маппинге, пропускать.

**3B_raw.json** (`content` — вложенный, 2 уровня):
```
content[parent_key][sub_key] = {"description": "...", "source": "url or text"}
```
Родительские ключи: `continuing_obligations`, `suspension`, `delisting_compulsory`, `delisting_voluntary`, `terminology`, `additional_findings`
Примечание: `additional_findings` в 3B — плоский (`content.additional_findings = {description, source}`)

**3C_raw.json** (`content` — вложенный, 2 уровня):
```
content[parent_key][sub_key] = {"description": "...", "source": "url or text"}
```
Родительские ключи: `monitoring_regime`, `sanctions`, `enforcement_practice`, `additional_findings`
Примечание: `additional_findings` в 3C — плоский

### Метаданные ячейки

Из любого из трёх файлов (они идентичны в этих полях):
- `cell_id` — строка
- `venue_key` — строка
- `instrument_class` — строка
- `tier_name` — строка (из `content.tier_name` или `tier_name_from_parallel`)

### Таблица маппинга (алгоритмическая)

#### Из 3A → G07_1 (первичный допуск)

| Поле content | Ячейка матрицы | Subtitle для UI |
|--------------|---------------|-----------------|
| `admission_overview` | G07_1.D01 | "Режим допуска" |
| `eligibility_requirements` | G07_1.D01 | "Требования к эмитенту" |
| `instrument_requirements` | G07_1.D01 | "Требования к инструменту" |
| `sponsor_and_infrastructure` | G07_1.D01 | "Инфраструктура и спонсор" |
| `restrictions_and_lock_ups` | G07_1.D01 | "Ограничения и lock-up" |
| `special_regimes` | G07_1.D01 | "Специальные режимы" |
| `procedure_and_timeline` | G07_1.D02 | "Процедура допуска" |
| `disclosure_at_admission` | G07_1.D05 | "Раскрытие при допуске" |
| `secondary_admission` | G07_1.D01 | "Вторичный допуск" |
| `additional_findings` | LLM | — |

#### Из 3B → G07_2, G07_3, G07_4

| Путь content | Ячейка матрицы | Subtitle |
|-------------|---------------|----------|
| `continuing_obligations.quantitative_thresholds` | G07_2.D01 | "Количественные пороги" |
| `continuing_obligations.qualitative_obligations` | G07_2.D01 | "Качественные обязательства" |
| `continuing_obligations.compliance_confirmation` | G07_2.D02 | "Подтверждение соответствия" |
| `continuing_obligations.periodic_reporting` | G07_2.D05 | "Периодическая отчётность" |
| `suspension.grounds` | G07_3.D01 | "Основания приостановки" |
| `suspension.duration_limits` | G07_3.D01 | "Сроки приостановки" |
| `suspension.procedure` | G07_3.D02 | "Процедура приостановки" |
| `suspension.disclosure` | G07_3.D05 | "Раскрытие при приостановке" |
| `delisting_compulsory.grounds` | G07_4.D01 | "Основания принудительного исключения" |
| `delisting_compulsory.procedure` | G07_4.D02 | "Процедура исключения" |
| `delisting_compulsory.grace_period` | G07_4.D02 | "Переходный период" |
| `delisting_compulsory.shareholder_protection` | G07_4.D02 | "Защита акционеров" |
| `delisting_compulsory.disclosure` | G07_4.D05 | "Раскрытие при исключении" |
| `delisting_voluntary.conditions` | G07_4.D01 | "Условия добровольного исключения" |
| `delisting_voluntary.procedure` | G07_4.D02 | "Процедура добровольного исключения" |
| `delisting_voluntary.shareholder_approval` | G07_4.D02 | "Одобрение акционеров" |
| `terminology` | metadata | — |
| `additional_findings` | LLM | — |

#### Из 3C → преимущественно G07_2

| Путь content | Ячейка (базовая) | Subtitle |
|-------------|-----------------|----------|
| `monitoring_regime.responsible_body` | G07_2.D03 | "Ответственный орган" |
| `monitoring_regime.mechanisms` | G07_2.D03 | "Механизмы контроля" |
| `monitoring_regime.sponsor_role` | G07_2.D03 | "Роль спонсора" |
| `monitoring_regime.issuer_reporting_to_exchange` | G07_2.D03 | "Отчётность перед биржей" |
| `sanctions.exchange_sanctions` | G07_2.D04 (LLM) | "Санкции биржи" |
| `sanctions.regulator_sanctions` | G07_2.D04 (LLM) | "Санкции регулятора" |
| `sanctions.disciplinary_procedure` | G07_2.D04 | "Дисциплинарная процедура" |
| `sanctions.publication_of_actions` | G07_2.D04 | "Публикация решений" |
| `enforcement_practice.recent_examples` | G07_2.D04 | "Практика применения" |
| `enforcement_practice.general_approach` | G07_2.D04 | "Общий подход к enforcement" |
| `additional_findings` | LLM | — |

### Пустые и пропускаемые значения

Если `description` равно `""`, `"not applicable"`, `"Not applicable"`, `"N/A"`, `"н/д"` (регистронезависимо) — **пропустить поле** (не добавлять content item).

### Ячейки "не применимо" по умолчанию

Следующие ячейки матрицы по умолчанию `null` (если Parallel не вернул данные):
- `G07_1.D03`, `G07_1.D04`, `G07_4.D03`

### Формат matrix.json

```json
{
  "cell_id": "GB_LSE_Main_Market_equity_shares_commercial_compa_equity",
  "venue_key": "LSE_Main_Market",
  "tier": "Equity Shares (Commercial Companies)",
  "instrument_class": "equity",
  "matrix": {
    "G07_1": {
      "D01_requirements": {
        "content": [
          {
            "subtitle": "Режим допуска",
            "description": "...",
            "source": "https://...",
            "origin_field": "admission_overview"
          }
        ]
      },
      "D02_procedures": {"content": [...]},
      "D03_monitoring": null,
      "D04_sanctions": null,
      "D05_disclosure": {"content": [...]}
    },
    "G07_2": {
      "D01_requirements": {"content": [...]},
      "D02_procedures": {"content": [...]},
      "D03_monitoring": {"content": [...]},
      "D04_sanctions": {"content": [...]},
      "D05_disclosure": {"content": [...]}
    },
    "G07_3": {
      "D01_requirements": {"content": [...]},
      "D02_procedures": {"content": [...]},
      "D03_monitoring": null,
      "D04_sanctions": null,
      "D05_disclosure": {"content": [...]}
    },
    "G07_4": {
      "D01_requirements": {"content": [...]},
      "D02_procedures": {"content": [...]},
      "D03_monitoring": null,
      "D04_sanctions": null,
      "D05_disclosure": {"content": [...]}
    }
  },
  "metadata": {
    "validation_status": "green",
    "phases_covered": ["G07_1", "G07_2", "G07_3", "G07_4"],
    "phases_not_covered": [],
    "terminology": {}
  }
}
```

Правило `null` vs `{"content": []}`:
- `null` — если ячейка "не применимо" (из списка выше) и Parallel не вернул данных
- `{"content": []}` — если ячейка ожидается, но данных не нашлось
- `{"content": [...]}` — если есть данные

### LLM-маппинг (один вызов на ячейку)

**Использовать `LLM_FAST_MODEL` из `pipeline/config.py`.**

Входные данные для LLM (только поля требующие маппинга):
- `sanctions.*` из 3C (`exchange_sanctions`, `regulator_sanctions`)
- `monitoring_regime.*` из 3C (весь блок, для поиска упоминаний suspension)
- `additional_findings.description` из 3A, 3B, 3C

**Промпт (на английском):**

```
You are analyzing regulatory content for a securities exchange listing cell.
Cell: {cell_id}, Venue: {venue_key}

TASK 1 - Sanctions phase routing:
The following sanctions text describes enforcement measures. For each distinct sanction type,
determine its primary lifecycle phase:
- G07_2 (maintenance): sanctions for ongoing compliance breaches (fines, censures, etc.)
- G07_3 (suspension): suspension of trading as a measure or during investigation
- G07_4 (removal): compulsory delisting/cancellation as ultimate sanction

Exchange sanctions text: {exchange_sanctions}
Regulator sanctions text: {regulator_sanctions}

TASK 2 - Monitoring during suspension:
Does the following monitoring text explicitly mention monitoring *during a suspension period*?
If yes, extract that specific fragment (verbatim or paraphrased). If no, return null.
Monitoring text: {monitoring_combined}

TASK 3 - Additional findings routing:
Route each additional_findings text to the appropriate matrix cell.
3A additional_findings: {af_3a}
3B additional_findings: {af_3b}
3C additional_findings: {af_3c}

Return JSON:
{
  "sanctions": {
    "G07_2": "text | null",
    "G07_3": "text | null",
    "G07_4": "text | null"
  },
  "monitoring_suspension": "text | null",
  "additional_findings": [
    {"text": "...", "phase": "G07_1|G07_2|G07_3|G07_4", "content_type": "D01|D02|D03|D04|D05", "source_query": "3A|3B|3C"}
  ]
}

Rules:
- If a sanctions text doesn't clearly fit G07_3 or G07_4, assign to G07_2
- For additional_findings, if unable to determine → return {"text": "...", "phase": "UNKNOWN", "content_type": "UNKNOWN", "source_query": "..."}
- UNKNOWN items are not added to the matrix
- Keep phase and content_type codes exactly as shown
```

**Используй `with_structured_output` из langchain** с Pydantic-схемой для валидации вывода:

```python
from pydantic import BaseModel
from typing import Optional

class SanctionsDistribution(BaseModel):
    G07_2: Optional[str] = None
    G07_3: Optional[str] = None
    G07_4: Optional[str] = None

class AdditionalFinding(BaseModel):
    text: str
    phase: str  # G07_1|G07_2|G07_3|G07_4|UNKNOWN
    content_type: str  # D01|D02|D03|D04|D05|UNKNOWN
    source_query: str  # 3A|3B|3C

class LLMMatrixOutput(BaseModel):
    sanctions: SanctionsDistribution
    monitoring_suspension: Optional[str] = None
    additional_findings: list[AdditionalFinding] = []
```

**LLM вызов через batch (не invoke), `max_concurrency=50`:**
```python
from langchain_core.messages import HumanMessage
chain = llm.with_structured_output(LLMMatrixOutput)
results = chain.batch(
    [[HumanMessage(content=prompt)] for prompt in prompts],
    config={"max_concurrency": 50}
)
```

### Сборка результатов LLM в матрицу

После получения `LLMMatrixOutput` для ячейки:

1. **Sanctions routing** (заменяет базовый G07_2.D04 для exchange_sanctions и regulator_sanctions):
   - Для каждой фазы G07_2/G07_3/G07_4 где результат не None → добавить content item в соответствующую ячейку × D04
   - Subtitle: "Санкции (биржа + регулятор)"
   - `origin_field`: "sanctions_llm_routed"
   - `source`: объединить источники `exchange_sanctions.source` + `regulator_sanctions.source`

2. **Monitoring during suspension** (если не None):
   - Добавить content item в G07_3.D03
   - Subtitle: "Мониторинг при приостановке"
   - `origin_field`: "monitoring_regime_suspension"
   - `source`: объединить source из monitoring_regime полей

3. **Additional findings** (только те, у которых phase и content_type != UNKNOWN):
   - Добавить в соответствующую ячейку матрицы
   - Subtitle: "Дополнительные находки"
   - `origin_field`: f"additional_findings_{source_query}"

### Архитектура `02_src/level_3/matrix_builder.py`

```python
def _extract_content_item(description: str, source: str, subtitle: str, origin_field: str) -> dict | None:
    """Returns content dict or None if description is empty/n/a."""
    ...

def build_matrix_algorithmic(raw_3a: dict, raw_3b: dict, raw_3c: dict) -> dict:
    """Builds matrix from deterministic field mappings. Returns partial matrix (dict)."""
    ...

def build_matrix_llm_inputs(raw_3a: dict, raw_3b: dict, raw_3c: dict) -> dict:
    """Returns dict of inputs needed for LLM prompt."""
    ...

def apply_llm_output(matrix: dict, llm_output: LLMMatrixOutput, raw_3c: dict) -> dict:
    """Applies LLM routing results to the algorithmic matrix. Returns updated matrix."""
    ...

def build_matrix_for_cell(cell_dir: Path, llm_chain) -> dict:
    """Full pipeline for one cell: load 3A/3B/3C, algo, LLM, assemble, return matrix."""
    ...

def build_matrix_all(venues: list[str] | None = None, llm=None) -> None:
    """Iterates COUNTRIES_DIR, finds all cell dirs, builds matrix.json. Idempotent.

    If llm is None, creates one using LLM_FAST_MODEL.
    Collects all prompts first, batch-calls LLM, then assembles and saves.
    """
    ...
```

### Путь к данным

```python
from pipeline.config import COUNTRIES_DIR
# COUNTRIES_DIR / name_ru / "level_3" / venue_key / cell_id / "3A_raw.json"
# COUNTRIES_DIR / name_ru / "level_3" / venue_key / cell_id / "matrix.json"
```

Итерация по всем ячейкам:
```python
for country_dir in COUNTRIES_DIR.iterdir():
    l3_dir = country_dir / "level_3"
    if not l3_dir.exists():
        continue
    for venue_dir in l3_dir.iterdir():
        for cell_dir in venue_dir.iterdir():
            if (cell_dir / "3A_raw.json").exists():
                yield cell_dir
```

### Паттерн lazy imports в run_pipeline.py

```python
def run_level3(venues: list[dict]) -> None:
    ...
    logger.info("--- L3 Step 6: Add citations ---")
    from pipeline.sources import process_level3_citations
    process_level3_citations()

    logger.info("--- L3 Step 7: Build matrix ---")
    from level_3.matrix_builder import build_matrix_all
    from pipeline.config import LLM_FAST_MODEL
    build_matrix_all(llm=None)  # создаёт LLM_FAST_MODEL внутри
```

### Обработка ошибок LLM

Если LLM вызов упал для конкретной ячейки:
- Логировать `logger.warning("LLM matrix failed for cell %s: %s", cell_id, exc)`
- Сохранить матрицу без LLM-части (только алгоритмический маппинг)
- Не прерывать обработку остальных ячеек

### Логирование

```python
from pipeline.logging_setup import get_logger
from pipeline.config import LOGS_DIR
import datetime
logger = get_logger("matrix_builder", LOGS_DIR / f"matrix_{datetime.date.today()}.log")
```

## Что реализовать

### Шаг 1: `02_src/level_3/matrix_builder.py`

Создать модуль с функциями из раздела архитектуры выше.

### Шаг 2: Обновить `02_src/run_pipeline.py`

Добавить L3 Step 7 (lazy import, вызов `build_matrix_all()`).

### Шаг 3: Catch-up скрипт `02_src/tools/run_matrix_catchup.py`

```python
"""Catch-up: строит matrix.json для всех существующих ячеек."""
# usage: python run_matrix_catchup.py [--dry-run]
# не запускать — только создать
```

## Файлы к изменению/созданию

- `02_src/level_3/matrix_builder.py` — **создать**
- `02_src/run_pipeline.py` — добавить L3 Step 7
- `02_src/tools/run_matrix_catchup.py` — **создать** (не запускать)

## Ключевые файлы для чтения (контекст)

- `02_src/pipeline/config.py` — COUNTRIES_DIR, LOGS_DIR, LLM_FAST_MODEL
- `02_src/pipeline/logging_setup.py` — get_logger
- `02_src/run_pipeline.py` — текущая структура run_level3()
- Пример данных: `03_data/countries/Великобритания/level_3/LSE_Main_Market/GB_LSE_Main_Market_equity_shares_commercial_compa_equity/3A_raw.json`

## Формат отчёта

Создай `01_tasks/008_matrix_builder/implementation_01.md`:
```
# Отчёт о реализации: Task 008 — L3 Matrix Builder 4×5

## Что реализовано
## Файлы (Новые / Изменённые)
## Особенности реализации
## Известные проблемы
```
