# Патч к пайплайну: укрупнение единицы L3-запроса

**Дата:** 2026-03-10  
**От:** Архитектор пайплайна  
**Кому:** Tech Lead  
**Статус:** К реализации

---

## 1. Проблема

При текущей архитектуре (один Parallel-запрос на ячейку = venue × tier × category × instrument_class) Parallel систематически подставляет данные, относящиеся к другой категории/тиру того же venue. Установленная корневая причина: промпт содержит название категории, но не содержит точных координат (конкретные главы rulebook), в результате чего Parallel находит данные из другой категории того же rulebook.

Проблема воспроизводится на площадках с многокатегориальной структурой (LSE Main Market post-UKLR 2024, и потенциально на Euronext, JPX, SGX при масштабировании).

---

## 2. Решение: укрупнение единицы L3-запроса

### 2.1. Новая единица запроса

**Было:** venue × tier × category × instrument_class (узкая ячейка).  
**Стало:** venue × instrument_class (все тиры/категории данного класса инструментов на venue в одном запросе).

Parallel на pro-процессоре получает широкий scope и видит весь rulebook в контексте — находит данные по всем тирам/категориям естественным образом, не путая их. Разнесение результата по ячейкам происходит на этапе LLM-постобработки, где есть venue_card с полной структурой площадки.

### 2.2. Что сохраняется

Три отдельных запроса по тематике **сохраняются**:
- **L3-A:** первичный допуск (требования, процедуры, раскрытие, спецрежимы)
- **L3-B:** негативные аспекты (поддержание, приостановка, исключение)
- **L3-C:** мониторинг и enforcement

Разделение необходимо, потому что регулирование в части допуска представлено в источниках обильно, а негативные аспекты (поддержание, исключение) и enforcement — скудно. При объединении в один запрос Parallel систематически перекашивает результат в сторону допуска. Отдельные запросы по негативным аспектам и мониторингу заставляют Parallel фокусировать на них всю глубину поиска.

### 2.3. Процессор

L3-A, L3-B, L3-C: **pro** (широкий scope требует глубины; негативные аспекты и мониторинг требуют глубины из-за скудности источников).

### 2.4. Оценка количества запросов

При ~120 venue и в среднем ~3 класса инструментов на venue:
- L3-A: ~360 запросов
- L3-B: ~360 запросов
- L3-C: ~360 запросов
- **Итого обзорных: ~1100** (против ~3000 в текущей архитектуре)

Плюс запросы 3P (параметры, Фаза 3) — количество определяется после Фазы 2.

---

## 3. JSON schema: компактная, на основе массива

### 3.1. Принцип

Schema определяет структуру тира **один раз**. Parallel заполняет массив — столько элементов, сколько тиров/категорий найдёт для данного класса инструментов на venue. Размер schema не зависит от числа тиров и остаётся компактным (~2–3 тыс. символов).

Привязка источников к полям **сохраняется** — это ключевое преимущество schema перед текстовым выходом или «мягкой» schema.

### 3.2. Детальность результатов

Результаты должны быть максимально подробными, насколько позволяет процессор. Parallel должен фиксировать всё найденное: конкретные пороги, формулы расчёта, исключения, альтернативные пути, условия, связки между требованиями. Из этих результатов на следующей фазе (Фаза 2 двухфазного подхода) будут извлекаться параметры для маппинга на словарь П01–П23 и последующей детализации в запросе 3P. Если результаты поверхностные — на Фазе 2 нечего извлекать.

Инструкция по детальности включается в каждый промпт (см. раздел 4, Блок 6).

### 3.3. Schema для L3-A (первичный допуск)

