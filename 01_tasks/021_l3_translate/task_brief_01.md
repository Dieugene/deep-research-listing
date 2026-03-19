# Task 021: L3 sections — description_ru

## Что нужно сделать

Добавить поле `description_ru` ко всем секциям контента в `3A_raw.json`, `3B_raw.json`, `3C_raw.json`. Сейчас каждая секция имеет только `description` (EN) — русского перевода нет.

Нужны:
- **Новый модуль** `02_src/pipeline/l3_translate.py` с основной функцией `run_l3_translate()`
- **Pipeline fix** — новый шаг в конце `run_level3()` в `02_src/run_pipeline.py`
- **Catchup script** — `02_src/tools/run_l3_translate_catchup.py` для всего `03_data/`

---

## Зачем

Весь текст секций на страницах ячеек отображается на английском. Перевод — самый крупный пробел интерфейса по охвату (~513 файлов 3A/3B/3C × до ~12 секций в каждом).

---

## Acceptance Criteria

- [ ] AC-1: Создан `02_src/pipeline/l3_translate.py` с функцией `run_l3_translate(llm=None, jurisdictions=None)`.
- [ ] AC-2: Обрабатываются оба формата секций — **FLAT** и **NESTED** (см. ниже).
- [ ] AC-3: Идемпотентность на уровне секции: уже переведённые `description_ru` пропускаются, переводятся только отсутствующие.
- [ ] AC-4: Перевод выполняется через LLM batch с `max_concurrency=50`.
- [ ] AC-5: В конец `run_level3()` в `02_src/run_pipeline.py` добавлен новый шаг (после Step 9: Build matrix) с вызовом `run_l3_translate()`, с фильтром по юрисдикциям.
- [ ] AC-6: Создан `02_src/tools/run_l3_translate_catchup.py`.
- [ ] AC-7: Логирование: `[TRANSLATED] label — N sections translated`, `[SKIP] label — all sections already have description_ru`.

---

## Контекст

### Структура файлов

Файлы: `03_data/countries/<country>/level_3/<venue>/<cell>/{3A,3B,3C}_raw.json`

Также возможны Phase 2 файлы: `03_data/countries/<country>/level_3/<venue>/_parallel_raw/*_raw.json`

### FLAT секция (большинство секций в 3A)

```json
"content": {
  "admission_overview": {
    "description": "The primary listing process requires...",
    "source": "UKLR 2.1"
  }
}
```

Нужно добавить:
```json
"admission_overview": {
  "description": "The primary listing process requires...",
  "description_ru": "Процедура первичного листинга требует...",
  "source": "UKLR 2.1"
}
```

### NESTED секция (большинство секций в 3B и 3C)

```json
"content": {
  "suspension": {
    "procedure": {
      "description": "Decision maker: market operator...",
      "source": "Rule 4.1"
    },
    "grounds": {
      "description": "Request of the AMF or SVT Secretariat...",
      "source": "Rule 4.2"
    }
  }
}
```

Нужно добавить `description_ru` к каждому subkey:
```json
"suspension": {
  "procedure": {
    "description": "Decision maker: market operator...",
    "description_ru": "Орган принятия решений: оператор рынка...",
    "source": "Rule 4.1"
  },
  "grounds": {
    "description": "Request of the AMF or SVT Secretariat...",
    "description_ru": "Запрос AMF или Секретариата SVT...",
    "source": "Rule 4.2"
  }
}
```

### Различие FLAT vs NESTED

Определять по структуре:
- FLAT: `value` — это dict с ключом `"description"` (str)
- NESTED: `value` — это dict, где values сами являются dict с `"description"`

Псевдокод:
```python
def is_flat(val: dict) -> bool:
    return isinstance(val.get("description"), str)

def is_nested(val: dict) -> bool:
    return any(isinstance(v, dict) for v in val.values())
```

### Ключи для передачи в LLM (dot-notation для NESTED)

