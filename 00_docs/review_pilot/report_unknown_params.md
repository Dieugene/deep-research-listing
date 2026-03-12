# Отчёт: параметры вне текущего словаря (по итогам Pass 1)

**Дата:** 2026-03-11
**Кому:** Разработчик концептуальной модели
**От кого:** Tech Lead
**Контекст:** По итогам Pass 1 (Phase 2, извлечение структуры параметров) LLM нашёл 69 параметров, не вошедших ни в один чеклист П01–П30. Все они залогированы как `[UNKNOWN_PARAM]`. Документ систематизирует находки и предлагает предварительную классификацию.

---

## Исходные данные

- **Пилот:** UK (LSE Main Market, LSE AIM, Aquis) + HK (HKEX Main Board, GEM)
- **Классы инструментов:** equity, bond, fund, depositary_receipt
- **Групп обработано:** 17
- **Известных параметров (из чеклистов П01–П30):** 217 вхождений
- **Дополнительных параметров (вне чеклистов):** 69 вхождений

---

## Классификация по кластерам

### Кластер A: Базовые условия допуска — качественные (инфраструктурные)

Появляются **во всех классах инструментов и обеих юрисдикциях**. Не числовые, но применяются почти универсально как обязательные условия допуска.

| Параметр | Классы | Вхождений | Описание LLM |
|---|---|---|---|
| Free transferability of securities | equity, bond, DR | 7 | Ценные бумаги должны быть свободно отчуждаемы. Проверяется FCA/биржей при подаче. UKLR 3.2.4R; HK Rule 8.13, 23.09 |
| Fully paid status | equity, DR | 3 | Акции/расписки должны быть полностью оплачены и не обременены залогами |
| Electronic settlement eligibility (CREST/CCASS) | equity, bond, DR | 6 | Ценные бумаги должны быть допущены в систему электронного расчёта. UK — CREST/Euroclear; HK — CCASS. Биржа проверяет при допуске и требует поддержания |
| Whole-class application | bond, DR | 3 | Заявка должна охватывать весь класс ценных бумаг, выпущенных и планируемых к выпуску. UKLR 3.2.1AR |
| Validity and authorisations (bond) | bond | 2 | Выпуск и любая гарантия должны быть надлежащим образом санкционированы уставными документами и применимым правом |

**Рекомендация:** рассмотреть добавление в словарь как группу качественных базовых условий (не количественных порогов). Они встречаются слишком системно, чтобы считаться периферийными.

---

### Кластер B: Процедурные требования (временны́е / операционные)

Специфичны для UK MTF (AIM). Касаются **сроков подачи документов**, а не пороговых значений.

| Параметр | Группы | Описание LLM |
|---|---|---|
| Pre-admission announcement timing | MTF equity standard, distinct | За 10 (стандарт) или 20 (quoted applicant) рабочих дней до допуска опубликовать информацию по Schedule One через RIS. AIM Rule 2 |
| Application submission and Nomad declaration | MTF equity distinct | Не менее чем за 3 рабочих дня до допуска подать приложение + декларацию Nomad. AIM Rule 5 |
| Early notification by Nomad | MTF equity standard | Nomad уведомляет AIM Regulation до публикации Schedule One |
| Home market compliance confirmation (Designated Market) | MTF equity distinct | Quoted applicant должен подтвердить соответствие требованиям своего Designated Market. AIM ADM template |
| Admission disclosure — document repository URL | MTF equity distinct | Опубликовать URL с документами за последние 2 года с Designated Market и URL с правами по ценным бумагам. AIM Rule 26 |

**Рекомендация:** эти параметры — операционные условия допуска, специфичные для MTF-режима. Не являются количественными порогами в смысле сравнительного исследования. Возможно, должны быть в отдельной категории «Процедурные требования» или вообще вне словаря параметров.

---

### Кластер C: Продолжающиеся обязательства (3B-территория)

Найдены в группе `UK_regulated_market_equity_att` (ATT-режим). Это **ongoing obligations** — они относятся к поддержанию листинга, а не к первичному допуску. LLM подтягивал их из 3B-данных.

