# Task 005: Рефакторинг архитектуры L3 (venue × instrument_class)

## Что нужно сделать

Переработать модуль Level 3 согласно патчу `pipeline_patch_variant_b.md`:

1. **Генератор промптов** — алгоритмический шаблон (9 блоков) вместо LLM-генерации
2. **JSON schema** — массивная (`tiers: array`), компактная (~2–3К символов)
3. **Runner L3** — новая единица запроса venue × instrument_class (не ячейка)
4. **LLM-постобработка** — разнесение массива `tiers` по ячейкам + перевод
5. **Валидация** — scope/completeness/sources check по каждой ячейке
6. **Обновление viewer** — отображение новых результатов

## Зачем

Текущая архитектура (запрос на ячейку) системно путает категории:
ESCC-ячейка получила Transition-данные (UKLR 22 вместо UKLR 3+6).
Причина: промпт называл категорию, но не давал координат глав.
Укрупнение даёт Parallel полный контекст rulebook — он находит все категории
естественным образом, без путаницы.

## Acceptance Criteria

- [ ] AC-1: Промпты генерируются алгоритмически из venue_card + jurisdiction_card без LLM
- [ ] AC-2: Единица запроса — venue × instrument_class (не ячейка)
- [ ] AC-3: JSON schema массивная (`tiers: array`), размер ≤ 3К символов
- [ ] AC-4: Все 9 блоков промпта реализованы (включая условные: split, supranational, legacy)
- [ ] AC-5: LLM-постобработка разносит массив tiers по ячейкам cells_list.json
- [ ] AC-6: Валидационный LLM-вызов по каждой ячейке (scope/completeness/sources)
- [ ] AC-7: Размер промпт+schema проверяется; при превышении 15К — разбивка по классам
- [ ] AC-8: Fallback при превышении: venue × один instrument_class вместо всех
- [ ] AC-9: Результаты сохраняются в `03_data/countries/{name_ru}/level_3/{venue_key}/`
- [ ] AC-10: Viewer отображает новые результаты

## Контекст

### Архитектурный патч

Файл: `00_docs/specs/05_pipeline/pipeline_patch_variant_b.md`

**Новая единица запроса:**
- Было: venue × tier × category × instrument_class (1 запрос = 1 ячейка)
- Стало: venue × instrument_class (1 запрос = все тиры данного класса на venue)

**Три типа запроса:** L3-A (допуск), L3-B (негативные), L3-C (мониторинг). Процессор: **pro**.

**Оценка запросов пилота:** 5 venue × ~3 класса × 3 типа ≈ 45 запросов (против 74).

### Структура промпта (9 блоков)

```
БЛОК 1: Контекст venue (из venue_card)
БЛОК 2: Определения понятий (константа)
БЛОК 3: Задание поиска (шаблон + перечень тиров)
БЛОК 4 (conditional): Split-архитектура (если G04=split)
БЛОК 5 (conditional): Наднациональная рамка (если supranational=true)
БЛОК 6: Инструкция по детальности
БЛОК 7: Структурирование по тирам
БЛОК 8 (conditional): Legacy-категории (если есть тиры с legacy=true)
БЛОК 9: Закрывающая инструкция
```

### JSON Schema L3-A

Массивная структура: `{ "tiers": [ { tier_name, admission_overview, eligibility_requirements,
instrument_requirements, sponsor_and_infrastructure, restrictions_and_lock_ups,
procedure_and_timeline, disclosure_at_admission, special_regimes, secondary_admission,
additional_findings } ], "common_requirements": {...} }`

Схемы L3-B и L3-C — аналогичная массивная структура, разные тематические блоки.
Полные схемы в патче.

### LLM-постобработка

Параметры batch-вызова (ОБЯЗАТЕЛЬНО):
```python
chain.batch(
    [[HumanMessage(content=prompt)] for prompt in prompts],
    config={"max_concurrency": 50},
    return_exceptions=True
)
```
- Входные данные: элемент `tiers[i]` из Parallel-результата + venue_card
- Маппинг: `tier_name` → конкретная ячейка из cells_list.json
- Выход: отдельный JSON-файл на каждую ячейку

### Валидация

Три проверки по каждой ячейке (LLM-вызов):
1. SCOPE CHECK — правильный venue/tier/instrument_class, нет чужих данных
2. COMPLETENESS CHECK — чеклист ожидаемых тем по классу инструментов
3. SOURCE CHECK — соответствие цитируемых глав rulebook ожидаемым

Выход: scope_ok / completeness_score / source_ok + список пробелов.

### Существующий код

- `02_src/level_3/` — текущий Level 3 (cell_runner.py, run_level3.py и др.)
- `02_src/level_2/postprocess.py` — пример алгоритмической генерации + LLM batch
- `02_src/pipeline/config.py` — PILOT_VENUES, пути к данным
- `03_data/countries/*/level_3/` — текущие результаты (устаревшие, будут перезаписаны)
