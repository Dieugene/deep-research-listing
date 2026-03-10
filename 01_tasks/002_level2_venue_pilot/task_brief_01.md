# Level 2: Детальная структура площадок — пилот (UK, Гонконг)

## Что нужно сделать

Реализовать второй уровень пайплайна: сбор детальной структуры площадок и генерация списка ячеек для Level 3. Для каждой площадки: LLM генерирует кастомный промпт → Parallel выполняет Deep Research → LLM постобрабатывает результат в venue card + список ячеек + промпты Level 3.

## Площадки для пилота

Источник истины — `03_data/exchanges.json`. Для Level 2 используем только ключи из этого файла:

| venue_key | Юрисдикция (ru) | Тиры (из Level 1) |
|---|---|---|
| `LSE` | Великобритания | Main Market: ESCC, CEIF, Transition, Secondary Listing, Shell, SFS; плюс AIM |
| `Aquis_Stock_Exchange` | Великобритания | Main Market; Growth Market: Access, Apex |
| `HKEX` | Гонконг | Main Board, GEM |

**Важно:** список площадок берётся из `exchanges.json`, а НЕ из `venues_list.json` (там шум от ATS/VATP/других торговых площадок, не релевантных для исследования листинга).

## Acceptance Criteria

- [ ] AC-1: `parallel_runner.py` поддерживает `output_schema="auto"` (новый тип в дополнение к `None`/text и `dict`/json)
- [ ] AC-2: Для каждой площадки LLM (gpt-5) генерирует кастомный 2A промпт → сохраняется в `03_data/prompts/level_2/{venue_key}_prompt.txt`
- [ ] AC-3: Parallel 2A задачи запущены и завершены для LSE, Aquis_Stock_Exchange, HKEX (processor: pro, output: auto)
- [ ] AC-4: Сырые результаты сохранены в `03_data/countries/{name_ru}/level_2/{venue_key}/2A_structure.json`
- [ ] AC-5: LLM постобработка (gpt-5): venue card сохранена как `venue_card.json`
- [ ] AC-6: Список ячеек сохранён как `cells_list.json` — только комбинации (тир × класс инструмента), реально присутствующие на площадке
- [ ] AC-7: Промпты Level 3 (3A, 3B, 3C; 3D где применимо) сгенерированы и сохранены в `03_data/prompts/level_3/{cell_id}_{query}.txt`
- [ ] AC-8: Исправлена логика `supranational_flag` в `02_src/level_1/postprocess.py` — флаг только для наднационального законодательства о листинге, не для схем доступа инвесторов (Stock Connect и т.п.)
- [ ] AC-9: State-файл `04_logs/level2_state.json` позволяет перезапустить с места сбоя
- [ ] AC-10: Создан `implementation_01.md` с описанием реализации и наблюдениями по качеству данных

## Технический контекст

Все правила из `00_docs/00_guidelines_01.txt` в силе. Работаем в venv (`D:\_workspace\deep-research-listing\venv`). Корень проекта: `D:\_workspace\deep-research-listing`.

**Стек:** Python, Parallel SDK (`parallel-web`), Langchain + gpt-5 (умные задачи) / gpt-5-mini (рутина), `.env` в корне.

**Промпты для LLM — самодостаточные** (без опоры на контекст диалога).

## Структура файлов

```
02_src/
  pipeline/
    parallel_runner.py       # Добавить поддержку output_schema="auto"
  level_1/
    postprocess.py           # Исправить supranational_flag логику
  level_2/
    prompt_generator.py      # LLM генерирует 2A промпты на языке площадки
    venue_runner.py          # Launch/poll Parallel 2A задач
    postprocess.py           # LLM → venue card + cells_list + L3 промпты
    run_level2.py            # Оркестратор

03_data/
  countries/
    Великобритания/
      level_2/
        LSE/
          2A_structure.json
          venue_card.json
          cells_list.json
        Aquis_Stock_Exchange/
          2A_structure.json
          venue_card.json
          cells_list.json
    Гонконг/
      level_2/
        HKEX/
          2A_structure.json
          venue_card.json
          cells_list.json
  prompts/
    level_2/
      LSE_prompt.txt
      Aquis_Stock_Exchange_prompt.txt
      HKEX_prompt.txt
    level_3/
      {cell_id}_3A.txt
      {cell_id}_3B.txt
      {cell_id}_3C.txt
      {cell_id}_3D.txt    # только где secondary admission применимо

04_logs/
  level2_state.json
  level2_YYYYMMDD.log
```

