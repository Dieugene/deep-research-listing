# Task 006: Phase 2 Translation Integration

## Что нужно сделать

1. **Встроить `run_pass2_translate` в `run_pipeline.py`** — чтобы перевод параметров выполнялся автоматически при каждом прогоне пайплайна.
2. **Изменить translate на `LLM_FAST_MODEL`** — перевод является простой задачей, не требующей умной модели.
3. **Выполнить catch-up прогон** для AU/DE/SG/FR — создать `pass2.json` и `pass2_ru.json` для юрисдикций, где их нет.

## Зачем

Ранее Phase 2 translation (`run_pass2_translate`) не была встроена в основной пайплайн. При добавлении AU/DE/SG/FR шаг translate был пропущен, и данные остались без русского перевода параметров. Интерфейс отображает параметры на английском языке вместо русского.

## Acceptance Criteria

- [ ] AC-1: `run_pass2_translate` вызывается в `run_pipeline.py` → `run_phase2()` после шагов создания `pass2.json`
- [ ] AC-2: Translate использует `LLM_FAST_MODEL` ("gpt-5-mini"), не `LLM_SMART_MODEL`
- [ ] AC-3: Все 4 юрисдикции (Австралия, Германия, Сингапур, Франция) имеют `pass2_ru.json` для каждой ячейки
- [ ] AC-4: Повторный запуск пайплайна на уже обработанных ячейках идемпотентен (SKIP, не перезапускает)
- [ ] AC-5: Новый прогон пайплайна (например, для новой юрисдикции) автоматически включает translate

## Контекст

### Архитектура Phase 2 — ОБЯЗАТЕЛЬНО изучи перед реализацией

`02_src/level_3/phase2_runner.py` содержит две версии pass2:

**Оригинальный pass2 (basic mode):**
- Функция: `run_pass2(state)`
- Выходной файл: **`params.json`** (per cell)
- Используется при `--phase2-mode basic` в `run_pipeline.py`

**Новый pass2 (extended mode / run_new_pass2):**
- Функция: `run_new_pass2(state, llm)`
- Выходной файл: **`pass2.json`** (per cell)
- Используется при `--phase2-mode extended` в `run_pipeline.py` (через `run_all_extended`)

**Translate:**
- Функция: `run_pass2_translate(llm)`
- Читает: **`pass2.json`** (НЕ `params.json`!)
- Выходной файл: **`pass2_ru.json`** (per cell)

**ВАЖНО:** translate читает `pass2.json`, который создаётся только `run_new_pass2`. Оригинальный `run_pass2` создаёт `params.json` — translate его не увидит.

UK/HK имеют `pass2.json` (прошли через extended mode с 3P drill-down). AU/DE/SG/FR не имеют ни `params.json`, ни `pass2.json` (Phase 2 никогда не запускалась).

### Текущий run_phase2() в run_pipeline.py (строки 259-295)

```python
def run_phase2(mode: str = "basic") -> None:
    from level_3.phase2_runner import (
        load_state as load_state_phase2,
        form_groups,
        run_pass1,
        run_pass2,
        run_all_extended,
        ...
    )

    state_phase2 = load_state_phase2()

    if mode == "extended":
        run_all_extended(state_phase2)
    else:
        # basic: form_groups → pass1 → pass2 (→ params.json, НЕ pass2.json!)
        form_groups(state_phase2)
        run_pass1(state_phase2)
        run_pass2(state_phase2)

    # ⚠️ run_pass2_translate НЕ вызывается ни в одной ветке!
```

### Модели в config.py

```python
# 02_src/pipeline/config.py
LLM_SMART_MODEL = "gpt-5"        # дорогой, для сложных задач
LLM_FAST_MODEL = "gpt-5-mini"    # дешёвый, для простых задач (перевод)
```

### Подпись run_pass2_translate

```python
def run_pass2_translate(llm: ChatOpenAI) -> None:
    """
    Для каждого pass2.json файла: переводит текстовые поля на русский через LLM batch.
    Сохраняет pass2_ru.json в той же директории.
    Идемпотентно: пропускает если pass2_ru.json уже существует.
    """
```

Функция сканирует COUNTRIES_DIR динамически (filesystem-aware) — не нужно передавать список юрисдикций.

### Паттерн вызова LLM в run_pipeline.py

