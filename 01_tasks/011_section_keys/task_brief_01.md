# Task 011: L3 Parameters — section_keys[]

## Что нужно сделать

Добавить поле `section_keys: list[str]` в каждый объект параметра в `pass2_ru.json` (и `pass2.json`, если `pass2_ru.json` отсутствует). Поле определяет, к каким секциям контента относится данный параметр.

## Acceptance Criteria

- [ ] AC-1: Функция `process_section_keys(jurisdictions=None)` реализована в `02_src/pipeline/section_keys.py`
- [ ] AC-2: Каждый параметр в `parameter_values[]` получает поле `section_keys: list[str]`
- [ ] AC-3: Маппинг детерминированный (без LLM) — основан на `lifecycle_phase_key` + анализе существующего контента ячейки
- [ ] AC-4: Идемпотентность — если ВСЕ параметры уже имеют `section_keys` → пропускать файл
- [ ] AC-5: `run_pipeline.py` вызывает функцию после шага Phase 2 translate (в `run_phase2()`)
- [ ] AC-6: Catch-up скрипт `02_src/tools/run_section_keys_catchup.py` создан (не запускать)

## Контекст

### Зачем

Сейчас в UI параметры дублируются под каждой секцией контента. `section_keys` позволяет показывать параметр только под релевантной секцией.

### Логика маппинга (детерминированная)

Маппинг основан на `lifecycle_phase_key` параметра. Для каждой ячейки мы знаем, какие секции контента имеют непустое содержание (из 3A/3B/3C_raw.json).

#### Правила маппинга lifecycle_phase_key → section_keys

**`admission`** → секции из 3A_raw.json, которые имеют непустой `description`:
- Список: `admission_overview`, `eligibility_requirements`, `instrument_requirements`, `sponsor_and_infrastructure`, `restrictions_and_lock_ups`, `special_regimes`, `procedure_and_timeline`, `disclosure_at_admission`, `secondary_admission`
- Включать только те, у которых description != "" и != "not applicable" (регистронезависимо)

**`continuing`** → суб-ключи из 3B_raw.json `content.continuing_obligations.*`, которые имеют непустой description:
- Формат ключа: `"continuing_obligations.{sub_key}"` (например, `"continuing_obligations.periodic_reporting"`)
- Суб-ключи: `quantitative_thresholds`, `qualitative_obligations`, `compliance_confirmation`, `periodic_reporting`

**`suspension`** → суб-ключи из 3B_raw.json `content.suspension.*`, которые имеют непустой description:
- Формат ключа: `"suspension.{sub_key}"`
- Суб-ключи: `grounds`, `duration_limits`, `procedure`, `disclosure`

**`delisting`**, **`enforcement`**, или содержит "delist" / "remov" в имени:
→ суб-ключи из 3B_raw.json `content.delisting_compulsory.*` + `content.delisting_voluntary.*`, которые имеют непустой description:
- Формат ключа: `"delisting_compulsory.{sub_key}"`, `"delisting_voluntary.{sub_key}"`

**Если `lifecycle_phase_key` пустой или не распознан** → `section_keys: []`

**Если 3A/3B файл отсутствует** → использовать пустой список для соответствующей фазы

### Проверка "пустого" description

```python
EMPTY_VALUES = {"", "not applicable", "n/a", "not relevant", "н/д", "none"}

def _is_empty(description: str) -> bool:
    return description.strip().lower() in EMPTY_VALUES
```

### Структура 3A content (плоский, 1 уровень)

```python
raw_3a = load_json(cell_dir / "3A_raw.json")
content_3a = raw_3a.get("content", {}) if raw_3a else {}
# content_3a["eligibility_requirements"]["description"] == "..."
```

### Структура 3B content (вложенный, 2 уровня)

```python
raw_3b = load_json(cell_dir / "3B_raw.json")
content_3b = raw_3b.get("content", {}) if raw_3b else {}
# content_3b["continuing_obligations"]["quantitative_thresholds"]["description"] == "..."
```

### Путь к файлам

```python
from pipeline.config import COUNTRIES_DIR
# COUNTRIES_DIR / name_ru / "level_3" / venue_key / cell_id / "pass2_ru.json"
# COUNTRIES_DIR / name_ru / "level_3" / venue_key / cell_id / "3A_raw.json"
# COUNTRIES_DIR / name_ru / "level_3" / venue_key / cell_id / "3B_raw.json"
```

Обход ячеек — аналогично matrix_builder.py:
```python
for country_dir in COUNTRIES_DIR.iterdir():
    l3_dir = country_dir / "level_3"
    if not l3_dir.exists():
        continue
    for venue_dir in l3_dir.iterdir():
        for cell_dir in venue_dir.iterdir():
            if (cell_dir / "pass2_ru.json").exists() or (cell_dir / "pass2.json").exists():
                yield cell_dir
```

### Приоритет: pass2_ru.json перед pass2.json

- Если есть `pass2_ru.json` → обновлять его (и также обновить `pass2.json` если существует)
- Если только `pass2.json` → обновлять его

### Целевая структура параметра

```json
{
  "param_id": "П01",
  "param_label": "Free float",
  "param_label_ru": "Свободный флоут",
  "value": "10%",
  "lifecycle_phase_key": "admission",
  "section_keys": ["eligibility_requirements", "instrument_requirements"],
  "status": "found"
}
```

### Архитектура `02_src/pipeline/section_keys.py`

```python
def _get_section_keys_for_phase(phase_key: str, raw_3a: dict, raw_3b: dict) -> list[str]:
    """Determine section_keys based on lifecycle_phase_key and available content."""
    ...

def _process_pass2_file(pass2_path: Path, cell_dir: Path) -> int:
    """Add section_keys to all parameters in one pass2 file. Returns count of updated params."""
    ...

def process_section_keys(jurisdictions: list[str] | None = None) -> None:
    """Iterate all cells, add section_keys to parameters. Idempotent."""
    ...
```

### Идемпотентность

Пропускать **весь файл**, если все параметры со статусом "found" уже имеют поле `section_keys` (даже если значение — пустой список `[]`).

```python
params = data.get("parameter_values", data.get("parameters", []))
found_params = [p for p in params if p.get("status") in ("found", "Найдено", "extracted")]
if all("section_keys" in p for p in found_params):
    logger.info("[SKIP] %s", cell_id)
    continue
```

### Интеграция в run_pipeline.py

Добавить в конец `run_phase2()` (после вызова `run_pass2_translate`):

```python
logger.info("--- Phase2 Step: Section keys ---")
from pipeline.section_keys import process_section_keys
process_section_keys()
```

### Логирование

```python
from pipeline.logging_setup import get_logger
from pipeline.config import LOGS_DIR
import datetime
logger = get_logger("section_keys", LOGS_DIR / f"section_keys_{datetime.date.today()}.log")
```

- `[UPDATED] {cell_id} — {n} params updated`
- `[SKIP] {cell_id} — all params already have section_keys`

## Ключевые файлы

- `02_src/pipeline/config.py` — COUNTRIES_DIR, LOGS_DIR
- `02_src/pipeline/logging_setup.py` — get_logger
- `02_src/run_pipeline.py` — добавить в run_phase2()
- Пример: `03_data/countries/Великобритания/level_3/LSE_Main_Market/GB_LSE_Main_Market_equity_shares_commercial_compa_equity/pass2_ru.json`

## Формат отчёта

Создай `01_tasks/011_section_keys/implementation_01.md`:
```
# Отчёт о реализации: Task 011 — L3 Parameters section_keys[]

## Что реализовано
## Файлы (Новые / Изменённые)
## Особенности реализации
## Известные проблемы
```
