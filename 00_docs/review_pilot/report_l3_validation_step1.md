# Отчёт аналитика: L3-валидация — Шаг 1 (общая картина)

**Дата:** 2026-03-10
**Аналитик:** Claude Code (Sonnet 4.6)
**Назначение:** Передача архитектору — разбивка 38 упавших ячеек L3-валидации

---

## Итог

Из **74 L3-ячеек** (5 venue × instrument_class × query_type):
- **38 FAILED** (overall_flag = True)
- **36 PASSED**

---

## Полная таблица упавших ячеек (38 штук)

| # | Cell | QT | scope_ok | compl. | source_ok | Причина флага |
|---|------|----|:--------:|:------:|:---------:|---------------|
| 1 | LSE_Main_Market / commercial_compa / equity | 3C | ✅ | 1.00 | ❌ | source=F; ambiguous UKLR citations для sponsor |
| 2 | LSE_Main_Market / international_co / equity | 3A | ✅ | 0.50 | ❌ | source=F; completeness граница; нет market cap, corp gov |
| 3 | LSE_Main_Market / international_co / equity | 3B | ✅ | 0.60 | ❌ | source=F; DTR/MAR не атрибутированы |
| 4 | LSE_Main_Market / international_co / equity | 3C | ✅ | 1.00 | ❌ | source=F; DTR/UKLR применены неверно для secondary listing |
| 5 | LSE_Main_Market / transition / equity | 3A | ✅ | 0.25 | ✅ | completeness<0.5; UKLR 22 — legacy, нет новых эмитентов |
| 6 | LSE_Main_Market / att_equity | 3A | ❌ | 0.38 | ❌ | scope=F + source=F; мешает UKLR с ATT Only rulebook |
| 7 | LSE_Main_Market / att_equity | 3B | ✅ | 0.30 | ✅ | completeness<0.5 |
| 8 | LSE_Main_Market / att_equity | 3C | ❌ | 1.00 | ✅ | scope=F; ссылается на MTF surveillance, не Main Market |
| 9 | LSE_Main_Market / att_bond | 3A | ❌ | 1.00 | ❌ | scope=F + source=F; UKLR/Official List для ATT-только пути |
| 10 | LSE_Main_Market / att_bond | 3C | ✅ | 0.25 | ✅ | completeness<0.5 |
| 11 | LSE_Main_Market / closed_ended_investment_fund | 3A | ✅ | 0.40 | ✅ | completeness<0.5; нет NAV/AUM, fund structure, mgmt company |
| 12 | LSE_Main_Market / closed_ended_investment_fund | 3B | ❌ | 0.25 | ✅ | scope=F; generic Main Market, не fund-specific; completeness<0.5 |
| 13 | LSE_Main_Market / fund_sfs | 3A | ✅ | 0.40 | ✅ | completeness<0.5; нет NAV/AUM, fund structure |
| 14 | LSE_Main_Market / fund_sfs | 3B | ✅ | 0.25 | ✅ | completeness<0.5; blank sources |
| 15 | LSE_Main_Market / depositary_receipts / DR | 3B | ✅ | 1.00 | ❌ | source=F; PwC secondary source вместо primary rulebook |
| 16 | LSE_Main_Market / att_depositary_receipt | 3C | ❌ | 1.00 | ❌ | scope=F + source=F; FCA LR/DTR применены к ATT Only |
| 17 | LSE_AIM / equity | 3B | ✅ | 0.40 | ✅ | completeness<0.5; нет inside info, free float, corp gov |
| 18 | **Aquis** / equity | 3A | ❌ | 0.75 | ❌ | scope=F + source=F; цитирует UKLR/FCA вместо AQSE ADS |
| 19 | **Aquis** / equity | 3B | ❌ | 0.50 | ❌ | scope=F + source=F; Aquis Access rulebook (другой сегмент) |
| 20 | **Aquis** / equity | 3C | ❌ | 1.00 | ❌ | scope=F + source=F; "Main Market tier" несовместим с flat AQSE |
| 21 | **Aquis** / international_co / equity | 3B | ❌ | 0.60 | ❌ | scope=F + source=F; FCA/UKLR смешаны с AQSE |
| 22 | **Aquis** / transition / equity | 3A | ✅ | 0.25 | ❌ | completeness<0.5 + source=F; FCA/AQSE смешаны |
| 23 | **Aquis** / bond | 3A | ❌ | 1.00 | ❌ | scope=F + source=F; FCA/Official List вместо AQSE |
| 24 | **Aquis** / bond | 3B | ✅ | 0.50 | ❌ | source=F; подозрительные UKLR-цитаты для AQSE |
| 25 | **Aquis** / bond | 3C | ❌ | 0.50 | ❌ | scope=F + source=F; "FCA Official List, NSM, Main Market" |
| 26 | **Aquis** / fund | 3A | ❌ | 0.80 | ❌ | scope=F + source=F; labeled "Main Market", цитирует UKLR |
| 27 | **Aquis** / fund | 3B | ❌ | 0.25 | ❌ | scope=F + source=F + completeness<0.5 |
| 28 | **Aquis** / depositary_receipt | 3A | ❌ | 0.75 | ❌ | scope=F + source=F; FCA UKLR/PRM вместо AQSE |
| 29 | **Aquis** / depositary_receipt | 3B | ❌ | 0.75 | ❌ | scope=F + source=F; blank sources |
| 30 | **Aquis** / depositary_receipt | 3C | ✅ | 1.00 | ❌ | source=F; "LSE Guide to DRs" — не тот venue |
| 31 | HKEX_Main_Board / equity | 3A | ✅ | 0.25 | ✅ | completeness<0.5; усечённый результат |
| 32 | HKEX_Main_Board / 19C_secondary / equity | 3C | ✅ | 1.00 | ❌ | source=F; generic Listing Rules, не Chapter 19C |
| 33 | HKEX_Main_Board / **HDR** / depositary_receipt | 3A | ❌ | 0.25 | ❌ | scope=F + source=F; Chapter 19C вместо Chapter 19B |
| 34 | HKEX_Main_Board / **HDR** / depositary_receipt | 3B | ✅ | 1.00 | ❌ | source=F; общие главы 6, 13 вместо Chapter 19B |
| 35 | HKEX_Main_Board / **HDR** / depositary_receipt | 3C | ✅ | 1.00 | ❌ | source=F; generic enforcement, не Chapter 19B |
| 36 | HKEX_GEM / equity | 3B | ✅ | 0.30 | ✅ | completeness<0.5; нет inside info, corp gov, delisting |
| 37 | HKEX_GEM / bond | 3A | ❌ | 1.00 | ❌ | scope=F + source=F; Main Board rule numbers (27.xx, 29.02) в GEM |
| 38 | HKEX_GEM / bond | 3C | ✅ | 0.50 | ❌ | source=F; правила 30.39A/30.40B могут быть Main Board |