```json
{
  "type": "object",
  "properties": {
    "tiers": {
      "type": "array",
      "description": "One element per listing tier or category found for this instrument class on this venue. If venue has no tiered structure — single element with tier_name 'flat'.",
      "items": {
        "type": "object",
        "properties": {
          "tier_name": {
            "type": "string",
            "description": "Official name of the listing tier or category. Use 'flat' if no tiered structure exists."
          },
          "admission_overview": {
            "type": "object",
            "properties": {
              "description": { "type": "string", "description": "Overall admission regime: main paths/tests for eligibility, structure of the process, key decision points, alternative routes. Be specific — list each test/path with conditions." },
              "source": { "type": "string" }
            }
          },
          "eligibility_requirements": {
            "type": "object",
            "properties": {
              "description": { "type": "string", "description": "Requirements to the ISSUER: financial history (years, audited accounts), profitability tests (thresholds, calculation, alternatives), assets/equity minimums, revenue requirements, working capital, corporate governance standards, board composition, auditor requirements, accounting standards. For each requirement: state the exact value/threshold, how it is calculated, what is included/excluded, whether alternatives exist, whether it varies by issuer type/size." },
              "source": { "type": "string" }
            }
          },
          "instrument_requirements": {
            "type": "object",
            "properties": {
              "description": { "type": "string", "description": "Requirements to the INSTRUMENT: free float (percentage, calculation methodology, what is excluded from float, verification), minimum market capitalisation (value, currency, which test), minimum number of shareholders (threshold, definition of qualifying holder), minimum share price, minimum issue size/volume. For each: exact value, calculation, exclusions, alternatives, links to other requirements (e.g., min price × min shares = implicit monetary threshold)." },
              "source": { "type": "string" }
            }
          },
          "sponsor_and_infrastructure": {
            "type": "object",
            "properties": {
              "description": { "type": "string", "description": "Sponsor/nominated adviser: mandatory or optional, role, responsibilities, liability. Market maker/liquidity provider: required or not, conditions. Prospectus/information document: required, who approves, which regulation governs content." },
              "source": { "type": "string" }
            }
          },
          "restrictions_and_lock_ups": {
            "type": "object",
            "properties": {
              "description": { "type": "string", "description": "Lock-up periods: duration, who is subject (controlling shareholders, management, cornerstone investors), conditions for release. Escrow arrangements. Any other post-admission restrictions on share sales." },
              "source": { "type": "string" }
            }
          },
          "procedure_and_timeline": {
            "type": "object",
            "properties": {
              "description": { "type": "string", "description": "Application procedure: documents required, submission process, review stages, decision timeline, approval/rejection, appeal mechanism. Typical end-to-end timeline from application to first trading day." },
              "source": { "type": "string" }
            }
          },
          "disclosure_at_admission": {
            "type": "object",
            "properties": {
              "description": { "type": "string", "description": "Prospectus or admission document requirements: content requirements, approval authority, language, format. Pre-admission announcements." },
              "source": { "type": "string" }
            }
          },
          "special_regimes": {
            "type": "object",
            "properties": {
              "description": { "type": "string", "description": "Modifications to standard requirements for specific issuer types: SPAC, dual-class/WVR shares, biotech/pre-revenue companies, mineral companies, foreign issuers, shell companies. For each: which standard requirements are modified and how." },
              "source": { "type": "string" }
            }
          },
          "secondary_admission": {
            "type": "object",
            "properties": {
              "description": { "type": "string", "description": "If a secondary listing / cross-listing regime exists on this tier: eligibility (qualifying exchanges, market cap), which standard requirements are waived or modified, additional requirements, continuing obligations differences. State 'not applicable' if no secondary regime." },
              "source": { "type": "string" }
            }
          },
          "additional_findings": {
            "type": "object",
            "properties": {
              "description": { "type": "string", "description": "Any significant requirements, conditions, or procedures not covered by the fields above." },
              "source": { "type": "string" }
            }
          }
        }
      }
    },
    "common_requirements": {
      "type": "object",
      "properties": {
        "description": { "type": "string", "description": "Requirements that apply equally to ALL tiers/categories of this instrument class on this venue, if any. Avoids duplication across tier elements." },
        "source": { "type": "string" }
      }
    }
  }
}
```

### 3.4. Schema для L3-B (негативные аспекты)

Аналогичная массивная структура. Тематические блоки внутри каждого tier:

- `continuing_obligations`: quantitative_thresholds, qualitative_obligations, periodic_reporting, compliance_confirmation
- `suspension`: grounds, procedure, duration_limits, disclosure
- `delisting_compulsory`: grounds, procedure, grace_period, shareholder_protection, disclosure
- `delisting_voluntary`: conditions, procedure, shareholder_approval
- `terminology`: delisting_local_term, suspension_local_term
- `additional_findings`

