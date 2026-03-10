# Level 1: Анализ юрисдикций — пилот (UK, Гонконг, Россия)

## Что нужно сделать

Реализовать первый уровень пайплайна: сбор и постобработка данных о регуляторной архитектуре для трёх пилотных юрисдикций (Великобритания, Гонконг, Россия). Включает инфраструктуру пайплайна (Parallel SDK, Langchain, storage, logging) и запуск реальных Deep Research запросов.

## Зачем

Это ядро пайплайна — фундамент для всех последующих уровней. Результат Level 1: карточки юрисдикций (JSON) + перечень площадок для Level 2. Пилот на трёх юрисдикциях позволяет проверить качество промптов, формат вывода и схему хранения до масштабирования на все 47 юрисдикций.

## Acceptance Criteria

- [ ] AC-1: Инфраструктура: async-runner для Parallel SDK работает (launch → poll → save)
- [ ] AC-2: Storage layer: JSON-результаты сохраняются в `03_data/countries/{country}/level_1/`
- [ ] AC-3: Logging: каждый шаг логируется в `04_logs/`, state-файл позволяет перезапустить с места сбоя
- [ ] AC-4: EU framework: запрос выполнен, результат в `03_data/supranational/eu.json`
- [ ] AC-5: Запросы 1A, 1B, 1C выполнены для UK, Гонконга и России
- [ ] AC-6: Сырые результаты сохранены: `1A_architecture.json`, `1B_institutional.json`, `1C_venues.json`
- [ ] AC-7: LLM-постобработка выполнена: `jurisdiction_card.json` + `venues_list.json` для каждой юрисдикции
- [ ] AC-8: Ключевые поля карточки переведены на русский
- [ ] AC-9: Создан отчёт `implementation_01.md` с описанием что сделано, структурой файлов и выводами по качеству данных

## Контекст

### Технологический стек

- **Python**, виртуальное окружение (venv)
- **Parallel SDK**: `pip install parallel-web` — для Deep Research запросов
  - Docs: https://docs.parallel.ai/task-api/task-deep-research
  - Задачи асинхронны: запускаем, получаем task_id, затем периодически проверяем статус (раз в минуту)
  - Процессор для всех запросов в этой задаче: **`pro`**
- **Langchain + OpenAI**: для LLM-постобработки
  - MCP `docs-langchain` доступен для справки по Langchain
  - `base_url` задаётся через параметр `base_url` (не через кастомный http-клиент)
  - Для структурированного вывода: `.with_structured_output(PydanticModel)`
  - Для умных задач: модель **`gpt-5`**; для рутинных массовых: **`gpt-5-mini`**
- **Переменные окружения**: файл `.env` в корне проекта
  - `OPENAI_API_KEY` — ключ для Langchain
  - `OPENAI_BASE_URL` — base_url для OpenAI-совместимого API
  - Parallel SDK имеет свой ключ — проверь в `.env` или документации SDK

### Важное правило для LLM-промптов

**Все промпты для LLM (и для Parallel, и для Langchain) должны быть самодостаточными** — содержать весь нужный контекст внутри себя. LLM не видит контекст диалога.

### Структура файлов проекта

```
02_src/                          # Весь код
  pipeline/
    config.py                    # Константы, список юрисдикций
    storage.py                   # Чтение/запись JSON
    parallel_runner.py           # Async runner для Parallel SDK
    llm_postprocessor.py         # Langchain постобработка
  level_1/
    eu_framework.py              # Запрос EU framework
    jurisdiction_runner.py       # Запросы 1A, 1B, 1C
    postprocess.py               # LLM → jurisdiction card

03_data/
  supranational/
    eu.json                      # EU framework (из запроса EU)
  countries/
    Великобритания/
      level_1/
        1A_architecture.json
        1B_institutional.json
        1C_venues.json
        jurisdiction_card.json   # Постобработанная карточка
        venues_list.json         # Перечень площадок для Level 2
    Гонконг/
      level_1/  ...
    Россия/
      level_1/  ...
  prompts/
    level_1/                     # Сохранённые промпты (для воспроизводимости)

04_logs/
  level1_state.json              # State: task_ids, статусы, пути к результатам
  level1_YYYYMMDD.log            # Рабочий лог
```