---

## Разбивка по паттернам

### Паттерн 1: source_ok=False — главная причина (17 ячеек)

Ячейки с scope=True, completeness≥0.5, но source=False:

| Cell | QT | compl. | Диагноз |
|------|----|--------|---------|
| LSE MM / commercial_compa / equity | 3C | 1.00 | Ambiguous sponsor citations |
| LSE MM / international_co / equity | 3A | 0.50 | DTR/MAR без атрибуции |
| LSE MM / international_co / equity | 3B | 0.60 | DTR/MAR без атрибуции |
| LSE MM / international_co / equity | 3C | 1.00 | UKLR неверно для secondary |
| LSE MM / depositary_receipts / DR | 3B | 1.00 | PwC вместо primary rulebook |
| Aquis / bond | 3B | 0.50 | UKLR в AQSE ячейке |
| Aquis / depositary_receipt | 3C | 1.00 | LSE Guide вместо AQSE |
| HKEX MB / 19C_secondary / equity | 3C | 1.00 | Generic LR, не Chapter 19C |
| HKEX MB / HDR | 3B | 1.00 | Главы 6, 13 вместо 19B |
| HKEX MB / HDR | 3C | 1.00 | Generic enforcement, не 19B |
| HKEX GEM / bond | 3C | 0.50 | Rule numbers 30.xx подозрительны |

**Гипотезы:** (а) валидатор слишком строг и не знает точных ожидаемых глав; (б) Parallel действительно не нашёл нужные главы. Нужен Шаг 2 для разбора.

---

### Паттерн 2: Aquis — провалы по scope+source (13 ячеек из 16)

Все 5 venue Aquis кроме:
- `international_co` 3A (PASSED) и 3C (PASSED)
- `fund` 3C (PASSED)