Плюс `common_obligations` на верхнем уровне.

Каждое поле description содержит детальную инструкцию (аналогично L3-A): что именно описывать, с какой детальностью.

### 3.5. Schema для L3-C (мониторинг и enforcement)

Аналогичная массивная структура. Тематические блоки:

- `monitoring_regime`: responsible_body, mechanisms, sponsor_role, issuer_reporting_to_exchange
- `sanctions`: exchange_sanctions, regulator_sanctions, disciplinary_procedure, publication_of_actions
- `enforcement_practice`: recent_examples, general_approach
- `additional_findings`

Плюс `common_monitoring` на верхнем уровне.

---

## 4. Формирование промптов: алгоритмическое

### 4.1. Обоснование

При укрупнённых запросах (venue × instrument_class) вариативность промптов структурирована и сводится к подстановке переменных и условным блокам. LLM-генерация промптов не требуется и добавляет риск (может пропустить переменную, переформулировать определение).

### 4.2. Структура промпта (шаблон)

```
БЛОК 1: Контекст venue
  — подстановка из venue_card: название venue, оператор, юрисдикция,
    тип рынка (regulated market / MTF), перечень тиров

БЛОК 2: Определения понятий
  — константа из ядра: venue, tier, segment, modifier
  — включая правило: "Instrument-class chapters are NOT tiers"

БЛОК 3: Задание поиска
  — шаблон: "Research [ТЕМА] for [INSTRUMENT_CLASS] on [VENUE] 
    in [JURISDICTION]. Cover ALL listing tiers/categories of this 
    instrument class on this venue."
  — перечень тиров из venue_card для ориентира

БЛОК 4 (условный): Split-архитектура
  (если jurisdiction_card.G04 = split)
  — "This jurisdiction separates official listing from admission 
    to trading. Cover requirements from BOTH the listing authority 
    ([название из маппинга Б03]) and the exchange ([название]). 
    Also cover admission-to-trading-only path if it exists."

БЛОК 5 (условный): Наднациональная рамка
  (если jurisdiction_card.supranational = true)
  — "This jurisdiction is subject to [название рамки]. 
    Indicate which requirements are set at supranational level 
    and which at national level."

БЛОК 6: Инструкция по детальности
  — "For each requirement, threshold, or condition found:
    - State the exact value, unit, formula
    - Explain how it is calculated (inclusions, exclusions, 
      verification mechanism)
    - State whether alternatives exist (either/or paths)
    - State whether it varies by company size, type, or other factors
    - State whether it is linked to other requirements 
      (combined thresholds, dependencies)
    Do NOT summarise — provide full detail for every requirement 
    found. These details will be used for systematic comparison 
    across jurisdictions."

БЛОК 7: Структурирование по тирам
  — "Structure your response by listing tier/category. 
    Known tiers for [INSTRUMENT_CLASS] on [VENUE]: [перечень].
    If you find tiers/categories not listed here — include them.
    If the venue has no tiered structure — use a single entry 
    with tier_name 'flat'."

БЛОК 8 (условный): Legacy-категории
  (если venue_card содержит тиры с legacy=true)
  — "The following categories are closed to new admissions 
    (transition/grandfathering): [перечень]. Do not research 
    admission requirements for them."

БЛОК 9: Закрывающая инструкция
  — "Include any relevant provisions from other chapters or 
    regulations beyond those listed above. 
    Cite specific rule numbers for each finding."
```

### 4.3. Переменные подстановки

| Переменная | Источник |
|-----------|---------|
| Venue, operator, jurisdiction | venue_card |
| Instrument class | перечень из venue_card |
| Перечень тиров | venue_card.tiers |
| G04 (split / merged / mixed) | jurisdiction_card |
| Listing authority (Б03) | jurisdiction_card.key_terms_mapping |
| Exchange name | venue_card |
| Наднациональная рамка | jurisdiction_card + /supranational/ |
| Legacy-тиры | venue_card.tiers (where legacy=true) |

### 4.4. Fallback при превышении лимита

Если промпт + schema > 15 000 символов:

Разбить scope по классам инструментов: вместо одного запроса venue × все классы — два запроса (например, venue × equities и venue × bonds+funds+DR). Schema остаётся та же, промпт короче.

