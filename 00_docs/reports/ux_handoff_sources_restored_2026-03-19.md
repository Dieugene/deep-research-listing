# Отчёт для UX-разработчика: восстановление источников и выдержек

**Дата:** 2026-03-19 (v2 — скорректирован после устранения дублирования)
**От:** Tech Lead (пайплайн)
**Кому:** UX-разработчик (02_src/interface/)

---

## Контекст

Аудит пайплайна выявил, что ~70% источников и выдержек из Parallel API терялись при переносе в файлы пайплайна. Причины: дедупликация по URL, фильтрация «orphaned» citations, потеря привязок к секциям. Все проблемы исправлены, данные восстановлены.

Дополнительно устранено дублирование: citations для L3 хранятся строго в одном месте (`_parallel_raw/`), без копирования в cell-директории или matrix.json.

---

## Итоговые цифры

| Уровень | Сырые citations | Сырые excerpts | Результат citations | Результат excerpts | Retention |
|---------|----------------|----------------|--------------------|--------------------|-----------|
| L1 | 607 | 1 331 | 555 | 1 244 | 91.4%* |
| L2 | 78 | 35 | 78 | 35 | 100% |
| L3 | 3 720 | 14 874 | 3 720 | 14 874 | 100% |
| L4 | 203 | 0 | 203 | 0 | 100% |
| **Итого** | **4 608** | **16 240** | **4 556** | **16 153** | **98.9%** |

*L1 дельта: Россия (-52 cit, -87 exc) — нет jurisdiction_card.json.

---

## Где источники/выдержки расположены

### Ключевая таблица для бэкенда

| Уровень | Что читать | Путь | Поле |
|---------|-----------|------|------|
| **L1** | Источники юрисдикции | `{jur}/level_1/jurisdiction_card.json` | `sources[]` |
| **L2** | Источники площадки | `{jur}/level_2/{venue}/venue_card.json` | `sources[]` |
| **L3** | Источники по venue x instrument x query | `{jur}/level_3/{venue}/_parallel_raw/{venue}_{instrument}_{query}_raw.json` | `citations[]` |
| **L3** | Контент ячейки (текст, description_ru) | `{jur}/level_3/{venue}/{cell_id}/matrix.json` | `matrix[phase][type].content[]` |
| **L3** | Параметры | `{jur}/level_3/{venue}/{cell_id}/pass2_ru.json` | `parameter_values[]` |
| **L4** | Источники анализа | `{jur}/level_4/level4.json` | `sources[]` |
| **L4** | Per-record источники | `{jur}/level_4/level4.json` | `reforms[].sources[]`, `problems[].sources[]`, etc. |

### L3: важные пояснения

**Источники L3 живут в `_parallel_raw/`, НЕ в cell-директориях и НЕ в matrix.json.**

Причина: Parallel API запрашивается на уровне venue x instrument_class (например, «LSE Main Market / equity»). Один запрос может порождать несколько ячеек (тиров). Citations принадлежат всему запросу, а не конкретному тиру. Копировать их в каждую ячейку — мультипликация.

**Маппинг _parallel_raw файл -> ячейки:**

Файл `_parallel_raw/LSE_Main_Market_equity_3A_raw.json` содержит citations для ВСЕХ equity-ячеек LSE Main Market (например, `equity_shares_commercial_compa_equity`, `equity_shares_international_co_equity`, `equity_shares_transition_equity`).

Для определения, какие ячейки обслуживает файл:
- `instrument_class` в файле (например, `"equity"`)
- Все cell-dir с тем же `instrument_class` в том же venue — обслуживаются этим файлом

**Имя файла:** `{venue_key}_{instrument_class}_{query_type}_raw.json`
- `query_type`: `3A` (допуск), `3B` (поддержание/приостановка/исключение), `3C` (мониторинг/санкции)

### Файлы cell-директорий (что в них осталось)

