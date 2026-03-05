# Пайплайн исследования: допуск и листинг ценных бумаг

## Версия 0.2

**Дата:** 2026-03-05  
**Статус:** Рабочий документ. Подлежит проверке на пилоте (UK, Гонконг, Россия).

**Зависимости:**
- Концептуальное ядро v0 (27 понятий, 5 блоков) + патч: словарь параметров (П01–П23)
- Набор институциональных факторов v0.1 (12 факторов Ф1–Ф12, 4 блока)
- Спецификация информационной архитектуры v0.1 + патч
- Регистры операций алгоритма (основной + институциональные факторы)

---

## 1. Архитектура пайплайна

### 1.1. Общая схема

```
Предварительный этап
  Институциональные факторы из публичных датасетов — по всем 47 юрисдикциям
  ~5 укрупнённых запросов (Parallel, JSON schema)
    ↓
Уровень 1. Юрисдикция (47 шт.)
  1А. Архитектура допуска + маппинг архитектурных понятий
  1Б. Институциональные факторы (качественные)
  1В. Ландшафтный обзор площадок юрисдикции
  → LLM-постобработка: карточка юрисдикции, перечень площадок, перевод
    ↓
  [Если обнаружена наднациональная рамка, ранее не исследованная →
   запрос по рамке, результат сохраняется в хранилище.
   При повторных упоминаниях — ссылка на сохранённый результат.]
    ↓
Уровень 2. Площадка (65 шт.)
  2А. Детальная структура площадки
  → LLM-постобработка: карточка площадки, генерация перечня ячеек
  → LLM: формирование промптов уровня 3 на «языке» площадки
    ↓
Уровень 3. Ячейка = площадка × уровень × класс инструмента (~1000 шт.)
  3А. Первичный допуск (требования, процедуры, раскрытие) — SCHEMA
  3Б. Негативные аспекты (поддержание, приостановка, исключение) — SCHEMA, повышенная глубина
  3В. Мониторинг и enforcement — SCHEMA, повышенная глубина
  3Г. Вторичный допуск (где применимо) — SCHEMA
    ↓
Пакетная постобработка уровня 3
  Приведение массива к словарю параметров
  Перевод на русский
  Выявление кандидатов на расширение словаря
    ↓
Уровень 4. Проблемно-ориентированный анализ (47 юрисдикций)
  4А. Регуляторные цели, связь с параметрами, обоснование калибровки — TEXT
  → LLM-постобработка: блок Ж карточки юрисдикции, перевод
    ↓
Загрузка в PostgreSQL
```

### 1.2. Роли LLM в пайплайне

1. **Формирование запросов.** После уровней 1 и 2 — LLM формирует промпты последующих уровней с использованием местной терминологии (названия уровней/сегментов, номера глав rulebook, местные термины из маппинга). Промпты сохраняются в /prompts/ для воспроизводимости.

2. **Постобработка на каждом уровне.** Структурирование результатов, формирование карточек, маппинг на понятия ядра, перевод на русский.

3. **Пакетная классификация (после уровня 3).** Приведение к словарю параметров, типологизация конструкций, выявление связок — на основе полного массива.

### 1.3. Выбор формата выхода: schema vs text

**Основной принцип:** schema (JSON) используется везде, где нужна привязка источников к конкретным полям. При текстовом выходе источники оказываются в общей куче, и LLM-постобработка не может надёжно их рассортировать.

| Формат | Когда используется | Обоснование |
|--------|-------------------|-------------|
| **JSON schema** | Уровни 1Б (институциональные факторы), 1В (ландшафт площадок), 3А–3Г (все запросы по ячейке) | Источники привязаны к конкретным полям. Структура результата предсказуема. |
| **Text** (markdown с цитатами) | Уровни 1А (архитектура + маппинг), 4А (проблемно-ориентированный анализ) | Нужен связный контекст и свободное аналитическое рассуждение, структура не предопределена. |
| **Auto** (JSON, структура определяется Parallel) | Уровень 2А (структура площадки) | Структура площадок слишком различна, жёсткая schema может не подойти. |

В JSON schema для уровня 3 предусматривается поле `additional_findings` — для содержания, не покрытого предопределёнными полями схемы.

### 1.4. Промежуточное хранение

JSON-файлы на диске. После стабилизации — загрузка в PostgreSQL.

