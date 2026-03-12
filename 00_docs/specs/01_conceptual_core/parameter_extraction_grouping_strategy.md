# Стратегия группировки ячеек для извлечения параметров
## Инструкции для постпроцессинга L3

**Дата:** 2026-03-10
**От кого:** Architect
**Кому:** Tech Lead
**Контекст:** Переход к этапу извлечения параметров из L3-результатов. Извлечение выполняется не по отдельным ячейкам, а по группам однородных ячеек. Документ определяет принцип группировки, логику двух проходов и обработку валидационных ограничений.

---

## 1. Почему группировка

Извлечение параметров отвечает на вопрос «какие параметры применяются и как они устроены» (набор, единицы измерения, методика расчёта, исключения, альтернативы, связки). Этот набор определяется не на уровне отдельной venue или tier, а на уровне регуляторной рамки. Ячейки, работающие в одной регуляторной рамке и по одному классу инструментов, имеют одинаковый набор параметров — различаются только числовые значения.

Группировка сокращает число запросов, устраняет избыточную фокусность и даёт более полную картину (LLM видит больше данных в одном контексте).

---

## 2. Принцип группировки

Ячейки объединяются по трём координатам:

```
Группа = Юрисдикция × Тип рынка (А03) × Класс инструментов (В02)
```

**Юрисдикция** — определяет законодательную базу и регулятора. Параметры задаются на этом уровне.

**Тип рынка (А03)** — regulated market, MTF, ATT Only, и т.д. Определяет объём применимых правил. Regulated market и MTF одной юрисдикции — разные группы, потому что у них разные регуляторные рамки и, как следствие, разные наборы параметров.

**Класс инструментов (В02)** — equities, bonds, funds, depositary receipts. У разных классов принципиально разные наборы параметров. Всегда раздельно.

---

## 3. Что НЕ объединяется

| Ситуация | Причина | Действие |
|---|---|---|
| Разные классы инструментов | Набор параметров принципиально различается | Всегда разные группы |
| Regulated market и MTF одной юрисдикции | Разный объём применимых правил, разные rulebook-и | Разные группы |
| Стандартный путь и ATT Only (admission_path=trading_only) на одной venue | Разные регуляторные рамки (полный UKLR vs. ADS only) | Разные группы |
| Distinct regime (secondary listing с принципиально иной структурой) | Другая структура требований | Отдельная группа |
| Подклассы с принципиально разным набором параметров (напр. professional vs. retail debt, если различаются не только значения, но и сам перечень применимых параметров) | Разный набор параметров | Разные группы |

**Пограничные случаи:** Если при формировании группы неясно, различаются ли подклассы по набору параметров или только по значениям — предварительно проверить: есть ли параметры, которые применяются к одному подклассу и не применяются к другому (например, требование к проспекту есть у retail, но отсутствует у professional). Если да — разные группы. Если набор одинаков, а различаются только пороги — одна группа.

---

## 4. Обработка валидационных ограничений

В группу включаются **только ячейки, прошедшие валидацию** (зелёные и жёлтые). Красные ячейки исключаются.

Логика:

| Ситуация | Действие |
|---|---|
| Все ячейки группы зелёные/жёлтые | Группа формируется, запускается извлечение |
| Часть ячеек группы красные | Группа формируется из оставшихся зелёных/жёлтых. В промпт включаются данные только по прошедшим валидацию ячейкам. В метаданных группы фиксируется: какие ячейки исключены и почему |
| Все ячейки группы красные | Группа не формируется. Фиксируется в логе как `[GROUP_SKIPPED]` с перечнем причин |
| В группе осталась одна ячейка | Группа формируется из одной ячейки — это допустимо, просто не даёт преимущества объединения |

**Важно:** группировка выполняется **после** валидации, а не до. Сначала — отфильтровать красные ячейки, затем — группировать оставшиеся.

---

## 5. Два прохода

### Проход 1: Извлечение структуры параметров (по группе)

**Цель:** определить, какие параметры из чеклиста применяются к данной группе, и описать конструкцию каждого параметра (единицы, методика расчёта, исключения, альтернативы, связки).

**Вход:** L3-данные всех ячеек группы (только прошедших валидацию).

**Промпт:**