Смотри как run_level4() вызывает LLM:
```python
def run_level4(jurisdictions):
    from level_4.level4_runner import run_level4_all, _get_llm as _get_llm_l4
    llm = _get_llm_l4(LLM_SMART_MODEL)
    run_level4_all(llm=llm, jurisdictions=jurisdictions)
```
Аналогично нужно импортировать `_get_llm` из `phase2_runner` и создавать LLM с `LLM_FAST_MODEL`.

### run_all_extended — структура (для справки)

```python
def run_all_extended(state):
    form_groups(state)
    run_pass1(state)
    run_3p_classify(...)
    run_3p_execute(...)
    run_new_pass2(state, llm)
    # ⚠️ translate тут тоже не вызывается
```

### Ключевые файлы

- `02_src/run_pipeline.py` — основной оркестратор; здесь `run_phase2()`
- `02_src/level_3/phase2_runner.py` — содержит все функции Phase 2 включая translate
- `02_src/level_3/run_phase2.py` — standalone CLI для Phase 2 (для catch-up прогона)
- `02_src/pipeline/config.py` — `LLM_SMART_MODEL`, `LLM_FAST_MODEL`, `COUNTRIES_DIR`

### Данные для проверки

Каталоги AU/DE/SG/FR в данных:
- Австралия: `03_data/countries/Австралия/`
- Германия: `03_data/countries/Германия/`
- Сингапур: `03_data/countries/Сингапур/`
- Франция: `03_data/countries/Франция/`

Путь к ячейке: `03_data/countries/{юрисдикция}/level_3/{venue_key}/{cell_id}/pass2.json`

## Что реализовать

### Изменение 1: run_pipeline.py — интеграция translate

В `run_phase2()` добавить вызов `run_pass2_translate` после создания `pass2.json`:

Логика:
- Для basic mode: после `run_pass2()` нужно также создать `pass2.json` через `run_new_pass2()`, а затем вызвать translate. ИЛИ: сменить basic mode чтобы он использовал `run_new_pass2` вместо `run_pass2` (предпочтительнее).
- Для extended mode: `run_all_extended()` завершается `run_new_pass2()`, после него добавить translate.
- Translate вызывается с `LLM_FAST_MODEL`.

Решение о точном подходе для basic mode (заменить pass2 на new_pass2 или добавить new_pass2 после pass2) — на усмотрение разработчика. Обоснуй выбор в implementation.md.

### Изменение 2: phase2_runner.py — модель для translate

В `run_pass2_translate(llm)`: документально это параметр, поэтому вызывающая сторона должна передавать правильную модель. Изменение уже обеспечивается через Изменение 1 (вызов с LLM_FAST_MODEL).

Дополнительно: можно добавить константу `LLM_TRANSLATE_MODEL = LLM_FAST_MODEL` в config.py для явности.

### Изменение 3: Catch-up скрипт для AU/DE/SG/FR

Создать `02_src/tools/run_phase2_catchup.py` — скрипт-однократный прогон Phase 2 для юрисдикций, у которых нет `pass2.json`.

Скрипт должен:
1. Сканировать `COUNTRIES_DIR` и найти ячейки без `pass2.json`
2. Для таких юрисдикций запустить: form_groups → run_pass1 → run_new_pass2 → run_pass2_translate
3. Все шаги идемпотентны (safe to run even if some cells already have files)
4. Вывод: список обработанных ячеек + количество pass2.json и pass2_ru.json созданных

**ВАЖНО:** Скрипт создаётся, но НЕ запускается разработчиком. Запуск выполняет Tech Lead.

## Логирование

Следуй существующим паттернам логирования в `phase2_runner.py`:
- `logger.info("[TRANSLATED] %s", cell_id)` — при успехе
- `logger.info("[SKIP] %s", cell_id)` — при пропуске (уже есть)
- `logger.error("[ERROR] %s", exc)` — при ошибке

## Тестирование

Используй реальные данные (`03_data/countries/`). Тесты нет смысла мокировать — вся логика filesystem-aware и идемпотентна.

Проверочный запрос (после запуска catch-up скрипта должны появиться pass2_ru.json):
```
# Проверка наличия pass2_ru.json для Австралии
03_data/countries/Австралия/level_3/*/*/pass2_ru.json
```

## Формат отчёта о реализации

Создай `01_tasks/006_phase2_translate_integration/implementation_01.md` по стандарту:
```
# Отчет о реализации: Task 006 — Phase 2 Translation Integration

## Что реализовано
## Файлы (Новые / Измененные)
## Особенности реализации
## Известные проблемы
```
