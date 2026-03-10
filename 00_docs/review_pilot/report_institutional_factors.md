# Отчёт для ревью: институциональные факторы (пилот UK + Гонконг)

**Дата:** 2026-03-06
**Кому:** Агент-автор спецификации институциональных факторов (`00_docs/specs/03_institutional_factors/`)
**От:** Tech Lead
**Цель:** Проверить полноту и корректность собранных данных по институциональным факторам Ф1–Ф12. Выявить пробелы и интерпретационные вопросы.

Спека: `00_docs/specs/03_institutional_factors/institutional_factors_operationalization_v01.md`

---

## 1. Как собирались данные по институциональным факторам

**Важное отклонение от спеки:** предварительный этап (5 Parallel-запросов из датасетов WGI/WDI/ASDI/LLSV/IOSCO) в рамках пилота реализован не был. Данные по институциональным факторам были импортированы из внешнего файла, созданного до начала разработки пайплайна.

Источник импорта: `D:\_storage_cbr\040_listing_deep_research\03_institutional_factors\_pilot_results\pilot_jurisdiction_cards.md`

Сохранено как: `03_data/countries/{name_ru}/level_1/1B_institutional.json`

---

## 2. Фактические данные по Великобритании

Файл: `03_data/countries/Великобритания/level_1/1B_institutional.json`

```json
{
  "jurisdiction": "United Kingdom",
  "source": "import_from_md",
  "qualitative_factors": {
    "F3_private_enforcement": {
      "value": "средний",
      "assessment": "Механизмы существуют и развиваются, но практика ограничена по сравнению с US. GLO (Group Litigation Orders) по CPR Part 19 — opt-in групповые иски, не opt-out...",
      "source": "Debevoise (2023); CPR Part 19; CPR Part 63A; Ashurst (2024)"
    },
    "F8_ownership_concentration": {
      "value": "дисперсная",
      "state_share_pct": "н/д",
      "assessment": "ONS (2022): Rest of world 57.7%, UK individuals 10.8%, Insurance+pension 4.2%...",
      "source": "ONS, Ownership of UK quoted shares, 2022"
    },
    "F9_investor_base": {
      "value": "институционалы",
      "institutional_share_pct": ">80%",
      "source": "ONS, Ownership of UK quoted shares, 2022 и 2024."
    },
    "F12_exchange_as_sro": {
      "value": "частичная",
      "assessment": "Листинговые правила (UKLR) устанавливает FCA, не LSE. LSE устанавливает Admission and Disclosure Standards...",
      "source": "FCA PS24/6; LSE Admission and Disclosure Standards."
    }
  },
  "preloaded_verification": {
    "F1_legal_family": {
      "value": "common law",
      "source": "Legislation.gov.uk — FSMA 2000 Part VI"
    },
    "F11_regulator_type": {
      "value": "отдельная комиссия",
      "source": "FSMA 2000; FCA website."
    }
  },
  "additional_factors": {
    "F10_market_competition": {
      "value": "конкурентная",
      "assessment": "Lit order books (LSE, Cboe Europe, Turquoise, Aquis): ~58% объёма...",
      "source": "FCA CP25/31; big xyt / FlexTrade data."
    }
  }
}
```

---

## 3. Матрица покрытия по Ф1–Ф12

| Фактор | Спека | UK статус | HK статус |
|--------|-------|-----------|-----------|
| **Ф1** Правовая семья | Категориальная: common law / civil law / mixed | ✅ "common law" | ✅ "common law" (в jurisdiction_card.json) |
| **Ф2** ASDI (статутарная защита инвесторов) | Числовой 0–1, Djankov et al. 2008 | ❌ Отсутствует | ❌ Отсутствует |
| **Ф3** Private enforcement | Категориальная: высокий/средний/низкий/отсутствует | ✅ "средний" + обоснование | ❌ Отсутствует в 1B |
| **Ф4** Качество регулирования (WGI) | Числовой, WGI DataBank | ❌ Отсутствует | ❌ Отсутствует |
| **Ф5** Верховенство права (WGI) | Числовой, WGI DataBank | ❌ Отсутствует | ❌ Отсутствует |
| **Ф6** Политическая стабильность (WGI) | Числовой, WGI DataBank | ❌ Отсутствует | ❌ Отсутствует |
| **Ф7** Глубина рынка (капитализация/ВВП) | Числовой %, WDI/WFE | ❌ Отсутствует | ❌ Отсутствует |
| **Ф8** Концентрация владения | Категориальная: дисперсная/умеренная/концентрированная | ✅ "дисперсная" + данные ONS | ❌ Отсутствует в 1B |
| **Ф9** Инвесторская база | Категориальная: розница/смешанная/институционалы | ✅ "институционалы" + доля | ❌ Отсутствует в 1B |
| **Ф10** Конкурентная структура площадок | Категориальная (авторская шкала) | ✅ "конкурентная" + описание | ❌ Отсутствует в 1B |
| **Ф11** Тип регулятора | ЦБ / комиссия / наднациональный / иной | ✅ "отдельная комиссия" | ✅ "commission" (в jurisdiction_card.json) |
| **Ф12** SRO-статус биржи | Категориальная: полная/частичная/отсутствует | ✅ "частичная" + обоснование | ❌ Отсутствует в 1B |

