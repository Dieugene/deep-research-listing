# Task 012: L1/L2 Normalizations

## Что нужно сделать

Добавить нормализованные поля в `jurisdiction_card.json` (L1) и `venue_card.json` (L2).

## Acceptance Criteria

- [ ] AC-1: `legal_family` нормализован к lowercase enum в каждом `jurisdiction_card.json`
- [ ] AC-2: Новое поле `market_type` добавлено в каждый `jurisdiction_card.json` (из lookup-таблицы)
- [ ] AC-3: Новое поле `listing_authority_short` добавлено в каждый `jurisdiction_card.json` (LLM)
- [ ] AC-4: `venue_type` нормализован в каждом `venue_card.json`
- [ ] AC-5: Все функции идемпотентны
- [ ] AC-6: `run_pipeline.py` вызывает `process_l1_normalizations()` как L1 Step 10 (после citations)
- [ ] AC-7: `run_pipeline.py` вызывает `process_l2_normalizations()` как L2 Step 6 (после citations)
- [ ] AC-8: Catch-up скрипт `02_src/tools/run_l1_l2_normalize_catchup.py` создан (не запускать)

## Детали нормализаций

### С-1: `legal_family` — lowercase enum (алгоритм)

Нормализация: `val.strip().lower()`.
Допустимые значения: `"common law"` | `"civil law"` | `"mixed"`.
Если уже lowercase и допустимое — пропускать.

Текущее состояние данных:
- Германия: `"Civil law"` → нужна нормализация
- Остальные 5 юрисдикций: уже `"common law"` или `"civil law"`

### С-2: `market_type` — DM/EM lookup-таблица (алгоритм)

Новое поле (сейчас отсутствует во всех jurisdiction_card.json).
Добавлять только если поле отсутствует.

```python
_MARKET_TYPE_LOOKUP = {
    "Австралия": "DM",
    "Великобритания": "DM",
    "Германия": "DM",
    "Гонконг": "DM",
    "Сингапур": "DM",
    "Франция": "DM",
}
```

Если юрисдикция не найдена в таблице — пропустить с предупреждением в лог.

### Ю-1: `listing_authority_short` — LLM gpt-5-mini

Новое поле (сейчас отсутствует во всех jurisdiction_card.json).
Добавлять только если поле отсутствует.

**Входные данные:** поле `listing_authority` из `jurisdiction_card.json`.

Если поле `listing_authority` пустое — пропустить.

**Паттерн LLM:**
```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOpenAI(model="gpt-5-mini", temperature=0)

system = SystemMessage(content=(
    "You are a financial regulatory expert. "
    "Extract a short abbreviation or name (max 30 characters) for the listing authority. "
    "Use the official acronym if visible in parentheses (e.g. FCA, SEHK, SGX-ST, AMF, ASIC). "
    "Return ONLY the short name, nothing else."
))
human = HumanMessage(content=listing_authority_text)
response = llm.invoke([system, human])
short_name = response.content.strip()[:30]
```

Ожидаемые значения для текущих данных:
- Австралия: "Exchanges (ASX, Cboe AU, NSX, SSX)" или краткий аналог
- Великобритания: "FCA"
- Германия: "Börsengeschäftsführung" или краткий аналог
- Гонконг: "SEHK"
- Сингапур: "SGX-ST"
- Франция: "Euronext Paris"

### П-2: `venue_type` — нормализованный enum (алгоритм)

Нормализация для `venue_card.json`.

```python
_VENUE_TYPE_MAP = {
    "regulated_market": "regulated_market",  # уже корректно
    "MTF": "mtf",
    "OTF": "otf",
    "other": "exchange_regulated",  # немецкие Freiverkehr площадки
}
```

Текущее состояние данных:
- 14 venue с `"regulated_market"` → без изменений
- 6 venue с `"MTF"` → `"mtf"`
- 3 venue с `"other"` (BÖAG_Börsen, Börse_München, Börse_Stuttgart) → `"exchange_regulated"`

Идемпотентность: если venue_type уже в нижнем регистре и является допустимым значением enum (`regulated_market`, `mtf`, `otf`, `exchange_regulated`) — пропускать.

## Архитектура модуля

### `02_src/pipeline/l1_l2_normalize.py`

