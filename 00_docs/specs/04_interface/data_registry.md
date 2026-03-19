# Реестр расположения данных для интерфейса

**Дата:** 2026-03-19
**Назначение:** Полный справочник — откуда бэкенд должен читать каждый тип данных для отображения в интерфейсе.

---

## Level 1: Юрисдикция

### `{jur}/level_1/jurisdiction_card.json` — карточка юрисдикции

| Поле | Тип | Назначение |
|------|-----|-----------|
| `jurisdiction` | string | Название (EN) |
| `jurisdiction_ru` | string | Название (RU) |
| `legal_family` | string | `"common law"` / `"civil law"` / `"mixed"` |
| `regulator_name` | string | Название регулятора |
| `regulator_type` | string | Тип регулятора |
| `admission_architecture` | string | Архитектура допуска (EN) |
| `admission_architecture_ru` | string | Архитектура допуска (RU) — приоритет отображения |
| `listing_authority` | string | Орган листинга (полное) |
| `listing_authority_short` | string | Орган листинга (краткое, до 30 символов) |
| `market_type` | string | `"DM"` / `"EM"` |
| `market_types` | list | Типы рынка |
| `venues` | list | Список площадок (краткий) |
| `notes` | string | Примечания (EN) |
| `notes_ru` | string | Примечания (RU) — приоритет отображения |
| `supranational_flag` | bool | Принадлежность к наднациональной юрисдикции |
| `supranational_framework` | string? | Наднациональная рамка (EU и т.д.) |
| **`sources[]`** | **list[dict]** | **Источники юрисдикции (из 1A+1B+1C)** |

**Формат `sources[]`:**
```json
{
  "url": "https://...",
  "title": "Document Title",
  "field": "content",
  "excerpts": ["excerpt text"],
  "confidence": "high",
  "type": "rulebook"
}
```

### Сырые файлы L1 (НЕ для прямого отображения)

| Файл | Содержит | Назначение |
|------|----------|-----------|
| `1A_architecture.json` | `content` (текст), `parallel_output.basis[]` | Сырой ответ Parallel — архитектура |
| `1B_institutional.json` | `parallel_output.basis[]` | Сырой ответ Parallel — институциональный фреймворк |
| `1C_venues.json` | `venues[]`, `parallel_output.basis[]` | Сырой ответ Parallel — площадки |

Бэкенд читает из `jurisdiction_card.json`, не из сырых файлов.

---

## Level 2: Площадка

### `{jur}/level_2/{venue}/venue_card.json` — карточка площадки

| Поле | Тип | Назначение |
|------|-----|-----------|
| `venue_key` | string | Идентификатор площадки |
| `venue_name_english` | string | Название (EN) |
| `venue_name_local` | string | Название (локальное) |
| `venue_name_ru` | string | Название (RU) |
| `venue_type` | string | `"regulated_market"` / `"mtf"` / `"otf"` / `"exchange_regulated"` |
| `operator` | string | Оператор площадки |
| `listing_architecture` | string | Архитектура листинга |
| `tiers[]` | list | Тиры (уровни листинга) |
| `segments[]` | list | Сегменты |
| `instrument_coverage[]` | list | Покрытие инструментов |
| `notes` | string | Примечания (EN) |
| `notes_ru` | string | Примечания (RU) |
| **`sources[]`** | **list[dict]** | **Источники площадки** |

### `{jur}/level_2/{venue}/cells_list.json` — список ячеек

| Поле | Тип | Назначение |
|------|-----|-----------|
| `venue_key` | string | Идентификатор площадки |
| `cells[]` | list[dict] | Ячейки: `{cell_id, tier, instrument_class, ...}` |

---

## Level 3: Ячейка (venue × tier × instrument_class)

### Контент: `{jur}/level_3/{venue}/{cell_id}/matrix.json`

Основной источник для tab-view и matrix-view.

| Поле | Тип | Назначение |
|------|-----|-----------|
| `cell_id` | string | Идентификатор ячейки |
| `venue_key` | string | Площадка |
| `tier` | string | Тир (EN) |
| `instrument_class` | string | Класс инструмента |
| `matrix` | dict | Матрица 4x5 |
| `metadata` | dict | Статус валидации, покрытие фаз, терминология |