```
/results
  /supranational/          ← наднациональные рамки (EU и др., по мере обнаружения)
  /level_1_jurisdiction/   ← карточки юрисдикций
  /level_2_platform/       ← карточки площадок + перечни ячеек
  /level_3_cells/          ← сырые результаты поиска по ячейкам
  /level_3_processed/      ← результаты пакетной постобработки
  /level_4/                ← проблемно-ориентированный анализ
  /dictionary/             ← словарь параметров (текущая версия + кандидаты)
  /prompts/                ← сформированные промпты (для воспроизводимости)
```

---

## 2. Предварительный этап

### 2.1. Назначение

Сбор количественных институциональных факторов по всем 47 юрисдикциям из публичных датасетов.

### 2.2. Запросы

~5 укрупнённых запросов. Каждый запрос покрывает 1–3 фактора с общим типом источника по **всем** юрисдикциям выборки. Формат: JSON schema, где каждая юрисдикция — элемент массива.

| # | Факторы | Источник | Что ищем |
|---|---------|----------|---------|
| П1 | Ф4 (качество регулирования), Ф5 (верховенство права), Ф6 (политическая стабильность) | World Bank WGI DataBank | Значения + перцентили. Зафиксировать год. |
| П2 | Ф7 (глубина рынка — капитализация/ВВП), Ф10 (конкурентная структура площадок — доля крупнейшей) | World Bank WDI, WFE | Процентные значения. Зафиксировать год. |
| П3 | Ф2 (статутарная защита инвесторов — ASDI) | Djankov et al. (2008), обзоры реформ | Индекс 0–1. Пометка юрисдикций с реформами после 2003. |
| П4 | Ф1 (правовая семья) | LLSV, CIA Factbook | Категориальное значение (common law / civil law / смешанная / иное). |
| П5 | Ф11 (тип регулятора) | IOSCO Member List | ЦБ / комиссия / наднациональный / иной. Название регулятора. |

**Процессор:** core (данные публичные, но нужна точность по всем 47 юрисдикциям).

**Выходная JSON schema (пример для П1):**

```json
{
  "data_year": "string",
  "source_url": "string",
  "jurisdictions": [
    {
      "jurisdiction": "string",
      "regulatory_quality": { "value": "number", "percentile": "number" },
      "rule_of_law": { "value": "number", "percentile": "number" },
      "political_stability": { "value": "number", "percentile": "number" }
    }
  ]
}
```

---

## 3. Наднациональные рамки

### 3.1. Подход

**EU** исследуется один раз заранее (единственная заведомо известная рамка). Результат сохраняется в /supranational/eu.json. При запросах уровня 1 по EU-юрисдикциям — ссылка на этот результат + выжимка подставляется в промпт.

**Прочие рамки** — при исследовании юрисдикции, если обнаруживается опора на наднациональное регулирование, ранее не исследованное: запрос, результат сохраняется в /supranational/. При повторных упоминаниях (следующая юрисдикция того же объединения) — ссылка на сохранённый результат.

### 3.2. Запрос по EU

**Тип:** Deep Research, text output.  
**Процессор:** ultra.

```
Research the EU regulatory framework for securities listing and 
admission to trading. Focus on:

1. Key directives and regulations: MiFID II/MiFIR, Prospectus 
   Regulation, Transparency Directive, Market Abuse Regulation, 
   Listing Act (2024 reform).

2. For each instrument class (equities, bonds, funds, depositary 
   receipts): what requirements are set at EU level vs delegated 
   to national authorities. Distinction between regulated market 
   admission and MTF admission.

3. Minimum harmonised requirements (free float, market cap, 
   financial history, etc.).

4. National discretion: where member states can set stricter or 
   different requirements.

5. Listing Act 2024: what changed, transition timeline.

6. Third-country equivalence for listing purposes.

Cite specific articles/provisions.
```

### 3.3. Шаблон запроса по динамически обнаруженной рамке

```
Research the [FRAMEWORK NAME] regulatory framework for securities 
markets, specifically provisions related to listing and admission 
to trading on stock exchanges of member states.

1. What harmonised requirements exist at the supranational level?
2. What is delegated to national authorities?
3. Are there mutual recognition / equivalence provisions?

Cite specific legal instruments.
```

---

## 4. Уровень 1. Юрисдикция

### 4.1. Назначение

