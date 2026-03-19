# Источники и выдержки: данные для UX-дизайна

**Дата:** 2026-03-16
**Аудитория:** UX-дизайнеры и UX-разработчик
**Цель:** Описать, какие именно данные по источникам и цитатам сейчас доступны, чтобы принять решение об их отображении

---

## Главное: что принципиально нового

### 1. Источники привязаны к конкретным блокам данных (field attribution)

У каждого источника есть поле `field` — к какому именно блоку анализа он относится. Это позволяет показывать источники **рядом с тем контентом, который они подтверждают**, а не одним общим списком в конце страницы.

### 2. Источники у каждой записи L4 (не только у юрисдикции целиком)

Каждая отдельная запись в разделах «Проблемы», «Реформы», «Противоречия», «Параметры как инструменты» имеет свои источники. Это 137 записей по 6 юрисдикциям — у каждой собственный `sources[]`.

### 3. Выдержки (excerpts) — реальный текст из первоисточников

В источниках уровней L1 и L3 хранятся дословные цитаты из нормативных документов. Это не аннотации и не пересказ — это прямые фрагменты оригинальных текстов (законов, правил биржи, регуляторных документов).

---

## Статистика покрытия

### L1 — `jurisdiction_card.json` (профиль юрисдикции)

| Показатель | Значение |
|-----------|---------|
| Всего источников (6 юрисдикций) | **384** |
| Источников с выдержками | **228** (59%) |
| Всего выдержек | **912** |
| Среднее выдержек на источник | ~4 |

Пример по Великобритании: 57 источников, 29 с выдержками, 182 выдержки.
Пример по Сингапуру: 55 источников, 35 с выдержками, 159 выдержек.

### L2 — `venue_card.json` (профиль площадки)

| Показатель | Значение |
|-----------|---------|
| Всего источников (все площадки) | **78** |
| Источников с выдержками | **21** (27%) |
| Всего выдержек | **35** |

### L3 — `3A_raw.json` / `3B_raw.json` / `3C_raw.json` (контент ячеек)

Источники хранятся в поле `citations[]` каждого raw-файла. Привязаны к конкретным секциям (`field`): `eligibility_requirements`, `instrument_requirements`, `admission_overview`, `disclosure_at_admission`, и др.

### L4 — `level4.json` (анализ: проблемы, реформы, противоречия, параметры)

| Показатель | Значение |
|-----------|---------|
| Всего записей (6 юрисдикций) | **137** |
| Записей с собственными источниками | **137** (100%) |
| Выдержек в per-record источниках | 0 (источники без excerpts — см. примечание) |

> **Примечание по excerpts в L4:** Per-record источники L4 содержат `url` и `title`, но без `excerpts` — синтез L4 происходил из нескольких входных источников одновременно, и атрибуция отдельных цитат к конкретной записи была бы ненадёжной. Основные выдержки с цитатами из первоисточников — на уровнях L1 и L3.

---

## Структура объекта источника

```json
{
  "url": "https://handbook.fca.org.uk/handbook/UKLR/22/",
  "title": "UKLR 22 — Continuing obligations",
  "field": "instrument_requirements",
  "excerpts": [
    "a sufficient number of shares will be taken to have been distributed to the public when 10% of the listed shares are in public hands",
    "treasury shares are not to be taken into consideration when calculating the number of shares of the class"
  ],
  "type": "rulebook"
}
```

| Поле | Тип | Содержимое |
|------|-----|-----------|
| `url` | string | Ссылка на первоисточник |
| `title` | string | Название документа |
| `field` | string | К какому блоку данных относится источник |
| `excerpts` | string[] | Дословные выдержки из документа |
| `type` | string | Тип документа: `legislation` / `rulebook` / `government` / `consultation` / `research` / `other` |

---

## Значения поля `field` по уровням

### L1 — профиль юрисдикции

| `field` | Что означает |
|---------|-------------|
| `"content"` | Общее содержание анализа юрисдикции |
| `"jurisdiction"` | Факты о юрисдикции (статистика, экономика) |
| `"venues"` | Сведения о торговых площадках |
| `"qualitative_factors"` | Качественные факторы (напр. у Сингапура) |
| `"operators"` | Сведения об операторах рынка |

