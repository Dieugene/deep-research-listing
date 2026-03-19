# Чеклист аудита: LSE_Main_Market
_Используется для отслеживания прохождения аудита. Обновляется по мере проверки._

## L2 — Страница площадки /venues/LSE_Main_Market

### Обзор страницы
- [ ] Название площадки: "Лондонская фондовая биржа — Основной рынок"
- [ ] Тип площадки: REG (regulated_market)
- [ ] Отображается ли venue_type корректно
- [ ] Список из 10 ячеек виден

### Источники L2 (ожидаются: 3 источника, 7 выдержек)
- [ ] Есть ли вкладка/секция «Источники» на странице площадки?
- [ ] Если есть: 3 источника? Все типа rulebook?
- [ ] Источник 1: "London Stock Exchange Admission and Disclosure..." (5 выдержек)
- [ ] Источник 2: "UKLR 1.1 Introduction - FCA Handbook" (1 выдержка)
- [ ] Источник 3: "N01/26 - Amendments to LSE A&D Standards..." (1 выдержка)

---

## L3 — Ячейки (по одной странице на каждую)

### EQUITY-1: equity_shares_commercial_compa_equity
_URL: /venues/LSE_Main_Market/GB_LSE_Main_Market_equity_shares_commercial_compa_equity_

#### Вкладка Допуск (3A)
Ожидаемые источники по секциям:
- [instrument_requirements]: 2 src, 4 exc (UKLR 22, LSE ADS)
- [admission_overview]: 2 src, 2 exc
- [additional_findings]: 1 src, 0 exc
- [disclosure_at_admission]: 1 src, 0 exc

**Проверки:**
- [ ] instrument_requirements секция: показывает «2 источника · 4 выдержки»?
- [ ] admission_overview секция: показывает «2 источника · 2 выдержки»?
- [ ] additional_findings секция: показывает «1 источник»?
- [ ] disclosure_at_admission: показывает «1 источник»?
- [ ] Параметры правильно отфильтрованы по section_keys (NOT все параметры в каждой секции)?

#### Вкладка Поддержание (3B)
- [additional_findings]: 1 src, 1 exc
- [suspension]: 1 src, 2 exc
- [continuing_obligations]: 2 src, 3 exc

**Проверки:**
- [ ] suspension секция: показывает «1 источник · 2 выдержки»?
- [ ] continuing_obligations секция: показывает «2 источника · 3 выдержки»?

#### Вкладка Исключение (3C)
- [additional_findings]: 2 src, 0 exc
- [sanctions]: 1 src, 0 exc
- [monitoring_regime]: 1 src, 0 exc
- [enforcement_practice]: 1 src, 3 exc

**Проверки:**
- [ ] enforcement_practice секция: показывает «1 источник · 3 выдержки»?

#### Матрица
- [ ] Матрица открывается
- [ ] Параметры в ячейках видны
- [ ] Source pills в ячейках матрицы?

---

### BOND-1: debt_and_debtlike_securities_bond
_URL: /venues/LSE_Main_Market/GB_LSE_Main_Market_debt_and_debtlike_securities_bond_

#### Вкладка Допуск (3A)
- [instrument_requirements]: 3 src, 6 exc
- [admission_overview]: 1 src, 1 exc
- [additional_findings]: 1 src, 1 exc

**Проверки:**
- [ ] instrument_requirements: «3 источника · 6 выдержек»?
- [ ] admission_overview: «1 источник · 1 выдержка»?

#### Вкладка Поддержание (3B)
- [additional_findings]: 1 src, 0 exc
- [suspension]: 1 src, 1 exc

**Проверки:**
- [ ] suspension: «1 источник · 1 выдержка»?

#### Вкладка Исключение (3C)
- [additional_findings]: 2 src, 0 exc
- [sanctions]: 1 src, 1 exc
- [enforcement_practice]: 1 src, 1 exc

---

### FUND-1: fund_sfs
_URL: /venues/LSE_Main_Market/GB_LSE_Main_Market_fund_sfs_

#### Вкладка Допуск (3A)
- [instrument_requirements]: 1 src, 0 exc
- [eligibility_requirements]: 1 src, 4 exc
- [additional_findings]: 1 src, 0 exc

**Проверки:**
- [ ] eligibility_requirements: «1 источник · 4 выдержки»?

#### Вкладка Поддержание (3B)
- [additional_findings]: 2 src, 0 exc
- [delisting_voluntary]: 1 src, 0 exc
- [continuing_obligations]: 1 src, 1 exc

