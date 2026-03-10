# Патч к пайплайну v0.2: venue / tier / segment

**Дата:** 2026-03-09  
**Основание:** Патч к концептуальному ядру (patch_venue_tier_segment.md) — формализация трёхуровневой иерархии Operator → Venue → Tier / Segment.

---

## 1. Замена «65 площадок» на «N venue»

**Проблема:** по всему пайплайну фигурирует «65 площадок» как единица уровня 2. Это число считалось по операторам (Б02), а не по venue (А02). Реальное число venue больше: у крупных операторов несколько venue с разными регуляторными рамками (LSE: Main Market + AIM + PSM + ISM; HKEX: Main Board + GEM; и т.д.).

**Изменение:** везде, где упоминается «65 площадок», заменить на «N venue (определяется по результатам уровня 1В; ориентировочно 100–150)». Точное число неизвестно до завершения уровня 1.

**Затронутые места:** раздел 1.1 (общая схема), раздел 5 (уровень 2), диаграмма зависимостей.

---

## 2. Промпт 1В (ландшафт площадок): добавить определение venue

**Проблема:** текущий промпт просит «overview of all securities trading venues», но не определяет, что считать отдельной venue. Parallel и LLM могут вернуть оператора (LSE) как одну venue с тирами Main Market и AIM.

**Изменение:** в промпт 1В добавить блок определений перед вопросами:

```
DEFINITIONS (use these when classifying):

OPERATOR: institution managing one or more trading venues 
(e.g., London Stock Exchange Group, HKEX).

VENUE: a trading venue with its own regulatory framework and its 
own set of admission/listing rules. Test: if two parts of the same 
exchange have different rulebooks or different regulatory 
classifications (e.g., one is a Regulated Market and another is 
an MTF) — they are separate venues, not tiers of one venue.

LISTING TIER: a hierarchical level within a single venue, 
determining the stringency of requirements. Requirements on one 
tier are a stricter/looser version of another tier's requirements, 
governed by the SAME rulebook. Test: are requirements on one level 
a subset/superset of requirements on another? If yes — these are 
tiers of one venue.

SEGMENT: a thematic overlay within a venue, with additional criteria 
on top of base requirements. Not a hierarchy of stringency — 
a specialisation. Test: are the additional criteria orthogonal 
(supplementary) to the tier requirements, rather than nested? 
If yes — this is a segment.

REGIME MODIFIER: a set of rule modifications applied to specific 
issuer types (SPAC, WVR/dual-class, biotech, foreign issuers) 
within an existing venue/tier. Not a separate segment or tier — 
a modification of the standard admission regime. Test: does it have 
its own "place" on the exchange (a named board/segment where issuers 
are listed), or is it a set of conditions that modify standard 
requirements? If the latter — it is a modifier, not a segment.

Use these definitions to classify each entity found.
```

**Изменение в выходной schema 1В:** добавить уровень operator, venue внутри operator:

```json
{
  "jurisdiction": "string",
  "operators": [
    {
      "operator_name": "string",
      "venues": [
        {
          "venue_name_local": "string",
          "venue_name_english": "string",
          "market_type": "string — regulated market / MTF / OTF / other",
          "own_rulebook": "string — название собственного свода правил",
          "tiers": [
            { "name": "string", "description": "string" }
          ],
          "segments": [
            { "name": "string", "description": "string" }
          ],
          "regime_modifiers": [
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
  ]
}
```

---

## 3. Единица запроса 2А: venue, не оператор

**Проблема:** в текущем пайплайне запрос 2А выполняется «по площадке», но пример промпта (HKEX) исследует оператора, запрашивая данные по Main Board и GEM в одном запросе. Это смешивает два разных регуляторных режима.

**Изменение:** один запрос 2А = одна venue. Для HKEX — два запроса: один по Main Board, один по GEM.

Промпт 2А формируется LLM на основе результатов 1В, где venue уже выделены. Пример для HKEX Main Board:

