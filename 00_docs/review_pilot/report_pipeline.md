# Отчёт для ревью: пайплайн (пилот UK + Гонконг)

**Дата:** 2026-03-06
**Кому:** Агент-автор спецификации пайплайна (`00_docs/specs/05_pipeline/pipeline_v0_2.md`)
**От:** Tech Lead
**Цель:** Проверить соответствие реализованного пилота спецификации. Выявить отклонения и вопросы, требующие решения перед масштабированием.

Спека пайплайна: `00_docs/specs/05_pipeline/pipeline_v0_2.md`

---

## 1. Что было реализовано

Пилот охватил три площадки: LSE (11 ячеек), Aquis Stock Exchange (12 ячеек), HKEX (5 ячеек). Юрисдикции: Великобритания и Гонконг.

Выполнены уровни 1, 2, 3. Уровни 4 и предварительный этап (институциональные факторы из датасетов) — не реализованы.

### Уровень 1 (юрисдикция)

Три подзапроса для каждой юрисдикции:
- **1А** (архитектура допуска + маппинг понятий) — текстовый выход (text), LLM-постобработка → `jurisdiction_card.json`
- **1Б** (институциональные факторы) — данные импортированы из внешнего файла, не через Parallel (см. раздел 4)
- **1В** (ландшафт площадок) — запрос выполнен через Parallel

Результаты сохранены в `03_data/countries/{name_ru}/level_1/`.

### Уровень 2 (площадка)

Один запрос 2А на площадку (output_schema="auto"), LLM-постобработка → `venue_card.json` + `cells_list.json` + промпты уровня 3.

Результаты: `03_data/countries/{name_ru}/level_2/{venue_key}/`.

### Уровень 3 (ячейки)

Запросы 3A, 3B, 3C (для всех ячеек) и 3D (где `secondary_admission_applicable=True`). Итого 105 задач, все завершены. Процессор: `core`.

Результаты: `03_data/countries/{name_ru}/level_3/{venue_key}/{cell_id}/{type}_raw.json`.

---

## 2. Фактические схемы данных — сравнение со спекой

### 2.1. jurisdiction_card.json (выход 1А + 1Б постобработки)

**Фактическая схема (Гонконг):**
```json
{
  "jurisdiction": "Hong Kong",
  "jurisdiction_ru": "Гонконг",
  "legal_family": "common law",
  "regulator_name": "Securities and Futures Commission (SFC)",
  "regulator_type": "commission",
  "admission_architecture": "...",
  "admission_architecture_ru": "...",
  "listing_authority": "...",
  "market_types": ["..."],
  "key_terms_mapping": { "местный_термин": "перевод", ... },
  "venues": [ { "name_english": "...", "type": "...", "tiers": [...] } ],
  "supranational_flag": true,
  "supranational_framework": "Stock Connect and Bond Connect cross-border schemes...",
  "notes": "..."
}
```

**Что в спеке:** pipeline_v0_2.md раздел 3 — наднациональные рамки имеются в виду как EU-типа (директивы, подменяющие национальное регулирование). Поле `supranational_flag` должно маркировать юрисдикции с наднациональным регуляторным overlay (EU-страны).

**Проблема A:** HK получил `supranational_flag: true` с обоснованием "Stock Connect and Bond Connect". Stock Connect — это cross-border market access scheme (технический механизм доступа), а не наднациональная регуляторная рамка в смысле спецификации. **Вопрос: считается ли Stock Connect/Bond Connect наднациональной рамкой в смысле данного проекта?**

---

### 2.2. venue_card.json (выход 2А + LLM-постобработки)

**Фактическая схема (LSE, сокращённо):**
```json
{
  "venue_key": "LSE",
  "venue_name_english": "London Stock Exchange",
  "venue_name_ru": "Лондонская фондовая биржа",
  "jurisdiction_ru": "Великобритания",
  "venue_type": "other",
  "operator": "London Stock Exchange plc",
  "issuer_eligibility_separate": true,
  "issuer_eligibility_description": "Two-gate model: issuers must meet FCA UKLR eligibility + LSE Admission Standards...",
  "secondary_listing_regime": true,
  "secondary_listing_description": "...",
  "tiers": [
    {
      "tier_name": "Equity Shares – Commercial Companies (ESCC)",
      "tier_name_ru": "Акции – коммерческие компании (ESCC)",
      "segment_type": "listing_tier",
      "instrument_classes": ["equity"],
      "rulebook_chapters": {},
      "secondary_admission_applicable": false
    }
  ],
  "key_rulebook_references": "...",
  "notes": "..."
}
```

**Проблема B:** Поля `issuer_eligibility_separate` и `issuer_eligibility_description` описывают требования к эмитенту на уровне площадки. Пользователь отметил как нежелательное: требования к эмитенту специфичны для конкретных ячеек (tier × instrument_class), не для площадки в целом. Данное поле описывает архитектурный факт (есть ли разделение между листинговыми требованиями и требованиями допуска к торгам), но контент частично перекрывается с тем, что должно быть в Level 3.

**Вопрос: является ли `issuer_eligibility_separate` допустимым структурным полем на уровне площадки, или это должно быть выброшено?**

---

### 2.3. Схема 3A (фактическая, сравнение двух ячеек)

В спеке (`pipeline_v0_2.md` раздел 6.3) указана следующая схема 3A:

```json
{
  "quantitative_requirements": {
    "free_float": { "description": "string", "source": "string" },
    "market_capitalisation": { "description": "string", "source": "string" },
    "shareholders_count": { "description": "string", "source": "string" },
    "share_price": { "description": "string", "source": "string" },
    "trading_volume": { "description": "string", "source": "string" },
    "issue_size": { "description": "string", "source": "string" }
  },
  "financial_requirements": { ... },
  "qualitative_requirements": { ... },
  "infrastructure": { ... },
  "restrictions": { ... },
  "procedure": { ... },
  "special_regimes": { ... },
  "additional_findings": { "description": "string", "source": "string" }
}
```