#### Вкладка Исключение (3C)
- [sanctions]: 1 src, 1 exc
- [enforcement_practice]: 2 src, 0 exc

---

### FUND-2: closed_ended_investment_funds_fund
_URL: /venues/LSE_Main_Market/GB_LSE_Main_Market_closed_ended_investment_funds_fund_

#### Вкладка Допуск (3A)
- [admission_overview]: 2 src, 2 exc
- [restrictions_and_lock_ups]: 1 src, 0 exc
- [disclosure_at_admission]: 1 src, 1 exc

**Проверки:**
- [ ] admission_overview: «2 источника · 2 выдержки»?
- [ ] disclosure_at_admission: «1 источник · 1 выдержка»?

---

### DR-1: depositary_receipts_depositary_receipt
_URL: /venues/LSE_Main_Market/GB_LSE_Main_Market_depositary_receipts_depositary_receipt_

#### Вкладка Допуск (3A)
- [additional_findings]: 1 src, 0 exc (⚠️ instrument_requirements отсутствует в цитатах!)

**Проверки:**
- [ ] Секция instrument_requirements: показывает 0 источников? Или это секция без цитат отображается без кнопки «источники»?

#### Вкладка Поддержание (3B)
- [additional_findings]: 1 src, 8 exc
- [continuing_obligations]: 1 src, 0 exc

**Проверки:**
- [ ] additional_findings: «1 источник · 8 выдержек»?

---

### EQUITY-2: equity_shares_transition_equity
_URL: /venues/LSE_Main_Market/GB_LSE_Main_Market_equity_shares_transition_equity_
_Особенность: только 3A (Допуск), нет 3B/3C файлов_

**Проверки:**
- [ ] Вкладки «Поддержание» и «Исключение» есть? Если есть — что показывают?
- [ ] instrument_requirements: 1 src, 0 exc
- [ ] eligibility_requirements: «2 источника · 2 выдержки»?
- [ ] disclosure_at_admission: «1 источник · 1 выдержка»?

---

### ATT cells (admission_to_trading_only)
_Три ячейки: att_bond, att_equity, att_depositary_receipt_

**Общие проверки для att_bond:**
_URL: /venues/LSE_Main_Market/GB_LSE_Main_Market_admission_to_trading_only_att_bond_
- [ ] instrument_requirements (3A): «4 источника · 4 выдержки»?
- [ ] restrictions_and_lock_ups (3A): «1 источник · 2 выдержки»?
- [ ] additional_findings (3B): «1 источник · 12 выдержек»?

---

### EQUITY-3: equity_shares_international_co_equity
_URL: /venues/LSE_Main_Market/GB_LSE_Main_Market_equity_shares_international_co_equity_

#### Вкладка Допуск (3A)
- [admission_overview]: 2 src, 5 exc
- [sponsor_and_infrastructure]: 1 src, 0 exc
- [disclosure_at_admission]: 2 src, 0 exc

**Проверки:**
- [ ] admission_overview: «2 источника · 5 выдержек»?

---

## Общие проверки (для всех ячеек)

### Ошибки, выявленные ранее (нужно подтвердить или снять)
- [ ] S4: «Fetched web page» как заголовок — встречается ли в других ячейках?
- [ ] S5: тип «ДРУГОЕ» для всех L3 источников — подтвердить для другой ячейки
- [ ] Bug #3 (section_keys): все ли параметры дублируются во все секции? (уже подтверждено для EQUITY-1)

### Общий UX
- [ ] Кнопка «показать» для выдержек (в inline-panel) — корректно раскрывает?
- [ ] Матрица: source pills в ячейках?
- [ ] Вид матрицы — все параметры видны?

---
## СТАТУС АУДИТА

| Страница | Проверено | Источники верны |
|---------|-----------|----------------|
| /venues/LSE_Main_Market | ☐ | ☐ |
| EQUITY-1 admission | ☐ | ☐ |
| EQUITY-1 maintenance | ☐ | ☐ |
| EQUITY-1 exclusion | ☐ | ☐ |
| EQUITY-1 matrix | ☐ | ☐ |
| BOND-1 admission | ☐ | ☐ |
| BOND-1 maintenance | ☐ | ☐ |
| BOND-1 exclusion | ☐ | ☐ |
| FUND-1 (sfs) admission | ☐ | ☐ |
| FUND-2 (closed-ended) admission | ☐ | ☐ |
| DR-1 (depositary) admission | ☐ | ☐ |
| EQUITY-2 (transition) admission | ☐ | ☐ |
| ATT-BOND admission | ☐ | ☐ |
| EQUITY-3 (international) admission | ☐ | ☐ |
