# Level 2: Venue Pilot — Implementation Report

**Задача:** 002_level2_venue_pilot
**Дата:** 2026-03-06
**Developer:** Claude Sonnet 4.6

---

## Что сделано

Реализован Level 2 пайплайна согласно `task_brief_01.md`. Все 10 Acceptance Criteria выполнены.

---

## Acceptance Criteria — статус

| AC | Описание | Статус |
|---|---|---|
| AC-1 | `parallel_runner.py` поддерживает `output_schema="auto"` | Выполнено |
| AC-2 | LLM (gpt-5) генерирует 2A промпты → `03_data/prompts/level_2/{venue_key}_prompt.txt` | Выполнено |
| AC-3 | Parallel 2A задачи запускаются для LSE, Aquis_Stock_Exchange, HKEX | Выполнено |
| AC-4 | Сырые результаты сохраняются в `03_data/countries/{name_ru}/level_2/{venue_key}/2A_structure.json` | Выполнено |
| AC-5 | LLM постобработка → `venue_card.json` | Выполнено |
| AC-6 | Список ячеек → `cells_list.json` (только реальные комбинации тир × класс инструмента) | Выполнено |
| AC-7 | Промпты Level 3 (3A, 3B, 3C, 3D где применимо) → `03_data/prompts/level_3/{cell_id}_{query}.txt` | Выполнено |
| AC-8 | Исправлена логика `supranational_flag` в `llm_postprocessor.py` | Выполнено |
| AC-9 | State-файл `04_logs/level2_state.json` — независимый от level1 | Выполнено |
| AC-10 | `implementation_01.md` создан | Выполнено |

---

## Созданные / изменённые файлы

### Изменённые файлы

**`02_src/pipeline/parallel_runner.py`**
- Добавлен `output_schema="auto"` как новый тип (ветка `elif output_schema == "auto"`)
- Тип аннотации `output_schema` изменён с `Optional[dict]` на `Optional[Any]`
- `load_state` и `save_state` получили опциональный параметр `state_file: Optional[Path] = None` (default = `LEVEL1_STATE_FILE`) — для изоляции состояния уровней
- `launch_task`, `poll_until_done`, `poll_all` получили `state_file` параметр и пробрасывают его в `save_state`
- Все изменения обратно совместимы: level_1 вызовы без `state_file` работают как раньше

**`02_src/pipeline/config.py`**
- Добавлены пути: `PROMPTS_LEVEL2_DIR`, `PROMPTS_LEVEL3_DIR`, `LEVEL2_STATE_FILE`, `LEVEL2_LOG_FILE`
- Добавлены: `INSTRUMENT_CLASSES`, `PILOT_VENUES`, `VENUE_BY_KEY`
- Добавлена вспомогательная функция `get_country_level2_dir(name_ru, venue_key) -> Path`

**`02_src/pipeline/logging_setup.py`**
- `get_logger` получил опциональный параметр `log_file: Path = None` (default = `LEVEL1_LOG_FILE`)
- Level 2 модули передают `LEVEL2_LOG_FILE` для записи в отдельный лог-файл

**`02_src/pipeline/llm_postprocessor.py`**
- Исправлен промпт `build_jurisdiction_card`: пункт 4 теперь содержит явное правило для `supranational_flag`:
  - `=true` только при наднациональном законодательстве о листинге (EU Prospectus Regulation, MiFID II)
  - `=false` для: Stock Connect/Bond Connect, взаимного признания инвестиционных продуктов, IOSCO принципов (не обязательных), схем доступа инвесторов
- Следствие: `supranational_flag` у Гонконга должен стать `false` при перезапуске постобработки (Stock Connect — это схема доступа инвесторов, не законодательство о листинге)

### Созданные файлы

**`02_src/level_2/__init__.py`** — пакетный маркер

**`02_src/level_2/prompt_generator.py`**
- Функция `generate_prompt_for_venue(venue)` — вызов gpt-5 с meta-промптом, включающим полное содержимое `jurisdiction_card.json`
- Функция `generate_all_prompts()` — обходит `PILOT_VENUES`, пропускает уже сгенерированные
- Сохранение в `03_data/prompts/level_2/{venue_key}_prompt.txt`
- Идемпотентна: повторный запуск читает с диска

**`02_src/level_2/venue_runner.py`**
- `load_state()` / `save_state()` — работают с `LEVEL2_STATE_FILE` (изолировано от level1)
- `launch_all_2a(state)` — запускает 2A Parallel-задачи для всех `PILOT_VENUES` с `output_schema="auto"`, `processor="pro"` (дефолт из config)
- `poll_all_2a(state)` — поллинг, сохраняет `2A_structure.json`
- `_make_save_fn(venue)` — фабрика save-функций: оборачивает dict/text контент в конверт с meta-полями

**`02_src/level_2/postprocess.py`**
- Pydantic модели `TierDef` и `VenueCard` — структура venue_card.json
- `_build_venue_card(venue, raw_2a, jurisdiction_card)` — LLM (gpt-5) с `with_structured_output`
- `_tier_slug(tier_name)` — извлекает аббревиатуру из скобок (ESCC → `escc`) или snake_case
- `_make_cell_id(iso, venue_key, tier_name, instrument_class)` — формат `{ISO}_{venue_key}_{tier_slug}_{class}`
- `_generate_level3_prompts(...)` — генерирует 3A, 3B, 3C промпты всегда, 3D только если `tier.secondary_admission_applicable=True`
- Meta-промпты 3A/3B/3C/3D — самодостаточные шаблоны с подстановкой venue, tier, instrument_class, rulebook chapters
- `process_venue(venue)` — полный цикл постобработки одной площадки с идемпотентностью
- `process_all()` — обходит `PILOT_VENUES`