Для каждой юрисдикции: архитектура допуска, маппинг архитектурных понятий, качественные институциональные факторы, ландшафт площадок.

### 4.2. Запрос 1А: Архитектура допуска и маппинг

**Тип:** Deep Research, text output.  
**Процессор:** pro.

Маппируются архитектурные понятия ядра (5–7 штук):
- Г02 «официальный листинг» / Г03 «допуск к торгам» / Г04 «признак архитектуры допуска» — разделены или объединены
- Б03 «листинговый орган» — кто это
- Б04 «регулятор» — название, тип, закон
- А03 «тип рынка» — какие типы (regulated market, MTF, OTF, иное)
- А04 «специализированный сегмент» / А05 «уровень листинга» — как устроена сегментация
- В04 «разделение эмитент/инструмент» — единая процедура или раздельная eligibility
- Г06 «вторичный допуск» — есть ли специальный режим

**Промпт:**

```
Research the securities listing and admission to trading framework 
in [JURISDICTION].

For each question: provide official local term (original language + 
English translation), relevant legal source (law/article), 
substantive answer.

1. Are "official listing" and "admission to trading" separate legal 
   concepts, or unified? Who decides on each?

2. Who acts as the listing authority — exchange, regulator, 
   separate body? Legal basis?

3. Name and type of securities regulator (central bank / commission / 
   other)? Governing law?

4. Types of trading venues (regulated market, MTF, OTF, local 
   equivalents)? How classified in law?

5. Exchange segmentation: hierarchical listing tiers and/or 
   thematic segments? Names of specific tiers and segments.

6. Issuer eligibility separate from per-issue admission? 
   Or single procedure?

7. Special regime for secondary listing / cross-listing?

Cite specific legal acts and provisions.

[Для EU-юрисдикций: выжимка из /supranational/eu.json — 
что определено на EU-уровне, что на национальном.]
```

### 4.3. Запрос 1Б: Институциональные факторы (качественные)

**Тип:** Deep Research, JSON schema.  
**Процессор:** core.

Факторы, требующие качественной оценки:
- Ф3 «private enforcement» (частноправовая защита инвесторов)
- Ф8 «концентрация владения»
- Ф9 «структура инвесторской базы»
- Ф12 «роль биржи как СРО» (саморегулируемой организации)

Также: верификация предзагруженных данных (Ф1 «правовая семья», Ф2 «ASDI», Ф4–Ф6 «WGI-индексы», Ф7 «капитализация/ВВП», Ф10 «конкурентная структура», Ф11 «тип регулятора»).

**Выходная JSON schema:**

```json
{
  "jurisdiction": "string",
  "qualitative_factors": {
    "F3_private_enforcement": {
      "value": "string — высокий / средний / низкий / отсутствует",
      "assessment": "string — какие механизмы, есть ли прецеденты",
      "source": "string"
    },
    "F8_ownership_concentration": {
      "value": "string — дисперсная / умеренная / высокая",
      "state_share_pct": "string — доля гос. сектора, если доступно",
      "assessment": "string",
      "source": "string"
    },
    "F9_investor_base": {
      "value": "string — институционалы / смешанная / розница",
      "institutional_share_pct": "string — если доступно",
      "source": "string"
    },
    "F12_exchange_as_sro": {
      "value": "string — полноценная / частичная / оператор",
      "assessment": "string — какие полномочия",
      "source": "string"
    }
  },
  "preloaded_verification": {
    "F1_legal_family": { "confirmed": "boolean", "corrected_value": "string | null", "source": "string" },
    "F11_regulator_type": { "confirmed": "boolean", "corrected_value": "string | null", "source": "string" },
    "F7_market_depth": { "confirmed": "boolean", "corrected_value": "string | null", "source": "string" }
  }
}
```

### 4.4. Запрос 1В: Ландшафтный обзор площадок

**Тип:** Deep Research, JSON schema.  
**Процессор:** core.

Выявление ландшафта: какие биржи, их уровни/борды, отраслевые и прочие сегменты, классы и подклассы инструментов в обороте.

**Промпт:**

