# Отчет о реализации: Level 1 — Анализ юрисдикций (пилот)

## Что реализовано

Инфраструктура Level 1 пайплайна: async-runner для Parallel SDK (launch → state → poll → save), хранилище JSON, логирование с state-файлом для перезапуска, промпты для EU framework и запросов 1A/1B/1C, LLM-постобработка через Langchain. Все компоненты провалидированы: LLM-связь (gpt-5/gpt-5-mini), structured output (`JurisdictionCard`), storage, logging. Parallel SDK подключён, ожидает `PARALLEL_API_KEY` в `.env`.

## Файлы

**Новые:**
- `02_src/pipeline/__init__.py`
- `02_src/pipeline/config.py` — константы, список пилотных юрисдикций, пути
- `02_src/pipeline/storage.py` — чтение/запись JSON, обёртки для сохранения результатов
- `02_src/pipeline/logging_setup.py` — логирование в консоль + файл `04_logs/level1_YYYYMMDD.log`
- `02_src/pipeline/parallel_runner.py` — sync runner: launch_task, poll_until_done, poll_all, state management
- `02_src/pipeline/llm_postprocessor.py` — Langchain + Pydantic: `JurisdictionCard`, `VenueRef`, `build_jurisdiction_card`
- `02_src/level_1/__init__.py`
- `02_src/level_1/prompts.py` — промпты 1A, 1B, 1C с JSON-схемами для Parallel SDK
- `02_src/level_1/eu_framework.py` — EU framework задача (launch/poll/run)
- `02_src/level_1/jurisdiction_runner.py` — запросы 1A/1B/1C для UK, Гонконга, России
- `02_src/level_1/postprocess.py` — LLM-постобработка → jurisdiction_card.json + venues_list.json
- `02_src/level_1/run_level1.py` — оркестратор всего Level 1 (`--step eu|launch-1a|poll-1a|...`)
- `run_pipeline.py` — точка входа из корня проекта

**Изменённые:**
- `.env` — добавлен `PARALLEL_API_KEY=` (пустой, требует заполнения)
- `.gitignore` — добавлены `.env`, `__pycache__/`, `*.pyc`, `venv/`

**Структура данных (создана):**
- `03_data/supranational/` — для eu.json
- `03_data/countries/{Великобритания,Гонконг,Россия}/level_1/` — для 1A/1B/1C/card/venues
- `03_data/prompts/level_1/` — сохранённые промпты
- `04_logs/` — лог-файлы и state

## Особенности реализации

### with_structured_output: method="function_calling"

**Причина:** OpenAI strict JSON schema mode не поддерживает `dict[str, str]` (поле `key_terms_mapping`). API возвращает 400.
**Решение:** Использован `method="function_calling"` в `.with_structured_output()`. Поля `key_terms_mapping` и `supranational_framework` сделаны `Optional` с `default=None`.

### Sync runner вместо async

**Причина:** Parallel SDK задачи асинхронны по природе (запустил → жди), но сам SDK предоставляет синхронный клиент. Использование `asyncio` добавило бы сложность без выигрыша в данном случае.
**Решение:** Sync polling loop с `time.sleep(60)`. Для параллельного запуска нескольких задач: все задачи запускаются в цикле (launch быстрый), затем единый polling loop проверяет все статусы за одну итерацию.

### PARALLEL_API_KEY отсутствует

**Причина:** Ключ не был предоставлен в `.env`. В task_brief указано "проверь в `.env` или документации SDK".
**Решение:** Добавлен placeholder `PARALLEL_API_KEY=` в `.env`. При попытке запустить задачу без ключа код выдаёт чёткое сообщение: `"PARALLEL_API_KEY is not set. Add it to the .env file"`. Все остальные компоненты (LLM, storage, logging) работают.

### Промпт 1C: контекст из 1A

**Причина:** task_brief требует вставить в 1C краткий контекст из 1A (регулятор, типы рынков). На момент запуска 1C результат 1A уже должен быть готов.
**Решение:** В `jurisdiction_runner.launch_all_1bc()` сначала читается `1A_architecture.json` и первые 500 символов content вставляются как контекст в промпт 1C.

