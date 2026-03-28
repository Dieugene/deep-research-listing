# Task 009: Backend — R-03 (ParamPill rename) + R-05 (source adapter)

## Что нужно сделать

Два изменения в бэкенде без касания пайплайна:

1. **R-03**: Переименовать поля `ParamPill` и добавить усечение значения до 40 символов
2. **R-05**: Добавить адаптер `source: str` → `sources: list[dict]` в оба репозитория

## Зачем

R-03: Интерфейс ожидает поля `param_id` и `value_short` (≤40 символов), а бэкенд возвращает `code` и `value`. Спецификация UX однозначна: `{param_id, label, value_short}`.

R-05: Исторические файлы данных могут содержать `"source": "https://..."` (строка) вместо `"sources": [...]` (массив объектов). Без адаптера бэкенд вернёт `null` вместо массива, и интерфейс не отобразит источники.

## Acceptance Criteria

- [ ] AC-1: `ParamPill` имеет поля `param_id: str` и `value_short: str` (не `code` и `value`)
- [ ] AC-2: `_get_cell_param_pills()` в `file_repo.py` создаёт `ParamPill(param_id=..., label=..., value_short=...)`; `value_short` усекается до 40 символов
- [ ] AC-3: Функция `_normalize_sources(data: dict) -> list[dict] | None` реализована (как модульная функция в `file_repo.py` и `sqlite_repo.py`, или как общая утилита)
- [ ] AC-4: Все три точки чтения (jurisdiction_card, venue_card, level4) в `file_repo.py` используют адаптер
- [ ] AC-5: Все три точки чтения в `sqlite_repo.py` используют адаптер
- [ ] AC-6: Приложение запускается без ошибок после изменений

## Контекст

### R-03: Текущее состояние

**`02_src/interface/backend/models/venue.py:9-15`** — нужно переименовать:
```python
class ParamPill(BaseModel):
    """A compact parameter display pill for the venue card UI."""
    model_config = ConfigDict(populate_by_name=True)

    code: str    # param_id, e.g. "П01"     ← ПЕРЕИМЕНОВАТЬ в param_id
    label: str   # param_label_ru or param_label
    value: str   # actual value string        ← ПЕРЕИМЕНОВАТЬ в value_short
```

Целевое состояние:
```python
class ParamPill(BaseModel):
    """A compact parameter display pill for the venue card UI."""
    model_config = ConfigDict(populate_by_name=True)

    param_id: str    # e.g. "П01"
    label: str       # param_label_ru or param_label
    value_short: str # actual value string, max 40 chars
```

**`02_src/interface/backend/repositories/file_repo.py:373-380`** — текущее создание pill:
```python
code = str(p.get("param_id", p.get("parameter_id", p.get("id", ""))))
label = str(p.get("param_label_ru", p.get("param_label", p.get("parameter_name", p.get("label", "")))))
value = str(p.get("value", p.get("param_value", "")))

...

pill = ParamPill(code=code, label=label, value=value)
```

Целевое состояние:
```python
code = str(p.get("param_id", p.get("parameter_id", p.get("id", ""))))
label = str(p.get("param_label_ru", p.get("param_label", p.get("parameter_name", p.get("label", "")))))
value = str(p.get("value", p.get("param_value", "")))

...

pill = ParamPill(param_id=code, label=label, value_short=value[:40])
```

### R-05: Текущее состояние

В обоих репозиториях (`file_repo.py` и `sqlite_repo.py`) есть три точки чтения:

```python
# Чтение jurisdiction_card.json:
sources=card.get("sources")                    # может вернуть None

# Чтение venue_card.json:
sources=vc.get("sources")                      # может вернуть None

# Чтение level4.json:
sources=l4.get("sources")                      # может вернуть None
```

В исторических данных поле может называться `"source"` (строка) вместо `"sources"` (список).

**Нужна вспомогательная функция:**
```python
def _normalize_sources(data: dict) -> list[dict] | None:
    """
    Normalizes source data:
    - If 'sources' is a list → return it
    - If 'source' is a non-empty string → wrap in list
    - Otherwise → return None
    """
    sources = data.get("sources")
    if isinstance(sources, list):
        return sources
    source_str = data.get("source")
    if isinstance(source_str, str) and source_str.strip():
        return [{"url": source_str, "title": source_str, "field": "", "excerpts": []}]
    return None
```

Применить вместо `.get("sources")` во всех трёх местах в каждом репозитории.

### Ключевые файлы

- `02_src/interface/backend/models/venue.py` — определение `ParamPill`
- `02_src/interface/backend/repositories/file_repo.py` — `_get_cell_param_pills()` + 3 точки sources
- `02_src/interface/backend/repositories/sqlite_repo.py` — 3 точки sources (нет ParamPill)
- `02_src/interface/backend/models/venue.py` — `CellInVenue` использует `list[ParamPill]` (поля не меняются)

### Что НЕ нужно менять

- `CellInVenue` — поля `params_admission`, `params_maintenance`, `params_enforcement` остаются, тип `list[ParamPill]` остаётся
- Логика фильтрации по phase в `_get_cell_param_pills()` — не трогать
- `sqlite_repo.py` — НЕ реализовывать `_get_cell_param_pills()` (он не конструирует pills)
- Любые другие части `file_repo.py` или `sqlite_repo.py`

## Как проверить

```bash
# Запустить бэкенд:
cd 02_src/interface && uvicorn backend.main:app --reload

# Проверить, что поля ParamPill переименованы (swagger):
# http://localhost:8000/docs → /venues/{venue_key} → CellInVenue.params_admission → ParamPill

# Либо python-проверка:
python -c "from backend.models.venue import ParamPill; p = ParamPill(param_id='П01', label='test', value_short='val'); print(p.model_dump())"
```

## Формат отчёта

Создай `01_tasks/009_backend_r03_r05/implementation_01.md`:
```
# Отчёт о реализации: Task 009 — Backend R-03 + R-05

## Что реализовано
## Файлы (Изменённые)
## Особенности реализации
## Известные проблемы
```
