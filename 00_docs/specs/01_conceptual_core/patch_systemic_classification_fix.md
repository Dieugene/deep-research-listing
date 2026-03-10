# Патч: системные исправления по итогам эскалации LSE
## Устранение корневых причин ошибок классификации

**Дата:** 2026-03-09
**Контекст:** Эскалация от Tech Lead: LLM некорректно классифицирует UKLR-категории LSE как listing_tier. Анализ показал, что проблема не в данных LSE, а в трёх системных пробелах, которые будут воспроизводиться на других юрисдикциях.

---

## Корневая причина 1: Level 2 смешивает структуру площадки и организацию по классам инструментов

### Диагноз

Промпт уровня 2 спрашивает у LLM: «какие тиры и сегменты есть на этой площадке?». LLM находит UKLR-категории (ESCC, CEF, Debt, DR и т.д.) и, не имея другого подходящего контейнера, маркирует их как listing_tier. Это происходит потому, что промпт предполагает: всё, что организует правила допуска на площадке, — это либо tier, либо segment. Но UKLR-категории — ни то, ни другое. Это организация правил **по классу инструментов**, что является не свойством площадки (уровень 2), а основанием для порождения ячеек (уровень 3).

### Почему это системная проблема

LSE — не единичный случай. Многие площадки организуют правила допуска по главам rulebook, каждая из которых посвящена отдельному классу инструментов (equities, debt, funds). Если промпт не разделяет эти два вопроса, LLM будет повторять ту же ошибку на SGX, HKEX, JPX и т.д.

### Исправление

Промпт уровня 2 должен задавать **два раздельных вопроса** вместо одного:

**Вопрос A (структура площадки):** «Есть ли на площадке иерархия уровней листинга (тиры с разной строгостью требований для одного и того же класса инструментов)? Если да — перечислить. Есть ли специализированные сегменты (тематические надстройки поверх базовых правил)? Если да — перечислить.»

**Вопрос B (покрытие по инструментам):** «Какие классы инструментов допускаются на этой площадке? Для каждого класса — есть ли отдельная глава rulebook или отдельный набор правил допуска?»

Результат вопроса A → заполняет поля tier и segment в модели площадки.
Результат вопроса B → определяет перечень ячеек уровня 3 (venue × tier × instrument class).

**Ключевое правило для промпта (включить буквально):**

```
CRITICAL RULE — Instrument-class chapters are NOT tiers and NOT segments.
If a venue organizes its rulebook into chapters by instrument type (e.g., one
chapter for equities, one for debt, one for funds), these chapters are NOT
listing tiers and NOT segments. They define which instrument classes are
available on this venue and will be used to generate Level 3 research cells.

Report them in response to Question B (instrument class coverage), NOT in
response to Question A (tier/segment structure).

A listing tier is a hierarchy of STRICTNESS within the SAME instrument class.
If the venue has no such hierarchy — report "no listing tiers (flat structure)".
```

### Логика постпроцессинга

При обработке ответа уровня 2:
- Ответ на вопрос A → TierDef / SegmentDef (может быть пустым: `tiers: none`).
- Ответ на вопрос B → InstrumentCoverage (перечень классов/подклассов с указанием, есть ли отдельные правила).
- Генерация ячеек уровня 3: декартово произведение `venue × tier (или "flat") × instrument_class` из InstrumentCoverage.

---

## Корневая причина 2: DEF-G06 не разграничивает «флаг» и «отдельная ячейка» для вторичного допуска

### Диагноз

DEF-G06 утверждает: «Secondary admission is NOT a separate cell — record it as a property of the primary admission cell.» Это работает, когда вторичный допуск — это тот же набор требований с пониженными порогами. Но UKLR International Commercial Companies Secondary Listing — это принципиально иной режим: другие входные условия (наличие первичного листинга в признанной юрисдикции), режим regulatory equivalence, иная логика disclosure. Промпт не даёт LLM возможности различить эти два случая.

### Почему это системная проблема

Аналогичные конструкции есть в других юрисдикциях: SGX secondary listing, SIX secondary listing — у каждого свои правила, и они различаются по степени отличия от первичного допуска.

### Исправление

Обновить DEF-G06. Заменить текущее определение на:

```
DEFINITION — Secondary Admission (cross-listing / secondary listing):
Admission of a financial instrument to a venue where it is NOT primarily listed,
when the instrument is already admitted on another venue (domestic or foreign).

TWO CASES — determine which applies:

CASE 1 — MODIFIED PRIMARY REGIME: The venue applies the same admission regime
as for primary admission, but with reduced thresholds or exemptions from specific
requirements. The structure of requirements is the same; only values differ.
→ Record as a FLAG on the primary admission cell: secondary_admission_applicable=true,
  plus a list of specific modifications (which thresholds are reduced, which
  requirements are waived).
→ Do NOT create a separate cell.

CASE 2 — DISTINCT SECONDARY REGIME: The venue has a separate set of rules for
secondary admission with fundamentally different structure — different eligibility
criteria (e.g., requirement for primary listing in a "recognized jurisdiction"),
equivalence-based assessment, or substantially different procedures.
→ Record as a SEPARATE CELL with secondary_admission=true and distinct_regime=true.
→ Run full Level 3 research on this cell.

TEST: Can the secondary admission requirements be described as "same as primary,
except [list of reduced thresholds]"? If yes → Case 1 (flag). If the requirements
have a fundamentally different STRUCTURE, not just different VALUES → Case 2
(separate cell).
```

