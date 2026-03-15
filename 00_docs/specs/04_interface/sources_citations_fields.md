# Поля sources и citations в данных пайплайна

## Что добавлено

В processed-файлы пайплайна добавлены поля с URL-ссылками на источники, которые Parallel API использовал при сборе данных. Источники извлекаются программно из `output.basis` — без участия LLM, напрямую из ответа Parallel.

---

## Структура поля

Все поля имеют одинаковую структуру — массив объектов:

```json
[
  {
    "url": "https://www.fca.org.uk/publications/...",
    "title": "PS24/6: Primary Markets Effectiveness Review",
    "field": "content"
  },
  {
    "url": "https://docs.londonstockexchange.com/...",
    "title": "ADMISSION AND DISCLOSURE STANDARDS",
    "field": "admission_overview"
  }
]
```

| Ключ | Тип | Описание |
|------|-----|----------|
| `url` | string | Прямой URL источника |
| `title` | string | Заголовок страницы/документа (может быть пустым) |
| `field` | string | Поле JSON-схемы, для которого Parallel использовал этот источник. Для текстовых запросов (1A, 4A) всегда `"content"`. |

---

## По каждому файлу

### jurisdiction_card.json

**Поле:** `sources`

**Источник:** Citations из трёх raw-файлов — `1A_architecture.json` + `1B_institutional.json` + `1C_venues.json`, объединённые с дедупликацией по URL.

**Пример:**
```json
{
  "jurisdiction": "United Kingdom",
  ...
  "sources": [
    {
      "url": "https://docs.londonstockexchange.com/.../admission-and-disclosure-standards.pdf",
      "title": "ADMISSION AND DISCLOSURE STANDARDS",
      "field": "content"
    },
    {
      "url": "https://www.fca.org.uk/publications/policy-statements/ps24-6-...",
      "title": "PS24/6: Primary Markets Effectiveness Review",
      "field": "content"
    }
  ]
}
```

**Охват:** UK — 57 источников, HK — 38 источников. Россия — нет (данные не собирались через Parallel). Для AU/SG/FR/DE — данные есть, но `jurisdiction_card.json` ещё не создан.

**Примечание:** Для UK, HK, России `1B_institutional.json` создавался через старый MD-импорт (без Parallel), поэтому source citations из 1B у этих трёх юрисдикций отсутствуют. Для всех новых юрисдикций 1B будет через Parallel.

---

### venue_card.json

**Поле:** `sources`

**Источник:** Citations из `2A_structure.json`.

**Охват:** Все 5 текущих площадок (LSE Main Market, LSE AIM, Aquis, HKEX Main Board, HKEX GEM) — 2–4 источника каждая.

**Пример:**
```json
{
  "venue_key": "LSE_Main_Market",
  ...
  "sources": [
    {
      "url": "https://docs.londonstockexchange.com/.../attachment_1_to_n1222.pdf",
      "title": "London Stock Exchange Admission and Disclosure ...",
      "field": "output"
    }
  ]
}
```

---

### level4.json

**Поле:** `sources`

**Источник:** Citations из `4A_raw.json`.

**Охват:** UK — 41 источник, HK — 23 источника.

```json
{
  "jurisdiction": "United Kingdom",
  "problems": [...],
  "reforms": [...],
  ...
  "sources": [
    {
      "url": "http://www.fca.org.uk/publication/policy/ps21-22.pdf",
      "title": "PS21/22: Primary Market Effectiveness Review",
      "field": "content"
    }
  ]
}
```

---

### L3 raw-файлы (per-cell и per-instrument-class)

**Поле:** `citations` (не `sources` — чтобы не конфликтовать с полем `content`)

**Источник:** Citations из `parallel_output.basis` в том же файле.

Два типа файлов получают поле `citations`:

**Phase 1 — per-cell файлы:**

Путь: `level_3/{venue_key}/{cell_id}/{query_type}_raw.json`

