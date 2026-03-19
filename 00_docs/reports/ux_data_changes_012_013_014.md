# Отчёт для UX-разработчика: изменения в данных (Tasks 012, 013, 014)

**Дата:** 2026-03-16
**От:** Tech Lead (пайплайн)
**Кому:** UX-разработчик (интерфейс)

---

## Task 012: L1/L2 Normalizations

### Новые поля в `jurisdiction_card.json` (L1)

**Путь:** `03_data/countries/{jurisdiction_ru}/level_1/jurisdiction_card.json`

#### `legal_family` — нормализован к lowercase enum

Поле уже существовало. Нормализовано к нижнему регистру. Допустимые значения: `"common law"` | `"civil law"` | `"mixed"`.

Пример:
```json
{ "legal_family": "civil law" }
```

#### `market_type` — новое поле (DM/EM)

Добавлено во все jurisdiction_card.json. Все текущие юрисдикции получили значение `"DM"` (Developed Market).

```json
{ "market_type": "DM" }
```

#### `listing_authority_short` — новое поле (короткое название органа листинга)

Добавлено во все jurisdiction_card.json, где `listing_authority` не пусто. Короткое название органа листинга (≤30 символов).

Примеры ожидаемых значений:
- Великобритания: `"FCA"`
- Германия: `"Börsengeschäftsführung"`
- Гонконг: `"SEHK"`
- Сингапур: `"SGX-ST"`
- Франция: `"Euronext Paris"`

```json
{ "listing_authority_short": "FCA" }
```

### Изменения в `venue_card.json` (L2)

**Путь:** `03_data/countries/{jurisdiction_ru}/level_2/{venue_key}/venue_card.json`

#### `venue_type` — нормализован к lowercase enum

Поле существовало. Нормализованы значения:
- `"MTF"` → `"mtf"`
- `"OTF"` → `"otf"`
- `"other"` (немецкие Freiverkehr площадки) → `"exchange_regulated"`
- `"regulated_market"` → без изменений

Затронутые venue:
- LSE_AIM, Tradegate_Berlin_Stock_Exchange, Aquis_Exchange_Europe, Euronext_Access_Paris, Euronext_Growth_Paris, MTS_France: `"MTF"` → `"mtf"`
- BÖAG_Börsen, Börse_München, Börse_Stuttgart: `"other"` → `"exchange_regulated"`

---

## Task 013: L4 Timeline Labels + articulated_by Normalization

### `label` — новое поле в записях L4

**Путь:** `03_data/countries/{jurisdiction_ru}/level_4/level4.json`

В каждую запись в `problems[]`, `contradictions[]`, `parameters_as_tools[]`, `reforms[]` добавлено поле `label` — короткое русскоязычное описание ≤35 символов для отображения на таймлайне.

**Было:**
```json
{
  "description_ru": "Федеральное правительство...",
  "articulated_by": "government"
}
```

**Стало:**
```json
{
  "description_ru": "Федеральное правительство...",
  "articulated_by": "government",
  "label": "Реформа листинга 2022–2024"
}
```

### `articulated_by` — нормализован к enum

Нормализованы значения:
- `"industry"` → `"market_participants"`
- Остальные значения (`"government"`, `"regulator"`, `"academic"`, `"exchange"`, `"market_participants"`) — без изменений

Допустимые значения после нормализации:
`"government"` | `"regulator"` | `"academic"` | `"market_participants"` | `"exchange"`

---

## Task 014: Классификация источников по типу

### Новое поле `type` в объектах источников

**Затронутые файлы:**
```
03_data/countries/{jurisdiction_ru}/level_1/jurisdiction_card.json  → sources[]
03_data/countries/{jurisdiction_ru}/level_2/{venue_key}/venue_card.json  → sources[]
03_data/countries/{jurisdiction_ru}/level_4/level4.json  → sources[]
```

Добавлено поле `type` к каждому объекту источника.

**Было:**
```json
{
  "url": "https://legislation.gov.uk/...",
  "title": "Financial Services and Markets Act 2000",
  "field": "content",
  "excerpts": []
}
```

**Стало:**
```json
{
  "url": "https://legislation.gov.uk/...",
  "title": "Financial Services and Markets Act 2000",
  "field": "content",
  "excerpts": [],
  "type": "legislation"
}
```

**Допустимые значения `type`:**

| Тип | Описание | Примеры доменов |
|-----|----------|-----------------|
| `legislation` | Официальные законодательные базы | legislation.gov.uk, legifrance.gouv.fr, gesetze-im-internet.de |
| `rulebook` | Биржевые правила, регуляторные своды правил | handbook.fca.org.uk, rulebook.sgx.com, euronext.com, asx.com.au |
| `government` | Публикации регуляторов и госорганов | fca.org.uk, bafin.de, mas.gov.sg, sfc.hk, asic.gov.au |
| `consultation` | Консультативные документы | URLs с путём, содержащим "consultation" |
| `research` | Научные/исследовательские публикации | oecd.org, worldbank.org, bis.org |
| `other` | Прочие источники | Юридические фирмы, новостные сайты |

---

## Итог: полная схема источника после Tasks 007, 014

```json
{
  "url": "https://handbook.fca.org.uk/handbook/UKLR/5/5.html",
  "title": "UK Listing Rules — Chapter 5",
  "field": "eligibility_requirements",
  "excerpts": ["Rule 5.5.2R: At least 10% of shares must be in public hands..."],
  "type": "rulebook"
}
```
