# Отчёт: Level 2 постпроцессинг — результаты пилота

**Дата запуска:** 2026-03-09
**Площадки:** LSE_Main_Market, LSE_AIM, Aquis_Stock_Exchange, HKEX_Main_Board, HKEX_GEM
**Применённые патчи:** patch_systemic_classification_fix.md, patch_att_only_and_defg04.md, interface_patch_issuer_eligibility.md
**Адресат:** Разработчик концептуальной модели (Architect)

---

## 1. Что запускалось и как

### Входные данные
Для каждой площадки уже существовал файл `2A_structure.json` — результат Deep Research запроса через Parallel API. Постпроцессинг читает эти данные и не требует повторного запуска Parallel.

### Stage 1: Извлечение VenueCard

**Метод:** `chain.batch()` (LangChain, `with_structured_output`, `method="function_calling"`), `max_concurrency=5`, все 5 площадок одновременно.

**Промпт:** `_build_venue_prompt()` в `postprocess.py`. Структура:
1. Контекст юрисдикции (Level 1 jurisdiction_card.json)
2. Исходные данные Deep Research (2A_structure.json)
3. Блок определений: CRITICAL RULE (instrument-class chapters ≠ tiers), DEF-A05 (Listing Tier), DEF-A04 (Specialized Segment), DEF-G08 (Admission Regime Modifier), DEF-G06 (Secondary Admission, Case 1 vs Case 2), DEF-G04 (Listing/Admission Architecture), вопрос о legacy-категориях
4. Два раздельных вопроса:
   - **Question A** → структура площадки (тиры и сегменты) → поле `tiers` в VenueCard
   - **Question B** → покрытие по инструментам → поле `instrument_coverage` в VenueCard

**Время:** ~1 мин 49 сек (5 площадок одновременно)

**Выходные данные:** `venue_card.json` для каждой площадки

### Stage 2: Генерация ячеек и L3 промптов

**Метод:** `llm.batch()` (LangChain), `max_concurrency=50`, все ячейки всех площадок одновременно.

**Логика генерации ячеек:** ячейки порождаются из `VenueCard.instrument_coverage` (Question B), а НЕ из `VenueCard.tiers`. Каждая запись в `instrument_coverage` = одна ячейка.

**Промпты:** meta-шаблоны 3A / 3B / 3C. 3D упразднён. Логика:
- Обычная ячейка → 3A (overview) + 3B (continuing obligations/delisting) + 3C (monitoring/enforcement)
- Legacy-ячейка (`legacy=true`) → только 3A с ограниченным скоупом (только continuing obligations + delisting/migration)
- Case 1 secondary (`secondary_admission_applicable=true, distinct_regime=false`) → стандартный 3A + подвопрос о пониженных порогах
- Case 2 distinct_regime → стандартный 3A/3B/3C (как любая другая ячейка)

**Время:** ~4 мин 2 сек (68 промптов, batch)

**Всего:** 24 ячейки, 68 L3 промптов, 0 ошибок

---

## 2. Результаты по площадкам

### 2.1 LSE Main Market (regulated_market)

**Оператор:** London Stock Exchange plc
**Архитектура:** split (FCA Official List + LSE ADS — две процедуры, два органа)
**Тиры (Question A):** отсутствуют (flat structure с реформы UKLR 2024)
**Сегменты (Question A):** SFS, HGS, Shanghai–London Stock Connect, SBM — информационные метаданные, ячеек не порождают

**Question B → 9 ячеек:**

| cell_id | instrument_class | флаги | промпты |
|---|---|---|---|
| GB_LSE_Main_Market_equity | equity | mod=[shell_company] | 3A/3B/3C |
| GB_LSE_Main_Market_equity_shares_international_co_equity | equity | distinct_regime | 3A/3B/3C |
| GB_LSE_Main_Market_equity_shares_transition_equity | equity | legacy | 3A only |
| GB_LSE_Main_Market_..._equity (ATT Only) | equity | admission_path=trading_only | 3A/3B/3C |
| GB_LSE_Main_Market_fund | fund | — | 3A/3B/3C |
| GB_LSE_Main_Market_..._fund (ATT Only) | fund | admission_path=trading_only | 3A/3B/3C |
| GB_LSE_Main_Market_depositary_receipt | depositary_receipt | — | 3A/3B/3C |
| GB_LSE_Main_Market_..._depositary_receipt (ATT Only) | depositary_receipt | admission_path=trading_only | 3A/3B/3C |
| GB_LSE_Main_Market_bond | bond | — | 3A/3B/3C |