```json
{
  "cell_id": "GB_LSE_Main_Market_equity_shares_commercial_compa_equity",
  "venue_key": "LSE_Main_Market",
  "query_type": "3A",
  "content": {...},
  "citations": [
    {
      "url": "https://www.handbook.fca.org.uk/handbook/UKLR/22/",
      "title": "Fetched web page",
      "field": "instrument_requirements"
    },
    {
      "url": "https://docs.londonstockexchange.com/.../admission-and-disclosure-standards_1.pdf",
      "title": "ADMISSION AND DISCLOSURE STANDARDS",
      "field": "instrument_requirements"
    }
  ]
}
```

Здесь `field` — это конкретный раздел схемы (например, `admission_overview`, `eligibility_requirements`, `instrument_requirements` и т.д.), что позволяет показывать источник рядом с конкретным параметром.

**Phase 2 — per-instrument-class файлы:**

Путь: `level_3/{venue_key}/_parallel_raw/{venue_key}_{instrument_class}_{query_type}_raw.json`

Та же структура поля `citations`.

---

## Как использовать

### Отображение источников для юрисдикции

Блок "Источники" в нижней части карточки юрисдикции. Просто рендерим `jurisdiction_card.sources` как список ссылок:

```
• ADMISSION AND DISCLOSURE STANDARDS — docs.londonstockexchange.com
• PS24/6: Primary Markets Effectiveness Review — fca.org.uk
• New rules for the public offers and admissions to trading — fca.org.uk
```

### Источник рядом с конкретным параметром L3

Для каждого параметра в L3 можно фильтровать `citations` по совпадению `field` с названием раздела:

```js
// Показать источники для раздела "eligibility_requirements"
const fieldCitations = cell.citations.filter(c => c.field === 'eligibility_requirements');
```

### Обработка пустого title

Parallel иногда возвращает пустой `title` (если страница не передала метаданные). В этом случае рекомендуется отображать доменное имя:

```js
const display = source.title || new URL(source.url).hostname;
```

---

## Покрытие данных (текущее состояние)

### L1 — jurisdiction_card.json → поле `sources`

| Юрисдикция | sources |
|------------|---------|
| Австралия | 94 |
| Великобритания | 57 |
| Германия | 78 |
| Гонконг | 38 |
| Сингапур | 55 |
| Франция | 62 |
| Россия | — (нет jurisdiction_card.json) |

Примечание: у UK, HK, России `1B_institutional.json` создавался через старый MD-импорт (без Parallel), поэтому 1B-источники у этих трёх отсутствуют. Для AU/SG/FR/DE все три файла (1A+1B+1C) — через Parallel.

### L2 — venue_card.json → поле `sources`

| Площадка | sources |
|----------|---------|
| Australian Securities Exchange | 7 |
| Cboe Australia | 5 |
| National Stock Exchange of Australia | 4 |
| Sydney Stock Exchange | 5 |
| Aquis Stock Exchange | 4 |
| LSE AIM | 3 |
| LSE Main Market | 3 |
| BÖAG Börsen | 5 |
| Börse München | 3 |
| Börse Stuttgart | 4 |
| Frankfurt Stock Exchange | 3 |
| Tradegate / Berlin Stock Exchange | 4 |
| HKEX GEM | 4 |
| HKEX Main Board | 2 |
| SGX Mainboard and Catalist | 5 |
| Aquis Exchange Europe | 2 |
| Euronext Access Paris | 3 |
| Euronext Growth Paris | 5 |
| Euronext Paris | 3 |
| MTS France | 4 |

### L3 — raw-файлы → поле `citations`

Все площадки с L3 данными покрыты (UK, HK, AU/Sydney, SG, FR/MTS, DE/Tradegate).

### L4 — level4.json → поле `sources`

| Юрисдикция | sources |
|------------|---------|
| Австралия | 34 |
| Великобритания | 41 |
| Германия | 33 |
| Гонконг | 23 |
| Сингапур | 36 |
| Франция | 36 |

---

## Пересборка sources при необходимости

Если нужно пересобрать поля (например, после добавления новых юрисдикций):

```bash
cd D:\_workspace\deep-research-listing
venv\Scripts\python.exe tools/add_citations.py --level L1   # только L1
venv\Scripts\python.exe tools/add_citations.py              # все уровни
```

Скрипт идемпотентен — перезаписывает `sources`/`citations` при каждом запуске.