| Параметр | Источник | Описание |
|---|---|---|
| Inside information disclosure (UK MAR Art.17) | MAR; ADS July 2024 | Раскрывать инсайдерскую информацию немедленно через RIS; для ATT — одновременно с домашней биржей |
| Periodic financial reporting deadlines (DTR 4) | FCA DTR 4 | Годовой отчёт — в течение 4 месяцев; полугодовой — в течение 3 месяцев |
| Major shareholding notifications (DTR 5) | FCA DTR 5 | UK-эмитенты: с 3% и каждый 1%; non-UK: с 5%, 10%, 15% и т.д. |
| Immediate notification of home exchange status changes | ADS Schedule 5, 4.2 | При приостановке/отзыве листинга на домашней бирже — немедленно уведомить LSE |
| Advance notification of corporate action timetables | ADS Rule 4.7 | Заблаговременно направлять в LSE расписание корпоративных действий |
| Voluntary cancellation notice period (20 business days) | ADS Rule 4.18 | Минимум 20 рабочих дней письменного уведомления + объявление через RIS до отмены допуска |
| Payment of LSE fees | ADS Rule 4.11 | Неуплата сборов — основание для отзыва допуска |
| Maintain active RIS and website disclosures | ADS Schedule 6; ADS Rule 4.4 | Обязанность поддерживать RIS и вебсайт с необходимыми раскрытиями |

**Рекомендация:** эти параметры находятся вне области применения чеклистов П01–П30, которые ориентированы на **условия первичного допуска**. Если в концептуальной модели планируется словарь **продолжающихся обязательств** — они там. При текущей области применения (admission parameters) — исключить из чеклиста.

---

### Кластер D: Параметры режима вторичного листинга (distinct)

Специфичны для secondary listing (distinct regime) в UK и HK. Это **предпосылки входа** — структурные ограничения, которые не существуют для первичного листинга.

| Параметр | Юрисдикция | Описание LLM |
|---|---|---|
| Qualifying home listing | UK | Эмитент должен иметь первичный листинг на "suitable exchange" в том же классе акций. UKLR 14.2.6R |
| Central management and control location | UK | Центр управления — в стране инкорпорации или стране домашнего листинга. UKLR 14.2.4R |
| Home listing status dependency and notification duty | UK | Обязанность немедленно уведомить FCA о приостановке/отзыве домашнего листинга — основание для UK suspension. UKLR 14.3.4R |
| Admission to trading — Official List linkage | UK | Ценные бумаги должны быть допущены к торгам на UK regulated market в привязке к UK Official List. UKLR 3.2.3R |
| Primary overseas listing pre-condition | HK | Первичный листинг на зарубежной бирже должен быть получен до вторичного листинга в HK. Rule 19C.02A |
| HK service of process | HK | Назначить авторизованное лицо в HK для принятия судебных извещений. Rule 19C.02A |
| Automatic waivers package and migration triggers | HK | Пакет отступлений для вторичных эмитентов (Chapters 3, 7, 13, 14/14A и др.); прекращается при переходе ≥55% торгов на HK. HKEX Rules Ch. 19C |

**Рекомендация:** возможно, имеет смысл отдельная секция словаря для `admission_path_type = distinct` — со своими параметрами, непересекающимися с первичным листингом.

---

### Кластер E: Инвестиционный контроль / ограничения доступа инвесторов

| Параметр | Классы | Описание LLM |
|---|---|---|
| Professional-investors-only selling restriction | bond (HK distinct) | Chapter 37 HKEX: документы должны содержать прямое ограничение на распространение только среди профессиональных инвесторов (определение по SFO Schedule 1) |
| Investing company — minimum cash fundraising | equity (UK MTF) | Инвестиционные компании должны привлечь не менее £6 млн денежными средствами при или непосредственно перед допуском и заявить/соблюдать инвестиционную политику. AIM Rules |
| Dealing policy from admission | equity (UK MTF) | Политика торговли ценными бумагами для PDMR: закрытые периоды, процедуры клиринга, временны́е окна. AIM Rule 21 |

**Рекомендация:** `Professional-investors-only` — значимый параметр, разграничивающий retail и distinct bond режимы. Кандидат на добавление. `Investing company threshold` — специфика MTF, но может быть применима к другим рынкам при масштабировании.

---

### Кластер F: HK-специфика