```
Research the detailed listing structure of HKEX Main Board 
(Regulated Market), operated by Hong Kong Exchanges and Clearing.

Context: Main Board is governed by the Main Board Listing Rules. 
GEM is a separate venue with its own rulebook — it is NOT part 
of this query.

[определения venue / tier / segment / modifier — те же, что в 1В]

1. Listing tiers within Main Board: are there hierarchical levels 
   with different stringency of requirements?

2. Segments within Main Board: thematic overlays with additional 
   criteria?

3. Regime modifiers: special chapters for specific issuer types 
   (SPAC, WVR, Biotech, overseas issuers) — list and briefly 
   describe. These are NOT segments — they are modifications 
   of the standard admission regime.

4. Instrument classes admitted on Main Board:
   [перечень]

5. Issuer eligibility: separate process?

6. Secondary admission regime?

7. For each admitted instrument class: which chapters of the 
   Main Board Listing Rules govern admission?

Cite specific rule references.
```

**Следствие:** количество запросов 2А увеличивается с ~65 до ~100–150. Но каждый запрос точнее и компактнее.

---

## 4. LLM-постобработка уровня 2: тесты классификации

**Проблема:** при генерации перечня ячеек уровня 3 LLM может ошибочно классифицировать venue как tier, segment как tier, или modifier как segment.

**Изменение:** в инструкцию LLM-постобработки уровня 2 добавить обязательные проверки:

```
VALIDATION CHECKS before generating cells_list:

1. VENUE vs TIER check: for each item classified as "tier" — 
   does it have its OWN rulebook, different from the venue's 
   rulebook? If yes → reclassify as separate venue, 
   not tier of current venue.

2. TIER vs SEGMENT check: for each item classified as "tier" — 
   are requirements a stricter/looser version of another tier 
   (hierarchy of stringency)? Or are they orthogonal/supplementary 
   (thematic)? If supplementary → reclassify as segment.

3. SEGMENT vs MODIFIER check: for each item classified as 
   "segment" — does it have its own named "place" on the exchange 
   where issuers are listed? Or is it a set of conditions 
   modifying standard requirements for a type of issuer? 
   If the latter → reclassify as regime_modifier. 
   Do NOT generate separate cells for regime modifiers.

4. CELL GENERATION: cells are generated for each combination of 
   venue × tier × instrument_class. Segments generate additional 
   cells only if they have substantively different requirements. 
   Modifiers do NOT generate cells — they are handled within 
   the cell's 3A/3P queries as special_regimes / variations.
```

---

## 5. Промпты уровня 3: добавить определения

**Проблема:** промпты уровня 3 используют слова «tier», «segment» без определений. Parallel может интерпретировать их по-разному.

**Изменение:** в каждый промпт уровня 3 (3A, 3B, 3C, 3D, 3P) добавить краткий контекстный блок:

```
Context: [VENUE NAME] is a [market_type] operated by [OPERATOR]. 
[TIER NAME, if applicable] is a listing tier (hierarchical level 
determining stringency of requirements) within this venue. 
This query covers [INSTRUMENT CLASS] on this specific venue/tier.
```

Это не полные определения (они уже есть в промптах 1В и 2А), а контекстная привязка: Parallel понимает, что ищет именно по данной venue/tier, а не по оператору в целом.

---

## 6. Диаграмма зависимостей: обновление

В mermaid-диаграмме: блок «Уровень 2 — Площадка (×65)» заменить на «Уровень 2 — Venue (×N, определяется на уровне 1)». Добавить: из блока 1В выходит стрелка «перечень venue» → блок 2А.

---

## Сводка изменений

| # | Что | Тип |
|---|-----|-----|
| 1 | «65 площадок» → «N venue» | Коррекция по всему документу |
| 2 | Промпт 1В + schema: определения + уровень operator | Изменение промпта и schema |
| 3 | Единица 2А: venue, не оператор | Изменение архитектуры запросов |
| 4 | Тесты классификации в LLM-постобработке уровня 2 | Добавление инструкции |
| 5 | Контекстный блок в промптах уровня 3 | Добавление в шаблоны |
| 6 | Диаграмма зависимостей | Обновление |

---

*Патч к pipeline_v0_2.md. Дата: 2026-03-09.*