Cell-dir `3A/3B/3C_raw.json` содержат только:
- `cell_id`, `venue_key`, `instrument_class`, `query_type`
- `tier_name_from_parallel`, `retrieved_at`
- `content` — контент конкретного тира (распакован из общего venue-ответа)

**НЕ содержат:** `parallel_output`, `citations`, `sources` — эти данные в `_parallel_raw/`.

`matrix.json` содержит:
- `matrix[phase][type].content[]` — контент, распределённый по матрице 4x5 (description, description_ru, subtitle)
- `matrix[phase][type].citations[]` — **пустой** (citations живут в _parallel_raw)

---

## Структура citation/source объекта

### В `jurisdiction_card.json`, `venue_card.json`, `level4.json` (`sources[]`):

```json
{
  "url": "https://...",
  "title": "Document Title",
  "field": "content",
  "excerpts": ["excerpt text 1", "excerpt text 2"],
  "confidence": "high",
  "type": "rulebook"
}
```

### В `_parallel_raw/*_raw.json` (`citations[]`):

```json
{
  "url": "https://handbook.fca.org.uk/...",
  "title": "FCA Handbook",
  "field": "instrument_requirements",
  "excerpts": ["Rule 5.5.2R: At least 10%..."],
  "confidence": "high",
  "type": "rulebook"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `url` | string | URL источника |
| `title` | string | Заголовок документа |
| `field` | string | К какой секции контента относится (`tiers`, `common_requirements`, `instrument_requirements`, etc.) |
| `excerpts` | string[] | Выдержки из документа (может быть пустым) |
| `type` | string | `legislation` / `rulebook` / `government` / `consultation` / `research` / `other` |
| `confidence` | string | `high` / `medium` / `low` — уровень уверенности Parallel API |

---

## Новые поля

### `confidence` в citations/sources

Добавлено при extraction из Parallel API basis. Корреляция: `high` = есть excerpts, `low` = нет excerpts.

### `reasoning` в content секциях

Cell-dir `3A/3B/3C_raw.json` содержат `reasoning` в секциях content:

```json
{
  "content": {
    "instrument_requirements": {
      "description": "...",
      "description_ru": "...",
      "source": "...",
      "reasoning": "The analysis was derived from FCA Handbook..."
    }
  }
}
```

Обоснование исследования — почему Parallel API пришёл к данному выводу. Можно показывать как tooltip или expandable блок.

---

## 1B данные восстановлены для UK, HK, RU

`1B_institutional.json` для Великобритании, Гонконга и России были legacy-импортами без `parallel_output`. Перезапрошены через Parallel API:

| Юрисдикция | Citations | Excerpts |
|------------|----------|----------|
| Великобритания | 39 | 109 |
| Гонконг | 26 | 95 |
| Россия | 32 | 87 |

Данные включены в `jurisdiction_card.json` для UK и HK (для RU — нет jurisdiction_card.json).

---

## Действия для бэкенда

### Обязательно:

- [ ] **L3 sources: читать из `_parallel_raw/`** — текущий бэкенд читает только cell-директории и matrix.json. Для отображения L3 citations нужно добавить чтение из `_parallel_raw/`. Маппинг: по `instrument_class` и `query_type` из cell-dir файла найти соответствующий `_parallel_raw` файл.
- [ ] **Пересчитать счётчики источников** — количество sources/citations выросло

### По необходимости:

- [ ] Использовать `confidence` для визуального индикатора достоверности
- [ ] Показать `reasoning` как tooltip рядом с секцией контента

### Что изменилось в данных:

- L1/L2/L4 `sources[]` содержат больше записей (без дедупликации по URL)
- Один URL может встречаться несколько раз с разными `field` — это корректно (один документ = источник для нескольких секций)
- L3 citations **не в matrix.json и не в cell-dir** — только в `_parallel_raw/`
- Новое поле `confidence`
- Новое поле `reasoning` в content

### Что НЕ нужно делать:

- **Не копировать** citations из `_parallel_raw` в cell-директории или matrix.json
- **Не дедуплицировать** sources по URL — каждая запись привязана к своей секции
