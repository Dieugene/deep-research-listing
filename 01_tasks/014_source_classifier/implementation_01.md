# Отчёт о реализации: Task 014 — Source Type Classification

## Что реализовано

Добавлен алгоритмический классификатор типов источников. Каждому объекту в `sources[]` присваивается поле `type` на основе домена и пути URL без использования LLM.

Поддерживаемые типы: `legislation` | `rulebook` | `government` | `consultation` | `research` | `other`

Алгоритм (4 шага):
1. Поиск домена (netloc) в `_DOMAIN_TYPE_MAP` — точное совпадение с поддержкой `www.`-нормализации.
2. Path-based overrides: `consultation` в пути URL → `"consultation"`; `handbook` в пути при текущем типе `government` → `"rulebook"`.
3. Паттерн TLD: домен содержит `.gov.` или заканчивается на `.gov` → `"government"`.
4. Default → `"other"`.

Идемпотентность: источники с уже заполненным непустым полем `type` пропускаются.

## Файлы

### Новые
- `02_src/pipeline/source_classifier.py` — основной модуль: `classify_source_url()`, `process_sources_in_data()`, `process_source_types()`
- `02_src/tools/run_source_classifier_catchup.py` — скрипт для ретроспективного запуска по всем существующим данным
- `01_tasks/014_source_classifier/implementation_01.md` — данный отчёт

### Изменённые
- `02_src/run_pipeline.py`:
  - L1 Step 11 (после Step 10 «Normalize L1 fields»): `process_source_types(jurisdictions=[...])`
  - L2 Step 7 (после Step 6 «Normalize L2 fields»): `process_source_types(jurisdictions=[...])`
  - L4 Step 5 (после Step 4 «Labels and articulated_by»): `process_source_types(jurisdictions=[...])`

## Особенности реализации

- Атомарное сохранение файлов через `tempfile.mkstemp` + `os.replace()` — единый паттерн с другими модулями пайплайна.
- `process_source_types(jurisdictions=None)` без аргументов обходит все директории в `COUNTRIES_DIR` — удобно для catch-up скрипта.
- Лог-формат: `[UPDATED] {name_ru}/{key} — N sources classified` / `[SKIP] {name_ru}/{key} — all sources already have type`.
- Все три вызова в run_pipeline.py (L1, L2, L4) идемпотентны — повторный вызов безопасен.

## Проверка на реальных данных

Великобритания, L1 (57 источников): `rulebook:19, government:9, legislation:7, other:22`
Великобритания, L4 (41 источник): `government:17, consultation:5, other:17, legislation:1, rulebook:1`

Все 17 unit-тестов классификатора пройдены успешно.

## Известные проблемы

- Домены, не охваченные `_DOMAIN_TYPE_MAP` и не соответствующие `.gov.` паттерну, получают тип `"other"`. Список доменов в карте может расширяться по мере добавления новых юрисдикций.
- `fca.org.uk` без `www.` (например, `http://fca.org.uk/...`) не попадёт в таблицу, т.к. в карте есть только `www.fca.org.uk`. При необходимости можно добавить `fca.org.uk` без префикса.