### L3 — контент ячеек (3A/3B/3C)

| `field` | Что означает |
|---------|-------------|
| `"eligibility_requirements"` | Требования к эмитенту |
| `"instrument_requirements"` | Требования к инструменту |
| `"admission_overview"` | Общий обзор процедуры допуска |
| `"procedure_and_timeline"` | Процедура и сроки |
| `"disclosure_at_admission"` | Раскрытие информации при допуске |
| `"additional_findings"` | Дополнительные сведения |

---

## Реальные примеры

### Пример 1 — L3: выдержки из правил биржи (rulebook), привязка к секции

**Контекст:** Ячейка GB / LSE Main Market / Equity (акции) / 3A (первичный допуск)

```json
{
  "url": "https://www.handbook.fca.org.uk/handbook/UKLR/22/",
  "title": "UKLR 22 — Continuing obligations",
  "field": "instrument_requirements",
  "excerpts": [
    "a sufficient number of shares will be taken to have been distributed to the public when 10% of the listed shares are in public hands; and treasury shares are not to be taken into consideration when calculating the number of shares of the class",
    "UKLR 22.2.1 19/01/2026 R — A listed company must at all times have equity shares admitted to trading which are in the class of equity shares which are listed in the equity shares (transition) category.",
    "When further equity shares of the same class as equity shares that are listed are issued, the listed company must comply with the requirements in UKLR 3.2.2R in relation to such further equity shares."
  ],
  "type": "rulebook"
}
```

**Что это значит для дизайна:** рядом с описанием требований к инструменту (`instrument_requirements`) можно разместить аккордеон «Источники» с прямыми цитатами из UKLR 22.

---

### Пример 2 — L1: выдержки из регуляторного документа (rulebook), описание реформы

**Контекст:** Профиль юрисдикции — Великобритания

```json
{
  "url": "https://docs.londonstockexchange.com/sites/default/files/documents/uk-capital-market-reforms-faqs.pdf",
  "title": "UK Capital Market Reforms — July 2024 FAQs",
  "field": "content",
  "excerpts": [
    "In the largest change to the UK listing regime in a generation, effective as of 29 July 2024 the FCA will replace the existing Standard and Premium listing segments with a single commercial companies category and move to a disclosure-based regime.",
    "The creation of a new single Main Market category for commercial companies. Equity Shares - Commercial Companies (ESCC), replacing the Premium and Standard segments for commercial companies.",
    "On 29 July 2024, the new Equity Shares Commercial Companies and Closed Ended Investment Funds listing categories on the Main Market, will become the eligible listing categories for inclusion to the FTSE UK Index Series."
  ],
  "type": "rulebook"
}
```

---

### Пример 3 — L1: выдержка из правительственного источника (government)

**Контекст:** Профиль юрисдикции — Великобритания, блок `content`

```json
{
  "url": "https://www.fca.org.uk/firms/authorisation/wholesale-markets/mtfs-otfs",
  "title": "Multilateral trading facilities and organised trading facilities | FCA",
  "field": "content",
  "excerpts": [
    "MTFs and OTFs facilitate the arranging and execution of transactions in financial instruments on a 'multilateral system', which means any system in which multiple third-party buying and selling interests in financial instruments are able to interact in the system."
  ],
  "type": "government"
}
```

---

### Пример 4 — L4: запись «Проблема» с лейблом и собственными источниками

**Контекст:** Юрисдикция — Великобритания, раздел `problems[]`

```json
{
  "description_ru": "Британские регуляторы и политики, во главе с FCA и при поддержке Обзора листингов (Lord Hill Review), выявили структурную проблему конкурентоспособности: рынок публичного капитала Великобритании сжимался и не привлекал новых эмитентов. В качестве доказательств приводились примерно 40-процентное сокращение числа компаний по сравнению с пиком 2008 года, а также лишь около 5% доли Великобритании в глобальных IPO в 2015–2020 годах.",
  "articulated_by": "regulator",
  "period": "2015–2021",
  "label": "Повысить привлекательность листинга",
  "sources": [
    {
      "url": "http://www.fca.org.uk/publication/policy/ps21-22.pdf",
      "title": "PS21/22: Primary Market Effectiveness Review",
      "excerpts": []
    },
    {
      "url": "https://www.gov.uk/government/publications/uk-listings-review",
      "title": "UK Listings Review - GOV.UK",
      "excerpts": []
    }
  ]
}
```