## Конфигурация площадок

Добавить в `02_src/pipeline/config.py`:

```python
# Классы инструментов в scope проекта
INSTRUMENT_CLASSES = ["equity", "bond", "fund", "depositary_receipt"]

# Пилотные площадки для Level 2 (из exchanges.json)
PILOT_VENUES = [
    {
        "venue_key": "LSE",
        "name_ru": "Великобритания",
        "name_en": "United Kingdom",
        "venue_name_english": "London Stock Exchange",
        "venue_name_local": "London Stock Exchange",
    },
    {
        "venue_key": "Aquis_Stock_Exchange",
        "name_ru": "Великобритания",
        "name_en": "United Kingdom",
        "venue_name_english": "Aquis Stock Exchange",
        "venue_name_local": "Aquis Stock Exchange",
    },
    {
        "venue_key": "HKEX",
        "name_ru": "Гонконг",
        "name_en": "Hong Kong",
        "venue_name_english": "The Stock Exchange of Hong Kong Limited (HKEX/SEHK)",
        "venue_name_local": "香港聯合交易所有限公司",
    },
]
```

## Исправление parallel_runner.py (AC-1)

В функции `launch_task` добавить обработку `output_schema="auto"`:

```python
if output_schema is None:
    task_spec = {"output_schema": {"type": "text"}}
elif output_schema == "auto":
    task_spec = {"output_schema": {"type": "auto"}}
else:
    task_spec = {"output_schema": {"type": "json", "json_schema": output_schema}}
```

## Генерация 2A промпта через LLM (AC-2)

`prompt_generator.py`: для каждой площадки вызов gpt-5 с мета-промптом. Промпт должен быть самодостаточным — включать полное содержимое jurisdiction_card.json.

```
You are preparing a Deep Research query about a securities exchange.

JURISDICTION CONTEXT (from prior research):
{full content of jurisdiction_card.json}

VENUE TO RESEARCH:
Name: {venue_name_english} ({venue_name_local})
Type: {venue_type}
Jurisdiction: {jurisdiction_en}

INSTRUMENT CLASSES IN SCOPE:
- Equities: ordinary shares, preference shares
- Bonds: corporate bonds, sovereign/government bonds, convertible bonds
- Funds: ETF, closed-end funds, REIT
- Depositary receipts

Generate a Deep Research prompt in English that asks about the detailed
listing structure of this venue. The prompt must:

1. Use the exact local terminology for tiers, segments, and rulebook
   sections (from the jurisdiction context above).
2. Cover for each tier/board separately:
   a) Which instrument classes are admitted (from the scope above only)
   b) Sub-segments if any
   c) Whether there is a separate issuer eligibility process vs per-issue admission
   d) Secondary/dual listing regime (if applicable): which chapter of rulebook,
      eligibility criteria, what standard requirements are modified
   e) Specific rulebook chapters governing each instrument class
3. Be self-contained — include all necessary context within the prompt itself.
4. Ask for specific rule/chapter references throughout.

Return only the generated Deep Research prompt text, nothing else.
```

Сохранить сгенерированный промпт в `03_data/prompts/level_2/{venue_key}_prompt.txt`.

## Структура выходных данных

### venue_card.json

Pydantic-модель для `.with_structured_output()`:

