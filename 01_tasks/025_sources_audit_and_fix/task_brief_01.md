# Task 025: Аудит и исправление потерь источников/выдержек

## Статус: Не начата

## Проблема

При переносе данных из сырого ответа Parallel API (`parallel_output.basis[]`) в файлы пайплайна происходит значительная потеря источников, выдержек и URL. Оценка потерь: 20–55% в зависимости от уровня.

## Выявленные проблемы

### П1. Дедупликация по URL — потеря привязки к секциям (sources.py:188–202)

`extract_sources_from_raw()` агрегирует citations по URL. Когда один URL фигурирует в нескольких `basis[].field` (привязан к разным секциям контента), сохраняется только **первый field**. Все последующие привязки теряются.

**Пример:** URL `handbook.fca.org.uk/...` фигурирует в basis для `instrument_requirements` И для `eligibility_requirements`. В итоговом `citations[]` остаётся одна запись с `field=instrument_requirements`. При распределении в матрицу — citation не попадёт в ячейку `eligibility_requirements`.

**Масштаб:** L1 — потеря ~22% citations (120 → 94 для Австралии). L3 — зависит от перекрытия URL между секциями.

### П2. Фильтрация orphaned citations — ложные срабатывания (sources.py:107–131)

`_filter_citations_by_content()` удаляет citations, привязанные к секциям с пустым description. Но:

- **`content.tiers` (list)** — функция `_is_empty_section()` возвращает True для non-dict, а `tiers` — это массив с полноценными данными. **2009 citations ложно удалены**.
- **`additional_findings` с пустым description** — Parallel записал reasoning и citations, но не заполнил description. Citations содержат реальные URL и excerpts. 10 случаев.
- **Секции с `"not applicable"`** — Parallel оставил citations как обоснование вывода «не применимо». 7 случаев с реальным reasoning.

**Масштаб:** 2061 citation-запись в basis помечена как orphaned. Из них 2009 — ложные (tiers), 52 — спорные (reasoning + excerpts к пустым секциям).

### П3. Потеря citations при распределении в матрицу (matrix_builder.py:260–266)

`_distribute_citations()` читает из `citations[]` (уже отфильтрованного), а не из `parallel_output.basis[]`. Потери от П1 и П2 каскадируются.

Также: citations с `field`, отсутствующим в `_CITATION_FIELD_MAP`, молча пропускаются.

### П4. `merge_sources_dedup()` — потеря при слиянии L1 файлов (sources.py:207–)

При слиянии sources из 1A/1B/1C в `jurisdiction_card.json` применяется та же дедупликация по URL с потерей field-привязки.

## Первый шаг: полный аудит (без исправлений)

Перед исправлениями необходимо:

1. **Составить полный перечень типов сырых данных** — все JSON-файлы с `parallel_output`.
2. **По каждому типу** — задокументировать структуру и расположение sources/citations/excerpts.
3. **По каждому типу источников** — проследить, как они отражены в результатах пайплайна.
4. **Идентифицировать** всё, что до результатов не дошло или было преобразовано.

## Количественная оценка потерь (на примерах)

### L1 Австралия:
- basis: 120 citations → jurisdiction_card.json: 94 sources → **потеря 22%**

### L3 GB LSE Main Market equity:
- basis 3A/3B/3C: суммарно десятки citations
- citations[] после извлечения: 12
- matrix.json citations: 12
- **основная потеря на этапе extraction + filtering**

### Агрегат по всему датасету:
- Текущие `citations[]` в raw-файлах: 1320
- Исходные citations в `basis`: 4434
- **Потеряно: 3114 (70%)**