**Диагноз:** Parallel возвращает контент по FCA UKLR/LSE вместо AQSE Exchange Listing Rules. LLM-постобработка разносит данные не на тот rulebook. Требует:
1. Проверки `3A_raw.json` Aquis до постобработки (Шаг 3).
2. Проверки промпта — достаточно ли чётко «Aquis Stock Exchange, NOT London Stock Exchange».

**Уточнение:** У `Aquis / transition` найден только 3A (нет 3B/3C файлов) — значит логика исключения L3-B/C для legacy работает.

---

### Паттерн 3: completeness < 0.5 без scope/source проблем (8 ячеек)

| Cell | QT | compl. | Топики отсутствуют |
|------|----|--------|--------------------|
| LSE MM / transition / equity | 3A | 0.25 | market cap, financial history, profitability, corp gov, sponsor, lock-ups |
| LSE MM / att_equity | 3B | 0.30 | periodic reporting, free float, corp gov, suspension grounds |
| LSE MM / att_bond | 3C | 0.25 | monitoring body, trustee role, event of default |
| LSE MM / closed_ended_fund | 3A | 0.40 | NAV/AUM, fund structure, mgmt company |
| LSE MM / closed_ended_fund | 3B | 0.25 | NAV, portfolio, redemption suspension *(+scope=F)* |
| LSE MM / fund_sfs | 3A | 0.40 | NAV/AUM, fund structure |
| LSE MM / fund_sfs | 3B | 0.25 | NAV frequency, portfolio, redemption suspension |
| LSE AIM / equity | 3B | 0.40 | inside info, free float, corp gov, controlling shareholder, voluntary delisting |
| HKEX MB / equity | 3A | 0.25 | financial history, profitability, corp gov, sponsor, prospectus, lock-ups |
| HKEX GEM / equity | 3B | 0.30 | inside info, free float, corp gov, controlling shareholder, suspension |

**Диагноз:** Часть — ожидаемые пробелы (transition — legacy; att_bond — ATT Only путь с ограниченным rulebook); часть — реальные пробелы в данных (fund, HKEX equity). Нужна проверка raw по HKEX equity 3A (Шаг 5-аналог).

---

### Паттерн 4: HDR — все три query_type упали (3 ячейки)

| QT | scope_ok | compl. | source_ok | Диагноз |
|----|:--------:|:------:|:---------:|---------|
| 3A | ❌ | 0.25 | ❌ | Parallel нашёл Chapter 19C (secondary), не Chapter 19B (HDR) |
| 3B | ✅ | 1.00 | ❌ | Completeness OK, но источники — общие главы 6/13, не 19B |
| 3C | ✅ | 1.00 | ❌ | Completeness OK, но generic enforcement, не 19B |

**Диагноз:** 3A — scope-провал, Parallel перепутал HDR с secondary listing. 3B/3C — контент корректный, но источники не специфичны для Chapter 19B. Вероятно ожидаемый пробел (мало публичных данных по HDR).

---

## Дополнительные наблюдения

- У `LSE_Main_Market / transition` и `Aquis / transition` — только 3A-файлы (нет 3B/3C). Логика исключения L3-B/C для legacy-ячеек **работает**.
- `HKEX GEM / bond` 3A: scope=F с completeness=1.00 — подозрительное сочетание. Вероятно, Parallel вернул Main Board bond данные, LLM-постобработка признала их «полными», но источники — Main Board chapters.
- `LSE MM / att_*` клетки (equity, bond, DR) системно страдают от смешения UKLR с LSE ADS. Это отдельная архитектурная проблема: ATT Only путь требует своего промпта.

---

## Рекомендации для Шагов 2–5

| Шаг | Приоритет | Что смотреть |
|-----|-----------|-------------|
| **Шаг 2** | Высокий | 3–5 ячеек source=F при compl≥0.75: открыть `*_cell.json` + `*_raw.json` + промпт валидатора |
| **Шаг 3** | Высокий | Aquis `3A_raw.json` (любой instrument) — UKLR или AQSE в raw? |
| **Шаг 4** | Средний | `cells_list.json` LSE MM и Aquis — есть ли `legacy=true` для transition? |
| **Шаг 5** | Средний | HKEX HDR `3A_raw.json` — есть ли Chapter 19B в raw? |

---

*Шаг 1 завершён. Следующий — Шаг 2 (source check).*
