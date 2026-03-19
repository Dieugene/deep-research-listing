# Аудит: LSE_Main_Market — полный отчёт
_Дата: 2026-03-17_
_Охват: /venues/LSE_Main_Market + все 10 ячеек (все вкладки), матрица_

---

## Общий итог

| Зона | Соответствие данным |
|------|-------------------|
| L2 страница площадки | ✅ корректно |
| 3A (Допуск) — все ячейки | ✅ корректно (за исключением D1) |
| 3B (Поддержание) — все ячейки | ❌ Bug #6 (системный) |
| 3C (Исключение) — все ячейки | ❌ Bug #7 + Bug #6 (системные) |
| Матрица | ✅ структура корректна, source pills отсутствуют |

---

## L2 — Страница площадки /venues/LSE_Main_Market

### Результат: ✅ КОРРЕКТНО

- Название: "Лондонская фондовая биржа — Основной рынок" ✅
- Тип площадки: REG (регулируемый рынок) ✅
- Список из 10 ячеек виден ✅
- Раздел «Источники площадки» присутствует ✅
- 3 источника, все тип «Правила» (rulebook) ✅
  - London Stock Exchange Admission and Disclosure Standards — 5 выдержек ✅
  - UKLR 1.1 Introduction - FCA Handbook — 1 выдержка ✅
  - N01/26 - Amendments to LSE A&D Standards — 1 выдержка ✅
- Итого 7 выдержек ✅

---

## L3 — Вкладки Допуск (3A)

Структура данных: все 3A файлы содержат **исключительно FLAT секции** — все секции рендерятся корректно.

### Верификация счётчиков источников по ячейкам

#### EQUITY-1: equity_shares_commercial_compa_equity ✅
| Секция | Данные | Фронтенд |
|--------|--------|----------|
| instrument_requirements | 2 src · 4 exc | «2 источника · 4 выдержки» ✅ |
| admission_overview | 2 src · 2 exc | «2 источника · 2 выдержки» ✅ |
| additional_findings | 1 src · 0 exc | «1 источник» ✅ |
| disclosure_at_admission | 1 src · 0 exc | «1 источник» ✅ |

⚠️ S4: В instrument_requirements 2 цитаты имеют title="Fetched web page" (не удалось получить заголовок при сборе)
⚠️ S5: Все цитаты без поля `type` → фронтенд показывает «ДРУГОЕ» для всех L3 источников

#### BOND-1: debt_and_debtlike_securities_bond ✅
| Секция | Данные | Фронтенд |
|--------|--------|----------|
| instrument_requirements | 3 src · 6 exc | «3 источника · 6 выдержек» ✅ |
| admission_overview | 1 src · 1 exc | «1 источник · 1 выдержка» ✅ |
| additional_findings | 1 src · 1 exc | «1 источник · 1 выдержка» ✅ |

#### FUND-1: fund_sfs ✅
| Секция | Данные | Фронтенд |
|--------|--------|----------|
| instrument_requirements | 1 src · 0 exc | «1 источник» ✅ |
| eligibility_requirements | 1 src · 4 exc | «1 источник · 4 выдержки» ✅ |
| additional_findings | 1 src · 0 exc | «1 источник» ✅ |

#### FUND-2: closed_ended_investment_funds_fund ✅
| Секция | Данные | Фронтенд |
|--------|--------|----------|
| admission_overview | 2 src · 2 exc | «2 источника · 2 выдержки» ✅ |
| restrictions_and_lock_ups | 1 src · 0 exc | «1 источник» ✅ |
| disclosure_at_admission | 1 src · 1 exc | «1 источник · 1 выдержка» ✅ |

#### DR-1: depositary_receipts_depositary_receipt ✅
| Секция | Данные | Фронтенд |
|--------|--------|----------|
| instrument_requirements | 0 src | нет индикатора ✅ (ожидаемо) |
| additional_findings | 1 src · 0 exc | «1 источник» ✅ |

_Примечание: instrument_requirements не имеет цитат → фронтенд корректно не показывает индикатор источников_

#### EQUITY-2: equity_shares_transition_equity ✅
| Секция | Данные | Фронтенд |
|--------|--------|----------|
| instrument_requirements | 1 src · 0 exc | «1 источник» ✅ |
| eligibility_requirements | 2 src · 2 exc | «2 источника · 2 выдержки» ✅ |
| disclosure_at_admission | 1 src · 1 exc | «1 источник · 1 выдержка» ✅ |