**Фактический результат для LSE ESCC equity (GB_LSE_escc_equity_3A):**
Структура СООТВЕТСТВУЕТ спеке — вложенная, с категориями и подполями:
```json
{
  "content": {
    "quantitative_requirements": {
      "free_float": { "description": "...", "source": "FCA UKLR 5" },
      "market_capitalisation": { "description": "...", "source": "..." },
      ...
    },
    "financial_requirements": { ... },
    "procedure": { ... },
    "special_regimes": { ... },
    "additional_findings": { "description": "...", "source": "..." }
  }
}
```

**Фактический результат для HKEX GEM equity (HK_HKEX__equity_0, 3A):**
Структура ПЛОСКАЯ — все поля на верхнем уровне, без категорий:
```json
{
  "content": {
    "free_float": { "description": "...", "source": "..." },
    "issue_size": { "description": "...", "source": "..." },
    "sponsor": { "description": "...", "source": "..." },
    "profit_requirements": { "description": "...", "source": "..." },
    "approval_decision": { "description": "...", "source": "..." },
    "foreign_issuer_modifications": { "description": "...", "source": "..." },
    "additional_findings": { "description": "...", "source": "..." }
    ...
  }
}
```

**Проблема C (критическая):** Одна и та же схема 3A даёт РАЗНЫЙ формат у разных ячеек — одни вложенные, другие плоские. Все 105 задач запускались с одним и тем же Python dict в качестве `output_schema`. Inconsistency может объясняться тем, что Parallel API не строго соблюдает JSON-схему при выдаче результатов, или что при трансляции spec-схемы в proper JSON Schema (которую требует Parallel API) произошла трансформация.

Технически: Developer задачи 003 преобразовал описательный dict из спеки в proper JSON Schema (с `type: object`, `properties` и т.д.) и выровнял 3A для уменьшения символов (схема была ~6172 символов, превышала лимит промпта). В итоге часть ячеек вернула вложенную структуру, часть — плоскую.

**Вопрос: являются ли обе структуры допустимыми результатами (поля одни и те же, просто без вложенности), или вложенность категорий принципиальна для последующей постобработки?**

---

### 2.4. Схемы 3B, 3C, 3D

Аналогичная ситуация — схемы переданы в Parallel API, но нет гарантии, что выход строго соответствует структуре. Необходима выборочная проверка.

Пример структуры 3B (спека):
```json
{
  "continuing_obligations": { ... },
  "suspension": { ... },
  "delisting_compulsory": { ... },
  "delisting_voluntary": { ... },
  "terminology": { "delisting_local_term": "string", "suspension_local_term": "string", "source": "string" },
  "additional_findings": { ... }
}
```

---

## 3. Что работает корректно

- **Идемпотентность и state management** — повторный запуск не дублирует задачи ✅
- **Сохранение результатов** — все 105 задач сохранены в правильные пути ✅
- **Промпты уровня 3** — формируются с терминологией конкретной площадки (местные названия тиров, ссылки на главы rulebook) ✅
- **cells_list.json** — корректно отражает ячейки с правильными флагами `secondary_admission_applicable` ✅
- **3D запросы** — запускались только для ячеек с `secondary_admission_applicable=True` ✅

---

## 4. Что не реализовано из спеки

| Элемент спеки | Статус |
|---------------|--------|
| **Предварительный этап** (5 Parallel-запросов по институциональным факторам Ф4-Ф7 из WGI/WDI/WFE/ASDI) | ❌ Не реализован. Данные для UK импортированы из внешнего файла (`1B_institutional.json` с `"source": "import_from_md"`). Многие факторы (Ф2, Ф4-Ф7) отсутствуют. |
| **Наднациональные рамки** (отдельное хранилище `/supranational/`) | ❌ Не реализован. `supranational_flag` фиксируется в `jurisdiction_card.json`, но отдельного запроса и хранилища нет. |
| **Пакетная постобработка уровня 3** (маппинг на П01–П23) | ⏳ Запланирована как следующая задача, ещё не реализована. |
| **Уровень 4** (проблемно-ориентированный анализ) | ❌ Не реализован. |
| **Загрузка в PostgreSQL** | ❌ Не реализован. |
| **Перевод на русский** в постобработке | ⚠️ Частично — `tier_name_ru`, `jurisdiction_ru`, `venue_name_ru` есть. Основной контент на английском. |

---

## 5. Вопросы к спеке, требующие решения

1. **Supranational flag для HK:** Stock Connect/Bond Connect — это наднациональная рамка в смысле проекта или нет? Если нет — нужна доработка промпта 1А и исправление данных по Гонконгу.

2. **Вложенность в схеме 3A:** Принципиальна ли категориальная группировка (`quantitative_requirements`, `financial_requirements`, etc.) для постобработки и маппинга на П01–П23? Или достаточно плоской структуры с теми же полями?

3. **Поле `issuer_eligibility_separate` в venue_card:** Это архитектурный факт площадки (допустимо) или излишнее поле (убрать)?

4. **Качество L3 результатов:** Parallel (core процессор) в ряде случаев возвращает общие ссылки ("требует дальнейшего извлечения") вместо конкретных цифр. Это ожидаемо для `core`? Нужен ли `pro` для L3 хотя бы частично?

5. **`rulebook_chapters` в tiers пусто (`{}`):** Постобработка не заполнила это поле. Насколько критично для промптов уровня 3?
