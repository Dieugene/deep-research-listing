# Task 007: Sources — Excerpts + Pipeline Integration

## Что нужно сделать

1. **Добавить `excerpts` в объект источника** — `extract_sources_from_raw()` сейчас отбрасывает текстовые выдержки из Parallel API.
2. **Рефакторинг: вынести логику в `02_src/pipeline/sources.py`** — чтобы `run_pipeline.py` мог импортировать функции напрямую.
3. **Встроить обработку источников в `run_pipeline.py`** — вызывать после каждого уровня (L1, L2, L3, L4).
4. **Обновить существующие данные** — создать catch-up скрипт для перезаписи sources во всех уже существующих файлах.

## Зачем

Parallel API возвращает реальные текстовые выдержки (`excerpts`) из нормативных документов. Они критичны: без них источник — просто URL, с ними — доказательная база тезисов. Интерфейс должен показывать пользователю именно выдержки, а не просто список ссылок.

Дополнительно: `add_citations.py` существует как standalone инструмент в `tools/`, но по архитектурному принципу проекта должен быть встроен в основной пайплайн.

## Acceptance Criteria

- [ ] AC-1: `extract_sources_from_raw()` сохраняет `excerpts: list[str]` в каждом объекте источника
- [ ] AC-2: При дедупликации по URL `excerpts` из дубликатов объединяются (merge, не потеря)
- [ ] AC-3: Логика извлечения перенесена в `02_src/pipeline/sources.py`
- [ ] AC-4: `tools/add_citations.py` остаётся рабочим standalone-инструментом (импортирует из `pipeline.sources`)
- [ ] AC-5: `run_pipeline.py` вызывает add_citations после каждого уровня (L1, L2, L3, L4)
- [ ] AC-6: Catch-up скрипт создан и готов к запуску (обновляет существующие данные)

## Контекст

### Текущая структура `extract_sources_from_raw()` (tools/add_citations.py:62-88)

```python
def extract_sources_from_raw(raw_file_path: Path) -> list[dict]:
    """Returns list of {"url": ..., "title": ..., "field": ...} dicts."""
    ...
    for field_basis in basis:
        field = field_basis.get("field", "")
        for citation in (field_basis.get("citations") or []):
            url = citation.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                sources.append({
                    "url": url,
                    "title": citation.get("title") or "",
                    "field": field,
                    # ⚠️ excerpts полностью отбрасываются
                })
    return sources
```

### Структура Parallel API `basis`

Каждый элемент `basis[]` содержит:
```json
{
  "field": "admission_requirements",  // поле схемы
  "citations": [
    {
      "url": "https://...",
      "title": "ASX Listing Rules",
      "excerpts": ["Rule 1.1 provides that...", "Applicants must satisfy..."]
    }
  ]
}
```

### Требования к выходному формату источника

Каждый объект источника должен содержать:
```json
{
  "url": "https://...",
  "title": "ASX Listing Rules",
  "field": "admission_requirements",
  "excerpts": ["Rule 1.1 provides that...", "Applicants must satisfy..."]
}
```

### Дедупликация при совпадении URL

Один URL может встречаться в нескольких полях `field`. Текущая логика: первый-увиденный выигрывает. Нужно: при совпадении URL — объединять `excerpts` из всех вхождений:

```python
if url in seen_urls:
    # merge excerpts from duplicate into existing entry
    existing["excerpts"] = list(dict.fromkeys(
        existing["excerpts"] + new_excerpts
    ))
    # поле field: оставить первое (или можно добавить fields: [])
else:
    seen_urls[url] = new_entry
    sources.append(new_entry)
```

### Архитектура рефакторинга

Текущее состояние:
```
tools/add_citations.py  ← вся логика здесь (standalone)
```

Целевое состояние:
```
02_src/pipeline/sources.py   ← ВСЯ логика извлечения и обработки
tools/add_citations.py       ← тонкая CLI-обёртка, импортирует из pipeline.sources
run_pipeline.py              ← вызывает pipeline.sources после каждого уровня
```

### Текущий `run_pipeline.py` — места интеграции