### Список пилотных юрисдикций

Из `03_data/exchanges.json`:
- `Великобритания` → площадки: LSE, Aquis_Stock_Exchange
- `Гонконг` → площадки: HKEX

Россия не включена в `exchanges.json` (добавить вручную в конфиг как пилотную юрисдикцию):
- `Россия` → площадки: МосБиржа (уточнить в процессе)

### Async-runner: рекомендуемый подход

```python
# Псевдокод структуры
# 1. Запускаем все задачи, получаем task_ids
# 2. Сохраняем state в 04_logs/level1_state.json (для перезапуска)
# 3. Polling loop: проверяем каждые 60 сек, сохраняем результаты по мере готовности
# 4. При перезапуске: читаем state, продолжаем только незавершённые задачи

state = {
  "tasks": {
    "uk_1A": {"task_id": "...", "status": "pending|running|done|error", "result_path": "..."},
    ...
  }
}
```

---

### Промпт: EU Framework (запрос нулевой, до 1A)

Тип: Deep Research, **text** output, процессор: **pro**

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

Результат сохранить в `03_data/supranational/eu.json` (обернуть в JSON: `{"framework": "EU", "content": "<text>", "retrieved_at": "<date>"}`).

---

### Промпт: Запрос 1A — Архитектура допуска и маппинг

Тип: Deep Research, **text** output, процессор: **pro**

Подставить `[JURISDICTION]` = "United Kingdom" / "Hong Kong" / "Russia".

Для UK добавить в конец промпта выжимку из `03_data/supranational/eu.json` (UK — post-Brexit, так что указать: "Note: UK left the EU in January 2020. Include references to retained EU law where relevant.").

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
```

Сохранить сырой текст в `03_data/countries/{country}/level_1/1A_architecture.json`:
```json
{"jurisdiction": "...", "query": "1A", "content": "<text>", "retrieved_at": "<date>"}
```

---

### Промпт: Запрос 1B — Институциональные факторы (качественные)

Тип: Deep Research, **JSON schema** output, процессор: **pro**

Подставить `[JURISDICTION]`.

```
Research the following institutional characteristics of [JURISDICTION]
securities markets. For each factor provide: value assessment,
substantive explanation, and source.

1. Private enforcement (F3): What mechanisms exist for private
   investor lawsuits against issuers/intermediaries for securities
   violations? Are there class actions, derivative suits?
   Level: high / medium / low / absent.

2. Ownership concentration (F8): Is share ownership dispersed
   (many small shareholders) or concentrated (controlling blocks
   common)? Approximate state sector share if available.
   Level: dispersed / moderate / concentrated.

3. Investor base structure (F9): Predominantly institutional
   investors, retail investors, or mixed?
   Approximate institutional share % if available.

4. Exchange as SRO (F12): Does the exchange have self-regulatory
   authority — listing enforcement, disciplinary powers over
   members? Or is it purely a market operator?
   Level: full SRO / partial / operator only.

Also verify (confirm or correct) these pre-loaded values:
- Legal family (F1): [common law / civil law / mixed / other]
- Regulator type (F11): [central bank / commission / supranational / other], regulator name
- Market depth (F7): market capitalisation as % of GDP (approximate)

All prompts are self-contained. Do not rely on prior context.
```

Выходная JSON schema (сохранить в `03_data/countries/{country}/level_1/1B_institutional.json`):
```json
{
  "jurisdiction": "string",
  "qualitative_factors": {
    "F3_private_enforcement": {
      "value": "string",
      "assessment": "string",
      "source": "string"
    },
    "F8_ownership_concentration": {
      "value": "string",
      "state_share_pct": "string",
      "assessment": "string",
      "source": "string"
    },
    "F9_investor_base": {
      "value": "string",
      "institutional_share_pct": "string",
      "source": "string"
    },
    "F12_exchange_as_sro": {
      "value": "string",
      "assessment": "string",
      "source": "string"
    }
  },
  "preloaded_verification": {
    "F1_legal_family": {"confirmed": "boolean", "corrected_value": "string|null", "source": "string"},
    "F11_regulator_type": {"confirmed": "boolean", "corrected_value": "string|null", "source": "string"},
    "F7_market_depth": {"confirmed": "boolean", "corrected_value": "string|null", "source": "string"}
  }
}
```

---

### Промпт: Запрос 1C — Ландшафт площадок

Тип: Deep Research, **JSON schema** output, процессор: **pro**

Подставить `[JURISDICTION]` + краткий контекст из результата 1A (регулятор, типы рынков).

```
Provide an overview of all securities trading venues in [JURISDICTION].