```python
"""
Task 012: L1/L2 field normalizations.
- legal_family: lowercase enum
- market_type: DM/EM lookup
- listing_authority_short: LLM extraction
- venue_type: normalized enum
"""

_LEGAL_FAMILY_VALID = {"common law", "civil law", "mixed"}
_MARKET_TYPE_LOOKUP = { ... }
_VENUE_TYPE_MAP = { ... }
_VENUE_TYPE_NORMALIZED = {"regulated_market", "mtf", "otf", "exchange_regulated"}

def _normalize_legal_family(val: str) -> str | None:
    """Return normalized value or None if no change needed."""

def _get_listing_authority_short(listing_authority: str, llm) -> str | None:
    """LLM call. Returns short name or None on error."""

def process_l1_normalizations(
    jurisdictions: list[str] | None = None,
    llm=None
) -> None:
    """
    Normalize jurisdiction_card.json fields:
    - legal_family (algorithmic)
    - market_type (lookup, new field)
    - listing_authority_short (LLM, new field)
    Idempotent.
    jurisdictions: list of name_ru. None = all.
    llm: langchain LLM instance for listing_authority_short. If None, created internally.
    """

def process_l2_normalizations(
    jurisdictions: list[str] | None = None
) -> None:
    """
    Normalize venue_card.json venue_type field.
    Idempotent.
    jurisdictions: list of name_ru (jurisdiction folders to process). None = all.
    """
```

### Пути к файлам

```python
from pipeline.config import COUNTRIES_DIR, LOGS_DIR, LLM_FAST_MODEL

# L1: COUNTRIES_DIR / name_ru / "level_1" / "jurisdiction_card.json"
# L2: COUNTRIES_DIR / name_ru / "level_2" / venue_key / "venue_card.json"
```

### Логирование

```python
from pipeline.logging_setup import get_logger
import datetime
logger = get_logger(
    "l1_l2_normalize",
    LOGS_DIR / f"l1_l2_normalize_{datetime.date.today()}.log"
)
```

Формат:
- `[L1 UPDATED] {name_ru} — legal_family: '{old}' → '{new}', market_type: '{mt}', listing_authority_short: '{short}'`
- `[L1 SKIP] {name_ru} — already normalized`
- `[L2 UPDATED] {venue_key} — venue_type: '{old}' → '{new}'`
- `[L2 SKIP] {venue_key} — already normalized`

## Интеграция в run_pipeline.py

### run_level1() — добавить L1 Step 10 (после citations step 9):

```python
logger.info("--- L1 Step 10: Normalize L1 fields ---")
from pipeline.l1_l2_normalize import process_l1_normalizations
process_l1_normalizations(jurisdictions=[j["name_ru"] for j in jurisdictions])
```

(llm создаётся внутри process_l1_normalizations при необходимости)

### run_level2() — добавить L2 Step 6 (после citations step 5):

```python
logger.info("--- L2 Step 6: Normalize L2 fields ---")
from pipeline.l1_l2_normalize import process_l2_normalizations
jurisdiction_names = list({v.get("name_ru") for v in venues if v.get("name_ru")})
process_l2_normalizations(jurisdictions=jurisdiction_names)
```

## Создание LLM внутри модуля

Если `llm` не передан в `process_l1_normalizations`, создавать его внутри:

```python
if llm is None:
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model=LLM_FAST_MODEL, temperature=0)
```

## Catch-up скрипт `02_src/tools/run_l1_l2_normalize_catchup.py`

```python
"""
Task 012 catch-up script: normalize L1/L2 fields for all existing data.
Run manually when needed: python 02_src/tools/run_l1_l2_normalize_catchup.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.l1_l2_normalize import process_l1_normalizations, process_l2_normalizations

if __name__ == "__main__":
    print("Running L1 normalization...")
    process_l1_normalizations()
    print("Running L2 normalization...")
    process_l2_normalizations()
    print("Done.")
```

## Ключевые файлы

- `02_src/pipeline/config.py` — COUNTRIES_DIR, LOGS_DIR, LLM_FAST_MODEL
- `02_src/pipeline/logging_setup.py` — get_logger
- `02_src/run_pipeline.py` — добавить шаги L1 Step 10 и L2 Step 6
- `03_data/countries/*/level_1/jurisdiction_card.json` — данные L1
- `03_data/countries/*/level_2/*/venue_card.json` — данные L2

## Формат отчёта

Создай `01_tasks/012_l1_l2_normalize/implementation_01.md`:
```
# Отчёт о реализации: Task 012 — L1/L2 Normalizations

## Что реализовано
## Файлы (Новые / Изменённые)
## Изменения в данных (what changed in actual JSON files)
## Особенности реализации
## Известные проблемы
```
