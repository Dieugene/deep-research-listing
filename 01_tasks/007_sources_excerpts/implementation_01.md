# Отчет о реализации: Task 007 — Sources Excerpts + Pipeline Integration

## Что реализовано

### AC-1: `extract_sources_from_raw()` — добавлено поле `excerpts`

Функция в `02_src/pipeline/sources.py` теперь возвращает объекты с полем `excerpts: list[str]`.
Для каждого citation из `parallel_output.basis[].citations` берётся `citation.get("excerpts") or []`.

### AC-2: Дедупликация с merge excerpts

Как в `extract_sources_from_raw()` (внутри одного файла), так и в `merge_sources_dedup()` (между несколькими списками):
- При совпадении URL excerpts объединяются (уникальные значения, порядок сохраняется).
- Поле `field` — first-seen.
- Ключ дедупликации — `dict[url → source]` вместо `set[url]`.

### AC-3: Логика перенесена в `02_src/pipeline/sources.py`

Новый модуль содержит:
- `extract_sources_from_raw(raw_file_path)` — с excerpts + internal dedup
- `merge_sources_dedup(lists)` — с excerpts merge
- `Stats` класс
- `process_level1_citations(jurisdictions, dry_run, stats)`
- `process_level2_citations(venues, dry_run, stats)`
- `process_level3_citations(dry_run, stats)`
- `process_level4_citations(jurisdictions, dry_run, stats)`

Логгер: `get_logger("sources", LOGS_DIR / f"sources_{today}.log")`.

### AC-4: `tools/add_citations.py` — тонкая CLI-обёртка

Вся логика удалена. Остались:
- argparse CLI (`--level`, `--dry-run`) — интерфейс не изменился
- Bootstrap `sys.path` для импорта из `pipeline.sources`
- Импорт всех 4 функций из `pipeline.sources`

### AC-5: `run_pipeline.py` — вызовы citations после каждого уровня

Добавлены lazy-import вызовы:
- `run_level1()`: Step 9 — `process_level1_citations(jurisdictions=[j["name_ru"] for j in jurisdictions])`
- `run_level2()`: Step 5 — `process_level2_citations(venues=[v["venue_key"] for v in venues])`
- `run_level3()`: Step 6 — `process_level3_citations()`
- `run_level4()`: Step 2 — `process_level4_citations(jurisdictions=[j["name_ru"] for j in jurisdictions])`

Phase 2 (`run_phase2()`) не получает отдельного шага citations — он работает с L3-данными, уже обработанными на шаге L3 Step 6.

### AC-6: Catch-up скрипт создан

`02_src/tools/run_citations_catchup.py` — обрабатывает все 4 уровня для всех существующих файлов.
Поддерживает `--dry-run` и `--level L1|L2|L3|L4|ALL`.
Не запускался.

## Файлы

### Новые
- `D:/_workspace/deep-research-listing/02_src/pipeline/sources.py` — вся логика citations
- `D:/_workspace/deep-research-listing/02_src/tools/run_citations_catchup.py` — catch-up скрипт

### Изменённые
- `D:/_workspace/deep-research-listing/tools/add_citations.py` — переписан как тонкая обёртка
- `D:/_workspace/deep-research-listing/02_src/run_pipeline.py` — добавлены 4 citations шага

## Особенности реализации

1. **Внутренняя дедупликация в `extract_sources_from_raw`**: функция теперь сама объединяет excerpts при повторных URL внутри одного файла (вместо первого-seen skip). Это важно, потому что один URL может встречаться в разных `field`-записях basis.

2. **`merge_sources_dedup` с excerpts**: переписан с `dict[url → source]` вместо `set[url]`, чтобы накапливать excerpts из всех дубликатов (не только первого).

3. **Сигнатуры функций с `stats` параметром**: все `process_level*_citations()` принимают `stats: Stats | None = None` и возвращают `Stats`. Это позволяет вызывать их как standalone (stats создаётся автоматически), так и с накопленным счётчиком.

4. **Фильтрация в `process_level*_citations()`**: параметры `jurisdictions` и `venues` позволяют обрабатывать только нужные юрисдикции/площадки, что используется в `run_pipeline.py` для батч-запусков.

5. **Баг в оригинальном `process_level3`**: в исходном `tools/add_citations.py` строка `print(f"  [{venue_key}]")` (строка 300) находится вне цикла `for venue_dir in sorted(l3_root.iterdir())` из-за неверного отступа. В новом `sources.py` отступы исправлены — `logger.info("[%s]", venue_key)` находится внутри цикла.

## Известные проблемы

- Нет. Реализация соответствует всем AC.
