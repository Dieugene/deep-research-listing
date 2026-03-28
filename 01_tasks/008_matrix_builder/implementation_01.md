# Отчёт о реализации: Task 008 — L3 Matrix Builder 4×5

## Что реализовано

### AC-1 ✅ build_matrix_all() создаёт matrix.json в директории каждой ячейки
`build_matrix_all()` итерирует `COUNTRIES_DIR`, находит все cell dirs с `3A_raw.json`, строит матрицу и сохраняет `matrix.json` в той же директории.

### AC-2 ✅ matrix.json соответствует схеме (разделы 5.3, 5.4)
Формат выходного JSON строго следует спецификации: `cell_id`, `venue_key`, `tier`, `instrument_class`, `matrix` (4 фазы × 5 типов), `metadata` (validation_status, phases_covered, phases_not_covered, terminology).

### AC-3 ✅ Алгоритмический маппинг корректен по таблице раздела 3
- 3A → G07_1: все 9 полей смаплены согласно таблице (`admission_overview`, `eligibility_requirements`, `instrument_requirements`, `sponsor_and_infrastructure`, `restrictions_and_lock_ups`, `special_regimes` → D01; `procedure_and_timeline` → D02; `disclosure_at_admission` → D05; `secondary_admission` → D01)
- 3B → G07_2, G07_3, G07_4: все поля continuing_obligations, suspension, delisting_compulsory/voluntary смаплены
- 3C → G07_2: monitoring_regime (D03), sanctions.disciplinary_procedure + publication_of_actions + enforcement_practice (D04)
- Поля с суффиксом `_common` пропускаются (не в маппинге)
- Ячейки G07_1.D03, G07_1.D04, G07_4.D03 — null по умолчанию

### AC-4 ✅ LLM-маппинг использует LLM_FAST_MODEL
- LLM вызывается через `chain.batch([[HumanMessage(content=p)] for p in prompts], config={"max_concurrency": 50})`
- Используется `with_structured_output(LLMMatrixOutput)` с Pydantic-схемой
- LLM роутит: sanctions (exchange + regulator) → G07_2/G07_3/G07_4.D04; monitoring_suspension → G07_3.D03; additional_findings → соответствующие ячейки

### AC-5 ✅ Идемпотентность
Если `matrix.json` уже существует — ячейка логируется как SKIP и пропускается.

### AC-6 ✅ run_pipeline.py вызывает build_matrix_all() как L3 Step 7
Добавлен шаг после L3 Step 6 (Add citations) в функции `run_level3()`.

### AC-7 ✅ Catch-up скрипт создан (не запускался)
`02_src/tools/run_matrix_catchup.py` — поддерживает `--dry-run` и `--venues` фильтр.

## Файлы

### Новые
- `02_src/level_3/matrix_builder.py` — основной модуль (функции: `_extract_content_item`, `build_matrix_algorithmic`, `build_matrix_llm_inputs`, `apply_llm_output`, `build_matrix_for_cell`, `build_matrix_all`, `_get_llm`, `_assemble_output`, `_extract_metadata`)
- `02_src/tools/run_matrix_catchup.py` — catch-up скрипт

### Изменённые
- `02_src/run_pipeline.py` — добавлен L3 Step 7 (lazy import + `build_matrix_all(llm=None)`)

## Особенности реализации

### Архитектура batch-обработки
`build_matrix_all()` работает в 3 фазы:
1. Загрузка всех ячеек и построение алгоритмических матриц
2. Один batch-вызов LLM для всех ячеек (max_concurrency=50)
3. Применение LLM-результатов и сохранение matrix.json

### Обработка ошибок LLM
- Если batch упал целиком — все ячейки получают алгоритмическую матрицу без LLM-части
- Если LLM-ответ для конкретной ячейки None — логируется warning, сохраняется алгоритмическая матрица
- Ошибки отдельных ячеек не прерывают обработку остальных

### Null vs empty content
- `null` — ячейки G07_1.D03, G07_1.D04, G07_4.D03 по умолчанию; переопределяются если LLM вернул данные
- `{"content": []}` — ячейки ожидаются, но данных не найдено
- `{"content": [...]}` — есть данные

### Фильтрация пустых значений
`_is_na()` проверяет значения `""`, `"not applicable"`, `"n/a"`, `"н/д"` (регистронезависимо). Поля с такими описаниями в матрицу не добавляются.

## Известные проблемы

- `build_matrix_for_cell()` по-прежнему возвращает dict с llm_inputs, а не сразу применяет LLM — это сделано намеренно, чтобы `build_matrix_all()` мог собрать все промпты и вызвать LLM одним batch-запросом.
- Синтаксическая проверка пройдена: `python -c "from level_3.matrix_builder import build_matrix_all; print('OK')"` → OK
