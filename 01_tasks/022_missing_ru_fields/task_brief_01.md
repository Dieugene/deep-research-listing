# Task 022: Недостающие _ru поля

## Что нужно сделать

Добавить перевод недостающих полей на русский во всех юрисдикциях. Шесть под-задач разного типа — часть требует LLM, часть алгоритмическая.

Нужны:
- **Новый модуль** `02_src/pipeline/translate_ru_fields.py` с функциями для каждой под-задачи
- **Pipeline fix** — добавить вызовы в `run_pipeline.py` (L1, Phase 2, L4)
- **Catchup script** `02_src/tools/run_missing_ru_catchup.py` — запускает всё по `03_data/`

---

## Acceptance Criteria

- [ ] AC-1: `translate_ru_fields.py` создан с 5 функциями (см. ниже)
- [ ] AC-2: `run_pipeline.py` — функции встроены в нужные уровни
- [ ] AC-3: `run_missing_ru_catchup.py` создан
- [ ] AC-4: Все функции идемпотентны (пропускают уже заполненные поля)
- [ ] AC-5: LLM функции используют `chain.batch` с `max_concurrency=50`, `return_exceptions=True`

---

## Под-задачи

### A. `notes_ru` в jurisdiction_card.json (L1 шаг)

**Поле:** `notes` → добавить `notes_ru`

**Структура:**
```json
// jurisdiction_card.json
{
  "notes": "The UK framework features...",
  "notes_ru": null  // нужно заполнить
}
```

**Функция:** `translate_jurisdiction_notes(llm, jurisdictions=None)`
- Читает `jurisdiction_card.json` для каждой юрисдикции
- Если `notes` есть и непустой, а `notes_ru` отсутствует/null → переводит
- LLM batch (одна запись = один `notes` текст)
- Сохраняет `notes_ru` обратно в `jurisdiction_card.json`

**Pipeline:** добавить в конец `run_level1()` в `run_pipeline.py`

---

### B. `tier_ru` в pass2_ru.json (Phase 2 шаг)

**Проблема:** Заголовок ячейки (H1 страницы) берётся из `content.tier_name` в `3A_raw.json`. В `pass2_ru.json` нет поля `tier_ru`.

**Структура:**
```json
// 3A_raw.json (источник)
"content": {
  "tier_name": "Debt and debt-like securities",
  ...
}

// pass2_ru.json (куда добавить)
{
  "cell_id": "...",
  "group_id": "...",
  "tier_ru": null,  // нужно добавить
  "parameter_values": [...]
}
```

**Алгоритм:**
- Для каждого `pass2_ru.json`: найти `3A_raw.json` в той же директории
- Прочитать `data.content.tier_name` (строка, не dict)
- Если `tier_ru` не заполнен — перевести через LLM
- Добавить `tier_ru` в `pass2_ru.json` на top-level

**Функция:** `translate_tier_names(llm, jurisdictions=None)`
- LLM batch (по одному промпту на ячейку)

**Pipeline:** добавить в конец `run_phase2()` в `run_pipeline.py`

---

### C. `param_label_ru` для ADDITIONAL параметров в pass2_ru.json (Phase 2 шаг)

**Проблема:** ADDITIONAL_X параметры имеют `parameter_name` на английском (это и есть их метка). Нужно добавить `param_label_ru`.

**Текущая структура ADDITIONAL параметра:**
```json
{
  "parameter_id": "ADDITIONAL_1",
  "parameter_name": "Issuer type eligibility",
  "param_label_ru": null
}
```

**Нужно:** добавить `param_label_ru` = перевод `parameter_name`.

**Алгоритм:**
- Для каждого `pass2_ru.json`:
  - Найти записи где `parameter_id` начинается с `"ADDITIONAL"`
  - Если `param_label_ru` null/пустой — собрать в batch
- LLM batch: переводит список `parameter_name` → `param_label_ru`
- Сохраняет обратно

**Функция:** `translate_additional_param_labels(llm, jurisdictions=None)`

**Pipeline:** добавить в конец `run_phase2()`, после `translate_tier_names`

---

### D. `driver_ru` и `opposition_ru` в level4.json (L4 шаг)

**Поля:** `reforms[].driver` → `driver_ru`, `reforms[].opposition` → `opposition_ru`

**Структура:**
```json
{
  "driver": "The need to improve market integrity...",
  "driver_ru": null,
  "opposition": "Retail advocates (ASA) objected...",
  "opposition_ru": null
}
```

**Функция:** `translate_reforms_fields(llm, jurisdictions=None)`
- Читает `level4.json` каждой юрисдикции
- Для каждого reform с непустым `driver` и отсутствующим `driver_ru` — в batch
- То же для `opposition`
- Один LLM batch на всю юрисдикцию (driver и opposition вместе как пары)

**Pipeline:** добавить в конец `run_level4()` в `run_pipeline.py`

---

### E. `problem_addressed_ru` и `calibration_debate_ru` в level4.json (L4 шаг)

**Поля:** `parameters_as_tools[].problem_addressed` → `problem_addressed_ru`, `.calibration_debate` → `calibration_debate_ru`

**Текущая структура:**
```json
{
  "parameter_description": "...",
  "parameter_description_ru": "...",   // уже есть
  "problem_addressed": "Insufficient free float...",
  "problem_addressed_ru": null,         // нужно добавить
  "calibration_debate": "Stakeholders disagreed...",
  "calibration_debate_ru": null         // нужно добавить
}
```

