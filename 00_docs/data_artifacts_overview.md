# Обзор артефактов данных пайплайна

**Дата:** 2026-03-12
**Адресат:** разработчик интерфейса (Viewer / UI)
**Статус:** актуально для текущего состояния пилота (UK полный, HK полный, Россия частичный)

---

## 1. Что представляет собой хранилище данных

Хранилище — результат многоуровневого пайплайна сбора и обработки регуляторных требований к листингу ценных бумаг по юрисдикциям. Данные организованы иерархически:

- **Level 1** — профиль юрисдикции (регулятор, архитектура допуска, список площадок).
- **Level 2** — профиль торговой площадки (venue): структура, тиры, ячейки.
- **Level 3 (Phase 1)** — сырые исследовательские данные по каждой ячейке (cell): первичный допуск (3A), негативные аспекты (3B), мониторинг (3C).
- **Level 3 (Phase 2)** — нормализованные параметры: группировка ячеек (_groups), Pass 1 (фреймворк параметров), доразведка (3P), Pass 2 (значения по ячейке).
- **Level 4** — регуляторные цели, противоречия и реформы по юрисдикции.

Корень хранилища данных: `03_data/`

Корень логов состояния: `04_logs/`

---

## 2. Структура директорий

```
03_data/
├── countries/
│   ├── Великобритания/
│   │   ├── level_1/
│   │   │   ├── 1A_architecture.json
│   │   │   ├── 1B_institutional.json
│   │   │   ├── 1C_venues.json
│   │   │   ├── jurisdiction_card.json
│   │   │   └── venues_list.json
│   │   ├── level_2/
│   │   │   ├── LSE_Main_Market/
│   │   │   │   ├── 2A_structure.json
│   │   │   │   ├── venue_card.json
│   │   │   │   └── cells_list.json
│   │   │   ├── LSE_AIM/
│   │   │   │   └── (аналогично)
│   │   │   └── Aquis_Stock_Exchange/
│   │   │       └── (аналогично)
│   │   ├── level_3/
│   │   │   ├── LSE_Main_Market/
│   │   │   │   ├── _parallel_raw/
│   │   │   │   │   ├── LSE_Main_Market_equity_3A_raw.json
│   │   │   │   │   ├── LSE_Main_Market_equity_3B_raw.json
│   │   │   │   │   └── ... (по 3 файла на каждый instrument_class × {3A,3B,3C})
│   │   │   │   ├── GB_LSE_Main_Market_equity_shares_commercial_compa_equity/
│   │   │   │   │   ├── 3A_raw.json
│   │   │   │   │   ├── 3A_validation.json
│   │   │   │   │   ├── 3B_raw.json
│   │   │   │   │   ├── 3B_validation.json
│   │   │   │   │   ├── 3C_raw.json
│   │   │   │   │   ├── 3C_validation.json
│   │   │   │   │   ├── pass2.json
│   │   │   │   │   └── pass2_ru.json
│   │   │   │   └── ... (остальные ячейки)
│   │   │   ├── LSE_AIM/
│   │   │   │   └── (аналогично)
│   │   │   ├── Aquis_Stock_Exchange/
│   │   │   │   └── (аналогично)
│   │   │   └── _groups/
│   │   │       ├── United_Kingdom_regulated_market_equity_standard/
│   │   │       │   ├── group_meta.json
│   │   │       │   ├── pass1.json
│   │   │       │   ├── pass1_unknowns.json
│   │   │       │   ├── 3P_prompt.txt
│   │   │       │   ├── 3P_schema.json
│   │   │       │   └── 3P_raw.json
│   │   │       └── ... (остальные группы)
│   │   └── level_4/
│   │       ├── 4A_raw.json
│   │       ├── level4.json
│   │       └── level4_validation.json
│   ├── Гонконг/
│   │   ├── level_1/     (аналогично UK)
│   │   ├── level_2/
│   │   │   ├── HKEX_Main_Board/
│   │   │   └── HKEX_GEM/
│   │   ├── level_3/
│   │   │   ├── HKEX_Main_Board/
│   │   │   ├── HKEX_GEM/
│   │   │   └── _groups/
│   │   └── level_4/
│   └── Россия/
│       └── level_1/
│           ├── 1A_architecture.json
│           └── 1B_institutional.json
├── supranational/
│   └── eu.json
└── prompts/
    ├── level_1/       # {id}_{юрисдикция}.txt
    ├── level_2/
    ├── level_3/       # {cell_id}_{3A|3B|3C}.txt
    └── level_3_v2/

04_logs/
├── level1_state.json
├── level2_state.json
├── level3_state.json
├── level3_v2_state.json
├── phase2_state.json
├── phase2_3p_state.json
└── level4_state.json
```