```
You are analyzing the admission parameter framework for a group of venues
within the same jurisdiction, market type, and instrument class.

JURISDICTION: [jurisdiction]
MARKET TYPE: [market_type]
INSTRUMENT CLASS: [instrument_class]
VENUES/TIERS IN THIS GROUP: [list of cell identifiers with venue names]

Using the research data from all cells in this group, extract the COMMON
parameter framework.

For each parameter in the checklist below:
- If the parameter APPLIES to this group: describe its structure using the
  6-question template below. Where parameter VALUES differ between venues
  or tiers within the group — note the range of values, but focus on the
  STRUCTURAL description (units, calculation method, exclusions, alternatives,
  linkages).
- If the parameter does NOT APPLY: state "not_applicable" with brief
  explanation.
- If the data does not contain information about this parameter: state
  "data_not_found".

[INSERT INSTRUMENT-CLASS-SPECIFIC CHECKLIST — see parameter_extraction_instructions.md section 2]

PARAMETER DESCRIPTION TEMPLATE (6 questions):
1. WHAT IS ESTABLISHED? Numeric threshold, qualitative criterion, or
   combination. In what units (%, count, monetary amount, combination).
   If monetary — in what currency.
2. HOW IS IT CALCULATED? What is included, what is excluded. Cutoff
   thresholds. Who verifies.
3. ARE THERE ALTERNATIVES? Either/or options.
4. DOES IT VARY? By company size, tier, issuer type, market maker presence.
5. IS IT LINKED TO OTHER PARAMETERS? Bundles, dependencies.
6. SOURCE. Specific rule, section, chapter.

LIFECYCLE PHASES:
For each parameter, specify which phase(s) the value applies to:
- ADMISSION: threshold for initial admission
- CONTINUING: threshold for maintaining listing
- REMOVAL: threshold triggering suspension or delisting
If values differ by phase — report each separately.

ADDITIONAL PARAMETERS NOT IN CHECKLIST:
If you find requirements not matching any checklist parameter — report them
in a separate section with the same 6-question description.
```

**Выход:** структурное описание параметров группы + список additional parameters + список data_not_found.

### Проход 2: Извлечение значений (по ячейке)

**Цель:** для каждой конкретной ячейки — зафиксировать числовые значения параметров, структура которых определена в проходе 1.

**Вход:** результат прохода 1 (структура параметров) + L3-данные конкретной ячейки.

**Промпт:**

```
Given the parameter framework below (extracted for this jurisdiction,
market type, and instrument class), extract the specific threshold VALUES
for this venue/tier.

PARAMETER FRAMEWORK:
[insert Pass 1 result]

CELL: [cell_id, venue, tier, instrument class]

For each parameter in the framework:
- Report the specific numeric value or qualitative criterion for THIS
  venue/tier.
- If the value differs by lifecycle phase (admission / continuing / removal)
  — report each separately.
- If a parameter from the framework does not apply specifically to this
  venue/tier — state why.

Do NOT re-describe the parameter structure — only report values.
```

**Выход:** таблица значений параметров для конкретной ячейки.

**Примечание:** проход 2 дешевле и быстрее, потому что LLM уже знает что искать. Промпт короче, задача уже.

---

## 6. Обработка результатов

### После прохода 1:

| Проверка | Условие | Действие |
|---|---|---|
| Пустой результат | Ни один параметр не найден и не помечен not_applicable | `[WARNING]` — вероятно, L3-данные группы недостаточны |
| Массовый data_not_found | >70% чеклиста — data_not_found | `[WARNING]` — кандидат на доразведку |
| Неизвестные параметры | Секция ADDITIONAL не пуста | `[UNKNOWN_PARAM]` в лог — эскалация на Architect |
| Расхождения внутри группы | Параметр применяется к одним ячейкам группы, но не к другим | Проверить: возможно, группа неоднородна и требует разделения |

### После прохода 2:

| Проверка | Условие | Действие |
|---|---|---|
| Значение не найдено | Параметр есть в структуре (проход 1), но значение для конкретной ячейки не извлечено | `[VALUE_NOT_FOUND]` — кандидат на точечный доразведочный запрос |
| Противоречие с проходом 1 | Ячейка показывает параметр, отсутствующий в структуре группы | `[INCONSISTENCY]` — проверить, корректна ли группировка |

---

## 7. Порядок работы

1. Отфильтровать красные ячейки (по результатам валидации).
2. Из оставшихся — сформировать группы по принципу «юрисдикция × тип рынка × класс инструментов» (раздел 2), с учётом исключений (раздел 3).
3. Для каждой группы — запустить проход 1 (извлечение структуры параметров).
4. Обработать результаты прохода 1 (раздел 6). Эскалировать unknown parameters.
5. Для каждой прошедшей валидацию ячейки — запустить проход 2 (извлечение значений).
6. Обработать результаты прохода 2 (раздел 6).
7. Сформировать сводку: покрытие параметров по группам, пробелы, неизвестные параметры, кандидаты на доразведку.

---

*Документ является инструкцией для этапа извлечения параметров. Связан с parameter_extraction_instructions.md (чеклисты по классам инструментов) и концептуальным ядром v0 (определения А03, В02, Г01).*