| Параметр | Класс | Описание LLM |
|---|---|---|
| CCASS eligibility | equity (HK) | Включён в кластер A (Electronic settlement) — CCASS является HK-аналогом CREST |
| Minimum public allocation — GEM (5%) | equity (HK) | Минимум 5% акций должно быть аллоцировано в публичный транш при IPO. GEM Rule 10.11A (с 4 авг. 2025). Количественный параметр |
| Sufficiency of operations/assets | equity (HK) | Принципиальная оценка: у эмитента должны быть достаточные операции и активы для продолжения листинга. MB Rule 13.24; GL106-19 |
| Suspension/delisting remedial periods | equity (HK) | MB: 18 месяцев; GEM: 12 месяцев — максимальный срок приостановки до принудительного делистинга. Количественный параметр |
| HK management presence / authorised representatives | equity (HK) | MB: 2 исполнительных директора, резидентов HK; GEM: 2 авторизованных представителя + квалифицированный секретарь с CPD. MB Rule 8.12 |
| No simultaneous listing of shares and HDRs | DR (HK) | Запрет на одновременный листинг акций и HDR одного класса на HKEX. Rule 19B.06 |
| Fungibility and free conversion HDR ↔ underlying | DR (HK) | Обязательная свободная конвертируемость HDR в базовые акции через депозитария. Rules 19B.07–19B.08 |
| Financial eligibility tests for HDR (profit/revenue/market cap) | DR (HK) | Три альтернативных теста Rule 8.05 применимы через DR-режим: (i) прибыльность; (ii) market cap ≥HK$2bn + revenue + cash flow; (iii) market cap ≥HK$4bn + revenue |
| Working capital sufficiency statement (HDR) | DR (HK) | Эмитент + спонсор подтверждают достаточность оборотного капитала минимум на 12 месяцев от даты листингового документа |

**Рекомендация:**
- `GEM minimum public allocation (5%)` — количественный параметр, кандидат на добавление в чеклист equity (возможно, как вариант П01 для режима IPO)
- `Suspension/delisting remedial periods` — количественный параметр, относится к фазе REMOVAL жизненного цикла
- `Financial eligibility tests for HDR` — вероятно, должны быть в чеклисте DR как П07/П08/П09/П10 (аналог equity-тестов, применяемых через DR)
- `Working capital sufficiency statement` — вариант П11 с дополнительным требованием о подтверждении спонсором

---

### Кластер G: Bond-специфика

| Параметр | Группы | Описание LLM |
|---|---|---|
| Permitted issuer types and incorporation | bond (HK distinct) | Допустимые эмитенты: государство, наднациональные органы, корпорации, трасты; валидность инкорпорации |
| Guarantor eligibility | bond (HK standard) | Гарант должен соответствовать тем же тестам по track record и собственному капиталу (≥HK$100m), что и эмитент. Количественный параметр |
| ABS-specific eligibility | bond (HK standard) | Для ABS: SPV-структура, права доверительного управляющего, допустимые классы обеспечения; вместо стандартных П07/П13 |
| Convertible/option-linked structures | bond (HK distinct) | Допустимые базовые активы для конвертируемых облигаций; требования к anti-dilution |
| Sufficient number of registered holders | bond (UK ATT) | Качественный тест LSE: достаточное число зарегистрированных держателей для обеспечения упорядоченного рынка. Без числового порога |
| Stabilisation control | bond (HK standard) | Любая стабилизация цены до начала торгов — только в соответствии с применимым законодательством |

**Рекомендация:**
- `Guarantor eligibility` — количественный параметр, специфичный для guaranteed issues. Кандидат на добавление (bond-only)
- `ABS-specific eligibility` — структурный параметр, применимый к специфическому подклассу

---

### Кластер H: Fund-специфика

| Параметр | Группы | Описание LLM |
|---|---|---|
| SFC authorisation of the CIS | fund (HK) | Фонд должен быть авторизован SFC и оставаться авторизованным. Немедленное уведомление биржи при угрозе отзыва авторизации. Foundational |
| Investment policy lock-in (3 years) | fund (HK) | Инвестиционная политика из листингового документа не может изменяться в течение 3 лет без одобрения SFC. Продолжающееся обязательство |
| Listing Agreement undertakings | fund (HK) | CIS, оператор, трасти/кастодиан — принимают на себя обязательства соответствовать Listing Rules и условиям авторизации SFC |
| Official List prerequisite / dual-regime operation | fund (UK) | Фонды, торгующиеся на Main Market, должны иметь листинг в UK Official List (дополнительный контроль FCA/COLL) |
| Quarterly cross-holdings disclosure | fund (UK) | Обязанность ежеквартального раскрытия перекрёстных активов — продолжающееся обязательство |

**Рекомендация:**
- `SFC authorisation of the CIS` — кандидат на добавление как отдельный параметр для fund class (отличается от П26 Manager licensing — это product-level авторизация, а не manager-level)
- `Investment policy lock-in` — продолжающееся обязательство, не параметр допуска

---

## Сводная таблица рекомендаций