**Классификационные решения:**
- Shell Companies (UKLR) → `modifiers=["shell_company"]` на equity-ячейке (не отдельная ячейка) ✅
- International Commercial Companies Secondary Listing → `distinct_regime=true`, отдельная ячейка ✅ (DEF-G06 Case 2)
- Equity Shares Transition → `legacy=true`, только 3A ✅
- ATT Only (ADS Schedule 6) → `admission_path="trading_only"` ✅ (не secondary listing по DEF-G06, не modifier по DEF-G08 — отдельный admission path)
- SFS, HGS, Shanghai-London, SBM → тематические сегменты в `tiers[]`, ячеек не порождают ✅

**⚠️ Вопрос для Architect:** ATT Only применён к 3 классам (equity, fund, DR). Патч ожидал 6 ячеек; получилось 9 за счёт 3 ATT Only ячеек. Вопрос: должен ли ATT Only рождать одну инструмент-независимую ячейку (т.к. правила ADS Schedule 6 одинаковы для всех классов) или отдельную на каждый класс (т.к. L3 исследование различается по классам)?

---

### 2.2 LSE AIM (MTF)

**Оператор:** London Stock Exchange plc
**Архитектура:** split, но AIM — pure MTF без Official List → все пути admission_path=trading_only
**Тиры (Question A):** отсутствуют
**Сегменты (Question A):** отсутствуют

**Question B → 2 ячейки:**

| instrument_class | флаги | промпты |
|---|---|---|
| equity | admission_path=trading_only, mod=[investing_company, mining_oil_gas, new_business_lock_in] | 3A/3B/3C |
| equity | distinct_regime, admission_path=trading_only (AIM Designated Market Route) | 3A/3B/3C |

**Классификационные решения:**
- AIM принимает только акции (equity) — 2 ячейки ✅
- Investing company, mining/oil-gas, new_business_lock_in → модификаторы ✅
- AIM Designated Market Route → `distinct_regime=true` (упрощённый вторичный допуск для компаний с листингом на Designated Market; другие правила) ✅
- `admission_path=trading_only` на обеих ячейках — MTF без Official List ✅

**⚠️ Замечание:** флаг `admission_path=trading_only` на ВСЕХ ячейках MTF — логически корректно (MTF = trading only), но возможна семантическая нагрузка отличается от LSE Main Market, где trading_only = альтернативный путь. Рекомендую Architect рассмотреть, нужен ли дополнительный флаг `venue_architecture=MTF` для разграничения.

---

### 2.3 Aquis Stock Exchange (regulated_market)

**Оператор:** Aquis Stock Exchange Limited
**Архитектура:** split (требует FCA Official List — в отличие от AIM)
**Тиры (Question A):** отсутствуют
**Сегменты (Question A):** отсутствуют

**Question B → 6 ячеек:**

| instrument_class | флаги | промпты |
|---|---|---|
| equity | mod=[shell_company] | 3A/3B/3C |
| equity | distinct_regime (UKLR 14 International Secondary) | 3A/3B/3C |
| equity | legacy (Transition) | 3A only |
| fund | — | 3A/3B/3C |
| bond | — | 3A/3B/3C |
| depositary_receipt | — | 3A/3B/3C |

**Классификационные решения:**
- Структура аналогична LSE Main Market (те же UKLR категории), но БЕЗ ATT Only — Aquis как регулируемый рынок требует включения в FCA Official List ✅
- Нет секций SFS/HGS/SBM (Aquis не имеет таких сегментов) ✅
- Legacy Transition-категория корректно унаследована от UKLR реформы ✅

---

### 2.4 HKEX Main Board (regulated_market)

**Оператор:** The Stock Exchange of Hong Kong Limited (SEHK)
**Архитектура:** merged (листинг + допуск к торгам — единая процедура; SFC сохраняет право возражения по Cap.571V s.6)
**Тиры (Question A):** отсутствуют
**Сегменты (Question A):** отсутствуют

**Question B → 5 ячеек:**

| instrument_class | флаги | промпты |
|---|---|---|
| equity | mod=[WVR (Ch.8A), biotech_pre_revenue (Ch.18A), SPAC (Ch.18B), specialist_technology (Ch.18C)] | 3A/3B/3C |
| equity | distinct_regime (Ch.19C Secondary Listing, Qualifying Exchanges) | 3A/3B/3C |
| bond | mod=[chapter_37_professional_only_debt, retail_debt (Ch.22–36)] | 3A/3B/3C |
| fund | mod=[ETF (Ch.20), CIS (SFC UT Code), REIT (SFC REIT Code), Closed-end (Ch.21)] | 3A/3B/3C |
| depositary_receipt | — (HDR, Ch.19B) | 3A/3B/3C |

**Классификационные решения:**
- WVR, Biotech, SPAC, Specialist Tech → модификаторы ✅ (именно то, что исправлял патч)
- Chapter 19C overseas secondary listing → `distinct_regime=true` ✅ (DEF-G06 Case 2)
- Нет `admission_path=trading_only` — merged архитектура ✅
- ETF/CIS/REIT/closed-end → модификаторы на fund-ячейке ✅