```
Provide an overview of all securities trading venues in [JURISDICTION].

For each venue:
1. Official name (local + English)
2. Type (regulated market / MTF / OTF / other)
3. Operator (if different from venue name)
4. Listing tiers / boards — names and brief description
5. Specialised segments (SME, ESG, technology, REIT, etc.)
6. Instrument classes traded: equities (ordinary, preference), 
   bonds (corporate, sovereign, convertible), funds (ETF, closed-end, 
   REIT), depositary receipts
7. Approximate scale (number of listed issuers, market cap)

[Контекст из запроса 1А.]
```

**Выходная JSON schema:**

```json
{
  "jurisdiction": "string",
  "venues": [
    {
      "name_local": "string",
      "name_english": "string",
      "type": "string",
      "operator": "string",
      "tiers": [
        { "name": "string", "description": "string" }
      ],
      "segments": [
        { "name": "string", "description": "string" }
      ],
      "instrument_classes": {
        "equities": { "admitted": "boolean", "subtypes": ["string"] },
        "bonds": { "admitted": "boolean", "subtypes": ["string"] },
        "funds": { "admitted": "boolean", "subtypes": ["string"] },
        "depositary_receipts": { "admitted": "boolean" }
      },
      "scale": { "listed_issuers": "string", "market_cap": "string" },
      "source": "string"
    }
  ]
}
```

### 4.5. LLM-постобработка уровня 1

**Вход:** результаты запросов 1А, 1Б, 1В + предзагруженные факторы.

**Задачи:**
- Формирование карточки юрисдикции (JSON).
- Перевод ключевых полей на русский.
- Определение перечня площадок для уровня 2.
- Если обнаружена неизвестная наднациональная рамка — пометка для динамического запроса.

---

## 5. Уровень 2. Площадка

### 5.1. Назначение

Для каждой площадки: детальная структура (точные названия уровней, маппинг на А04 «специализированный сегмент» / А05 «уровень листинга», классы инструментов по уровням, специальные режимы, включая вторичный допуск). Результат определяет перечень ячеек уровня 3.

### 5.2. Запрос 2А: Детальная структура площадки

**Тип:** Deep Research, auto output.  
**Процессор:** core.

**Промпт формируется LLM** на языке площадки с подстановкой из карточки юрисдикции. Пример (HKEX):

```
Research the detailed listing structure of the Hong Kong Stock 
Exchange (HKEX), operated by Hong Kong Exchanges and Clearing Limited.

Context: HKEX operates Main Board and GEM (Growth Enterprise Market). 
The Securities and Futures Commission (SFC) is the regulator. 
Listing governed by Main Board Listing Rules and GEM Listing Rules.

For Main Board and GEM separately:

1. Instrument classes admitted:
   - Equity securities (ordinary shares, preference shares, 
     shares of SPAC companies, WVR companies)
   - Debt securities (corporate bonds, convertible bonds)
   - Collective investment schemes (ETF, REIT)
   - Depositary receipts

2. Sub-tiers or segments within Main Board / GEM?

3. Separate issuer eligibility process (Chapter 8 of Main Board 
   Rules) distinct from securities admission?

4. Secondary listing regime: Chapter 19C — categories of issuers, 
   exemptions from standard requirements?

5. For each admitted instrument class: which chapters of the 
   Listing Rules govern admission?

Provide specific rule references.
```

### 5.3. LLM-постобработка уровня 2

**Задачи:**
- Карточка площадки (JSON): уровни, сегменты, маппинг на А04/А05, классы инструментов.
- **Генерация перечня ячеек уровня 3:** каждая уникальная комбинация площадка × уровень × класс инструмента.
- **Пометка ячеек с вторичным допуском:** где запрос 3Г применим.
- **Формирование промптов уровня 3** на языке площадки: подстановка названий уровней, номеров глав rulebook, местных терминов. Промпты сохраняются в /prompts/.
- Перевод ключевых полей на русский.

---

## 6. Уровень 3. Ячейка

### 6.1. Назначение

Основной объём. Для каждой ячейки (площадка × уровень × класс инструмента) — сбор фактических данных.

Количество ячеек: ~1000 (определяется по результатам уровня 2).

### 6.2. Принцип разделения запросов

Все запросы уровня 3 используют **JSON schema** (привязка источников к полям).

Разделение по **доступности информации и глубине поиска**:

