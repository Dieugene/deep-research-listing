# Отчет о реализации: Level 3 — Сбор данных по ячейкам

## Что реализовано

Реализован Level 3 runner: запуск 105 Parallel Deep Research задач (типы 3A/3B/3C/3D) для всех ячеек по трём площадкам (LSE, Aquis_Stock_Exchange, HKEX), polling до завершения и сохранение сырых JSON-результатов. Запуск подтверждён — все 105 задач успешно отправлены в Parallel API.

## Файлы

**Новые:**
- `02_src/level_3/__init__.py` — пустой пакет
- `02_src/level_3/cell_runner.py` — схемы 3A/3B/3C/3D, load/save state, launch_all_cells, poll_all_cells
- `02_src/level_3/run_level3.py` — CLI оркестратор с --step launch|poll|all

**Изменённые:**
- `02_src/pipeline/config.py` — добавлены LEVEL3_STATE_FILE, LEVEL3_LOG_FILE, get_country_level3_dir

## Особенности реализации

**JSON Schema → flattened SCHEMA_3A:** Parallel API требует root-level `"type": "object"` с `"properties"`. Изначально SCHEMA_3A была двухуровневой (вложенные группы), что давало 6172 символа. Суммарно с крупнейшим промптом (12920 символов) превышало лимит 18000. Решение: схема 3A выравнена до одного уровня (25 полей напрямую в root properties), что снизило её размер до 3557 символов. Максимальный суммарный размер по всем 105 задачам — 16477 символов.

**Дублирующиеся cell_id:** AQSE (Access и Apex тиры делят cell_id на индексах 4-7 и 8-11) и HKEX (`HK_HKEX__equity` на индексах 0 и 4). Task key и папка сохранения суффиксируются `_{i}` (0-based индекс ячейки в списке) при обнаружении дубля.

**Путь сохранения:** `03_data/countries/{name_ru}/level_3/{venue_key}/{cell_id}/` для уникальных cell_id и `03_data/countries/{name_ru}/level_3/{venue_key}/{cell_id}_{i}/` для дублирующихся.

## Известные проблемы

Нет