| # | Параметр | Класс | Рекомендация |
|---|---|---|---|
| 1 | Free transferability | equity, bond, DR | ➕ В словарь (качественный, cross-class) |
| 2 | Electronic settlement eligibility | equity, bond, DR | ➕ В словарь (качественный, cross-class) |
| 3 | Fully paid status | equity, DR | ➕ В словарь (возможно, объединить с Free transferability) |
| 4 | Whole-class application | bond, DR | ➕ В словарь (качественный) |
| 5 | Validity and authorisations | bond | ➕ В словарь (qualitative, bond/DR) |
| 6 | Professional-investors-only selling restriction | bond | ➕ В словарь (investor eligibility) |
| 7 | GEM minimum public allocation (5%) | equity | ➕ В словарь (количественный, IPO-specific) |
| 8 | Suspension/delisting remedial periods | equity | ➕ В словарь (фаза REMOVAL, количественный) |
| 9 | Guarantor eligibility | bond | ➕ В словарь (bond, guaranteed issues) |
| 10 | SFC authorisation of CIS | fund | ➕ В словарь (fund, product-level) |
| 11 | Financial eligibility tests for HDR | DR | ➕ Расширить DR-чеклист (П07/П08/П09/П10) |
| 12 | Working capital sufficiency (HDR) | DR | ➕ Расширить DR-чеклист (вариант П11) |
| 13 | Investing company minimum fundraising (£6m) | equity MTF | 🔍 Уточнить область применения |
| 14 | HK management presence / auth. reps | equity | 🔍 Уточнить: скорее governance (П12), чем отдельный параметр |
| 15 | Sufficient number of registered holders (bond) | bond | 🔍 Вариант П03 для bonds — уточнить |
| 16 | Qualifying home listing (distinct regime) | equity | 🔄 В отдельную секцию distinct-параметров |
| 17 | Primary overseas listing pre-condition (HK) | equity | 🔄 В отдельную секцию distinct-параметров |
| 18 | Automatic waivers and migration triggers (HK) | equity | 🔄 В отдельную секцию distinct-параметров |
| 19 | No simultaneous listing of shares and HDRs | DR | 🔄 Structural constraint для DR distinct |
| 20 | Fungibility HDR↔underlying | DR | 🔄 Structural constraint для DR |
| — | Ongoing obligations (DTR 4/5, MAR 17, ADS fees) | equity | ❌ Вне области (не admission parameters) |
| — | Procedural timelines (pre-admission announcements) | equity MTF | ❌ Вне области (операционные, не пороги) |
| — | Investment policy lock-in | fund | ❌ Вне области (continuing obligation) |
| — | Stabilisation control | bond | ❌ Вне области (операционный контроль) |

Условные обозначения: ➕ добавить · 🔍 уточнить · 🔄 в отдельную секцию · ❌ вне области

---

## Полный список 69 параметров (для справки)