Context: [вставить из 1A: название регулятора, типы рынков]

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

All information must be self-contained. Do not rely on prior context.
```

Выходная JSON schema (сохранить в `03_data/countries/{country}/level_1/1C_venues.json`):
```json
{
  "jurisdiction": "string",
  "venues": [
    {
      "name_local": "string",
      "name_english": "string",
      "type": "string",
      "operator": "string",
      "tiers": [{"name": "string", "description": "string"}],
      "segments": [{"name": "string", "description": "string"}],
      "instrument_classes": {
        "equities": {"admitted": "boolean", "subtypes": ["string"]},
        "bonds": {"admitted": "boolean", "subtypes": ["string"]},
        "funds": {"admitted": "boolean", "subtypes": ["string"]},
        "depositary_receipts": {"admitted": "boolean"}
      },
      "scale": {"listed_issuers": "string", "market_cap": "string"},
      "source": "string"
    }
  ]
}
```

---

### LLM-постобработка (Langchain, gpt-5)

После получения результатов 1A + 1B + 1C для юрисдикции — выполнить постобработку.

**Задача:** Сформировать `jurisdiction_card.json` и `venues_list.json`.

Промпт для постобработки должен быть самодостаточным: вставить в него полное содержимое 1A, 1B, 1C.

```
You are processing research results about [JURISDICTION] securities markets.

Below are three research outputs:
--- 1A: REGULATORY ARCHITECTURE ---
[полное содержимое 1A_architecture.json]

--- 1B: INSTITUTIONAL FACTORS ---
[полное содержимое 1B_institutional.json]

--- 1C: VENUE LANDSCAPE ---
[полное содержимое 1C_venues.json]

Your tasks:
1. Create a structured jurisdiction card combining all three sources.
2. Translate key descriptive fields to Russian.
3. Extract a list of venues for further research (Level 2).
4. Flag if any previously unknown supranational regulatory framework
   was mentioned (other than EU) — set supranational_flag=true and
   name the framework.

Return valid JSON matching the schema provided.
```

Использовать `.with_structured_output(JurisdictionCard)` где `JurisdictionCard` — Pydantic-модель:

```python
class VenueRef(BaseModel):
    name_english: str
    name_local: str
    type: str
    tiers: list[str]

class JurisdictionCard(BaseModel):
    jurisdiction: str
    jurisdiction_ru: str
    legal_family: str
    regulator_name: str
    regulator_type: str
    admission_architecture: str          # объединён/раздельный листинг
    admission_architecture_ru: str
    listing_authority: str
    market_types: list[str]
    key_terms_mapping: dict[str, str]    # local term → english term
    venues: list[VenueRef]
    supranational_flag: bool
    supranational_framework: str | None
    notes: str
```

Сохранить в:
- `03_data/countries/{country}/level_1/jurisdiction_card.json`
- `03_data/countries/{country}/level_1/venues_list.json` (список venues для Level 2)

---

### Порядок выполнения

1. Настроить инфраструктуру (runner, storage, logging)
2. Запустить EU framework (async, ждать результата)
3. Запустить 1A для UK, Гонконга, России параллельно
4. По готовности 1A → запустить 1B и 1C параллельно (для каждой юрисдикции)
5. По готовности 1A+1B+1C → LLM-постобработка
6. Проверить результаты, зафиксировать наблюдения в `implementation_01.md`

### Где смотреть дополнительный контекст

- `00_docs/specs/05_pipeline/pipeline_v0_2.md` — полная спецификация пайплайна
- `03_data/exchanges.json` — полный список юрисдикций и площадок
- `00_docs/00_guidelines_01.txt` — технические ограничения и соглашения проекта