| Запрос | Содержание | Глубина | Обоснование |
|--------|-----------|---------|-------------|
| 3А | Первичный допуск | Стандартная (core) | Хорошо документирован, источников много |
| 3Б | Поддержание, приостановка, исключение | Повышенная (pro) | Документирован плохо, источники скудны |
| 3В | Мониторинг и enforcement | Повышенная (pro) | Источники разрозненны |
| 3Г | Вторичный допуск (где применимо) | Стандартная (core) | Отдельная глава rulebook, точечный запрос |

Каждая schema содержит поле `additional_findings` для содержания, не покрытого предопределёнными полями.

### 6.3. Запрос 3А: Первичный допуск

**Тип:** Deep Research, JSON schema.  
**Процессор:** core.

**Промпт формируется LLM** на языке площадки. Пример (HKEX Main Board, акции):

```
Research the initial listing requirements and procedures for equity 
securities on the Main Board of HKEX, as governed by the Main Board 
Listing Rules (particularly Chapters 8, 9, 11A).

Cover: quantitative eligibility (profit test / market cap test / 
revenue test under Rule 8.05), public float (Rule 8.08), minimum 
market capitalisation, minimum shareholders (Rule 8.08(2)), 
minimum share price, track record and financial history, corporate 
governance (Appendix C1), sponsor requirements (Chapter 3A), 
prospectus requirements, lock-up restrictions (Rule 10.07), 
application procedure and timeline.

For each requirement: what exactly established, how calculated, 
alternatives (either/or), variations by company size/type, 
links to other requirements.

Special regimes: how modified for SPAC (Chapter 18B), 
WVR companies (Chapter 8A), Biotech (Chapter 18A), 
overseas issuers (Chapter 19)?

Cite specific rule numbers.
```

**Выходная JSON schema:**

```json
{
  "quantitative_requirements": {
    "free_float": { "description": "string", "source": "string" },
    "market_capitalisation": { "description": "string", "source": "string" },
    "shareholders_count": { "description": "string", "source": "string" },
    "share_price": { "description": "string", "source": "string" },
    "trading_volume": { "description": "string", "source": "string" },
    "issue_size": { "description": "string", "source": "string" }
  },
  "financial_requirements": {
    "financial_history": { "description": "string", "source": "string" },
    "profit_requirements": { "description": "string", "source": "string" },
    "assets_equity": { "description": "string", "source": "string" },
    "revenue": { "description": "string", "source": "string" },
    "working_capital": { "description": "string", "source": "string" }
  },
  "qualitative_requirements": {
    "corporate_governance": { "description": "string", "source": "string" },
    "auditor_standards": { "description": "string", "source": "string" }
  },
  "infrastructure": {
    "sponsor": { "description": "string", "source": "string" },
    "market_maker": { "description": "string", "source": "string" },
    "prospectus": { "description": "string", "source": "string" }
  },
  "restrictions": {
    "lock_up": { "description": "string", "source": "string" },
    "escrow": { "description": "string", "source": "string" }
  },
  "procedure": {
    "application_process": { "description": "string", "source": "string" },
    "timeline": { "description": "string", "source": "string" },
    "approval_decision": { "description": "string", "source": "string" }
  },
  "special_regimes": {
    "spac_modifications": { "description": "string", "source": "string" },
    "wvr_modifications": { "description": "string", "source": "string" },
    "foreign_issuer_modifications": { "description": "string", "source": "string" }
  },
  "additional_findings": { "description": "string", "source": "string" }
}
```

### 6.4. Запрос 3Б: Негативные аспекты (поддержание, приостановка, исключение)

**Тип:** Deep Research, JSON schema.  
**Процессор:** pro (повышенная глубина).

**Обоснование повышенной глубины:** в предыдущих итерациях эти аспекты систематически покрывались плохо — движок находил обильную информацию о допуске/IPO, а на поддержание и делистинг ресурсов оставалось мало. Отдельный запрос с повышенной глубиной фокусирует поиск.

**Промпт формируется LLM** на языке площадки с указанием конкретных глав rulebook, отвечающих за поддержание и исключение.

**Выходная JSON schema:**