**⚠️ Вопрос для Architect:** Chapter 37 (professional-only debt) и Chapters 22–36 (retail debt) классифицированы как **модификаторы** на bond-ячейке. Но разница между ними существенна (разные target audience, разные правила disclosure). Должны ли они быть отдельными ячейками (аналогично тому, как International Secondary — отдельная ячейка для equity)? Тест: «Can retail debt requirements be described as 'same as professional, except [list of reduced/changed thresholds]'?» — если нет → Case 2, отдельная ячейка.

---

### 2.5 HKEX GEM (regulated_market)

**Оператор:** The Stock Exchange of Hong Kong Limited (SEHK)
**Архитектура:** merged
**Тиры (Question A):** отсутствуют
**Сегменты (Question A):** отсутствуют

**Question B → 2 ячейки:**

| instrument_class | флаги | промпты |
|---|---|---|
| equity | — | 3A/3B/3C |
| bond | — | 3A/3B/3C |

**Классификационные решения:**
- GEM — equity-focused; fund и DR только на Main Board ✅
- Нет secondary listing режима ✅
- Streamlined transfer to Main Board (Rule 9.24) → modifier (не ячейка) ✅

---

## 3. Сводная таблица

| Площадка | Тип | Тиры | Ячеек | L3 промптов | ATT Only | distinct_regime | legacy | Ключевые модификаторы |
|---|---|---|---|---|---|---|---|---|
| LSE_Main_Market | regulated_market | нет (flat) | 9 | 26 | equity/fund/DR | International Secondary | Transition | shell_company |
| LSE_AIM | MTF | нет | 2 | 6 | все (MTF) | Designated Market Route | нет | investing_company, mining, new_business |
| Aquis | regulated_market | нет | 6 | 17 | нет | International Secondary | Transition | shell_company |
| HKEX_Main_Board | regulated_market | нет | 5 | 15 | нет | Ch.19C Secondary | нет | WVR/Biotech/SPAC/SpecTech; ETF/CIS/REIT; Ch.37 debt |
| HKEX_GEM | regulated_market | нет | 2 | 6 | нет | нет | нет | transfer_to_main_board |
| **Итого** | | | **24** | **68** | | | | |

---

## 4. Архитектурные вопросы для Architect

### В01. ATT Only: одна ячейка или per-instrument-class?
**Факт:** ATT Only создал 3 ячейки (equity, fund, DR) на LSE Main Market. Патч ожидал ~6 ячеек итого; вышло 9.
**Вопрос:** Нужно ли ввести правило «admission_path=trading_only без instrument-class специфики → одна ячейка», или per-class правильно?

### В02. admission_path=trading_only на MTF
**Факт:** Все AIM-ячейки получили `admission_path=trading_only`, т.к. AIM — MTF без Official List.
**Вопрос:** Для MTF trading_only — это «архитектурная черта площадки» (venue_type=MTF), а не «отдельный path» как на Main Market. Нужно ли разграничить эти два случая (например, флаг `is_trading_only_venue` на VenueCard вместо поля на каждой ячейке)?

### В03. HKEX bonds: модификаторы или отдельные ячейки?
**Факт:** Chapter 37 (professional) и Ch.22–36 (retail) — модификаторы на одной bond-ячейке.
**Вопрос:** Применяется ли DEF-G06 Case 2 тест к классам инструментов внутри одного instrument_class? Если professional и retail debt принципиально разные режимы (не просто «те же правила, пониженные пороги») → два отдельных bond-ячейки.

### В04. Сегменты (SFS, HGS, Shanghai-London, SBM) не порождают ячеек
**Факт:** Эти тематические сегменты хранятся в `venue_card.tiers[]` (segment_type=thematic_segment) как метаданные. L3-исследование по ним не запускается.
**Вопрос:** Это намеренное решение или SFS/HGS требуют собственных ячеек? SFS, например, формально не входит в FCA Official List — у него другие правила допуска.

---

## 5. Технические результаты прогона

| Параметр | Значение |
|---|---|
| VenueCard extraction | chain.batch(), max_concurrency=5, ~1 мин 49 сек |
| L3 prompt generation | llm.batch(), max_concurrency=50, ~4 мин 2 сек |
| Общее время | ~6 мин |
| Ошибки | 0 |
| exit code | 0 |
| 3D промптов | 0 (упразднён) |
| Legacy-ячейки только с 3A | 2 (LSE_Main_Market Transition, Aquis Transition) |

---

*Документ сформирован по итогам пилота Level 2. Дата: 2026-03-09.*