---

## Корневая причина 3: отсутствие концепции legacy/grandfathering-категорий

### Диагноз

UKLR Equity Shares — Transition — гранdfathering-категория, в которую невозможен новый листинг. LLM обрабатывает её наравне с действующими категориями, тратя ресурсы на полное L3-исследование.

### Почему это системная проблема

Регуляторные реформы происходят регулярно. Переходные категории, legacy-режимы, «закрытые для новых эмитентов» уровни — типичное явление. Без обработки этого случая каждая реформа будет порождать ненужные ячейки.

### Исправление

Добавить в промпт уровня 2 явный вопрос:

```
QUESTION — Legacy categories:
Are there any listing categories, tiers, or segments on this venue that are
CLOSED to new admissions (grandfathering/transition categories created by
regulatory reform, where existing issuers remain but no new admissions are
accepted)?

If yes — list them with:
- Name of the legacy category
- Date when it was closed to new admissions
- What category/tier existing issuers are expected to transition to (if any)
- Whether the legacy category has its own continuing obligations that differ
  from the target category

Mark these as legacy=true.
```

Логика постпроцессинга:
- Если `legacy=true` → ячейка создаётся, но L3-промпты генерируются только для фаз Г07.2 (поддержание) и Г07.4 (исключение). Фаза Г07.1 (первичный допуск) пропускается.

---

## Корневая причина 4: разграничение модификатора (Г08) и отдельной ячейки

### Диагноз

Shell Companies в UKLR — это не отдельный класс инструментов и не тир. Это модификатор (Г08): тот же класс инструментов (equities), но с изменёнными требованиями для специфического типа эмитента. Текущий промпт не даёт LLM инструмента для такого разграничения, и Shell Companies маркируется наравне с ESCC.

### Исправление

DEF-G08 уже содержит правильный тест («changes WHO is eligible, not WHERE the issuer is listed»), но он не интегрирован в логику промпта уровня 2. Нужно включить в промпт явную инструкцию:

```
CLASSIFICATION RULE — Modifier vs. instrument class:
If a separate chapter/category of the rulebook applies to a specific TYPE OF
ISSUER (e.g., shell companies, SPACs, biotech without revenue, companies with
weighted voting rights) while the INSTRUMENT CLASS remains the same (equities)
— classify this as an admission regime modifier (DEF-G08), NOT as a separate
instrument class.

Report modifiers separately from instrument classes. Modifiers will be recorded
as adjustments to the base cell, not as additional cells.

Example: "Equity Shares – Shell Companies" → instrument class = equities,
modifier = shell_company. NOT a separate instrument class.
```

Логика постпроцессинга:
- Модификатор не порождает отдельную ячейку. Вместо этого — в ячейке `venue × tier × equities` добавляется поле `modifiers: [shell_company, spac, wvr, ...]`.
- При генерации L3-промптов для ячейки с модификаторами — в промпт добавляется вопрос: «Как изменяются требования для [modifier type] по сравнению со стандартным режимом?».

---

## Сводка изменений

| # | Что меняется | Где | Тип изменения |
|---|-------------|-----|---------------|
| 1 | Разделение вопросов A (структура) и B (инструменты) в промпте уровня 2 | Промпт L2 | Переформулировка промпта |
| 2 | Правило: instrument-class chapters ≠ tiers | Промпт L2 (вставка) | Новое правило в промпте |
| 3 | Логика генерации ячеек: из InstrumentCoverage, а не из TierDef | Постпроцессинг L2 → L3 | Изменение логики |
| 4 | DEF-G06: два случая (flag vs. separate cell) с тестом | Определения (prompt-ready) | Обновление определения |
| 5 | Вопрос о legacy-категориях в промпте уровня 2 | Промпт L2 | Новый вопрос |
| 6 | Логика: legacy=true → L3 только по фазам Г07.2 и Г07.4 | Постпроцессинг L2 → L3 | Новая логика |
| 7 | Правило: modifier vs. instrument class в промпте уровня 2 | Промпт L2 (вставка) | Новое правило в промпте |
| 8 | Логика: модификаторы → поле в ячейке, а не отдельная ячейка | Постпроцессинг L2 → L3 | Изменение логики |

---

## Ожидаемый результат для LSE Main Market после исправлений

**Уровень 2, вопрос A (структура):**
- Tiers: none (flat structure since UKLR 2024)
- Segments: [SFS, HGS, Shanghai-London Stock Connect, SBM]

**Уровень 2, вопрос B (инструменты):**
- Instrument classes: equities, closed-end funds, depositary receipts, debt
- Modifiers: shell_company, transition (legacy=true)
- Distinct secondary regime: International Commercial Companies Secondary Listing (secondary_admission=true, distinct_regime=true)

**Генерация ячеек уровня 3:**
- `Main Market × flat × equities` (modifiers: shell_company; secondary: International → separate cell)
- `Main Market × flat × closed-end funds`
- `Main Market × flat × depositary receipts`
- `Main Market × flat × debt`
- `Main Market × flat × equities [secondary, distinct regime]`
- `Main Market × flat × equities [transition, legacy=true]` → L3 только по Г07.2/Г07.4

**Итого:** 6 ячеек (вместо 11), каждая семантически корректна.

---

*Патч подлежит применению до повторного процессинга. После применения — повторный L2 для LSE Main Market с проверкой результата.*