```json
{
  "continuing_obligations": {
    "quantitative_thresholds": {
      "description": "string — какие пороги при поддержании, 
                      чем отличаются от допуска",
      "source": "string"
    },
    "qualitative_obligations": {
      "description": "string",
      "source": "string"
    },
    "periodic_reporting": {
      "description": "string — сроки, форматы, стандарты",
      "source": "string"
    },
    "compliance_confirmation": {
      "description": "string — процедура подтверждения соответствия",
      "source": "string"
    }
  },
  "suspension": {
    "grounds": { "description": "string", "source": "string" },
    "procedure": { "description": "string", "source": "string" },
    "disclosure": { "description": "string", "source": "string" },
    "duration_limits": { "description": "string", "source": "string" }
  },
  "delisting_compulsory": {
    "grounds": { "description": "string", "source": "string" },
    "procedure": { "description": "string", "source": "string" },
    "grace_period": { "description": "string", "source": "string" },
    "shareholder_protection": { "description": "string", "source": "string" },
    "disclosure": { "description": "string", "source": "string" }
  },
  "delisting_voluntary": {
    "conditions": { "description": "string", "source": "string" },
    "procedure": { "description": "string", "source": "string" },
    "shareholder_approval": { "description": "string", "source": "string" }
  },
  "terminology": {
    "delisting_local_term": "string",
    "suspension_local_term": "string",
    "source": "string"
  },
  "additional_findings": { "description": "string", "source": "string" }
}
```

### 6.5. Запрос 3В: Мониторинг и enforcement

**Тип:** Deep Research, JSON schema.  
**Процессор:** pro (повышенная глубина).

**Промпт формируется LLM** на языке площадки.

**Выходная JSON schema:**

```json
{
  "monitoring_regime": {
    "responsible_body": {
      "description": "string — кто: биржа, регулятор, оба",
      "source": "string"
    },
    "mechanisms": {
      "description": "string — регулярные проверки, автоматический 
                      мониторинг, ad-hoc запросы",
      "source": "string"
    },
    "sponsor_role": {
      "description": "string — роль спонсора/nomad в мониторинге",
      "source": "string"
    },
    "issuer_reporting_to_exchange": {
      "description": "string — отчётность бирже помимо публичного раскрытия",
      "source": "string"
    }
  },
  "sanctions": {
    "exchange_sanctions": {
      "description": "string — перечень: предупреждение, штраф, 
                      понижение, приостановка, делистинг",
      "source": "string"
    },
    "regulator_sanctions": {
      "description": "string",
      "source": "string"
    },
    "disciplinary_procedure": {
      "description": "string — расследование, слушание, апелляция",
      "source": "string"
    },
    "publication_of_actions": {
      "description": "string — публикуются ли, где",
      "source": "string"
    }
  },
  "enforcement_practice": {
    "recent_examples": {
      "description": "string — конкретные примеры за 3–5 лет",
      "source": "string"
    },
    "general_approach": {
      "description": "string — толерантность vs строгий enforcement",
      "source": "string"
    }
  },
  "additional_findings": { "description": "string", "source": "string" }
}
```

### 6.6. Запрос 3Г: Вторичный допуск

**Тип:** Deep Research, JSON schema.  
**Процессор:** core.  
**Выполняется:** только для площадок, где на уровне 2 выявлен режим вторичного допуска (Г06 «вторичный допуск»).

Вторичный допуск — не самостоятельная фаза жизненного цикла, а вариант первичного допуска (Г05 «первичный допуск») с модифицирующим атрибутом «инструмент уже допущен на другой площадке». Однако на практике это часто отдельные главы rulebook с существенно иными требованиями, что обосновывает отдельный запрос.

**Промпт формируется LLM.** Пример (HKEX):

```
Research the secondary listing / dual primary listing regime for 
equity securities on HKEX Main Board, as governed by Chapter 19C 
of the Main Board Listing Rules.

1. Eligibility: which issuers qualify (qualifying exchange, market 
   cap thresholds, track record)?
2. Which standard listing requirements are waived or modified for 
   secondary-listed issuers?
3. What additional requirements apply specifically to secondary 
   listings?
4. Distinction between secondary listing and dual-primary listing 
   under Chapter 19C.
5. Continuing obligations: how differ from primary-listed issuers?
6. Recent changes to the regime.

Cite specific rule numbers.
```

**Выходная JSON schema:**

