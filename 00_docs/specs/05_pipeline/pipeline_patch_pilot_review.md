# Патч к пайплайну v0.2 по итогам пилота (UK + Гонконг)

**Дата:** 2026-03-06  
**Основание:** Отчёт Tech Lead по пилоту (105 задач, LSE + Aquis + HKEX) + ревью с автором спецификации.

---

## 1. Нумерация запросов: унификация

**Проблема:** в спеке кириллица (3А, 3Б, 3В, 3Г), в реализации латиница (3A, 3B, 3C, 3D).

**Решение:** переход на латиницу везде. Маппинг:

| Спека (старое) | Код (новое) | Содержание |
|----------------|-------------|------------|
| 3А | 3A | Первичный допуск (обзор) |
| 3Б | 3B | Негативные аспекты (обзор) |
| 3В | 3C | Мониторинг и enforcement (обзор) |
| 3Г | 3D | Вторичный допуск |
| — (новый) | 3P | Целевой запрос по параметрам |

Аналогично для уровней 1 и 2: 1A, 1B, 1C, 2A.

---

## 2. Supranational flag: уточнение определения

**Проблема:** Гонконг получил `supranational_flag: true` с обоснованием «Stock Connect / Bond Connect». Это некорректно. Stock Connect — механизм кросс-граничного доступа к торгам, не наднациональная регуляторная рамка.

**Определение для промпта 1A и для LLM-постобработки:**

> Наднациональная рамка (supranational framework) — наднациональное законодательство, устанавливающее обязательные минимальные стандарты для допуска / листинга ценных бумаг на площадках юрисдикций-участников. Примеры: EU (MiFID II, Prospectus Regulation, Transparency Directive). НЕ являются наднациональными рамками: механизмы кросс-граничного доступа к торгам (Stock Connect), соглашения о взаимном признании, двусторонние меморандумы регуляторов.

**Действие:** исправить данные по Гонконгу (`supranational_flag: false`). Добавить определение в промпт 1A и в инструкцию для LLM-постобработки уровня 1.

---

## 3. Поле `issuer_eligibility` в venue_card: ограничение содержания

**Проблема:** поле `issuer_eligibility_description` в venue_card содержит конкретные требования по классам инструментов (какие главы rulebook, какие режимы для каких типов эмитентов). Это содержание уровня 3, не уровня 2.

**Что допустимо на уровне площадки:**
- `issuer_eligibility_separate`: boolean — есть ли раздельная процедура eligibility эмитента
- `issuer_eligibility_authority`: string — кто проводит (биржа / регулятор / оба)
- `issuer_eligibility_legal_basis`: string — правовое основание (ссылка на закон/главу)

**Что НЕ допустимо на уровне площадки:**
- Описание конкретных требований к эмитенту по классам инструментов
- Перечисление специальных режимов (SPAC, WVR, Biotech) и их условий
- Описание процедуры для разных типов инструментов (фонды через SFC, долговые через programme)

Всё это — содержание ячеек уровня 3 (площадка × уровень × класс инструмента).

**Действие:** в инструкции для LLM-постобработки уровня 2 явно ограничить поле `issuer_eligibility_description` архитектурным фактом. Конкретику перенести в промпты уровня 3 как контекст.

---

## 4. Поле `rulebook_chapters` в tiers — желательно к заполнению

**Проблема:** постобработка уровня 2 не заполнила `rulebook_chapters` (пустой объект `{}`). Промпты уровня 3 формируются без ссылок на конкретные главы rulebook, что может снижать точность поиска Parallel.

**Действие:** 

В промпте 2A желательно запросить по каждому tier/segment:
```
For each tier and each admitted instrument class: 
which specific chapters/sections of the exchange's rulebook 
govern the admission requirements?
```

В инструкции для LLM-постобработки уровня 2: если из результата Parallel удаётся извлечь номера глав — заполнить `rulebook_chapters`. Если не удаётся — пометить как пробел, не оставлять пустым. Формат (пример):