---

## 3. Артефакты по уровням пайплайна

### 3.1 Level 1 — профиль юрисдикции

Путь: `03_data/countries/{jurisdiction_ru}/level_1/`

#### `jurisdiction_card.json`

Сводная карточка юрисдикции. Основной файл для отображения шапки юрисдикции в UI.

**Ключевые поля:**

| Поле | Тип | Описание |
|------|-----|----------|
| `jurisdiction` | string | Английское название юрисдикции |
| `jurisdiction_ru` | string | Русское название (совпадает с именем папки) |
| `legal_family` | string | Правовая семья (`"common law"`, `"civil law"`, ...) |
| `regulator_name` | string | Название регулятора |
| `regulator_type` | string | Тип регулятора (`"commission"`, ...) |
| `admission_architecture` | string | Описание архитектуры допуска (EN) |
| `admission_architecture_ru` | string | Описание архитектуры допуска (RU) |
| `listing_authority` | string | Орган, выдающий листинг |
| `market_types` | array[string] | Типы рынков юрисдикции |
| `key_terms_mapping` | object | Словарь: термин → определение |
| `venues` | array[object] | Список площадок (краткий, без деталей) |
| `supranational_flag` | boolean | Признак наднациональной рамки |
| `supranational_framework` | string\|null | Идентификатор рамки (`"eu"` или `null`) |
| `notes` | string | Произвольные комментарии |

> Отсутствует у России (только 1A и 1B собраны в пилоте).

#### `venues_list.json`

Плоский список площадок юрисдикции. Используется как входной список для Level 2.

```json
{
  "jurisdiction": "United Kingdom",
  "venues": [
    {
      "name_english": "London Stock Exchange – Main Market",
      "name_local": "...",
      "type": "Regulated Market",
      "tiers": ["Equity Shares – Commercial Companies (ESCC)", "..."]
    }
  ]
}
```

#### `1A_architecture.json`, `1B_institutional.json`, `1C_venues.json`

Сырые результаты отдельных запросов Parallel API (подзадачи Level 1). Viewer напрямую не читает эти файлы — они источник для `jurisdiction_card.json`.

---

### 3.2 Level 2 — профиль площадки (venue)

Путь: `03_data/countries/{jurisdiction_ru}/level_2/{venue_key}/`

#### `venue_card.json`

Детальная карточка торговой площадки. Основной файл для страницы venue в UI.

**Ключевые поля:**

| Поле | Тип | Описание |
|------|-----|----------|
| `venue_key` | string | Технический ключ площадки, совпадает с именем папки |
| `venue_name_english` | string | Название площадки (EN) |
| `venue_name_local` | string | Название на местном языке |
| `venue_name_ru` | string | Название на русском |
| `jurisdiction` | string | Юрисдикция (EN) |
| `jurisdiction_ru` | string | Юрисдикция (RU) |
| `venue_type` | string | `"regulated_market"` \| `"MTF"` \| `"OTF"` |
| `operator` | string | Название оператора площадки |
| `issuer_eligibility_separate` | boolean | Отдельная процедура eligibility эмитента |
| `issuer_eligibility_authority` | string | Кто выдаёт eligibility |
| `secondary_listing_regime` | boolean | Наличие режима вторичного листинга |
| `listing_architecture` | string | `"split"` \| `"unified"` |
| `tiers` | array | Тиры площадки (может быть пустым при flat-структуре) |
| `segments` | array[object] | Сегменты (альтернатива тирам) |
| `instrument_coverage` | array[object] | Покрытие инструментов |
| `regime_modifiers` | array[object] | Модификаторы режима (например, `"shell_company"`) |
| `key_rulebook_references` | string | Ссылки на регуляторные документы |
| `notes` | string | Примечания (EN) |
| `notes_ru` | string | Примечания (RU) |

**Объект `instrument_coverage`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `instrument_class` | string | `"equity"` \| `"bond"` \| `"fund"` \| `"depositary_receipt"` |
| `regime_name` | string | Название режима |
| `distinct_regime` | boolean | Отдельный режим вторичного допуска |
| `admission_path` | string\|null | `null` (стандарт) \| `"trading_only"` (ATT) |
| `secondary_admission_applicable` | boolean | Применимость вторичного допуска |
| `legacy` | boolean | Закрытый/переходный сегмент |
| `segment` | string\|null | Принадлежность к сегменту |
| `modifiers` | array[string] | Применимые модификаторы режима |
| `notes` | string | Примечания |