```json
{
  "eligibility": {
    "qualifying_exchanges": { "description": "string", "source": "string" },
    "market_cap_threshold": { "description": "string", "source": "string" },
    "track_record": { "description": "string", "source": "string" }
  },
  "waivers_from_standard": {
    "description": "string — какие стандартные требования снимаются или 
                    модифицируются",
    "source": "string"
  },
  "additional_requirements": {
    "description": "string — требования, специфичные для вторичного допуска",
    "source": "string"
  },
  "continuing_obligations_differences": {
    "description": "string — чем отличаются от первичного листинга",
    "source": "string"
  },
  "secondary_vs_dual_primary": {
    "description": "string — различие режимов, если есть",
    "source": "string"
  },
  "additional_findings": { "description": "string", "source": "string" }
}
```

### 6.7. Формирование промптов и местная терминология

Все промпты уровня 3 формируются LLM с подстановкой:
- Названий конкретных уровней/сегментов площадки (из карточки площадки уровня 2).
- Номеров глав/разделов rulebook (из результатов уровня 2).
- Местных терминов из маппинга (из карточки юрисдикции уровня 1).
- Контекста: тип регулятора, архитектура допуска, наднациональная рамка.

Сформированные промпты сохраняются в /prompts/ для воспроизводимости и отладки.

---

## 7. Пакетная постобработка уровня 3

### 7.1. Назначение

Выполняется **после** сбора массива результатов уровня 3 (или значительной его части). Не встроена в цепочку обработки каждой ячейки — пакетная обработка на полном массиве даёт возможность кросс-юрисдикционного сравнения и классификации.

### 7.2. Задачи

1. **Приведение к словарю параметров (П01–П23).** Для каждого поля из JSON-результатов 3А и 3Б — определить соответствие параметру словаря.

2. **Перевод на русский.** Все текстовые поля description.

3. **Структурирование по 6 вопросам протокола описания параметра** (что установлено, как рассчитывается, альтернативы, вариации, связи, источник).

4. **Фиксация связок** между параметрами (мин. цена × мин. число акций = неявный денежный порог).

5. **Фиксация модификаторов** (SPAC, WVR, иностранный эмитент → отклонения от базового параметра).

6. **Типологизация конструкций** по каждому параметру (процентный порог / денежный порог / скользящая шкала / качественный критерий / нет требования).

7. **Кандидаты на расширение словаря.** Содержание из полей `additional_findings`, повторяющееся в нескольких юрисдикциях → кандидат на П24+.

8. **Фиксация пробелов.** Поле schema пустое → «не найден» или «не применимо».

---

## 8. Уровень 4. Проблемно-ориентированный анализ

### 8.1. Назначение

Сбор данных о регуляторных целях юрисдикции и связи с параметрами. Выполняется после уровня 3.

### 8.2. Запрос 4А: Регуляторные цели и обоснования

**Тип:** Deep Research, text output.  
**Процессор:** pro.

Здесь text — сознательный выбор: нужно свободное аналитическое рассуждение, структура не предопределена. Источники будут в общем потоке, но для аналитического слоя это допустимо — здесь важнее reasoning, чем точная привязка.

**Промпт:**

```
Research the regulatory policy objectives and rationale behind 
the securities listing framework in [JURISDICTION].

1. REGULATORY OBJECTIVES
   What objectives does [НАЗВАНИЕ РЕГУЛЯТОРА] and/or [НАЗВАНИЕ 
   ПЛОЩАДКИ/ПЛОЩАДОК] articulate for their listing regime?
   Sources: statutory mandate, strategic documents, annual reports, 
   policy statements.

   Map to framework (where applicable):
   - Investor protection
   - Fair, efficient, transparent markets
   - Reduction of systemic risk
   - Issuer attraction / venue competitiveness
   - Capital market development
   - International harmonisation

2. PARAMETER-OBJECTIVE LINKAGE
   For the following key parameters in this jurisdiction:
   [подставляются 5–7 характерных параметров из результатов 
   уровня 3, с конкретными значениями]
   — evidence of explicit reasoning linking calibration to objective?

3. TRADE-OFFS AND CONFLICTS
   Documented discussions of trade-offs? How resolved?

4. RECENT REFORMS
   Stated motivation? What problem solved?

Cite: consultation papers, regulatory impact assessments, 
parliamentary materials, regulator speeches, exchange strategy docs.
```

### 8.3. LLM-постобработка уровня 4

Формирование блока Ж карточки юрисдикции:
1. Регуляторные цели, обсуждавшиеся в юрисдикции.
2. Связь параметров с целями.
3. Релевантность для РФ (маппинг на проблемы ПА1–ПА5, ПБ1–ПБ10, конфликты К1–К4).

