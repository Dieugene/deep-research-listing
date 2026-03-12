# Спецификация: Уровень 4 — регуляторные цели и обоснования

**Дата:** 2026-03-11  
**От:** Архитектор пайплайна  
**Кому:** Tech Lead  
**Контекст:** Завершён сбор справочных данных (L3 + Pass 2) по пилотным юрисдикциям. Уровень 4 — последний разведочный этап пайплайна.

---

## 1. Назначение

Сбор данных о регуляторных проблемах, противоречиях и обоснованиях, связанных с правилами допуска/листинга в каждой юрисдикции. Какие проблемы обсуждались, какие цели вступали в противоречие, какими параметрами регулирования предлагалось решать выявленные проблемы, и когда это происходило.

Данные собираются для последующего изучения аналитиками.

---

## 2. Единица запроса

**Юрисдикция.** Один запрос на юрисдикцию (47 запросов при масштабировании). Регуляторные дискуссии ведутся на уровне юрисдикции: в документах регулятора, парламентских обсуждениях, consultation papers, аналитических публикациях.

---

## 3. Формат запроса

**Тип:** Deep Research, text output.  
**Процессор:** pro.

Text output — нужен связный аналитический нарратив с контекстом: почему принимались решения, какие были дискуссии, какие альтернативы рассматривались. JSON schema здесь неуместна — регуляторная дискуссия не раскладывается в предопределённые поля.

---

## 4. Формирование промпта

Промпт формируется **алгоритмически** с подстановкой из jurisdiction_card.

### Шаблон промпта

```
БЛОК 1: Контекст юрисдикции (подстановка)

Jurisdiction: [JURISDICTION]
Securities regulator: [REGULATOR NAME] ([REGULATOR TYPE])
Main trading venues: [перечень venue из jurisdiction_card]


БЛОК 2: Задание

Research the regulatory policy debate around securities listing 
and admission to trading in [JURISDICTION]. Focus on substance — 
problems identified, conflicts between objectives, and how 
regulatory parameters were used to address them.

A. REGULATORY PROBLEMS DISCUSSED

What problems related to listing and admission to trading have 
been discussed in [JURISDICTION] — both at the official level 
(regulator statements, consultation papers, legislative reviews, 
regulatory impact assessments) and in public/analytical discourse 
(industry associations, academic research, market commentary)?

For each problem identified:
- What was the problem (e.g., declining IPO numbers, insufficient 
  investor protection, regulatory burden on SMEs, low liquidity 
  of secondary market, capital flight to competing venues)
- Who articulated it (regulator, exchange, industry body, 
  academic, government)
- Approximate period (years/decade — precision to the year 
  is sufficient, greater detail not needed)
- Source (document, publication)

B. REGULATORY CONTRADICTIONS AND PRIORITIES

What contradictions between regulatory objectives have been 
identified or debated?

Examples of contradiction types (not exhaustive — find what 
actually exists in this jurisdiction):
- Investor protection vs attracting issuers (stricter rules 
  protect investors but deter listings)
- Market quality vs market development (high thresholds ensure 
  quality but exclude smaller companies)
- National competitiveness vs international harmonisation 
  (differentiation vs convergence)
- Public market access vs investor sophistication 
  (retail participation vs professional-only segments)

For each contradiction found:
- Which objectives conflicted
- How was the trade-off resolved (which objective was prioritised, 
  what compromise was reached)
- Approximate period
- Source

C. REGULATORY PARAMETERS AS TOOLS

Which specific listing parameters (thresholds, requirements, 
procedures) were explicitly discussed as instruments for addressing 
the identified problems?

Do not list all listing rules — only those where there is evidence 
in regulatory documents or public discourse that the parameter was 
DELIBERATELY CHOSEN or CALIBRATED to address a specific problem 
or achieve a specific objective.

For each:
- Which parameter (e.g., free float threshold, market cap minimum, 
  sponsor requirement, lock-up period)
- What problem it was intended to address
- Was the calibration debated (e.g., "25% vs 10% free float — 
  arguments for and against")
- Approximate period of the discussion/decision
- Source

D. REFORMS AND THEIR DRIVERS

What significant reforms of the listing/admission framework have 
occurred in [JURISDICTION] in the last 10–15 years?

For each reform:
- What changed (briefly — the current rules are already collected 
  separately)
- What problem or objective drove the reform
- Was there opposition or alternative proposals
- Approximate year
- Source (consultation paper, explanatory memorandum, 
  parliamentary record)


БЛОК 3: Инструкция по источникам

Preferred sources (in order of priority):
1. Consultation papers and regulatory impact assessments 
   by [REGULATOR NAME]
2. Explanatory memoranda to legislation
3. Strategic documents and annual reports of [REGULATOR NAME] 
   and [VENUE NAME(S)]
4. Parliamentary / legislative committee records
5. Industry body publications (e.g., CBI, TheCityUK for UK; 
   HKIFA, Chamber of Commerce for HK)
6. Academic research on capital market regulation 
   in [JURISDICTION]
7. Regulator speeches and public statements

Do NOT rely on generic descriptions of listing rules. 
The rules themselves are already collected. This query is about 
the REASONING and DEBATE behind the rules.


БЛОК 4: Временной аспект

For all findings — note the approximate time period (decade or 
specific years). Regulatory objectives and priorities change over 
time. A jurisdiction may have prioritised market development 
in the 2000s and shifted to investor protection after a crisis 
in the 2010s. Capturing this evolution is important.

Precision: year or period (e.g., "2015–2018", "post-GFC", 
"following the 2024 reform"). Do not attempt month-level dating.
```

