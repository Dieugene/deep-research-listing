# Task 010: L4 Sources per Record

## Что нужно сделать

Для каждой записи в `level4.json` (problems, contradictions, parameters_as_tools, reforms) добавить поле `sources: list[dict]`, разобрав существующую строку `source` и обогатив её excerpts из верхнеуровневого массива `sources[]`.

**Примечание:** `text_ru` поля для всех юрисдикций уже заполнены — эта часть задачи выполнена.

## Acceptance Criteria

- [ ] AC-1: Функция `process_level4_record_sources(jurisdictions=None)` реализована в `02_src/pipeline/level4_postprocess.py`
- [ ] AC-2: Каждая запись в `problems[]`, `contradictions[]`, `parameters_as_tools[]`, `reforms[]` получает поле `sources: list[dict]` с `{url, title, excerpts}`
- [ ] AC-3: Оригинальный `source: str` сохраняется (не удалять — может использоваться другим кодом)
- [ ] AC-4: Идемпотентность: если запись уже имеет непустой `sources[]` — пропускать
- [ ] AC-5: `run_pipeline.py` вызывает функцию как L4 Step 3 после Step 2 (Add citations)
- [ ] AC-6: Catch-up скрипт `02_src/tools/run_l4_sources_catchup.py` создан (не запускать)

## Контекст

### Текущая структура записи в level4.json

```json
{
  "description": "Germany's federal government...",
  "description_ru": "Федеральное правительство...",
  "articulated_by": "government",
  "period": "2022–2024",
  "source": "Drucksache 20/9363 - Deutscher Bundestag — https://dserver.bundestag.de/btd/20/093/2009363.pdf; Regierungsentwurf... — https://www.bmjv.de/..."
}
```

### Целевая структура (добавить `sources[]`, сохранить `source`)

```json
{
  "description": "...",
  "description_ru": "...",
  "articulated_by": "government",
  "period": "2022–2024",
  "source": "Drucksache 20/9363... — https://...; Regierungsentwurf... — https://...",
  "sources": [
    {
      "url": "https://dserver.bundestag.de/btd/20/093/2009363.pdf",
      "title": "Drucksache 20/9363 - Deutscher Bundestag",
      "excerpts": []
    },
    {
      "url": "https://www.bmjv.de/...",
      "title": "Regierungsentwurf eines Gesetzes zur Finanzierung von ...",
      "excerpts": []
    }
  ]
}
```

### Формат строки `source`

Разделитель между элементами: `"; "` (точка с запятой + пробел)
Разделитель внутри элемента между title и URL: ` — ` (пробел + em dash `\u2014` + пробел)

Парсинг одного элемента:
```python
def _parse_source_entry(entry: str) -> dict:
    """Parse 'Title — URL' into {url, title}."""
    sep = " \u2014 "  # em dash with spaces
    if sep in entry:
        # split from the right to handle titles with em dashes
        title, url = entry.rsplit(sep, 1)
        return {"url": url.strip(), "title": title.strip()}
    elif entry.strip().startswith("http"):
        # fallback: no title, just URL
        return {"url": entry.strip(), "title": entry.strip()}
    else:
        return {"url": "", "title": entry.strip()}
```

### Обогащение excerpts

Верхнеуровневый `sources[]` в level4.json содержит `{url, title, field, excerpts}`. После парсинга строки — для каждого URL искать соответствующую запись в `sources[]` и брать её `excerpts`.

```python
# Build lookup from top-level sources[]
top_sources_by_url = {s["url"]: s for s in data.get("sources", [])}

# For each parsed url:
top = top_sources_by_url.get(url, {})
excerpts = top.get("excerpts", [])
```

### Секции для обработки

| Секция | Поле text | Поле source |
|--------|-----------|-------------|
| `problems` | `description` / `description_ru` | `source` |
| `contradictions` | `resolution` / `resolution_ru` | `source` |
| `parameters_as_tools` | `parameter_description` / `parameter_description_ru` | `source` |
| `reforms` | `description` / `description_ru` | `source` |

### Путь к данным

```python
from pipeline.config import COUNTRIES_DIR
# COUNTRIES_DIR / name_ru / "level_4" / "level4.json"
```

### Архитектура модуля `02_src/pipeline/level4_postprocess.py`

```python
def _parse_source_string(source_str: str) -> list[dict]:
    """Parse 'Title — URL; Title — URL' string into list of {url, title} dicts."""
    ...

def _enrich_with_top_sources(parsed: list[dict], top_sources: list[dict]) -> list[dict]:
    """Add excerpts from top-level sources[] by URL match."""
    ...

def process_level4_record_sources(jurisdictions: list[str] | None = None) -> None:
    """
    For each level4.json: add sources[] to each record in problems/contradictions/
    parameters_as_tools/reforms. Idempotent: skips records that already have sources[].
    jurisdictions: list of jurisdiction_ru names; if None, processes all.
    """
    ...
```

### Паттерн интеграции в run_pipeline.py

```python
def run_level4(jurisdictions: list[dict]) -> None:
    ...
    logger.info("--- L4 Step 2: Add citations ---")
    from pipeline.sources import process_level4_citations
    process_level4_citations(jurisdictions=[j["name_ru"] for j in jurisdictions])

    logger.info("--- L4 Step 3: Enrich record sources ---")
    from pipeline.level4_postprocess import process_level4_record_sources
    process_level4_record_sources(jurisdictions=[j["name_ru"] for j in jurisdictions])
```

### Логирование

```python
from pipeline.logging_setup import get_logger
from pipeline.config import LOGS_DIR
import datetime
logger = get_logger("level4_postprocess", LOGS_DIR / f"level4_postprocess_{datetime.date.today()}.log")
```

Формат:
- `logger.info("[UPDATED] %s — %d records enriched", name_ru, count)`
- `logger.info("[SKIP] %s — all records already have sources[]", name_ru)`

## Ключевые файлы

- `02_src/pipeline/config.py` — COUNTRIES_DIR, LOGS_DIR
- `02_src/pipeline/logging_setup.py` — get_logger
- `02_src/run_pipeline.py` — добавить L4 Step 3 (lazy import)
- `03_data/countries/Германия/level_4/level4.json` — пример данных

## Что НЕ нужно

- LLM вызовы (парсинг строк — алгоритмический)
- Изменение существующего поля `source: str` (сохранять)
- Изменение верхнеуровневого `sources[]` массива (только читать)

## Формат отчёта

Создай `01_tasks/010_l4_sources_per_record/implementation_01.md`:
```
# Отчёт о реализации: Task 010 — L4 Sources per Record

## Что реализовано
## Файлы (Новые / Изменённые)
## Особенности реализации
## Известные проблемы
```