**Структура `matrix`:**
```json
{
  "G07_1": {
    "D01_requirements": {
      "content": [
        {
          "subtitle": "Требования к эмитенту",
          "description": "Financial History: No requirement...",
          "description_ru": "Финансовая история: требование отсутствует...",
          "source": "https://...",
          "origin_field": "eligibility_requirements"
        }
      ],
      "citations": []
    },
    "D02_procedures": { "content": [...], "citations": [] },
    "D03_monitoring": null,
    "D04_sanctions": null,
    "D05_disclosure": { "content": [...], "citations": [] }
  },
  "G07_2": { ... },
  "G07_3": { ... },
  "G07_4": { ... }
}
```

**Фазы (строки):** G07_1 (Допуск), G07_2 (Поддержание), G07_3 (Приостановка), G07_4 (Исключение)
**Типы содержания (столбцы):** D01 (Требования), D02 (Процедуры), D03 (Мониторинг), D04 (Санкции), D05 (Раскрытие)
**`null`** означает «не применимо» (например, мониторинг при допуске).

**`citations[]` в matrix.json — пустые.** L3 sources читать из `_parallel_raw/` (см. ниже).

### Маппинг фаз матрицы на файлы `_parallel_raw/`

| Фаза | Файл(ы) `_parallel_raw/` | Какие `field` в citations относятся к фазе |
|------|--------------------------|-------------------------------------------|
| G07_1 (Допуск) | `*_3A_raw.json` | все (`tiers`, `common_requirements`, `admission_overview`, `eligibility_requirements`, ...) |
| G07_2 (Поддержание) | `*_3B_raw.json` + `*_3C_raw.json` | 3B: `continuing_obligations`, `common_obligations`, `tiers`; 3C: `monitoring_regime`, `sanctions`, `enforcement_practice`, `common_monitoring`, `tiers` |
| G07_3 (Приостановка) | `*_3B_raw.json` | `suspension` |
| G07_4 (Исключение) | `*_3B_raw.json` | `delisting_compulsory`, `delisting_voluntary` |

**Почему G07_2 берёт из двух файлов:** 3B и 3C — разные запросы к Parallel API. 3B спрашивал про «негативные аспекты» (continuing obligations + suspension + delisting), 3C — про «мониторинг и enforcement». Оба содержат данные, релевантные фазе «Поддержание».

**Фильтрация citations по field:** Не все citations из файла относятся к одной фазе. Файл `*_3B_raw.json` содержит citations для G07_2, G07_3 и G07_4. Фронтенд фильтрует по `field`:
- `field=continuing_obligations` или `field=common_obligations` -> G07_2
- `field=suspension` -> G07_3
- `field=delisting_compulsory` или `field=delisting_voluntary` -> G07_4
- `field=tiers` -> относится ко всем фазам файла (общий источник для всех секций)

**Metadata:**
```json
{
  "validation_status": "green",
  "phases_covered": ["G07_1", "G07_2", "G07_3", "G07_4"],
  "phases_not_covered": [],
  "terminology": {
    "suspension_local_term": "...",
    "delisting_local_term": "..."
  }
}
```

### Источники L3: `{jur}/level_3/{venue}/_parallel_raw/{venue}_{instrument}_{query}_raw.json`

**Единственный источник citations/excerpts для L3.**

| Поле | Тип | Назначение |
|------|-----|-----------|
| `venue_key` | string | Площадка |
| `instrument_class` | string | Класс инструмента |
| `query_type` | string | `"3A"` / `"3B"` / `"3C"` |
| **`citations[]`** | **list[dict]** | **Источники с выдержками** |
| `parallel_output` | dict | Сырой ответ Parallel (basis, content) |

**Маппинг на ячейки:** Файл обслуживает ВСЕ ячейки (тиры) с совпадающим `instrument_class` в данном venue. Привязка:
- Прочитать `instrument_class` из cell-dir `3A_raw.json`
- Найти `_parallel_raw/{venue}_{instrument_class}_{query_type}_raw.json`

**Пример:** `LSE_Main_Market_equity_3A_raw.json` содержит citations для всех equity-ячеек LSE Main Market.

**3 файла на instrument_class:** `*_3A_raw.json` (допуск), `*_3B_raw.json` (поддержание), `*_3C_raw.json` (мониторинг).

### Параметры: `{jur}/level_3/{venue}/{cell_id}/pass2_ru.json`

| Поле | Тип | Назначение |
|------|-----|-----------|
| `cell_id` | string | Идентификатор ячейки |
| `tier_ru` | string | Тир (RU) — для заголовков и хлебных крошек |
| `parameter_values[]` | list[dict] | Параметры |