**Функция:** `translate_ptools_fields(llm, jurisdictions=None)`
- Аналогично `translate_reforms_fields` — batch по юрисдикциям

**Pipeline:** добавить в конец `run_level4()`, после `translate_reforms_fields`

---

### F. Нормализация `param_id` формата П→P (алгоритмическая, без LLM)

**Проблема:** В части ячеек `parameter_id` использует латинскую P (`P01`), в части — кириллическую П (`П01`).

**Нужно:** нормализовать к кириллице П во всех pass2_ru.json.

**Правило:**
```python
if param_id.startswith("P") and param_id[1:].isdigit():
    param_id = "П" + param_id[1:]  # P01 → П01
```
ADDITIONAL_X не трогать.

**Функция:** `normalize_param_ids(jurisdictions=None)` — без LLM

**Pipeline:** добавить в конец `run_phase2()`

---

## LLM batch — критический паттерн

```python
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

class TextTranslation(BaseModel):
    translation: str  # для одиночных текстов

# Batch call:
results = chain.batch(
    [[HumanMessage(content=prompt)] for prompt in prompts],
    config={"max_concurrency": 50},
    return_exceptions=True,
)
```

Для многополевых переводов (driver + opposition вместе):
```python
class ReformTranslation(BaseModel):
    driver_ru: str
    opposition_ru: str

class PToolTranslation(BaseModel):
    problem_addressed_ru: str
    calibration_debate_ru: str
```

---

## Получение LLM

```python
from langchain_openai import ChatOpenAI
from pipeline.config import LLM_FAST_MODEL
import os

def _get_llm(model=LLM_FAST_MODEL):
    return ChatOpenAI(model=model, api_key=os.environ["OPENAI_API_KEY"], temperature=0)
```

---

## Интеграция в run_pipeline.py

### run_level1() — в конец:
```python
logger.info("--- L1 Step 12: Translate jurisdiction notes ---")
from pipeline.translate_ru_fields import translate_jurisdiction_notes
llm = ...  # создать inline
translate_jurisdiction_notes(llm=llm, jurisdictions=[j["name_ru"] for j in jurisdictions])
```

### run_phase2() — после existing steps:
```python
logger.info("--- Phase 2 Step: Translate tier names ---")
from pipeline.translate_ru_fields import translate_tier_names
translate_tier_names(llm=..., jurisdictions=None)  # Phase 2 runs on all data

logger.info("--- Phase 2 Step: Translate ADDITIONAL param labels ---")
from pipeline.translate_ru_fields import translate_additional_param_labels
translate_additional_param_labels(llm=..., jurisdictions=None)

logger.info("--- Phase 2 Step: Normalize param IDs ---")
from pipeline.translate_ru_fields import normalize_param_ids
normalize_param_ids()
```

### run_level4() — в конец (после существующих шагов):
```python
logger.info("--- L4 Step 6: Translate reforms fields ---")
from pipeline.translate_ru_fields import translate_reforms_fields
translate_reforms_fields(llm=..., jurisdictions=[j["name_ru"] for j in jurisdictions])

logger.info("--- L4 Step 7: Translate ptools fields ---")
from pipeline.translate_ru_fields import translate_ptools_fields
translate_ptools_fields(llm=..., jurisdictions=[j["name_ru"] for j in jurisdictions])
```

---

## Структура файлов

Обход юрисдикций (аналогично уже существующим функциям):
```python
from pipeline.config import COUNTRIES_DIR

for country_dir in sorted(COUNTRIES_DIR.iterdir()):
    if not country_dir.is_dir(): continue
    if jurisdictions and country_dir.name not in jurisdictions: continue
    ...
```

Атомарная запись: `tempfile.mkstemp + os.replace` (паттерн из `source_classifier.py`)

Logging: через `get_logger("translate_ru_fields", LOGS_DIR / f"translate_ru_fields_{date}.log")`

---

## Catchup script

`02_src/tools/run_missing_ru_catchup.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.translate_ru_fields import (
    translate_jurisdiction_notes,
    translate_tier_names,
    translate_additional_param_labels,
    translate_reforms_fields,
    translate_ptools_fields,
    normalize_param_ids,
)
from pipeline.translate_ru_fields import _get_llm

if __name__ == "__main__":
    llm = _get_llm()
    print("1. Translating jurisdiction notes...")
    translate_jurisdiction_notes(llm)
    print("2. Translating tier names...")
    translate_tier_names(llm)
    print("3. Translating ADDITIONAL param labels...")
    translate_additional_param_labels(llm)
    print("4. Normalizing param IDs...")
    normalize_param_ids()
    print("5. Translating reforms fields...")
    translate_reforms_fields(llm)
    print("6. Translating ptools fields...")
    translate_ptools_fields(llm)
    print("Done.")
```

---

## Файлы для изменения / создания

| Действие | Файл |
|----------|------|
| СОЗДАТЬ | `02_src/pipeline/translate_ru_fields.py` |
| ИЗМЕНИТЬ | `02_src/run_pipeline.py` — добавить шаги в run_level1, run_phase2, run_level4 |
| СОЗДАТЬ | `02_src/tools/run_missing_ru_catchup.py` |

---

## Ограничения

- Не запускать код — только писать
- max_concurrency = 50 для всех batch вызовов
- return_exceptions=True в chain.batch
- Идемпотентность: проверять наличие _ru поля перед добавлением в batch
- load_dotenv в catchup скрипте
- Атомарная запись

## Отчёт

После реализации создать `01_tasks/022_missing_ru_fields/implementation_01.md`
