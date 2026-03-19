# Отчёт для UX-разработчика: структура данных и вмешательство в зону интерфейса

**Дата:** 2026-03-16
**От:** Tech Lead (пайплайн)
**Кому:** UX-разработчик (02_src/interface/)

---

## 1. Что было затронуто в зоне интерфейса (02_src/interface/)

### Task 009 — изменения в бэкенде (сделаны Tech Lead, не UX-разработчиком)

Задача 009 ошибочно затронула зону интерфейса. Вот что было изменено:

#### 1.1. `backend/models/venue.py` — переименование полей `ParamPill`

| Старое имя поля | Новое имя поля | Описание |
|-----------------|----------------|----------|
| `code` | `param_id` | Идентификатор параметра (напр. "П01") |
| `value` | `value_short` | Значение параметра, усечённое до 40 символов |

`label` не изменился. Бэкенд теперь возвращает:
```json
{
  "param_id": "П01",
  "label": "Свободный флоут",
  "value_short": "10%"
}
```

**Затронутые эндпоинты:** `GET /venues/{venue_key}` → `cells[].params_admission`, `params_maintenance`, `params_enforcement`.

#### 1.2. `backend/repositories/file_repo.py` — добавлен `_normalize_sources()`

Добавлена вспомогательная функция, которая приводит легаси-формат источника (строка) к массиву:

```python
# Легаси: { "source": "https://..." }
# → нормализовано: { "sources": [{"url": "...", "title": "...", "field": "", "excerpts": []}] }
```

Применяется при чтении `jurisdiction_card.json`, `venue_card.json`, `level4.json`.

---

## 2. Критический баг, введённый Task 012 (требует исправления в бэкенде)

### `VENUE_TYPE_LABELS` в `backend/core/labels.py` — несоответствие регистра

**Проблема:** Task 012 нормализовал `venue_type` в JSON-файлах к lowercase. Бэкенд читает `venue_type` из файла и передаёт через `_venue_type_label()`, которая ищет в `VENUE_TYPE_LABELS`. Но словарь содержит только старые uppercase ключи.

**Текущее состояние `VENUE_TYPE_LABELS`:**
```python
VENUE_TYPE_LABELS = {
    "regulated_market": "Regulated Market",  # ✅ без изменений в данных
    "MTF": "MTF",    # ❌ в данных теперь "mtf"
    "OTF": "OTF",    # ❌ в данных теперь "otf"
    # "exchange_regulated" — вообще отсутствует
}
```

**Значения `venue_type` в JSON после нормализации:**
| venue_type в JSON | Текущий результат API | Должно быть |
|-------------------|-----------------------|-------------|
| `"regulated_market"` | `"Regulated Market"` | `"Regulated Market"` |
| `"mtf"` | `"mtf"` (fallback, нет совпадения) | `"MTF"` или `"Multilateral Trading Facility"` |
| `"otf"` | `"otf"` (fallback) | `"OTF"` или `"Organised Trading Facility"` |
| `"exchange_regulated"` | `"exchange_regulated"` (fallback) | `"Exchange Regulated Market"` или аналог |

**Файл для исправления:** `02_src/interface/backend/core/labels.py`

**Исправление:**
```python
VENUE_TYPE_LABELS: dict[str, str] = {
    "regulated_market": "Regulated Market",
    "mtf": "MTF",
    "otf": "OTF",
    "exchange_regulated": "Exchange Regulated Market",
}
```

---

## 3. Новые поля в данных — что доступно для отображения

Все новые поля добавлены пайплайном и уже присутствуют в JSON-файлах. Бэкенд частично их использует или передаёт как `dict`.

### 3.1. `jurisdiction_card.json` — новые поля L1

**Файл:** `03_data/countries/{jurisdiction_ru}/level_1/jurisdiction_card.json`

#### `market_type` (новое поле)
```json
{ "market_type": "DM" }
```
Значения: `"DM"` (Developed Market) | `"EM"` (Emerging Market).