## Известные проблемы

- `PARALLEL_API_KEY` не заполнен — Parallel SDK запросы не будут работать до добавления ключа
- Реальные Deep Research запросы (EU, 1A, 1B, 1C) не запускались: нет ключа; данные `jurisdiction_card.json` и `venues_list.json` не существуют (AC-4 – AC-8 не выполнены, ожидают ключ)
- Качество данных по результатам прогонов будет оценено после получения ключа

## Как запустить

```bash
# Из корня проекта (venv активирован)
# 1. Добавить PARALLEL_API_KEY в .env
# 2. Полный прогон:
python run_pipeline.py

# Или по шагам (из 02_src/):
python -m level_1.run_level1 --step eu                   # EU framework
python -m level_1.run_level1 --step launch-1a            # Запустить 1A
python -m level_1.run_level1 --step poll-1a              # Дождаться 1A
python -m level_1.run_level1 --step import-institutional # Импорт 1B из MD
python -m level_1.run_level1 --step launch-1c            # Запустить 1C
python -m level_1.run_level1 --step poll-1c              # Дождаться 1C
python -m level_1.run_level1 --step postprocess          # LLM-постобработка
```

---

## Revision 2 — замена Parallel 1B на импорт из MD

**Дата:** 06.03.2026

### Что изменено

#### Новый файл: `02_src/level_1/import_institutional.py`

Скрипт читает `pilot_jurisdiction_cards.md` (путь по умолчанию:
`D:\_storage_cbr\040_listing_deep_research\03_institutional_factors\_pilot_results\pilot_jurisdiction_cards.md`)
и для каждой пилотной юрисдикции (United Kingdom, Hong Kong, Russia) извлекает
структурированные данные с помощью LangChain + `gpt-5-mini` (`.with_structured_output(InstitutionalFactors, method="function_calling")`).

Результат сохраняется в:
`03_data/countries/{name_ru}/level_1/1B_institutional.json`

Ключевые детали реализации:
- MD-файл парсится регулярными выражениями: секция каждой юрисдикции извлекается
  по заголовку `## United Kingdom` / `## Hong Kong` / `## Russia`.
- Промпт самодостаточен — включает полный текст блока MD.
- `ChatOpenAI` инициализируется с `base_url` из `.env` (без кастомного http-клиента).
- Pydantic-модель `InstitutionalFactors` охватывает все поля JSON-формата:
  `qualitative_factors` (F3, F8, F9, F12), `preloaded_verification` (F1, F11),
  `additional_factors` (F10).
- CLI: `python -m level_1.import_institutional [--md-file PATH]`

#### Изменён: `02_src/level_1/jurisdiction_runner.py`

- `launch_all_1bc` → `launch_all_1c` (удалён запуск 1B)
- `poll_all_1bc` → `poll_all_1c` (удалён polling 1B)
- Удалены импорты `build_prompt_1b`, `SCHEMA_1B`
- Удалена функция `_save_fn_1b`
- CLI: `--launch-1bc` → `--launch-1c`, `--poll-1bc` → `--poll-1c`

#### Изменён: `02_src/level_1/run_level1.py`

Новый порядок шагов:
1. EU Framework
2. Launch 1A + poll
3. **Import institutional (1B из MD)** — вызов `import_all()` из `import_institutional`
4. Launch 1C + poll (с контекстом из 1A)
5. LLM postprocessing

STEPS: добавлен `import-institutional`, удалены `launch-1bc` / `poll-1bc`,
добавлены `launch-1c` / `poll-1c`.

### Что НЕ изменено

`eu_framework.py`, `postprocess.py`, `prompts.py` (1B-функции остались в файле,
они просто не импортируются из `jurisdiction_runner`), весь `pipeline/`.

### Проверка

```
python -c "from level_1 import import_institutional, jurisdiction_runner, run_level1"
# → OK (проверено)
```