- FLAT: ключ = `"admission_overview"`
- NESTED subkey: ключ = `"suspension.procedure"`, `"suspension.grounds"`

Строить словарь `{display_key: description_en}` — только для секций без `description_ru`.

### Секции, которые НЕ нужно переводить

Пропускать:
- `"tier_name"` — это короткая метка, не описание
- `"terminology"` содержит `suspension_local_term`, `delisting_local_term` — это термины, можно переводить (они тоже имеют `description`)

Не пропускать никакие другие секции.

---

## LLM batch — критически важный паттерн

Из памяти проекта:
```python
from langchain_core.messages import HumanMessage, SystemMessage
# chain.batch принимает list[list[BaseMessage]]:
results = chain.batch(
    [[HumanMessage(content=prompt)] for prompt in prompts],
    config={"max_concurrency": 50},
    return_exceptions=True,
)
```

**Pydantic модель для structured output:**
```python
from pydantic import BaseModel

class SectionTranslations(BaseModel):
    translations: dict[str, str]
```

**Промпт для одного файла:**
```
You are translating securities regulation content from English to Russian.
Translate each section description and return JSON {"translations": {"key": "russian_text", ...}}.
Preserve proper nouns, regulatory acronyms (FCA, MiFID, UKLR, ASX, etc.), and legal terms.
Do not translate section keys — only values.

Sections:
{json.dumps(sections_dict, ensure_ascii=False, indent=2)}
```

### Получение LLM (аналогично matrix_builder)

```python
from pipeline.config import LLM_FAST_MODEL
import os
from langchain_openai import ChatOpenAI

def _get_llm(model: str = LLM_FAST_MODEL) -> ChatOpenAI:
    return ChatOpenAI(model=model, api_key=os.environ["OPENAI_API_KEY"], temperature=0)
```

---

## Алгоритм run_l3_translate

```python
def run_l3_translate(llm=None, jurisdictions=None):
    if llm is None:
        llm = _get_llm(LLM_FAST_MODEL)

    chain = llm.with_structured_output(SectionTranslations)

    # 1. Collect work items
    work_items = []  # list of {raw_path, label, sections_to_translate: dict[str, str]}
    for raw_path, label in _iter_l3_raw_files(jurisdictions):
        data = _load_json(raw_path)
        if not data: continue
        content = data.get("content", {})
        if not content: continue

        sections = _collect_untranslated(content)  # {display_key: description_en}
        if not sections:
            logger.info("[SKIP] %s — all sections already have description_ru", label)
            continue

        work_items.append({
            "raw_path": raw_path,
            "label": label,
            "data": data,
            "sections": sections,
        })

    if not work_items:
        logger.info("No files need translation")
        return

    logger.info("Translating %d files", len(work_items))

    # 2. Build prompts
    prompts = [_build_prompt(item["sections"]) for item in work_items]

    # 3. Batch translate
    results = chain.batch(
        [[HumanMessage(content=p)] for p in prompts],
        config={"max_concurrency": 50},
        return_exceptions=True,
    )

    # 4. Apply and save
    for item, result in zip(work_items, results):
        if isinstance(result, Exception):
            logger.error("[ERROR] %s: %s", item["label"], result)
            continue

        n = _apply_translations(item["data"], result.translations)
        _save_json(item["raw_path"], item["data"])
        logger.info("[TRANSLATED] %s — %d sections", item["label"], n)
```

---

## Вспомогательные функции

### _collect_untranslated(content: dict) -> dict[str, str]

Возвращает `{display_key: description_en}` для секций без `description_ru`:

```python
def _collect_untranslated(content: dict) -> dict[str, str]:
    result = {}
    for key, val in content.items():
        if not isinstance(val, dict):
            continue
        if is_flat(val):
            if not val.get("description_ru") and val.get("description"):
                result[key] = val["description"]
        elif is_nested(val):
            for subkey, subval in val.items():
                if isinstance(subval, dict) and isinstance(subval.get("description"), str):
                    if not subval.get("description_ru"):
                        result[f"{key}.{subkey}"] = subval["description"]
    return result
```