**Итого по UK:** 6 из 12 факторов (Ф1, Ф3, Ф8, Ф9, Ф10, Ф11, Ф12) — покрыты или частично покрыты. Ф2, Ф4, Ф5, Ф6, Ф7 отсутствуют (они количественные, из публичных датасетов — не были собраны пайплайном).

**Итого по HK:** только Ф1 и Ф11 есть в jurisdiction_card.json. 1B файл аналогичного наполнения для HK отсутствует (не импортировался).

---

## 4. Вопрос по Гонконгу — supranational_flag

В `jurisdiction_card.json` Гонконга выставлен `supranational_flag: true` с пояснением:

```
"supranational_framework": "Stock Connect and Bond Connect cross-border schemes linking Hong Kong and Mainland China"
```

Из спецификации факторов (раздел о наднациональных рамках в pipeline_v0_2.md):
> "EU исследуется один раз заранее (единственная заведомо известная рамка). Прочие рамки — при исследовании юрисдикции, если обнаруживается опора на наднациональное регулирование."

**Вопрос:** Stock Connect и Bond Connect — это:
- (а) технические схемы cross-border market access (инфраструктурные, не регуляторные), поэтому `supranational_flag` должен быть `false` для HK, или
- (б) достаточно значимая наднациональная регуляторная надстройка (Mainland China regulation через Connect schemes), которую нужно исследовать отдельно и учитывать при анализе?

Если (а) — данные нужно исправить вручную. Если (б) — уточнить, что именно должен покрывать запрос по этой "рамке".

---

## 5. Структурный вопрос: формат 1B_institutional.json

Фактический формат имеет три раздела: `qualitative_factors`, `preloaded_verification`, `additional_factors`. Это артефакт импорта из markdown-файла, не чистая схема пайплайна.

**Вопрос:** Какой должна быть целевая схема 1B для последующей загрузки в PostgreSQL? Предлагаемый вариант (на основе спеки Ф1–Ф12):

```json
{
  "jurisdiction": "string",
  "collected_at": "ISO timestamp",
  "factors": {
    "F1_legal_family": { "value": "string", "source": "string" },
    "F2_asdi": { "value": "number | null", "source": "string", "note": "string" },
    "F3_private_enforcement": { "value": "string", "assessment": "string", "source": "string" },
    "F4_regulatory_quality": { "value": "number", "percentile": "number", "year": "string", "source": "string" },
    "F5_rule_of_law": { "value": "number", "percentile": "number", "year": "string", "source": "string" },
    "F6_political_stability": { "value": "number", "percentile": "number", "year": "string", "source": "string" },
    "F7_market_depth": { "value": "number", "unit": "pct_gdp", "year": "string", "source": "string" },
    "F8_ownership_concentration": { "value": "string", "state_share_pct": "string | null", "assessment": "string", "source": "string" },
    "F9_investor_base": { "value": "string", "institutional_share_pct": "string | null", "source": "string" },
    "F10_market_competition": { "value": "string", "assessment": "string", "source": "string" },
    "F11_regulator_type": { "value": "string", "regulator_name": "string", "source": "string" },
    "F12_exchange_as_sro": { "value": "string", "assessment": "string", "source": "string" }
  }
}
```

Требует ли эта схема доработки или изменений?

---

## 6. Итого: что нужно для завершения пилота по институциональным факторам

| Действие | Приоритет |
|----------|-----------|
| Сбор Ф2 (ASDI), Ф4–Ф7 (WGI, WDI) через предварительный этап пайплайна | Высокий |
| Заполнение 1B для Гонконга (Ф3, Ф8, Ф9, Ф10, Ф12) | Высокий |
| Прояснение статуса Stock Connect/Bond Connect (supranational_flag HK) | Высокий |
| Согласование целевой схемы 1B_institutional.json | Средний |
| Проверка данных по Ф1 для HK (common law — верно, но Гонконг имеет смешанную систему с элементами mainland law в отдельных областях) | Средний |