| Группа | Класс | Параметр |
|---|---|---|
| UK_MTF_equity_distinct | equity | Pre-admission announcement timing (quoted applicant) |
| UK_MTF_equity_distinct | equity | Application submission and Nomad declaration |
| UK_MTF_equity_distinct | equity | Settlement eligibility and arrangements |
| UK_MTF_equity_distinct | equity | Home market compliance confirmation (Designated Market) |
| UK_MTF_equity_distinct | equity | Admission disclosure – document repository and rights URL |
| UK_MTF_equity_distinct | equity | Investing company – cash fundraising and investing policy |
| UK_MTF_equity_standard | equity | Transferability of securities |
| UK_MTF_equity_standard | equity | Eligibility for electronic settlement |
| UK_MTF_equity_standard | equity | Unconditional allotment and class-wide admission |
| UK_MTF_equity_standard | equity | Pre-admission announcement lead time and early notification |
| UK_MTF_equity_standard | equity | Investing companies – minimum fundraising and policy |
| UK_MTF_equity_standard | equity | Dealing policy (from admission) |
| UK_RM_bond_att | bond | Home listing on a suitable exchange (and continuing compliance) |
| UK_RM_bond_att | bond | Sufficient number of registered holders |
| UK_RM_bond_standard | bond | Entire class must be included in the application |
| UK_RM_bond_standard | bond | Free transferability of securities |
| UK_RM_bond_standard | bond | Validity and authorisations |
| UK_RM_bond_standard | bond | Electronic settlement eligibility |
| UK_RM_DR_att | DR | Electronic settlement eligibility (CREST/Euroclear UK & International) |
| UK_RM_DR_standard | DR | Admission to trading dependency (regulated market) |
| UK_RM_DR_standard | DR | Transferability and fully paid status (certificates and underlying) |
| UK_RM_DR_standard | DR | Whole-class application (all certificates of the class) |
| UK_RM_DR_standard | DR | Electronic settlement eligibility (market infrastructure) |
| UK_RM_equity_att | equity | Inside information disclosure (UK MAR Article 17) |
| UK_RM_equity_att | equity | Periodic financial reporting deadlines (DTR 4) |
| UK_RM_equity_att | equity | Major shareholding notifications (DTR 5) |
| UK_RM_equity_att | equity | Immediate notification of home exchange status changes |
| UK_RM_equity_att | equity | Advance notification of corporate action timetables |
| UK_RM_equity_att | equity | Voluntary cancellation notice period (20 business days) |
| UK_RM_equity_att | equity | Payment of LSE fees |
| UK_RM_equity_att | equity | Maintain active RIS and website disclosures |
| UK_RM_equity_distinct | equity | Admission to trading on a regulated market (Official List linkage) |
| UK_RM_equity_distinct | equity | Qualifying Home Listing (Secondary listing prerequisite) |
| UK_RM_equity_distinct | equity | Central management location (Secondary listing prerequisite) |
| UK_RM_equity_distinct | equity | Home listing status dependency and notification duty |
| UK_RM_equity_distinct | equity | Transferability and fully-paid shares |
| UK_RM_equity_standard | equity | Transferability / Fully paid and free of liens |
| UK_RM_equity_standard | equity | Dual-Class/Weighted Voting Rights (WVR/DCSS) regime |
| UK_RM_equity_standard | equity | Admission to trading on a regulated market (Official List linkage) |
| UK_RM_fund_att | fund | Investor targeting – professional/institutional focus |
| UK_RM_fund_att | fund | Electronic settlement eligibility (CREST) and orderly operations |
| UK_RM_fund_standard | fund | Official List prerequisite / dual-regime operation |
| UK_RM_fund_standard | fund | Quarterly cross-holdings disclosure |
| UK_RM_fund_standard | fund | Corporate-action timetable pre-notification to the exchange |
| HK_RM_bond_distinct | bond | Professional-Investors-only selling restriction |
| HK_RM_bond_distinct | bond | Convertible/option-linked structures — acceptable underlying and anti-dilution |
| HK_RM_bond_distinct | bond | Permitted issuer types and incorporation |
| HK_RM_bond_distinct | bond | Authorisation and legality of issue and any guarantee |
| HK_RM_bond_distinct | bond | Free transferability of securities |
| HK_RM_bond_standard | bond | Free transferability of the securities |
| HK_RM_bond_standard | bond | Authorisations and legal conformity (issuer/guarantor) |
| HK_RM_bond_standard | bond | Guarantor eligibility (for guaranteed issues) |
| HK_RM_bond_standard | bond | Asset-backed securities (ABS) specific eligibility |
| HK_RM_bond_standard | bond | Admission procedure and timeline (documents and timing) |
| HK_RM_bond_standard | bond | Stabilisation control |
| HK_RM_DR_standard | DR | Working capital sufficiency statement |
| HK_RM_DR_standard | DR | Financial eligibility (profit/revenue/market cap track record) |
| HK_RM_DR_standard | DR | No simultaneous HK listing of shares and HDRs of the same class |
| HK_RM_DR_standard | DR | Fungibility and free conversion between HDRs and underlying shares |
| HK_RM_equity_distinct | equity | Primary overseas listing pre-condition and HK service of process |
| HK_RM_equity_distinct | equity | Automatic waivers package and migration triggers |
| HK_RM_equity_standard | equity | Free transferability and CCASS eligibility |
| HK_RM_equity_standard | equity | Sufficiency of operations/assets (continuing listing eligibility) |
| HK_RM_equity_standard | equity | Suspension/delisting remedial periods (MB: 18 months; GEM: 12 months) |
| HK_RM_equity_standard | equity | Hong Kong management presence / authorised representatives |
| HK_RM_equity_standard | equity | Minimum public allocation – GEM (5%) |
| HK_RM_fund_standard | fund | SFC authorisation of the CIS (product-level) |
| HK_RM_fund_standard | fund | Investment policy lock-in (3 years) |
| HK_RM_fund_standard | fund | Listing Agreement undertakings by CIS, Operator and trustee/custodian |

---

*Полные описания по 6-вопросному шаблону доступны в `pass1.json` для каждой группы: `03_data/countries/{jurisdiction}/level_3/_groups/{group_id}/pass1.json`.*

*Tech Lead, 2026-03-11*
