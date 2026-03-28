# Отчет о реализации: Task 006 — Phase 2 Translation Integration

## Что реализовано

`run_pass2_translate` встроен в `run_pipeline.py` — вызывается в конце `run_phase2()` после обоих режимов (basic и extended) с `LLM_FAST_MODEL`. В basic mode `run_pass2` (legacy) заменён на `run_new_pass2`, чтобы создавался `pass2.json`, который translate умеет читать. Создан catch-up скрипт `02_src/tools/run_phase2_catchup.py` для обработки AU/DE/SG/FR.

## Файлы

**Новые:**
- `02_src/tools/run_phase2_catchup.py` — standalone catch-up скрипт для запуска Phase 2 на всех юрисдикциях, где отсутствуют `pass2.json` / `pass2_ru.json`

**Изменённые:**
- `02_src/run_pipeline.py` — добавлен импорт `LLM_FAST_MODEL`; в `run_phase2()`: удалён `run_pass2` из импорта, добавлены `run_new_pass2` (явный вызов в basic mode) и `run_pass2_translate` (вызывается после обоих режимов)

## Особенности реализации

### Выбор: замена run_pass2 на run_new_pass2 vs добавление поверх

**Выбор: замена** (run_new_pass2 вместо run_pass2 в basic mode).

Обоснование:
- `run_pass2` (legacy) пишет `params.json`, `run_pass2_translate` читает только `pass2.json`.
- Если добавить `run_new_pass2` поверх `run_pass2`, для каждой ячейки запускались бы два полных LLM-прохода — двойные затраты без пользы.
- `run_new_pass2` является более новой и полной версией, поддерживает 3P-результаты — нет причин держать legacy вызов в основном пайплайне.
- `params.json` (из legacy mode) не используется последующими шагами; `pass2.json` используется translate и L4/UI.

**Итог:** basic mode теперь: form_groups → pass1 → run_new_pass2 → translate. Semantics -- не изменились, поведение стало правильным.

### Обработка LLM в basic mode

В basic mode `run_new_pass2` теперь явно получает `llm_smart = _get_llm_phase2(LLM_SMART_MODEL)`. Это соответствует паттерну из `run_level4()` и гарантирует, что дорогой умный model используется только там, где нужен.

### Catch-up скрипт

- Сканирует `COUNTRIES_DIR` динамически — filesystem-aware, не зависит от registry.
- Поддерживает `--dry-run` для аудита без LLM вызовов.
- Все шаги идемпотентны: если файлы уже существуют, шаги пропускаются.
- Оптимизация: если все ячейки уже имеют `pass2.json`, шаги form_groups/pass1/pass2-new пропускаются целиком; если все имеют `pass2_ru.json` — translate тоже пропускается.

## Известные проблемы

Нет.