Перевод на русский.

---

## 9. Пилот

### 9.1. Юрисдикции

| Юрисдикция | Причина выбора |
|-----------|---------------|
| **UK** | Раздельный листинг/допуск. Реформа 2024. Англоязычная. |
| **Гонконг** | Объединённый режим. WVR, SPAC, Chapter 18A/18B/19C. Англоязычные правила. |
| **Россия** | Базовый случай. Знакомый контекст для верификации. Русскоязычные источники. |

### 9.2. Что проверяется

1. Качество промптов — содержательность результатов на каждом уровне.
2. Выбор процессора — достаточна ли глубина core для 3А, pro для 3Б/3В.
3. Объём результатов — управляемость.
4. Эффект JSON schema — привязка источников к полям, адекватность полей.
5. Формирование промптов через LLM — корректность подстановки местной терминологии.
6. Словарь параметров — достаточность П01–П23, кандидаты на расширение.
7. Наднациональный слой — работает ли подача EU-контекста для UK.
8. Перевод — качество при постобработке.
9. Вторичный допуск (3Г) — адекватность отдельного запроса (HKEX Chapter 19C, LSE).

Языковой барьер — отдельный расширенный пилот при необходимости.

### 9.3. Решение после пилота

Фиксируются: ядро v1 (только расширения), словарь параметров v1, шаблоны промптов, выбор процессоров, выходные JSON schema, решение о масштабном запуске.

---

## 10. Режим выполнения

### 10.1. Полуручное сопровождение (пилот и отладка)

```
1. Запрос 1А (архитектура + маппинг, text) → просмотр
2. Запрос 1Б (качественные факторы, schema) → просмотр
3. Запрос 1В (ландшафт площадок, schema) → просмотр
4. LLM-постобработка → карточка юрисдикции → просмотр
   [Если обнаружена неизвестная наднациональная рамка → запрос, 
    результат сохраняется]
5. Для каждой площадки:
   5.1. LLM формирует промпт 2А на языке площадки → просмотр промпта
   5.2. Запрос 2А (детальная структура, auto) → просмотр
   5.3. LLM-постобработка → карточка площадки + перечень ячеек
   5.4. LLM формирует промпты уровня 3 → просмотр промптов
6. Для каждой ячейки:
   6.1. Запрос 3А (первичный допуск, schema, core) → просмотр
   6.2. Запрос 3Б (негативные аспекты, schema, pro) → просмотр
   6.3. Запрос 3В (мониторинг/enforcement, schema, pro) → просмотр
   6.4. [Если применимо] Запрос 3Г (вторичный допуск, schema, core)
   6.5. Решение: эскалация? → повтор с повышенной глубиной
7. [После накопления массива:]
   Пакетная постобработка уровня 3
8. Запрос 4А (проблемно-ориентированный, text, pro) → просмотр
9. LLM-постобработка → блок Ж → просмотр
```

### 10.2. Массовый запуск

Уровень 1 — параллельно по всем юрисдикциям.  
Уровень 2 — параллельно по всем площадкам.  
Уровень 3 — максимальный параллелизм (ячейки независимы).

### 10.3. Обратная связь

**Только на расширение.** Добавление параметра (П24+), понятия, фактора — допускается. Ранее собранные данные валидны. Переопределение — не допускается.

---

## 11. Нерешённые вопросы

| # | Вопрос | Когда решается |
|---|--------|---------------|
| 1 | Тарифы Parallel — выбор процессоров | До пилота |
| 2 | Rate limits — допустимый параллелизм | До массового запуска |
| 3 | Детальная спецификация промежуточного JSON | При разработке скриптов |
| 4 | Расширенный пилот (не-англоязычные юрисдикции) | После основного пилота |
| 5 | Модификаторы П20–П23: отдельные параметры или атрибуты | После пилота |
| 6 | Параметры для сводной таблицы по классам инструментов | После пилота |
| 7 | Алгоритм кластеризации | После заполнения факторов |
| 8 | Наднациональные рамки помимо EU | По мере обнаружения |
| 9 | Детализация JSON schema для каждого типа запроса | При подготовке пилота |
| 10 | Размер выходной schema vs лимит input Parallel (15 000 символов) | При подготовке пилота |

---

*Документ создан 2026-03-05. Версия 0.2.*