#### `cells_list.json`

Список ячеек (cells) для данной площадки. Это центральный реестр единиц измерения пайплайна.

**Структура файла:**

```json
{
  "venue_key": "LSE_Main_Market",
  "jurisdiction_ru": "Великобритания",
  "generated_at": "2026-03-10T07:38:27.727043+00:00",
  "cells": [...]
}
```

> Viewer читает через `data_loader.load_cells_list()`, который прозрачно обрабатывает как `{"cells": [...]}`, так и plain-array формат.

**Объект ячейки:**

| Поле | Тип | Описание |
|------|-----|----------|
| `cell_id` | string | Уникальный ID ячейки (до 50 символов) |
| `venue_key` | string | Ключ площадки |
| `tier` | string | Название тира/сегмента |
| `instrument_class` | string | Класс инструмента |
| `secondary_admission_applicable` | boolean | Применимость вторичного допуска |
| `distinct_regime` | boolean | Отдельный режим |
| `legacy` | boolean | Признак закрытого сегмента |
| `admission_path` | string\|null | Путь допуска |
| `segment` | string\|null | Сегмент площадки |
| `modifiers` | array[string] | Модификаторы |
| `prompts` | object | Пути к файлам промптов `{"3A": "...", "3B": "...", "3C": "..."}` |

> Поля `prompts.3B` и `prompts.3C` могут быть `null` для legacy-ячеек.

#### `2A_structure.json`

Сырой результат запроса Parallel API по структуре площадки. Не используется Viewer напрямую.

---

### 3.3 Level 3 Phase 1 — сырые исследовательские данные

Путь: `03_data/countries/{jurisdiction_ru}/level_3/{venue_key}/{cell_id}/`

Одна папка = одна ячейка. Содержит до 6 файлов (3 сырых + 3 валидации).

#### `3A_raw.json` — первичный допуск

Содержит данные о требованиях первичного допуска к листингу.

```json
{
  "cell_id": "GB_LSE_Main_Market_equity_shares_commercial_compa_equity",
  "venue_key": "LSE_Main_Market",
  "instrument_class": "equity",
  "query_type": "3A",
  "tier_name_from_parallel": "Equity Shares (Commercial Companies)",
  "retrieved_at": "2026-03-10T12:24:10.581058+00:00",
  "content": {
    "admission_overview": {"description": "...", "source": "..."},
    "eligibility_requirements": {"description": "...", "source": "..."},
    "instrument_requirements": {"description": "...", "source": "..."},
    "procedure_and_timeline": {"description": "...", "source": "..."},
    "disclosure_at_admission": {"description": "...", "source": "..."},
    "secondary_admission": {"description": "...", "source": "..."},
    "special_regimes": {"description": "...", "source": "..."},
    "restrictions_and_lock_ups": {"description": "...", "source": "..."},
    "sponsor_and_infrastructure": {"description": "...", "source": "..."},
    "common_requirements_common": {"description": "...", "source": "..."},
    "additional_findings": {"description": "...", "source": "..."}
  }
}
```

#### `3B_raw.json` — негативные аспекты

Данные о требованиях поддержания листинга, основаниях приостановки и делистинга. Структура аналогична 3A.

#### `3C_raw.json` — мониторинг и enforcement

Данные о надзоре, санкциях и регуляторной дисциплине. Структура аналогична 3A.

**Примечание по legacy-ячейкам:** ячейки с `legacy: true` получают только 3A (только исторические данные), файлы 3B и 3C отсутствуют.

#### `3A_validation.json`, `3B_validation.json`, `3C_validation.json`

Результат автоматической валидации сырых данных.