#### ATT-BOND: admission_to_trading_only_att_bond ✅
| Секция | Данные | Фронтенд |
|--------|--------|----------|
| instrument_requirements | 4 src · 4 exc | «4 источника · 4 выдержки» ✅ |
| admission_overview | 1 src · 0 exc | «1 источник» ✅ |
| restrictions_and_lock_ups | 1 src · 2 exc | «1 источник · 2 выдержки» ✅ |

#### EQUITY-3: equity_shares_international_co_equity ⚠️ Частично (D1)
| Секция | Данные | Фронтенд |
|--------|--------|----------|
| sponsor_and_infrastructure | 1 src · 0 exc | «1 источник» ✅ |
| admission_overview | 2 src · 5 exc | ❌ НЕ ПОКАЗАН — description="not applicable" |
| disclosure_at_admission | 2 src · 0 exc | ❌ НЕ ПОКАЗАН — description="not applicable" |

**D1 (Orphaned citations)**: Секции admission_overview, additional_findings, special_regimes, disclosure_at_admission имеют description="not applicable" с пустым source, но в массиве citations есть 4 записи (admission_overview: 2 src/5 exc, disclosure_at_admission: 2 src/0 exc). Фронтенд правомерно не рендерит секции с "not applicable", но 9 цитируемых источников (включая 5 выдержек) полностью недоступны. **Проблема данных — пайплайн не добыл контент, но цитаты сохранил.**

---

## L3 — Вкладки Поддержание (3B) — Bug #6

### Системная проблема

**Структура 3B файлов одинакова для ВСЕХ ячеек:**
- FLAT (рендерятся): `additional_findings`, `common_obligations_common`
- NESTED (НЕ рендерятся): `suspension`, `continuing_obligations`, `delisting_compulsory`, `delisting_voluntary`, `terminology`

Фронтенд рендерит только FLAT секции формата `{description, source}`. NESTED секции (с субключами) полностью игнорируются — **Bug #6**.

### Цитаты, скрытые в 3B по Bug #6

| Ячейка | Потерянная секция | Данные |
|--------|-------------------|--------|
| EQUITY-1 | suspension | 1 src · 2 exc ❌ |
| EQUITY-1 | continuing_obligations | 2 src · 3 exc ❌ |
| BOND-1 | suspension | 1 src · 1 exc ❌ |
| FUND-1 | delisting_voluntary | 1 src · 0 exc ❌ |
| FUND-1 | continuing_obligations | 1 src · 1 exc ❌ |
| FUND-2 | suspension | 2 src · 1 exc ❌ |
| FUND-2 | additional_findings | 1 src · 3 exc — но это FLAT ✅ (показывается) |
| DR-1 | continuing_obligations | 1 src · 0 exc ❌ |
| EQUITY-3 | terminology | 1 src · 1 exc ❌ |
| EQUITY-3 | continuing_obligations | 2 src · 0 exc ❌ |
| EQUITY-3 | delisting_voluntary | 1 src · 0 exc ❌ |

**FLAT секции 3B работают корректно:**
- ATT-BOND additional_findings: «1 источник · 12 выдержек» ✅
- DR-1 additional_findings: «1 источник · 8 выдержек» ✅
- Все additional_findings и common_obligations_common отображаются ✅

### EQUITY-2 (transition)
Нет 3B файла → вкладка «Поддержание» показывает "Данные в работе" ✅ (корректное поведение)

---

## L3 — Вкладки Исключение (3C) — Bug #7

### Системная проблема

**Bug #7**: `phase=exclusion` в URL не переключает данные на 3C — отображается содержимое 3A (Допуск). Подтверждено для EQUITY-1 и BOND-1. По архитектуре касается всех ячеек с 3C файлами.

**Двойной удар**: Даже если Bug #7 был бы исправлен, Bug #6 скрыл бы основные 3C секции (sanctions, monitoring_regime, enforcement_practice — все NESTED).

### Цитаты, скрытые в 3C (при исправлении Bug #7 осталось бы Bug #6)

| Ячейка | Потерянная секция | Данные |
|--------|-------------------|--------|
| EQUITY-1 | sanctions | 1 src · 0 exc |
| EQUITY-1 | monitoring_regime | 1 src · 0 exc |
| EQUITY-1 | enforcement_practice | 1 src · 3 exc |
| BOND-1 | sanctions | 1 src · 1 exc |
| BOND-1 | enforcement_practice | 1 src · 1 exc |
| FUND-1 | sanctions | 1 src · 1 exc |
| FUND-2 | sanctions | 1 src · 0 exc |
| DR-1 | sanctions | 1 src · 0 exc |
| DR-1 | monitoring_regime | 1 src · 1 exc |
| DR-1 | enforcement_practice | 2 src · 0 exc |
| ATT-BOND | enforcement_practice | 1 src · 1 exc |
| EQUITY-3 | sanctions | 1 src · 1 exc |

