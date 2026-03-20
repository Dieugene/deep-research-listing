# Эскалация: канонический маппинг тиров L3 → ячейки

**Дата:** 2026-03-20
**От:** Tech Lead
**Кому:** Разработчик пайплайна
**Тип:** Архитектурное изменение постобработки L3

---

## 1. Выявленная проблема

### Суть

Parallel API на этапе L3 возвращает данные по venue × instrument_class, где внутри ответа — массив `tiers[]`. Имена тиров:
- **Различаются между запросами 3A, 3B, 3C** для одного и того же venue × instrument_class
- **Содержат тиры, не принадлежащие запрошенному venue** (например, Open Market тиры в ответе на запрос о Regulated Market)

Текущий `postprocess_l3.py` маппит тиры на ячейки (cell_id) **независимо для каждого файла** (3A, 3B, 3C). Результат: неполная или некорректная дезагрегация.

### Масштаб

7 неполных ячеек из ~105:
- Frankfurt Stock Exchange: equity (есть 3B, нет 3A/3C), bond (есть 3A, нет 3B/3C)
- BÖAG Börsen: equity_primrmarkt (есть 3B, нет 3A/3C)
- SGX: отсутствует Catalist для equity/fund/depositary_receipt
- Aquis Exchange Europe: equity (нет 3C)
- 2 GB transition cells (отдельный кейс — возможно, легитимно неполные)

### Конкретный пример: Frankfurt Stock Exchange / equity

**cells_list.json** (из L2): 1 ячейка `GE_Frankfurt_Stock_Exchange_equity`, tier = `"(no listing tiers — flat structure)"`

**L3 Parallel вернул:**

| Запрос | Тиры |
|--------|------|
| 3A | `"General Standard"`, `"Prime Standard"`, `"Scale"`, `"Basic Board"` |
| 3B | `"Regulated Market – General Standard"`, `"Regulated Market – Prime Standard"`, `"Regulated Market – ATT Only"`, `"Open Market – Scale"`, `"Open Market – Basic Board"` |
| 3C | `"Regulated Market - General Standard / Prime Standard"`, `"Open Market - Scale / Basic Board"` |

**Проблемы:**
1. cells_list знает 1 flat ячейку → маппинг 4 тиров на 1 ячейку невозможен
2. 3A/3B/3C используют разные имена для одних и тех же тиров
3. Scale и Basic Board — это Open Market (Freiverkehr), другой регуляторный статус. Они не принадлежат venue `"Frankfurt Stock Exchange Regulated Market"`
4. 3C объединяет тиры попарно (General + Prime, Scale + Basic Board)
5. 3B нашёл дополнительный тир (ATT Only), которого нет в 3A/3C

### Корневые причины

1. **L2 → cells_list**: LLM при извлечении VenueCard записал тиры в `tiers[]`, но не связал их с `instrument_coverage[]` → cells_list получил flat
2. **L3 промпт не содержит определений venue vs tier** — Parallel не знает, что Scale/Basic Board — другой venue
3. **postprocess_l3 маппит каждый файл независимо** — нет единого взгляда на тиры

---

## 2. Предлагаемое решение

### Архитектура

Добавить шаг **между** получением L3 данных и дезагрегацией:

```
3A _parallel_raw ─┐
3B _parallel_raw ─┼→ LLM: канонический маппинг → обновить cells_list → дезагрегация
3C _parallel_raw ─┘
```

**Один LLM-вызов на venue × instrument_class** вместо трёх независимых маппингов.

### Что делает LLM

На входе:
- venue_card (venue_type, listing_architecture, tiers[], segments[])
- Определения venue / tier / segment / modifier (из L2 промпта)
- Для каждого тира из каждого запроса (3A, 3B, 3C): `tier_name` + полный `content`

На выходе:
- Список канонических тиров с маппингом на конкретные тиры из 3A/3B/3C
- Для каждого тира — принадлежность к venue (текущий venue или другой)

### Что делает алгоритм после LLM

1. Обновляет cells_list: добавляет новые ячейки для ранее неизвестных тиров
2. Перенаправляет тиры другого venue (Scale → Freiverkehr ячейка)
3. Дезагрегирует контент по обновлённому маппингу

---

## 3. Планируемый промпт LLM-постобработки

### Pydantic-схема результата

```python
class TierMapping(BaseModel):
    """Маппинг одного канонического тира."""
    canonical_id: str          # slug: "general_standard", "prime_standard", "scale"
    canonical_name: str        # "General Standard (Regulierter Markt)"
    belongs_to_venue: bool     # True = текущий venue, False = другой venue
    other_venue_hint: str = "" # Если belongs_to_venue=False: "Freiverkehr (Open Market)"
    tier_3a: str = ""          # Имя тира в 3A ответе (или "" если отсутствует)
    tier_3b: str = ""          # Имя тира в 3B ответе
    tier_3c: str = ""          # Имя тира в 3C ответе
    merged_in_3c: bool = False # True если 3C объединил этот тир с другим


class TierCanonicalMap(BaseModel):
    """Результат канонического маппинга для одного venue × instrument_class."""
    tiers: list[TierMapping]
```

### Текст промпта