Определение необходимости разбиения: алгоритмическое, по длине сформированного промпта.

---

## 5. LLM-постобработка L3

### 5.1. Разнесение по ячейкам

Результат Parallel содержит массив `tiers`. LLM-постобработка:
- Извлекает каждый элемент массива
- Маппит `tier_name` на конкретную ячейку из cells_list.json
- Формирует отдельный JSON-файл результата для каждой ячейки
- Переводит на русский язык

Выполняется либо LLM, либо если есть понимание алгоритма, делается алгоритмическое разнесение. 
Но скорее всего придется делать запрос к LLM - название объекта в массиве может не совпадать с названием в ячейке. Запрос может быть небольшим (работа с заголовками) и выполняться в бэтче (при общем постпроцессинге всех результатов).
Контекст для LLM: venue_card с полной структурой площадки.

### 5.2. Двухфазный подход (параметры) — без изменений

После разнесения по ячейкам:
- **Фаза 2:** LLM извлекает параметры из всех результатов (L3-A + L3-B + L3-C) по ячейке, маппит на словарь П01–П23, формирует промпт и динамическую schema для 3P.
- **Фаза 3:** запрос 3P (целевой по параметрам, core).

Подробности — см. патч pipeline_patch_pilot_review.md, раздел 5.

---

## 6. Валидация результатов

После LLM-постобработки — валидационный LLM-вызов по каждой ячейке.

**Вход:**
- Результат Parallel (элемент массива tiers для данной ячейки)
- venue_card (структура площадки, тиры, классы инструментов)
- jurisdiction_card (архитектура допуска, маппинг терминов, тип регулятора)
- Определения понятий из ядра (venue, tier, segment, modifier)
- Чеклист ожидаемых тем для данного класса инструментов

**Чеклист** формируется алгоритмически из словаря параметров. Для equities: free float, market capitalisation, number of shareholders, financial history, profit/revenue test, corporate governance, sponsor, prospectus, lock-up. Для bonds: минимальный объём выпуска, рейтинговые требования, проспект, раскрытие. Для funds: NAV, управляющая компания, структура фонда.

**Три проверки:**

```
1. SCOPE CHECK: Does the result contain information about the 
   correct venue, tier, and instrument class? Are there references 
   to other tiers/categories/venues that should not be here?

   Context: This result should cover [TIER_NAME] on [VENUE_NAME] 
   for [INSTRUMENT_CLASS]. The following OTHER tiers exist on this 
   venue: [перечень из venue_card]. Data about these other tiers 
   should NOT be in this result.

2. COMPLETENESS CHECK: For [INSTRUMENT_CLASS] admission on 
   [VENUE_TYPE], the following topics are expected:
   [чеклист]
   Which are present in the result? Which are missing?

3. SOURCE CHECK: Do the cited rulebook chapters and regulations 
   correspond to [TIER_NAME] on [VENUE_NAME]?
   Flag any sources that appear to belong to a different 
   tier/category.
```

**Выход:** scope_ok / completeness_score / source_ok + список пробелов + подозрительные источники. При проблемах — пометка для ревью.

---

## 7. Итоговая последовательность уровня 3

```
Для каждой venue × instrument_class:

1. Алгоритмическая сборка промпта (подстановки + условные блоки)
   → сохранение в /prompts/
   → проверка размера; если > лимит → разбить по классам

2. Parallel-запросы (параллельно):
   L3-A (первичный допуск, pro)
   L3-B (негативные аспекты, pro)
   L3-C (мониторинг/enforcement, pro)

3. LLM-постобработка:
   Разнесение массива tiers по ячейкам
   Перевод на русский

4. Валидация (LLM):
   Scope check, completeness check, source check
   → при проблемах: пометка для ревью

5. Фаза 2 (LLM):
   Извлечение параметров из L3-A + L3-B + L3-C по ячейке
   Маппинг на словарь П01–П23
   Формирование промпта и динамической schema для 3P

6. Фаза 3:
   3P (целевой запрос по параметрам, core)

7. Пакетная постобработка (после накопления массива):
   Типологизация конструкций
   Фиксация связок параметров
   Обработка кандидатов на расширение словаря
```

---

*Патч к pipeline_v0_2.md. Дата: 2026-03-10.*