### Переменные подстановки

| Переменная | Источник |
|-----------|---------|
| Jurisdiction | jurisdiction_card |
| Regulator name, type | jurisdiction_card |
| Venue names | jurisdiction_card.venues |
| G04 (split/merged/mixed) | jurisdiction_card |
| EU membership | jurisdiction_card.supranational |

Промпт не содержит конкретных параметров из Pass 2. Parallel сам находит, какие параметры обсуждались в регуляторном контексте, и это может не совпадать с тем, что мы считаем ключевыми.

---

## 5. Постобработка

### LLM-постобработка (один вызов на юрисдикцию)

**Вход:** текстовый результат Parallel.

**Задачи:**

1. **Структурирование.** Из свободного текста выделить:
   - Перечень проблем (с датировкой, источником, кто артикулировал)
   - Перечень противоречий (какие цели, как разрешено, период)
   - Перечень параметров-инструментов (какой параметр, какая проблема, период)
   - Перечень реформ (что изменилось, драйвер, год)

2. **Перевод на русский.**

3. **Сохранение** как блок Ж карточки юрисдикции (level4.json).

### Формат level4.json

```json
{
  "jurisdiction": "string",
  "problems": [
    {
      "description": "string",
      "description_ru": "string",
      "articulated_by": "string — regulator / exchange / industry / academic / government",
      "period": "string — e.g., '2015–2020', 'post-GFC'",
      "source": "string"
    }
  ],
  "contradictions": [
    {
      "objective_a": "string",
      "objective_b": "string",
      "resolution": "string — how the trade-off was resolved",
      "resolution_ru": "string",
      "period": "string",
      "source": "string"
    }
  ],
  "parameters_as_tools": [
    {
      "parameter_description": "string — какой параметр",
      "parameter_description_ru": "string",
      "problem_addressed": "string",
      "calibration_debate": "string — if any",
      "period": "string",
      "source": "string"
    }
  ],
  "reforms": [
    {
      "description": "string",
      "description_ru": "string",
      "driver": "string — what problem/objective",
      "opposition": "string — if any",
      "year": "string",
      "source": "string"
    }
  ],
  "sources_summary": ["string — all sources cited"]
}
```

Примечание: поле `parameters_as_tools.parameter_description` — свободный текст, не parameter_id из словаря. Маппинг на словарь П01–П35 (если нужен) — отдельный аналитический шаг, не часть данного пайплайна.

---

## 6. Отображение во Viewer

Добавить в карточку юрисдикции блок «Регуляторные цели и обоснования» (блок Ж по спецификации информационной архитектуры). Четыре свёртываемых секции:
- Проблемы
- Противоречия
- Параметры как инструменты
- Реформы

Каждая запись — с датировкой и источником. Цветовой индикатор validation_status.

---

## 7. Количество запросов

| Компонент | На юрисдикцию | Пилот (2 юрисдикции) | Масштабирование (47) |
|-----------|--------------|---------------------|---------------------|
| Parallel (4A) | 1 | 2 | 47 |
| LLM-постобработка | 1 | 2 | 47 |
| LLM-валидация | 1 | 2 | 47 |

---

*Спецификация для реализации. Дата: 2026-03-11.*