### _apply_translations(data: dict, translations: dict[str, str]) -> int

Записывает `description_ru` обратно в `data["content"]`:

```python
def _apply_translations(data: dict, translations: dict[str, str]) -> int:
    content = data.get("content", {})
    updated = 0
    for display_key, ru_text in translations.items():
        if "." in display_key:
            section_key, subkey = display_key.split(".", 1)
            section = content.get(section_key, {})
            subsection = section.get(subkey, {})
            if isinstance(subsection, dict):
                subsection["description_ru"] = ru_text
                updated += 1
        else:
            section = content.get(display_key, {})
            if isinstance(section, dict):
                section["description_ru"] = ru_text
                updated += 1
    return updated
```

---

## Итерация по файлам

Использовать **тот же паттерн** что в `source_classifier.py` — функцию `_iter_l3_raw_files` (уже реализована в Task 020). Но `l3_translate.py` — отдельный модуль, поэтому нужно либо:
- Импортировать: `from pipeline.source_classifier import _iter_l3_raw_files` (приватная функция, но приемлемо внутри pipeline пакета)
- Или скопировать аналогичный обход локально

**Рекомендация**: переместить `_iter_l3_raw_files` в отдельный `pipeline/l3_utils.py` и импортировать оттуда в оба модуля. Если слишком сложно — просто скопировать паттерн локально.

---

## Интеграция в run_pipeline.py

В `run_level3(venues)` добавить **последним шагом** (после Step 9: Build matrix):

```python
logger.info("--- L3 Step 10: Translate section descriptions to Russian ---")
from pipeline.l3_translate import run_l3_translate
from pipeline.config import LLM_FAST_MODEL
llm_translate = _get_llm_for_l3()  # или создать inline
run_l3_translate(llm=llm_translate, jurisdictions=jurisdiction_names or None)
```

Для получения LLM в `run_level3` можно создать локально:
```python
from langchain_openai import ChatOpenAI
import os
llm_translate = ChatOpenAI(model=LLM_FAST_MODEL, api_key=os.environ["OPENAI_API_KEY"], temperature=0)
```

Или использовать паттерн из `matrix_builder` — `build_matrix_all(llm=None)` создаёт LLM внутри.

---

## Catchup script

`02_src/tools/run_l3_translate_catchup.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.l3_translate import run_l3_translate

if __name__ == "__main__":
    print("Translating L3 section descriptions...")
    run_l3_translate()
    print("Done.")
```

---

## Файлы для изменения / создания

| Действие | Файл |
|----------|------|
| СОЗДАТЬ | `02_src/pipeline/l3_translate.py` |
| ИЗМЕНИТЬ | `02_src/run_pipeline.py` — добавить Step 10 в run_level3 |
| СОЗДАТЬ | `02_src/tools/run_l3_translate_catchup.py` |

---

## Важные ограничения

- **Не запускать код** — только писать. Запуск выполняет Tech Lead отдельно.
- **max_concurrency = 50** — обязательно для всех batch вызовов.
- **return_exceptions=True** — обязательно в chain.batch.
- **Атомарная запись**: использовать `tempfile.mkstemp + os.replace` (паттерн из source_classifier.py) или `pipeline.storage.save_json`.
- **Загрузка .env**: в catchup-скрипте нужен `load_dotenv()` (OPENAI_API_KEY).
- **Logging**: через `get_logger` из `pipeline.logging_setup`, лог-файл `LOGS_DIR / f"l3_translate_{datetime.date.today()}.log"`.

---

## Отчёт

После реализации создать `01_tasks/021_l3_translate/implementation_01.md` с:
- Список созданных/изменённых файлов
- Описание `_collect_untranslated` и `_apply_translations`
- Инструкция запуска catchup