**Что это значит для дизайна:** на таймлайне или карточке «проблемы» отображается `label` («Повысить привлекательность листинга»), при раскрытии — полный текст + ссылки на источники. Поле `articulated_by` указывает, кто это проблему артикулировал («regulator» = FCA, в данном случае).

---

### Пример 5 — L4: запись «Реформа» — полный объект

**Контекст:** Юрисдикция — Великобритания, раздел `reforms[]`

```json
{
  "description_ru": "В 2014 году FCA реализовала пакет мер защиты для премиального листинга компаний с контролирующими акционерами в ответ на скандалы в ENRC и Bumi. Правила ввели обязательные соглашения о взаимоотношениях между эмитентом и контролирующим акционером и закрепили механизм двойного голосования при избрании независимых директоров, чтобы усилить голос миноритариев.",
  "driver": "Minority protection following ENRC/Bumi scandals.",
  "opposition": "Sell-side and some market participants opposed mandating a majority of independent directors.",
  "year": "2014",
  "articulated_by": "regulator",
  "label": "Усилить голос миноритариев",
  "sources": [
    {
      "url": "https://cms-lawnow.com/en/ealerts/2014/05/fca-introduces-stricter-rules-for-premium-listed-companies-with-a-controlling-shareholder",
      "title": "FCA introduces stricter rules for premium listed companies with a controlling shareholder",
      "excerpts": []
    },
    {
      "url": "http://www.fca.org.uk/publication/consultation/cp13-15.pdf",
      "title": "CP13/15 Consultation Paper",
      "excerpts": []
    }
  ]
}
```

---

### Пример 6 — L4: запись «Противоречие» (два конкурирующих объектива)

**Контекст:** Юрисдикция — Великобритания, раздел `contradictions[]`

```json
{
  "objective_a": "Investor protection",
  "objective_b": "Attracting issuers",
  "resolution_ru": "В 2013–2014 годах FCA ответила на скандалы, отдав приоритет защите инвесторов (обязательные соглашения, двойное голосование по независимым директорам). Начиная с 2021 года приоритет сместился в сторону привлечения эмитентов: FCA разрешила структуры акций с двойным классом голосов и заменила деление на премиальный/стандартный сегменты единой категорией на основе раскрытий.",
  "period": "2013–2024",
  "articulated_by": "regulator",
  "label": "FCA меняет регулирование акций",
  "sources": [
    {
      "url": "http://www.fca.org.uk/publication/consultation/cp13-15.pdf",
      "title": "CP13/15 Consultation Paper",
      "excerpts": []
    },
    {
      "url": "https://www.afme.eu/publications/consultation-responses/uk-finance-afme-response-to-fca-cp2310/",
      "title": "UK Finance-AFME response to FCA CP23/10",
      "excerpts": []
    }
  ]
}
```

---

## Возможности для UX-дизайна

На основе этих данных возможны следующие паттерны:

| Паттерн | Данные | Примечание |
|---------|--------|-----------|
| **Inline-источники** рядом с секцией текста | `field` — атрибуция источника к секции | Показывать источники под каждой секцией, не в общем списке |
| **Цитата-аккордеон** | `excerpts[]` | Раскрывающийся блок с дословными цитатами из документа |
| **Бейдж типа документа** | `type` | Цветовая или иконочная маркировка: закон / правила биржи / регулятор / исследование |
| **Таймлайн проблем и реформ** | `label`, `period`/`year`, `articulated_by` | `label` — короткий заголовок ≤35 символов; `period` — ось X |
| **Источник записи** (L4) | per-record `sources[]` | Ссылки на первоисточники прямо в карточке проблемы/реформы |
| **Фильтр по типу источника** | `type` | Показывать только legislation / только rulebook |