> **Важно:** Бэкенд читает `market_type` **не из JSON**, а из статического словаря `core/jurisdiction_meta.py → JURISDICTION_MARKET_TYPE`. Значения совпадают, но используется именно словарь. Поле в JSON избыточно для текущего бэкенда.

#### `listing_authority_short` (новое поле)
```json
{ "listing_authority_short": "FCA" }
```
Короткое название органа листинга (≤30 символов). Примеры:
- Австралия: `"ASX"`
- Великобритания: `"FCA"`
- Германия: `"Deutsche Börse AG"`
- Гонконг: `"SEHK"`
- Сингапур: `"SGX-ST"`
- Франция: `"Euronext Paris"`

> **Важно:** Бэкенд **не читает** `listing_authority_short`. Модель `JurisdictionSummary` содержит поле `listing_authority` (читает полную строку `listing_authority`, не `listing_authority_short`). Для отображения в UI короткой версии — нужно добавить поле в модель и в `file_repo.py → get_jurisdictions()`.

#### `legal_family` — нормализован к lowercase
```json
{ "legal_family": "civil law" }
```
Возможные значения: `"common law"` | `"civil law"` | `"mixed"`. Ранее Германия имела `"Civil law"` — исправлено.

### 3.2. `venue_card.json` — нормализация L2

**Файл:** `03_data/countries/{jurisdiction_ru}/level_2/{venue_key}/venue_card.json`

#### `venue_type` — нормализован к lowercase enum
| Было | Стало | Кто затронут |
|------|-------|-------------|
| `"MTF"` | `"mtf"` | LSE AIM, Tradegate, Aquis Europe, Euronext Access Paris, Euronext Growth Paris, MTS France |
| `"OTF"` | `"otf"` | (нет таких площадок в текущих данных) |
| `"other"` | `"exchange_regulated"` | BÖAG Börsen, Börse München, Börse Stuttgart (Freiverkehr) |
| `"regulated_market"` | без изменений | Все основные площадки |

**⚠️ Требует исправления в `core/labels.py`** (см. раздел 2).

### 3.3. `sources[]` — новые поля во всех источниках

**Затронутые файлы:** `jurisdiction_card.json`, `venue_card.json`, `level4.json`

#### `type` (новое поле)
```json
{
  "url": "https://handbook.fca.org.uk/...",
  "title": "UK Listing Rules",
  "field": "eligibility_requirements",
  "excerpts": ["Rule 5.5.2R: At least 10%..."],
  "type": "rulebook"
}
```

Допустимые значения `type`:
| Значение | Описание |
|----------|----------|
| `"legislation"` | Законодательные базы (legislation.gov.uk, legifrance.gouv.fr) |
| `"rulebook"` | Биржевые правила (handbook.fca.org.uk, rulebook.sgx.com) |
| `"government"` | Регуляторы и госорганы (fca.org.uk, mas.gov.sg) |
| `"consultation"` | Консультативные документы |
| `"research"` | Научные публикации (oecd.org, worldbank.org) |
| `"other"` | Прочие |

Бэкенд передаёт `sources` как `list[dict]` без фильтрации — поле `type` доступно в ответе API.

#### `excerpts` (добавлено Task 007)
```json
{ "excerpts": ["Rule 5.5.2R: At least 10% of shares must be in public hands."] }
```
Бэкенд передаёт `sources` как `list[dict]` — `excerpts` доступны в ответе API.

### 3.4. `level4.json` — новые поля L4

**Файл:** `03_data/countries/{jurisdiction_ru}/level_4/level4.json`

#### `label` (новое поле в каждой записи)
```json
{
  "description_ru": "Правительство рассматривало реформу...",
  "articulated_by": "government",
  "label": "Реформа листинга 2022–2024"
}
```
Поле `label` добавлено в каждую запись массивов `problems[]`, `contradictions[]`, `parameters_as_tools[]`, `reforms[]`. Длина ≤35 символов, на русском языке.

Бэкенд передаёт весь Level4 как `list[dict]` — `label` доступен в ответе API без изменений бэкенда.