**Формат параметра:**
```json
{
  "parameter_id": "П01",
  "param_label_ru": "Свободный флоут",
  "value": "10%",
  "value_short": "10%",
  "lifecycle_phase": "admission",
  "section_keys": ["eligibility_requirements", "instrument_requirements"],
  "status": "found",
  "source": "UKLR 5.5.2R"
}
```

**`section_keys[]`** — к каким секциям контента относится параметр. Использовать для фильтрации: показывать параметр только под релевантной секцией.

### Контент секций: `{jur}/level_3/{venue}/{cell_id}/3A_raw.json` (3B, 3C)

| Поле | Тип | Назначение |
|------|-----|-----------|
| `cell_id` | string | Идентификатор ячейки |
| `instrument_class` | string | Для маппинга на `_parallel_raw` |
| `query_type` | string | `"3A"` / `"3B"` / `"3C"` |
| `content` | dict | Секции контента для данного тира |

**Секции content содержат:**
```json
{
  "instrument_requirements": {
    "description": "...",
    "description_ru": "...",
    "source": "текстовая ссылка",
    "reasoning": "обоснование исследования Parallel API"
  }
}
```

**НЕ содержат:** `parallel_output`, `citations` — эти данные в `_parallel_raw/`.

Бэкенд использует cell-dir raw файлы как **fallback**, если matrix.json отсутствует.

### Валидация: `{jur}/level_3/{venue}/{cell_id}/3A_validation.json` (3B, 3C)

| Поле | Тип | Назначение |
|------|-----|-----------|
| `validation_status` | string | `"green"` / `"yellow"` / `"red"` |
| `completeness_score` | float | Полнота данных (0–1) |
| `missing_topics[]` | list[string] | Пропущенные темы |
| `scope_ok` | bool | Соответствие скоупу |

---

## Level 4: Анализ юрисдикции

### `{jur}/level_4/level4.json` — аналитика

| Поле | Тип | Назначение |
|------|-----|-----------|
| `jurisdiction` | string | Юрисдикция |
| `problems[]` | list[dict] | Проблемы регуляторного фреймворка |
| `contradictions[]` | list[dict] | Противоречия |
| `parameters_as_tools[]` | list[dict] | Параметры как инструменты |
| `reforms[]` | list[dict] | Реформы |
| **`sources[]`** | **list[dict]** | **Источники анализа L4** |

**Формат записи (пример `reforms[]`):**
```json
{
  "description": "...",
  "description_ru": "...",
  "driver": "...",
  "driver_ru": "...",
  "opposition": "...",
  "opposition_ru": "...",
  "year": "2024",
  "label": "Реформа листинга 2024",
  "articulated_by": "government",
  "source": "текстовая ссылка",
  "sources": [{"url": "...", "title": "...", "type": "..."}]
}
```

**Приоритет отображения `_ru` полей:** `description_ru ?? description`, `driver_ru ?? driver`, и т.д.

Per-record `sources[]` — источники конкретной записи. Top-level `sources[]` — все источники L4.

---

## Сводная таблица: что откуда читать

| Что отображать | Файл | Поле |
|----------------|------|------|
| Карточка юрисдикции | `jurisdiction_card.json` | все top-level поля |
| L1 источники | `jurisdiction_card.json` | `sources[]` |
| Карточка площадки | `venue_card.json` | все top-level поля |
| L2 источники | `venue_card.json` | `sources[]` |
| Список ячеек | `cells_list.json` | `cells[]` |
| Контент ячейки (tab/matrix view) | `matrix.json` | `matrix[phase][type].content[]` |
| Тир (RU) | `pass2_ru.json` | `tier_ru` |
| Параметры ячейки | `pass2_ru.json` | `parameter_values[]` |
| **L3 источники/выдержки** | **`_parallel_raw/{venue}_{ic}_{qt}_raw.json`** | **`citations[]`** |
| L3 reasoning | cell-dir `3A/3B/3C_raw.json` | `content[section].reasoning` |
| Валидация ячейки | `3A/3B/3C_validation.json` | `validation_status`, `completeness_score` |
| L4 проблемы/реформы/etc | `level4.json` | `problems[]`, `reforms[]`, etc. |
| L4 источники | `level4.json` | `sources[]`, per-record `sources[]` |