```python
class TierDef(BaseModel):
    tier_name: str
    tier_name_ru: str
    segment_type: str  # "listing_tier" | "thematic_segment" | "board"
    instrument_classes: list[str]  # только из: equity, bond, fund, depositary_receipt
    rulebook_chapters: dict[str, str]  # instrument_class -> chapter reference
    secondary_admission_applicable: bool

class VenueCard(BaseModel):
    venue_key: str
    venue_name_english: str
    venue_name_local: str
    venue_name_ru: str
    jurisdiction: str
    jurisdiction_ru: str
    venue_type: str  # regulated_market | MTF | OTF | other
    operator: str
    issuer_eligibility_separate: bool
    issuer_eligibility_description: str
    secondary_listing_regime: bool
    secondary_listing_description: str | None
    tiers: list[TierDef]
    key_rulebook_references: str  # общее описание основных документов
    notes: str
    notes_ru: str
```

### cells_list.json

```json
{
  "venue_key": "LSE",
  "jurisdiction_ru": "Великобритания",
  "generated_at": "ISO timestamp",
  "cells": [
    {
      "cell_id": "GB_LSE_ESCC_equity",
      "venue_key": "LSE",
      "tier": "Equity Shares – Commercial Companies (ESCC)",
      "instrument_class": "equity",
      "secondary_admission_applicable": false,
      "prompts": {
        "3A": "03_data/prompts/level_3/GB_LSE_ESCC_equity_3A.txt",
        "3B": "03_data/prompts/level_3/GB_LSE_ESCC_equity_3B.txt",
        "3C": "03_data/prompts/level_3/GB_LSE_ESCC_equity_3C.txt",
        "3D": null
      }
    }
  ]
}
```

`cell_id` format: `{ISO country code}_{venue_key}_{tier_slug}_{instrument_class}`
`tier_slug` — первые значимые слова тира, snake_case, max 30 символов.

### Промпты Level 3 (AC-7)

Для каждой ячейки LLM (gpt-5) генерирует 3 (или 4) промпта по шаблонам из `00_docs/specs/05_pipeline/pipeline_v0_2.md` (разделы 6.3–6.6). Промпты должны быть самодостаточными: включать venue context, tier name, instrument class, rulebook references.

Сохранять в: `03_data/prompts/level_3/{cell_id}_3A.txt` и т.д.

## Исправление supranational_flag (AC-8)

В `02_src/level_1/postprocess.py` — в промпт LLM-постобработки добавить явное правило:

```
Set supranational_flag=true ONLY if a supranational legislative framework
directly governs listing/admission to trading requirements in this jurisdiction
(e.g., EU Prospectus Regulation, MiFID II for EU member states).

Do NOT set supranational_flag=true for:
- Cross-border investor access schemes (Stock Connect, Bond Connect, etc.)
- Mutual recognition arrangements for investment products
- International standards (IOSCO principles) that are not binding legislation
- Any arrangement that affects who can invest, not what is required for listing
```

## Порядок выполнения

```
1. Исправить parallel_runner.py (AC-1)
2. Исправить postprocess.py уровня 1 (AC-8)
3. Для каждой площадки: сгенерировать 2A промпт (LLM, gpt-5)
4. Запустить Parallel 2A задачи для всех 3 площадок параллельно
5. Ждать завершения (polling, 60 сек)
6. Для каждой площадки: LLM постобработка → venue_card + cells_list
7. Для каждой ячейки: сгенерировать промпты Level 3
8. Создать implementation_01.md
```

run_level2.py CLI шаги:
```
--step generate-prompts   # шаг 3: генерация 2A промптов
--step launch-2a          # шаг 4
--step poll-2a            # шаг 5
--step postprocess        # шаги 6–7
--step all                # всё подряд (default)
```

## Входные данные

- `03_data/countries/Великобритания/level_1/jurisdiction_card.json`
- `03_data/countries/Гонконг/level_1/jurisdiction_card.json`
- `03_data/exchanges.json`
- `00_docs/specs/05_pipeline/pipeline_v0_2.md` — шаблоны промптов 3A/3B/3C/3D (разделы 6.3–6.6)