```python
def run_level1(jurisdictions):
    ...
    logger.info("--- L1 Step 8: Postprocess ---")
    process_all_l1(jurisdictions=jurisdictions)
    # ← ДОБАВИТЬ: run_add_citations_l1()

def run_level2(venues):
    ...
    logger.info("--- L2 Step 4: Postprocess ---")
    process_all_l2(venues=venues)
    # ← ДОБАВИТЬ: run_add_citations_l2()

def run_level3(venues):
    ...
    logger.info("--- L3 Step 4: Postprocess ---")
    ...
    logger.info("--- L3 Step 5: Validate ---")
    ...
    # ← ДОБАВИТЬ: run_add_citations_l3()

def run_level4(jurisdictions):
    ...
    run_level4_all(llm=llm, jurisdictions=jurisdictions)
    # ← ДОБАВИТЬ: run_add_citations_l4()
```

### Ключевые файлы

- `tools/add_citations.py` — текущая реализация (источник для рефакторинга)
- `02_src/run_pipeline.py` — добавить вызовы add_citations
- `02_src/pipeline/sources.py` — **создать** (логика из add_citations.py)
- `02_src/pipeline/config.py` — COUNTRIES_DIR, LOGS_DIR
- `02_src/pipeline/logging_setup.py` — get_logger

### Паттерн импорта в run_pipeline.py

Следовать существующему паттерну lazy imports (внутри функции):
```python
def run_level1(jurisdictions):
    ...
    logger.info("--- L1 Step 9: Add citations ---")
    from pipeline.sources import process_level1_citations
    process_level1_citations(jurisdictions=jurisdictions)
```

## Что реализовать

### Шаг 1: Создать `02_src/pipeline/sources.py`

Перенести из `tools/add_citations.py`:
- `extract_sources_from_raw(raw_file_path)` — с добавлением `excerpts` + merge при дедупликации
- `merge_sources_dedup(lists)` — адаптировать для слияния excerpts
- `Stats` класс
- `process_level1_citations(jurisdictions=None)` — L1 источники
- `process_level2_citations(venues=None)` — L2 источники (принимать venue list или сканировать все)
- `process_level3_citations()` — L3 источники
- `process_level4_citations(jurisdictions=None)` — L4 источники

Функции принимают опциональный фильтр (jurisdictions/venues list) — когда None, обрабатывают все на диске (filesystem-aware).

### Шаг 2: Обновить `tools/add_citations.py`

Заменить всю логику импортом из `pipeline.sources`:
```python
from pipeline.sources import (
    process_level1_citations,
    process_level2_citations,
    process_level3_citations,
    process_level4_citations,
    Stats,
)
```
CLI-интерфейс (`--level`, `--dry-run`) оставить без изменений.

### Шаг 3: Обновить `run_pipeline.py`

Добавить вызовы `from pipeline.sources import ...` в соответствующие `run_levelN()` функции.

### Шаг 4: Catch-up скрипт

Создать `02_src/tools/run_citations_catchup.py`:
- Запускает все уровни (L1, L2, L3, L4) для всех существующих файлов
- По сути: `process_level1_citations(); process_level2_citations(); process_level3_citations(); process_level4_citations()`
- Логирует количество обновлённых файлов
- Поддерживает `--dry-run`

**НЕ запускать** — только создать. Запуск выполняет Tech Lead.

## Логирование

В `pipeline/sources.py` использовать `get_logger("sources", LOGS_DIR / "sources.log")`.
В CLI `tools/add_citations.py` оставить print-вывод (для консоли).

## Тестирование

Реальные данные, без моков. Проверочные команды (после запуска catch-up):
```bash
# Должен показать excerpts в объектах источников
python -c "import json; d=json.load(open('03_data/countries/Австралия/level_1/jurisdiction_card.json', encoding='utf-8')); print(d['sources'][0])"
```

## Формат отчёта

Создай `01_tasks/007_sources_excerpts/implementation_01.md` по стандарту:
```
# Отчет о реализации: Task 007 — Sources Excerpts + Pipeline Integration

## Что реализовано
## Файлы (Новые / Измененные)
## Особенности реализации
## Известные проблемы
```