```
You are analyzing listing tier structures for a securities exchange.

VENUE CONTEXT:
- Venue: {venue_name_english} ({venue_type})
- Operator: {operator}
- Jurisdiction: {jurisdiction}
- Instrument class: {instrument_class}

VENUE CARD DATA (from Level 2 research):
- Tiers found at L2: {venue_card_tiers}
- Segments: {venue_card_segments}
- Listing architecture: {venue_card_listing_architecture}

DEFINITIONS (apply strictly):

DEFINITION — Trading Venue:
A market with its own regulatory framework and its own set of admission rules,
operating under its own regulatory status (e.g., EU Regulated Market under MiFID,
MTF, OTF, or exchange-regulated market). If two markets have DIFFERENT regulatory
status (e.g., one is a Regulated Market and the other is a Freiverkehr/MTF) —
they are separate venues, even if operated by the same entity.

DEFINITION — Listing Tier:
A hierarchical level within a SINGLE venue that determines the strictness of
admission and continuing obligation requirements. A tier shares the SAME regulatory
framework and rulebook as other tiers, but sets HIGHER or LOWER quantitative
thresholds. If the entity has its OWN rulebook or DIFFERENT regulatory status —
it is a separate venue, not a tier.

TASK:
Three independent research queries (3A, 3B, 3C) were sent to investigate
{instrument_class} listing on {venue_name_english}. Each returned its own
array of "tiers". These arrays may:
- Use different names for the same tier
- Split or merge tiers differently
- Include tiers that belong to a DIFFERENT venue (different regulatory status)

For each query, here are the tiers found with their content:

=== 3A (Primary Admission) ===
{for each tier in 3A: tier_name + full content}

=== 3B (Maintenance / Suspension / Delisting) ===
{for each tier in 3B: tier_name + full content}

=== 3C (Monitoring / Enforcement) ===
{for each tier in 3C: tier_name + full content}

INSTRUCTIONS:
1. Identify all UNIQUE tiers across 3A, 3B, 3C by analyzing their content
   (not just names — names may differ for the same tier).
2. For each unique tier, determine:
   a) A canonical ID (snake_case slug)
   b) A canonical name (human-readable, include regulatory framework in parentheses)
   c) Whether it belongs to the CURRENT venue ({venue_name_english}, {venue_type})
      or to a DIFFERENT venue. Use the definitions above — if the tier has a
      different regulatory status, it belongs to a different venue.
   d) Which 3A/3B/3C tier name(s) map to this canonical tier
   e) Whether 3C merged this tier with another (common for monitoring/enforcement
      that applies to multiple tiers equally)
3. If a tier from 3C covers multiple canonical tiers (e.g., "Regulated Market -
   General Standard / Prime Standard"), set merged_in_3c=true for each canonical
   tier it covers, and put the same 3C tier name in tier_3c for all of them.

Return the result as a JSON object with a "tiers" array.
```

---

## 4. Встраивание в пайплайн

### Расположение

В `run_pipeline.py` → `run_level3()`:
- **После** Step 3 (Poll tasks) — L3 данные получены и сохранены в `_parallel_raw/`
- **Перед** Step 4 (Postprocess) — `postprocess_l3.py` использует обновлённый cells_list

```
L3 Step 3: Poll tasks
L3 Step 3.5: Canonical tier mapping (НОВЫЙ)  ← здесь
L3 Step 4: Postprocess (дезагрегация)
```

### Каскадные эффекты

После изменения cells_list и перезапуска дезагрегации:
- Новые cell-директории → нужен Phase 2 (pass1 → pass2)
- Нужны переводы (description_ru, tier_ru, param_label_ru)
- Нужна matrix.json
- Нужны section_keys

Всё это выполняется последующими шагами пайплайна автоматически.

### Данные другого venue

Если LLM определил, что тир принадлежит другому venue (Scale → Freiverkehr):
1. Проверить, есть ли этот venue в cells_list для данной юрисдикции
2. Если есть — перенаправить данные тира в соответствующую ячейку этого venue
3. Если нет — записать в лог warning: «Tier X belongs to venue Y which is not in cells_list. Data preserved in _parallel_raw but not disaggregated.»

Данные не теряются: они остаются в `_parallel_raw/` файле. При необходимости можно добавить venue и перезапустить дезагрегацию.

---

## 5. Объём реализации

| Шаг | Что | LLM? |
|-----|-----|------|
| Канонический маппинг | Один вызов на venue × instrument_class | Да (gpt-5) |
| Обновление cells_list | Алгоритмически | Нет |
| Перенаправление тиров | Алгоритмически | Нет |
| Модификация postprocess_l3 | Использовать каноническую карту вместо per-file маппинга | Нет |

Оценка: ~62 LLM-вызова (по числу _parallel_raw instrument_class файлов), один batch.

---

## 6. Вопросы для решения

1. **Нужно ли перепрогонять L3 Parallel запросы?** Или достаточно перезапустить постобработку на существующих `_parallel_raw` данных?

2. **Перенаправление между venues:** если Scale попал в ответ на Frankfurt Regulated Market запрос, но у нас нет отдельного venue «Frankfurt Freiverkehr» — создавать ли его автоматически?

3. **Полный перепрогон:** предлагается сделать бэкап текущих данных, реализовать исправление, перепрогнать весь пайплайн, сверить результаты.
