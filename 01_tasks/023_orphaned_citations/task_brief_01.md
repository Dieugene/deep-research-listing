# Task 023: Orphaned citations — чистка + защита

## Что нужно сделать

В некоторых L3 ячейках секции имеют `description = "not applicable"` или пустое описание, но в массиве `citations[]` всё равно присутствуют записи для этих секций. Фронтенд правомерно не рендерит секции без контента → citations недоступны пользователю.

**Два компонента:**
1. **Pipeline fix** — при записи L3 citations фильтровать entries, относящиеся к секциям без контента
2. **Catchup script** — сканировать все существующие файлы, удалить orphaned citations

---

## Acceptance Criteria

- [ ] AC-1: Функция `remove_orphaned_citations(jurisdictions=None)` создана в `02_src/pipeline/sources.py` или отдельном модуле
- [ ] AC-2: Функция сканирует все `3A/3B/3C_raw.json`, находит citations с `field` соответствующим секции без контента (description пустое / "not applicable")
- [ ] AC-3: Такие citations удаляются из `citations[]`
- [ ] AC-4: Функция идемпотентна (повторный запуск не меняет уже чистые файлы)
- [ ] AC-5: Функция `_filter_citations_by_content(citations, content)` добавлена в логику записи citations — вызывается при создании citations в `_add_citations_to_raw_file`
- [ ] AC-6: Catchup script `02_src/tools/run_orphaned_citations_catchup.py` создан
- [ ] AC-7: Логирование: кол-во удалённых citations per file

---

## Контекст

### Пример orphaned citation (EQUITY-3, 3A_raw.json)

```json
"content": {
  "admission_overview": {
    "description": "not applicable",
    "source": ""
  }
},
"citations": [
  {
    "url": "https://...",
    "title": "Some document",
    "field": "admission_overview",
    "excerpts": ["..."]
  }
]
```

Citation с `field: "admission_overview"` orphaned — потому что секция имеет `description: "not applicable"`.

### Условие "пустой секции"

Секция считается пустой/неприменимой если:
```python
def _is_empty_section(section_value) -> bool:
    if not isinstance(section_value, dict):
        return True
    desc = section_value.get("description", "")
    if not desc or not isinstance(desc, str):
        return True
    desc_stripped = desc.strip().lower()
    return desc_stripped in (
        "not applicable", "n/a", "not applicable.", "n/a.",
        "", "none"
    )
```

Для NESTED секций — пустой считается если ВСЕ subkey имеют пустое description.

### Логика фильтрации citations

```python
def _filter_citations_by_content(citations: list, content: dict) -> list:
    """
    Remove citations where field maps to an empty/not-applicable section.
    Returns filtered list.
    """
    clean = []
    for cit in citations:
        field = cit.get("field", "")
        if not field:
            clean.append(cit)  # keep if no field info
            continue
        # Check if section exists and has content
        section = content.get(field)
        if section is None:
            clean.append(cit)  # keep if field not in content (unknown section)
            continue
        if _is_empty_section(section):
            # Drop — orphaned citation
            continue
        clean.append(cit)
    return clean
```

---

## Компонент 1: Pipeline fix (в sources.py)

В функции `_add_citations_to_raw_file` в `02_src/pipeline/sources.py`:

**Текущий код:**
```python
def _add_citations_to_raw_file(raw_path, label, dry_run, stats):
    raw_data = _load_json(raw_path)
    ...
    citations = extract_sources_from_raw(raw_path)
    ...
    raw_data["citations"] = citations
    _save_json(raw_path, raw_data)
```

**После правки:** добавить фильтрацию перед записью:
```python
content = raw_data.get("content", {})
if content:
    citations = _filter_citations_by_content(citations, content)
raw_data["citations"] = citations
```

Функции `_is_empty_section` и `_filter_citations_by_content` добавить в `sources.py`.

---

## Компонент 2: Catchup

**Функция:** `remove_orphaned_citations(jurisdictions=None)` — добавить в `02_src/pipeline/sources.py`

```python
def remove_orphaned_citations(jurisdictions=None):
    """
    Scan all 3A/3B/3C_raw.json, remove citations pointing to empty/NA sections.
    Idempotent.
    """
    from pipeline.source_classifier import _iter_l3_raw_files
    ...
    for raw_path, label in _iter_l3_raw_files(jurisdictions):
        data = _load_json(raw_path)
        citations = data.get("citations", [])
        content = data.get("content", {})
        if not citations or not content:
            continue

        filtered = _filter_citations_by_content(citations, content)
        removed = len(citations) - len(filtered)

        if removed > 0:
            data["citations"] = filtered
            _save_json(raw_path, data)
            logger.info("[UPDATED] %s — %d orphaned citations removed", label, removed)
        else:
            logger.info("[SKIP] %s — no orphaned citations", label)
```

**Атомарная запись:** использовать `tempfile.mkstemp + os.replace` (паттерн уже есть в модуле через `_save_json`).

---

## Catchup script

`02_src/tools/run_orphaned_citations_catchup.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.sources import remove_orphaned_citations

if __name__ == "__main__":
    print("Removing orphaned citations...")
    remove_orphaned_citations()
    print("Done.")
```

---

## Интеграция в run_pipeline.py

В `run_level3()` после Step 6 (Add citations), перед Step 7 (Classify citation types):

```python
logger.info("--- L3 Step 6b: Remove orphaned citations ---")
from pipeline.sources import remove_orphaned_citations
remove_orphaned_citations(jurisdictions=jurisdiction_names or None)
```

Или можно встроить прямо в `_add_citations_to_raw_file` — тогда pipeline fix не требует отдельного шага, всё происходит автоматически при записи citations. **Предпочтительный вариант**: встроить в `_add_citations_to_raw_file` напрямую.

---

## Файлы для изменения / создания

| Действие | Файл |
|----------|------|
| ИЗМЕНИТЬ | `02_src/pipeline/sources.py` — добавить `_is_empty_section`, `_filter_citations_by_content`, `remove_orphaned_citations`, встроить фильтрацию в `_add_citations_to_raw_file` |
| СОЗДАТЬ | `02_src/tools/run_orphaned_citations_catchup.py` |
| ИЗМЕНИТЬ | `02_src/run_pipeline.py` — если выбран вариант с отдельным шагом (опционально) |

---

## Ограничения

- Не запускать код — только писать
- Идемпотентность обязательна
- Атомарная запись (`tempfile.mkstemp + os.replace`)
- Если `_save_json` в sources.py не атомарная — заменить на атомарную версию

## Отчёт

После реализации создать `01_tasks/023_orphaned_citations/implementation_01.md`