```json
{
  "cell_id": "GB_LSE_Main_Market_equity_shares_commercial_compa_equity",
  "query_type": "3A",
  "scope_ok": true,
  "scope_issues": [],
  "completeness_score": 1.0,
  "missing_topics": [],
  "source_ok": false,
  "suspicious_sources": ["source 1", "source 2"],
  "validation_status": "yellow",
  "notes": "..."
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `scope_ok` | boolean | Данные покрывают нужный scope |
| `scope_issues` | array[string] | Описание проблем со scope |
| `completeness_score` | float | Полнота от 0.0 до 1.0 |
| `missing_topics` | array[string] | Отсутствующие темы |
| `source_ok` | boolean | Источники верифицированы |
| `suspicious_sources` | array[string] | Список подозрительных источников |
| `validation_status` | string | `"green"` \| `"yellow"` \| `"red"` |
| `notes` | string | Комментарии валидатора |

---

### 3.4 Level 3 Phase 1 — параллельные сырые данные (вспомогательные)

Путь: `03_data/countries/{jurisdiction_ru}/level_3/{venue_key}/_parallel_raw/`

Файлы вида `{venue_key}_{instrument_class}_{3A|3B|3C}_raw.json`. Это промежуточные артефакты — агрегированные ответы Parallel API до разбивки по ячейкам. Viewer напрямую не читает эти файлы.

---

### 3.5 Level 3 Phase 2 — нормализованные параметры (группы)

Путь: `03_data/countries/{jurisdiction_ru}/level_3/_groups/{group_id}/`

Группы формируются по ключу `jurisdiction × market_type × instrument_class × admission_path_type`.

#### `group_meta.json`

Метаданные группы и список входящих ячеек.

```json
{
  "group_id": "United_Kingdom_regulated_market_equity_standard",
  "name_ru": "Великобритания",
  "name_en": "United Kingdom",
  "market_type": "regulated_market",
  "instrument_class": "equity",
  "admission_path_type": "standard",
  "cells": [
    {
      "cell_id": "GB_LSE_Main_Market_equity_shares_commercial_compa_equity",
      "venue_key": "LSE_Main_Market",
      "tier": "Equity Shares (Commercial Companies)",
      "valid_qts": ["3A", "3B", "3C"],
      "excluded_qts": []
    }
  ]
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `group_id` | string | Уникальный ID группы |
| `market_type` | string | `"regulated_market"` \| `"MTF"` \| `"OTF"` |
| `instrument_class` | string | Класс инструмента группы |
| `admission_path_type` | string | `"standard"` \| `"att"` \| `"distinct"` |
| `cells[].valid_qts` | array | Типы запросов, включённые в группу |
| `cells[].excluded_qts` | array | Типы запросов, исключённые (пустые для данной ячейки) |

#### `pass1.json`

Результат Pass 1 — фреймворк параметров для всей группы. Определяет, какие параметры применимы в данной юрисдикции × market_type × instrument_class.

```json
{
  "group_id": "United_Kingdom_regulated_market_equity_standard",
  "instrument_class": "equity",
  "parameters": [
    {
      "parameter_id": "П01",
      "parameter_name": "Free float / Public float / Shares in public hands",
      "status": "applicable",
      "description": "...",
      "note": ""
    }
  ]
}
```

Возможные статусы параметра:

| Статус | Значение |
|--------|----------|
| `"applicable"` | Параметр применим, данные найдены |
| `"not_applicable"` | Параметр не применим для данного инструмента/рынка |
| `"data_not_found"` | Параметр применим, но данные не обнаружены |

#### `pass1_unknowns.json`

Список параметров, которые пайплайн нашёл в данных, но не смог сопоставить со словарём (для ручной ревизии). Не используется Viewer.

```json
[
  {
    "category": "B",
    "candidate_id": "CANDIDATE_01",
    "description": "...",
    "evidence": "..."
  }
]
```

Категории: A (маппируется на существующий параметр), B (кандидат на новый параметр), C (не является параметром).

#### `3P_raw.json`

Результат доразведки параметров (Parallel API). Содержит детализированную информацию по каждому параметру на уровне группы.

```json
[
  {
    "parameter_id": "П01",
    "definition_and_value": "...",
    "calculation_methodology": "...",
    "exclusions_and_inclusions": "...",
    "alternatives": "...",
    "variations": "...",
    "linked_requirements": "...",
    "differences_across_phases": "..."
  }
]
```

#### `3P_prompt.txt`, `3P_schema.json`

Промпт и JSON-схема, использованные при запросе доразведки. Служебные артефакты, Viewer не читает.

---

### 3.6 Level 3 Phase 2 — значения параметров по ячейке

Путь: `03_data/countries/{jurisdiction_ru}/level_3/{venue_key}/{cell_id}/`

#### `pass2.json`

Извлечённые значения параметров для конкретной ячейки. Язык — английский.

```json
{
  "cell_id": "GB_LSE_Main_Market_equity_shares_commercial_compa_equity",
  "group_id": "United_Kingdom_regulated_market_equity_standard",
  "parameter_values": [
    {
      "parameter_id": "П01",
      "parameter_name": "Free float / Public float / Shares in public hands",
      "lifecycle_phase": "admission",
      "value": "At least 10% of the class must be in public hands at admission.",
      "calculation_methodology": "...",
      "alternatives": "...",
      "variations": "...",
      "linkages": ["П17", "П14"],
      "source": "UKLR 5.5.2R–5.5.3R; LSE ADS",
      "drill_down_applied": true,
      "status": "found",
      "note": "..."
    }
  ]
}
```

**Ключевые поля объекта параметра:**

| Поле | Тип | Описание |
|------|-----|----------|
| `parameter_id` | string | ID параметра из словаря (П01–П35+) |
| `parameter_name` | string | Название параметра |
| `lifecycle_phase` | string | Фаза жизненного цикла (см. ниже) |
| `value` | string | Конкретное значение/требование |
| `calculation_methodology` | string | Методология расчёта |
| `alternatives` | string | Альтернативные пути соответствия |
| `variations` | string | Вариации по типу эмитента |
| `linkages` | array[string] | Связанные параметры |
| `source` | string | Источник (нормативный документ + статья) |
| `drill_down_applied` | boolean | Применялась ли доразведка (3P) |
| `status` | string | `"found"` \| `"not_found"` \| `"not_applicable"` |
| `note` | string | Дополнительные комментарии |

**Значения `lifecycle_phase`:**

| Значение | Описание |
|----------|----------|
| `"admission"` | Требования при первичном допуске |
| `"continuing"` | Требования поддержания после допуска |
| `"delisting"` | Условия исключения с торгов |
| `"multiple"` | Общие требования без фазовой специфики |

> Один параметр может присутствовать несколько раз с разными `lifecycle_phase`.

#### `pass2_ru.json`

Идентичная структура с `pass2.json`, но текстовые поля (`value`, `calculation_methodology`, `alternatives`, `variations`, `note`) переведены на русский язык. Поля `source` и `parameter_name` сохранены в оригинале.

Viewer предпочитает `pass2_ru.json`, при его отсутствии — `pass2.json`.

---

### 3.7 Level 4 — регуляторные цели и реформы

Путь: `03_data/countries/{jurisdiction_ru}/level_4/`

#### `level4.json`

Аналитические данные о регуляторной политике юрисдикции.

```json
{
  "jurisdiction": "United Kingdom",
  "problems": [
    {
      "description": "...",
      "description_ru": "...",
      "articulated_by": "regulator",
      "period": "2015–2021",
      "source": "URL"
    }
  ],
  "contradictions": [
    {
      "objective_a": "Investor protection",
      "objective_b": "Attracting issuers",
      "resolution": "...",
      "resolution_ru": "...",
      "period": "2013–2024",
      "source": "URL"
    }
  ],
  "parameters_as_tools": [
    {
      "parameter": "...",
      "usage": "...",
      "usage_ru": "...",
      "period": "...",
      "source": "URL"
    }
  ],
  "reforms": [
    {
      "description": "...",
      "description_ru": "...",
      "driver": "...",
      "period": "...",
      "source": "URL"
    }
  ]
}
```

**Разделы:**

| Раздел | Описание |
|--------|----------|
| `problems` | Проблемы, признанные регулятором |
| `contradictions` | Противоречия между регуляторными целями и их разрешение |
| `parameters_as_tools` | Использование параметров как инструментов политики |
| `reforms` | Реформы с описанием драйверов и периодов |

#### `level4_validation.json`

```json
{
  "jurisdiction": "Великобритания",
  "validation_status": "green",
  "section_counts": {
    "problems": 6,
    "contradictions": 4,
    "parameters_as_tools": 8,
    "reforms": 8
  },
  "notes": "..."
}
```

#### `4A_raw.json`

Сырой ответ Parallel API по Level 4. Viewer не читает напрямую.

---

### 3.8 Наднациональная рамка

Путь: `03_data/supranational/eu.json`

Кешированные данные о европейской регуляторной рамке. Подставляются при обработке EU-юрисдикций. Viewer не читает напрямую.

```json
{
  "framework": "eu",
  "content": "...",
  "retrieved_at": "..."
}
```

---

### 3.9 Промпты

Путь: `03_data/prompts/`

Служебные файлы, Viewer не читает. Хранятся по уровням:

- `level_1/` — промпты Level 1 (`{id}_{юрисдикция}.txt`)
- `level_2/` — промпты Level 2
- `level_3/` — промпты Level 3 Phase 1 (`{cell_id}_{3A|3B|3C}.txt`)
- `level_3_v2/` — промпты версии 2

---

### 3.10 Файлы состояния пайплайна (логи)

Путь: `04_logs/`

| Файл | Описание |
|------|----------|
| `level1_state.json` | Статусы задач Level 1 |
| `level2_state.json` | Статусы задач Level 2 |
| `level3_state.json` | Статусы задач Level 3 Phase 1 |
| `level3_v2_state.json` | Статусы Level 3 Phase 1 (версия 2) |
| `phase2_state.json` | Статусы задач Phase 2 (Pass 1, Pass 2) |
| `phase2_3p_state.json` | Статусы задач 3P-доразведки |
| `level4_state.json` | Статусы задач Level 4 |

Формат каждого файла состояния:

```json
{
  "tasks": {
    "task_key": {
      "status": "done",
      ...
    }
  }
}
```

Возможные статусы задачи: `"done"` | `"pending"` | `"error"`

---

## 4. Идентификаторы и конвенции именования

| Сущность | Пример | Формат |
|----------|--------|--------|
| `jurisdiction_ru` | `"Великобритания"` | Русское название; является ключом папки в `countries/` |
| `jurisdiction` | `"United Kingdom"` | Английское название |
| `venue_key` | `"LSE_Main_Market"` | snake_case с заглавной первой буквой; ключ папки в `level_2/` и `level_3/` |
| `cell_id` | `"GB_LSE_Main_Market_equity_shares_commercial_compa_equity"` | `{cc}_{venue_key}_{tier_slug}_{instrument_class}`, до 50 символов; ключ папки в `level_3/{venue_key}/` |
| `group_id` | `"United_Kingdom_regulated_market_equity_standard"` | `{jurisdiction_en}_{market_type}_{instrument_class}_{admission_path_type}` |
| `parameter_id` | `"П01"` | Кириллица П + двузначный номер |
| `instrument_class` | `"equity"` | `equity` \| `bond` \| `fund` \| `depositary_receipt` |
| `market_type` | `"regulated_market"` | `regulated_market` \| `MTF` \| `OTF` |
| `admission_path_type` | `"standard"` | `standard` \| `att` \| `distinct` |
| `lifecycle_phase` | `"admission"` | `admission` \| `continuing` \| `delisting` \| `multiple` |
| `query_type` | `"3A"` | `3A` \| `3B` \| `3C` |

**Коды юрисдикций (prefixes в cell_id):**

| Код | Юрисдикция |
|-----|-----------|
| `GB` | Великобритания |
| `HK` | Гонконг |
| `RU` | Россия |

**Важно:** `tier_slug` в `cell_id` может быть усечён до 35–40 символов (не является реверсируемым); для получения полного названия тира используйте поле `tier` в `cells_list.json`.

---

## 5. Система валидации

### 5.1 Трёхцветная схема (per-file)

Каждый файл `3A_validation.json`, `3B_validation.json`, `3C_validation.json` содержит поле `validation_status`:

| Статус | Условие | Интерпретация |
|--------|---------|---------------|
| `"green"` | `scope_ok = true` AND `completeness_score ≥ 0.5` AND `source_ok = true` | Данные надёжны, источники верифицированы |
| `"yellow"` | `scope_ok = true` AND `completeness_score ≥ 0.5` AND `source_ok = false` | Данные пригодны, но источники не верифицированы; отображать с пометкой |
| `"red"` | `scope_ok = false` OR `completeness_score < 0.5` | Данные ненадёжны; ячейку следует пометить как н/д |

### 5.2 Агрегированный статус ячейки

Viewer вычисляет статус всей ячейки через `data_loader.load_cell_validation_status()` по принципу worst-case из трёх файлов:

1. Если хотя бы один файл имеет статус `"red"` → ячейка `"red"`.
2. Если хотя бы один файл имеет статус `"yellow"` → ячейка `"yellow"`.
3. Если все три файла `"green"` → ячейка `"green"`.
4. Если файлы валидации отсутствуют → `"unknown"`.

### 5.3 Валидация Level 4

Файл `level4_validation.json` содержит самостоятельный `validation_status` по той же трёхцветной схеме и количество объектов в каждом разделе (`section_counts`).

---

## 6. Текущее состояние данных пилота

### 6.1 Покрытие по юрисдикциям

| Юрисдикция | L1 | L2 | L3 Phase 1 | Phase 2 | L4 |
|------------|----|----|------------|---------|-----|
| Великобритания | полный | 3 venue | полный | groups + pass2 | есть |
| Гонконг | полный | 2 venue | полный | groups + pass2 | есть |
| Россия | частичный (1A+1B) | нет | нет | нет | нет |

### 6.2 Площадки (venues) пилота

**Великобритания:**

| venue_key | Тип |
|-----------|-----|
| `LSE_Main_Market` | Regulated Market |
| `LSE_AIM` | MTF |
| `Aquis_Stock_Exchange` | MTF |

**Ячейки LSE_Main_Market (UK):**
- `GB_LSE_Main_Market_equity_shares_commercial_compa_equity`
- `GB_LSE_Main_Market_equity_shares_international_co_equity`
- `GB_LSE_Main_Market_equity_shares_transition_equity`
- `GB_LSE_Main_Market_debt_and_debtlike_securities_bond`
- `GB_LSE_Main_Market_depositary_receipts_depositary_receipt`
- `GB_LSE_Main_Market_closed_ended_investment_funds_fund`
- `GB_LSE_Main_Market_fund_sfs`
- `GB_LSE_Main_Market_admission_to_trading_only_att_equity`
- `GB_LSE_Main_Market_admission_to_trading_only_att_bond`
- `GB_LSE_Main_Market_admission_to_trading_only_att_depositary_receipt`

**LSE_AIM (UK):**
- `GB_LSE_AIM_equity`
- `GB_LSE_AIM_aim_designated_market_route_equity`

**Aquis_Stock_Exchange (UK):**
- `GB_Aquis_Stock_Exchange_equity`
- `GB_Aquis_Stock_Exchange_equity_shares_international_co_equity`
- `GB_Aquis_Stock_Exchange_equity_shares_transition_equity`
- `GB_Aquis_Stock_Exchange_bond`
- `GB_Aquis_Stock_Exchange_depositary_receipt`
- `GB_Aquis_Stock_Exchange_fund`

**Гонконг:**

| venue_key | Тип |
|-----------|-----|
| `HKEX_Main_Board` | Regulated Market |
| `HKEX_GEM` | MTF |

**Ячейки HKEX_Main_Board (HK):**
- `HK_HKEX_Main_Board_equity`
- `HK_HKEX_Main_Board_fund`
- `HK_HKEX_Main_Board_hdr_depositary_receipt`
- `HK_HKEX_Main_Board_debt_securities_retailpublic_m_bond`
- `HK_HKEX_Main_Board_chapter_37_debt_professional_i_bond`
- `HK_HKEX_Main_Board_chapter_19c_secondary_listing_equity`

**HKEX_GEM (HK):**
- `HK_HKEX_GEM_equity`
- `HK_HKEX_GEM_bond`

### 6.3 Группы Phase 2

**Великобритания (_groups):**
- `United_Kingdom_regulated_market_equity_standard`
- `United_Kingdom_regulated_market_equity_att`
- `United_Kingdom_regulated_market_equity_distinct`
- `United_Kingdom_MTF_equity_standard`
- `United_Kingdom_MTF_equity_distinct`
- `United_Kingdom_regulated_market_bond_standard`
- `United_Kingdom_regulated_market_bond_att`
- `United_Kingdom_regulated_market_depositary_receipt_standard`
- `United_Kingdom_regulated_market_depositary_receipt_att`
- `United_Kingdom_regulated_market_fund_standard`
- `United_Kingdom_regulated_market_fund_att`

**Гонконг (_groups):**
- `Hong_Kong_regulated_market_equity_standard`
- `Hong_Kong_regulated_market_equity_distinct`
- `Hong_Kong_regulated_market_bond_standard`
- `Hong_Kong_regulated_market_bond_distinct`
- `Hong_Kong_regulated_market_depositary_receipt_standard`
- `Hong_Kong_regulated_market_fund_standard`

---

## 7. Что читает текущий Viewer

Viewer (Streamlit) использует `data_loader.py` для чтения следующих файлов:

| Файл | Функция загрузки | Назначение |
|------|-----------------|-----------|
| `level_1/jurisdiction_card.json` | `load_jurisdiction_card(name_ru)` | Шапка юрисдикции |
| `level_2/{venue_key}/venue_card.json` | `load_venue_card(name_ru, venue_key)` | Карточка площадки |
| `level_2/{venue_key}/cells_list.json` | `load_cells_list(name_ru, venue_key)` | Список ячеек площадки |
| `level_3/{venue_key}/{cell_id}/{qt}_raw.json` | `load_l3_result(...)` | Сырые данные ячейки |
| `level_3/{venue_key}/{cell_id}/{qt}_validation.json` | `load_cell_validation_status(...)` | Статус валидации |
| `level_3/{venue_key}/{cell_id}/pass2_ru.json` или `pass2.json` | `load_pass2_data(...)` | Значения параметров (RU предпочтительно) |
| `level_4/level4.json` | `load_level4_data(name_ru)` | Регуляторные цели |
| `level_4/level4_validation.json` | `load_level4_validation(name_ru)` | Валидация L4 |
| `04_logs/level3_state.json` | `load_level3_state()` | Статус выполнения задач L3 (fallback) |

**Логика определения статуса ячейки (`get_l3_status`):**

1. Если файл `{qt}_raw.json` существует на диске → статус `"done"`.
2. Если запись в `level3_state.json` имеет статус, отличный от `"done"` → статус `"pending"`.
3. Иначе → `"not started"`.

Filesystem является ground truth: наличие файла на диске всегда приоритетнее state.json.

---

## 8. Примечания и ограничения

### 8.1 Именование папок

- Ключ папки юрисдикции — **русское** название (`Великобритания`, `Гонконг`, `Россия`). При построении путей необходимо использовать `jurisdiction_ru`, а не `jurisdiction`.
- Ключ папки venue — `venue_key` (например, `LSE_Main_Market`). Совпадает с полем в `venue_card.json` и `cells_list.json`.
- Ключ папки ячейки — `cell_id`. Может содержать усечённый tier_slug; для отображения имени тира читайте из `cells_list.json`.

### 8.2 Двойная версия cells_list.json

`data_loader.load_cells_list()` обрабатывает два формата:
- Plain array: `[{cell}, ...]`
- Envelope object: `{"cells": [...], "venue_key": "...", ...}`

При обращении напрямую к файлу учитывайте оба варианта.

### 8.3 Отсутствие файлов — нормальное состояние

- Для legacy-ячеек отсутствие `3B_raw.json` и `3C_raw.json` — штатная ситуация.
- Для ячеек с `admission_path = "trading_only"` набор файлов может отличаться.
- Отсутствие `pass2.json` и `pass2_ru.json` означает, что Phase 2 для ячейки не выполнена.
- Отсутствие `jurisdiction_card.json` (как у России) означает незавершённость Level 1.

### 8.4 Параметры — кириллические идентификаторы

`parameter_id` содержит кириллическую букву «П» (не латинскую «P»). Сортировка и сравнение должны учитывать Unicode. Диапазон текущего словаря: П01–П35+.

### 8.5 Множественные строки pass2 на параметр

Один и тот же `parameter_id` может встречаться в `parameter_values` несколько раз с разными `lifecycle_phase`. При отображении в таблице группируйте по параметру с раскрытием фаз, либо отображайте отдельные строки.

### 8.6 pass2 vs pass1 — соотношение

`pass1.json` задаёт фреймворк параметров на уровне группы (применимость). `pass2.json` содержит конкретные значения на уровне ячейки. Для отображения статуса «применим / н/п / не найден» для конкретной ячейки используйте `pass2.parameter_values[].status`, а не `pass1.parameters[].status`.

### 8.7 Россия — ограниченные данные

Для России доступны только `1A_architecture.json` и `1B_institutional.json`. Файлы `jurisdiction_card.json`, `venues_list.json`, Level 2, Level 3, Level 4 отсутствуют. При попытке загрузить их `data_loader` вернёт `None`.

### 8.8 Файлы состояния пайплайна

Файлы `*_state.json` в `04_logs/` обновляются пайплайном в процессе работы. При параллельном запуске возможны гонки данных. Для чтения состояния ячейки в UI используйте filesystem-first подход (как реализовано в `get_l3_status`).

### 8.9 Источники (source) в pass2

Поле `source` содержит ссылки на нормативные документы в виде строки (например, `"UKLR 5.5.2R–5.5.3R; LSE ADS"`). Это не URL, а citation в стиле юридических ссылок. Для гиперссылок потребуется дополнительный маппинг.