```json
"rulebook_chapters": {
  "equity": ["Chapter 8", "Chapter 9", "Appendix C1"],
  "bonds": ["Chapter 37"],
  "funds": ["Chapter 20", "Chapter 21"]
}
```

---

## 5. Архитектура уровня 3: двухфазный подход

**Проблема (критическая):** schema для 3A была организована по параметрам словаря (П01–П23), что превратило исследовательский запрос в enrichment-запрос по параметрам. Parallel искал не «как устроен допуск», а «заполни значения для free_float, market_cap, ...». Потеряны: общая архитектура допуска, условные развилки (альтернативные тесты), взаимосвязи между требованиями.

**Решение: двухфазная архитектура уровня 3.**

### Фаза 1. Обзорные запросы (3A, 3B, 3C, 3D)

Запросы по регуляторным темам. Schema организована по тематическим блокам, не по параметрам. Parallel описывает режим в целом: какие требования, процедуры, раскрытие, спецрежимы.

Запросы 3A, 3B, 3C, 3D **выполняются параллельно** по ячейке.

**Новая schema для 3A (первичный допуск):**

```json
{
  "admission_overview": {
    "description": "string — общее описание режима допуска, основные пути/тесты",
    "source": "string"
  },
  "eligibility_requirements": {
    "description": "string — требования к эмитенту: финансовая история, прибыльность, активы, корпоративное управление, аудитор, альтернативные пути",
    "source": "string"
  },
  "instrument_requirements": {
    "description": "string — требования к инструменту: free float, капитализация, число акционеров, цена акции, объём выпуска, связки между ними",
    "source": "string"
  },
  "sponsor_and_infrastructure": {
    "description": "string — спонсор, маркет-мейкер, проспект, их роль",
    "source": "string"
  },
  "restrictions_and_lock_ups": {
    "description": "string — lock-up, escrow, ограничения после допуска",
    "source": "string"
  },
  "procedure_and_timeline": {
    "description": "string — порядок подачи, рассмотрение, сроки, одобрение, апелляция",
    "source": "string"
  },
  "disclosure_at_admission": {
    "description": "string — проспект, информационный документ, требования к содержанию",
    "source": "string"
  },
  "special_regimes": {
    "description": "string — модификации для SPAC, WVR, biotech, иностранных эмитентов",
    "source": "string"
  },
  "additional_findings": {
    "description": "string",
    "source": "string"
  }
}
```

Промпт для 3A включает инструкцию по глубине описания параметров:

```
For each specific requirement, threshold, or condition found, 
describe in detail:
- What exactly is established (value, unit, formula)
- How it is calculated (what included/excluded)
- Whether alternatives exist (either/or paths)
- Whether it varies by company size, type, or other factors
- Whether it is linked to other requirements

Do not just state "free float is 25%" — explain the full 
construction of the requirement.

Include any relevant provisions from other chapters or regulations 
not listed above.
```

Schemas для 3B и 3C **не меняются** — они уже организованы по регуляторным темам (continuing_obligations, suspension, delisting; monitoring, sanctions, enforcement_practice).

### Фаза 2. Извлечение и маппинг параметров (LLM)

После завершения всех обзорных запросов по ячейке (3A + 3B + 3C + 3D если применимо) — LLM-обработка:

**Вход:** все обзорные результаты по ячейке + словарь параметров (П01–П23).

**Задачи:**

1. Из ВСЕХ обзорных результатов извлечь все упомянутые параметры с контекстом:
   - Название параметра (как в источнике)
   - Значение (если указано)
   - В какой фазе жизненного цикла упоминается (допуск / поддержание / делистинг / мониторинг)
   - Какая роль (порог входа / условие поддержания / основание для исключения)
   - Откуда взят (раздел rulebook)

2. Смэппить каждый найденный параметр на словарь П01–П23. Зафиксировать:
   - Смэппившиеся параметры (с ID)
   - Параметры вне словаря (кандидаты на расширение)
   - Параметры из словаря, не найденные в ячейке