#### `articulated_by` — нормализован к enum
Нормализовано: `"industry"` → `"market_participants"`.

Допустимые значения: `"government"` | `"regulator"` | `"academic"` | `"market_participants"` | `"exchange"`.

Бэкенд передаёт записи как `list[dict]` — значение доступно без изменений.

#### Per-record `sources[]` (Task 010)
Каждая запись теперь имеет свои источники:
```json
{
  "description_ru": "...",
  "articulated_by": "government",
  "label": "...",
  "sources": [
    {
      "url": "https://...",
      "title": "...",
      "type": "government"
    }
  ]
}
```

### 3.5. `pass2_ru.json` — `section_keys[]` (Task 011)

**Файл:** `03_data/countries/{jurisdiction_ru}/level_3/{venue_key}/{cell_id}/pass2_ru.json`

Каждый параметр теперь содержит поле `section_keys[]` — к каким секциям схемы (3A/3B/3C) относится:
```json
{
  "param_id": "П01",
  "param_label_ru": "Свободный флоут",
  "value": "10%",
  "section_keys": ["eligibility_requirements", "instrument_requirements"],
  "lifecycle_phase_key": "admission",
  "status": "found"
}
```

> **Важно:** Бэкенд **не читает** `section_keys`. Модель `ParameterValue` (`backend/models/parameter.py`) не содержит этого поля. Для использования в UI (показывать параметр только под релевантной секцией) — нужно добавить `section_keys: list[str] = []` в `ParameterValue` и дописать чтение в `get_cell_parameters()`.

---

## 4. Что бэкенд УЖЕ читает из новых данных (без изменений)

| Новое поле | Где доступно в API | Как |
|-----------|-------------------|-----|
| `sources[].type` | Все эндпоинты с sources | Pass-through как dict |
| `sources[].excerpts` | Все эндпоинты с sources | Pass-through как dict |
| `level4.label` | GET /jurisdictions/{name_ru} → level4.* | Pass-through как dict |
| `level4.articulated_by` (нормализован) | GET /jurisdictions/{name_ru} → level4.* | Pass-through как dict |
| `level4 per-record sources` | GET /jurisdictions/{name_ru} → level4.* | Pass-through как dict |
| `legal_family` (lowercase) | GET /jurisdictions и GET /jurisdictions/{name_ru} | Прямое чтение |

---

## 5. Что бэкенд НЕ читает из новых данных (требует доработки по необходимости)

| Новое поле | Файл данных | Что нужно сделать |
|-----------|-------------|-------------------|
| `listing_authority_short` | jurisdiction_card.json | Добавить в `JurisdictionSummary` + `get_jurisdictions()` |
| `section_keys[]` в параметрах | pass2_ru.json | Добавить в `ParameterValue` + `get_cell_parameters()` |
| `market_type` из JSON | jurisdiction_card.json | Уже есть через `JURISDICTION_MARKET_TYPE` словарь — дублирует, не баг |

---

## 6. Итоговый список действий для UX-разработчика

### Обязательно (баги):
1. **Исправить `VENUE_TYPE_LABELS`** в `backend/core/labels.py` — добавить lowercase ключи и `"exchange_regulated"` (см. раздел 2)

### По необходимости (новый функционал):
2. **`listing_authority_short`** — если нужна короткая форма в UI, добавить в `JurisdictionSummary` и `get_jurisdictions()`
3. **`section_keys[]`** в параметрах — если нужна фильтрация параметров по секции, добавить в `ParameterValue` и `get_cell_parameters()`
4. **`sources[].type`** — доступен как-есть, можно использовать для фильтрации источников в UI по типу документа
5. **`level4.label`** — доступен как-есть, можно использовать для таймлайна (уже встроено в данные)

### Информационно:
6. `ParamPill.code` → `param_id`, `value` → `value_short` — фронтенд должен был быть обновлён при Task 009 (затронуты `types.ts`, `VenuePage.tsx`)
7. `_normalize_sources()` — работает прозрачно, обратная совместимость с легаси `source: str` обеспечена