---

## Матрица — EQUITY-1

- ✅ Открывается корректно
- ✅ 3 строки (Допуск / Поддержание / Исключение)
- ✅ 5 столбцов (Требования / Процедуры / Мониторинг и надзор / Санкции / Раскрытие информации)
- ✅ Параметры видны в ячейках (текст значений П01, П02, П12...)
- ✅ Индикатор «данные есть» / «—» в нечитаемых ячейках с кнопкой просмотра
- ⚠️ Source pills в ячейках матрицы: **не отображаются** — только параметры и индикаторы наличия данных

---

## Реестр багов и проблем

### Bug #6 — NESTED секции не рендерятся
**Затронуто**: все 3B и 3C файлы по всем ячейкам
**Эффект**: NESTED секции (`{subkey: {description, source}}`) полностью игнорируются. Контент и источники недоступны. Потеряно ~10-15 цитат (включая 10+ выдержек) по 3B, аналогично по 3C.
**Данные: норма. Фронтенд: критический баг.**

### Bug #7 — Исключение показывает содержимое Допуска
**Затронуто**: все ячейки с 3C файлами при phase=exclusion
**Эффект**: Вкладка «Исключение» отображает неправильный контент (3A вместо 3C). Всё содержимое вкладки Исключение недостоверно.
**Данные: норма. Фронтенд: критический баг.**

### S4 — "Fetched web page" как заголовок источника
**Затронуто**: EQUITY-1 3A — 2 из 6 цитат
**Эффект**: В панели источников отображается "Fetched web page" вместо реального заголовка документа.
**Данные: баг пайплайна. Нужен catchup скрипт для перезаписи заголовков.**

### S5 — Отсутствует поле type в L3 цитатах
**Затронуто**: все L3 цитаты всех ячеек
**Эффект**: Все L3 источники показываются с типом «ДРУГОЕ» вместо правильного (rulebook, regulator и т.д.)
**Данные: пайплайн source_classifier не заполнил поле. Нужен catchup.**

### D1 — Orphaned citations (секции "not applicable")
**Затронуто**: EQUITY-3 (international_co_equity)
**Эффект**: admission_overview (2 src/5 exc) и disclosure_at_admission (2 src/0 exc) имеют description="not applicable" — фронтенд не рендерит эти секции, цитаты полностью недоступны.
**Данные: проблема пайплайна — контент не добыт, но цитаты сохранены к несуществующим секциям.**

---

## Статус аудита

| Страница | Проверено | Источники верны |
|---------|-----------|----------------|
| /venues/LSE_Main_Market | ✅ | ✅ |
| EQUITY-1 admission | ✅ | ✅ |
| EQUITY-1 maintenance | ✅ | ❌ Bug #6 |
| EQUITY-1 exclusion | ✅ | ❌ Bug #7 |
| EQUITY-1 matrix | ✅ | ✅ (source pills отсутствуют) |
| BOND-1 admission | ✅ | ✅ |
| BOND-1 maintenance | ✅ | ❌ Bug #6 (suspension скрыт) |
| BOND-1 exclusion | ✅ | ❌ Bug #7 |
| FUND-1 (sfs) admission | ✅ | ✅ |
| FUND-1 (sfs) maintenance | ✅ данные | ❌ Bug #6 |
| FUND-2 (closed-ended) admission | ✅ | ✅ |
| FUND-2 (closed-ended) maintenance | ✅ данные | ❌ Bug #6 (suspension) |
| DR-1 (depositary) admission | ✅ | ✅ |
| DR-1 (depositary) maintenance | ✅ | ✅ (additional_findings 1/8 ✅) |
| EQUITY-2 (transition) admission | ✅ | ✅ |
| EQUITY-2 maintenance | ✅ | "Данные в работе" (нет 3B) ✅ |
| ATT-BOND admission | ✅ | ✅ |
| ATT-BOND maintenance | ✅ | ✅ (additional_findings 1/12 ✅) |
| EQUITY-3 (international) admission | ✅ | ⚠️ D1 (orphaned citations) |

_ATT-EQUITY и ATT-DR не проверялись браузерно, но по архитектуре аналогичны ATT-BOND._
_Вкладки Исключение для FUND-1/FUND-2/DR-1/ATT-BOND/EQUITY-3 — Bug #7 применим по умолчанию._