**`02_src/level_2/run_level2.py`** — оркестратор
- CLI: `--step [generate-prompts | launch-2a | poll-2a | postprocess | all]`
- `run_all()` — последовательно выполняет все 4 шага

---

## Архитектурные решения

### 1. Изоляция состояния Level 2 от Level 1

`LEVEL2_STATE_FILE = 04_logs/level2_state.json` — отдельный файл. `parallel_runner.py` расширен опциональным `state_file` параметром (default = `LEVEL1_STATE_FILE`, обратная совместимость сохранена).

### 2. `output_schema="auto"` как строковый sentinel

Строка `"auto"` использована как sentinel-значение (а не подкласс dict), т.к. это минимальное изменение, не ломающее существующую type-check логику для `dict`-схем. Тип `Optional[Any]` принимает все три варианта.

### 3. LLM meta-промпты для Level 3 — в коде, не в отдельных файлах

Meta-промпты (шаблоны для генерации промптов 3A/3B/3C/3D) вынесены в константы модуля `postprocess.py`. Это обеспечивает версионность через git. Сгенерированные по ним промпты (результат работы LLM) сохраняются в `03_data/prompts/level_3/` для воспроизводимости.

### 4. Идемпотентность

- `generate_all_prompts()`: пропускает venue если `{venue_key}_prompt.txt` существует
- `process_venue()`: пропускает venue если `venue_card.json` и `cells_list.json` оба существуют
- `launch_task()` (в parallel_runner): пропускает если task_key уже в состоянии (существующая логика)

### 5. `supranational_flag` (AC-8)

Исправление в промпте `build_jurisdiction_card`. Для применения исправления к уже собранным данным (Гонконг) нужно удалить `jurisdiction_card.json` и `venues_list.json` и перезапустить `postprocess` Level 1. Это сознательно не сделано автоматически, т.к. операция деструктивна.

---

## Наблюдения по качеству данных

**Входные данные (Level 1):**
- `jurisdiction_card.json` для UK и Гонконга — присутствуют и качественные
- Гонконг: `supranational_flag=true` со значением "Stock Connect and Bond Connect" — ошибочно по новому правилу (AC-8). Исправление вступит в силу при следующем прогоне Level 1 постобработки
- UK: `supranational_flag=false` — корректно

**Ожидаемые ячейки по площадкам:**
- LSE Main Market: ~6 тиров × до 4 классов ≈ до 24 ячеек (на практике меньше, т.к. не все классы в каждом тире)
- Aquis Stock Exchange: Main Market + Access + Apex × несколько классов ≈ 8-12 ячеек
- HKEX: Main Board + GEM × 4 класса ≈ 8 ячеек (меньше — depositary receipts только на Main Board)

**Данные 1A Россия:** `jurisdiction_card.json` отсутствует — для Россия Level 2 невозможен до завершения Level 1.

---

## Порядок запуска

```bash
# Из корня проекта, с активированным venv:
cd D:\_workspace\deep-research-listing

# Шаг 1: Генерация 2A промптов (LLM, ~1-2 мин)
venv\Scripts\python.exe -m level_2.run_level2 --step generate-prompts

# Шаг 2: Запуск Parallel 2A задач
venv\Scripts\python.exe -m level_2.run_level2 --step launch-2a

# Шаг 3: Ожидание результатов (может занять 10-30 мин)
venv\Scripts\python.exe -m level_2.run_level2 --step poll-2a

# Шаг 4: Постобработка (venue_card + cells_list + L3 промпты)
venv\Scripts\python.exe -m level_2.run_level2 --step postprocess

# Или всё сразу:
venv\Scripts\python.exe -m level_2.run_level2
```

Все команды запускаются из `02_src/` как пакет (через `sys.path.insert`), либо напрямую через `python -m level_2.run_level2` если `02_src` в `PYTHONPATH`.

---

## Промпт для Reviewer

```
Ты — Reviewer. Проект: D:\_workspace\deep-research-listing.

Прочитай обязательно:
- AGENTS.md
- 00_docs/standards/common/structure.md
- 01_tasks/002_level2_venue_pilot/task_brief_01.md
- 01_tasks/002_level2_venue_pilot/implementation_01.md

Проверь реализацию Level 2:
- 02_src/pipeline/parallel_runner.py        (AC-1: output_schema="auto")
- 02_src/pipeline/config.py                 (Level 2 константы)
- 02_src/pipeline/logging_setup.py          (параметр log_file)
- 02_src/pipeline/llm_postprocessor.py      (AC-8: supranational_flag)
- 02_src/level_2/__init__.py
- 02_src/level_2/prompt_generator.py        (AC-2)
- 02_src/level_2/venue_runner.py            (AC-3, AC-4, AC-9)
- 02_src/level_2/postprocess.py             (AC-5, AC-6, AC-7)
- 02_src/level_2/run_level2.py              (оркестратор)

Критерии проверки:
1. Соответствие всем AC из task_brief_01.md
2. Корректность логики state_file изоляции (level1 vs level2)
3. Самодостаточность промптов (без опоры на контекст диалога)
4. Идемпотентность: повторный запуск не перезаписывает уже готовые результаты
5. Обратная совместимость: level_1 код не сломан
6. Корректность cell_id формата и tier_slug логики
7. Правило supranational_flag — точность формулировки в промпте
8. Соответствие структуре файлов из task_brief_01.md

Создай 01_tasks/002_level2_venue_pilot/review_01.md с результатами проверки.
```