3. Сформировать динамическую schema и промпт для запроса 3P — только по найденным и смэппившимся параметрам.

### Фаза 3. Целевой запрос по параметрам (3P)

**Тип:** Deep Research, JSON schema (динамическая).  
**Процессор:** core (запрос сфокусирован, источники указаны в контексте).

Schema формируется динамически — массив объектов, по одному на каждый найденный параметр:

```json
{
  "parameters": [
    {
      "parameter_id": "string — ID из словаря (P01, P02, ...) или NEW_01",
      "parameter_name": "string — название",
      "lifecycle_phases": "string — в каких фазах ЖЦ найден",
      "definition_and_value": { "description": "string", "source": "string" },
      "calculation_methodology": { "description": "string", "source": "string" },
      "alternatives": { "description": "string", "source": "string" },
      "variations": { "description": "string", "source": "string" },
      "linked_requirements": { "description": "string", "source": "string" },
      "differences_across_phases": { 
        "description": "string — если параметр используется в нескольких фазах, чем различаются пороги/условия",
        "source": "string" 
      }
    }
  ]
}
```

Промпт включает контекст по каждому параметру. Пример:

```
For equity securities on HKEX Main Board, provide detailed analysis 
of the following listing parameters.

1. FREE FLOAT (P01)
   Identified in: Main Board Listing Rules, Rule 8.08
   Phases: initial admission (threshold 25%), continuing obligations 
   (Rule 13.32 — grounds for suspension if falls below)
   Task: describe calculation methodology, inclusions/exclusions, 
   verification mechanism, alternatives, variations, threshold 
   differences between admission and maintenance.

2. MARKET CAPITALISATION (P02)
   Identified in: Rule 8.09
   Phases: initial admission (HKD 500M under profit test / 
   HKD 4B under market cap test / HKD 2B under revenue test)
   Task: [...]

[только найденные параметры, с контекстом из обзорных запросов]

Include provisions from any relevant chapters not listed above.
Cite specific rule numbers.
```

### Итоговая последовательность уровня 3

```
Фаза 1 (параллельно по ячейке):
  3A-обзор (первичный допуск, schema по темам, core)
  3B-обзор (негативные аспекты, schema по темам, pro)
  3C-обзор (мониторинг/enforcement, schema по темам, pro)
  3D (вторичный допуск, где применимо, schema, core)
      ↓
Фаза 2 (LLM):
  Извлечение параметров из ВСЕХ обзоров
  Маппинг на словарь П01–П23
  Формирование динамической schema и промпта для 3P
      ↓
Фаза 3:
  3P (параметры, динамическая schema, core)
```

Запросов на ячейку: 4–5 (обзоры) + 1 (параметры) = 5–6.

---

## 6. Пакетная постобработка: без изменений

Раздел 7 спеки (пакетная постобработка уровня 3) остаётся в силе. Она работает поверх результатов запроса 3P, а не поверх обзорных запросов. Задачи:

- Перевод на русский
- Типологизация конструкций (процентный порог / денежный порог / скользящая шкала / ...)
- Фиксация связок между параметрами
- Фиксация модификаторов (SPAC, WVR, ...)
- Обработка кандидатов на расширение словаря

---

## Сводка изменений

| # | Что | Тип изменения |
|---|-----|---------------|
| 1 | Нумерация запросов → латиница | Унификация |
| 2 | Определение supranational framework | Уточнение промпта + исправление данных HK |
| 3 | `issuer_eligibility` в venue_card | Ограничение содержания до архитектурного факта |
| 4 | `rulebook_chapters` желательно заполнять | Уточнение промпта 2A + инструкция постобработки |
| 5 | Уровень 3 → двухфазный (обзоры → параметры) | **Архитектурное изменение** |

---

*Патч к pipeline_v0_2.md. Дата: 2026-03-06.*
