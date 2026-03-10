# Патч: корректировки Level 2 по итогам ревизии отчёта

**Дата:** 2026-03-09
**От кого:** Architect
**Кому:** Tech Lead
**Контекст:** Ревизия report_level2_postprocess_results.md. Результаты в целом корректны, но выявлены четыре проблемы, из которых две влияют на количество ячеек (блокеры), две — на семантическую чистоту (нужны до масштабирования).

---

## Блокер 1. HKEX Main Board bonds: разбить на две ячейки

**Проблема:** Chapter 37 (professional-only debt) и Chapters 22–36 (retail debt) классифицированы как модификаторы на одной bond-ячейке. Это некорректно.

**Обоснование:** Тест из DEF-G06 Case 2: «Can retail debt requirements be described as 'same as professional, except [list]'?» — нет. У них разная целевая аудитория, разные требования к проспекту (professional освобождён), разные стандарты disclosure, разный надзорный подход. Структура требований различается, а не только значения. Это два разных admission regime для двух подклассов инструмента.

**Действие:** Заменить одну ячейку `HKEX_Main_Board_bond` на две:
- `HK_HKEX_Main_Board_bond_professional` (Ch.37, professional investors only)
- `HK_HKEX_Main_Board_bond_retail` (Ch.22–36, retail)

Модификаторы `chapter_37_professional_only_debt` и `retail_debt` убрать — они стали отдельными ячейками.

Генерировать стандартные L3-промпты (3A/3B/3C) для каждой.

---

## Блокер 2. LSE Main Market: добавить ячейку для SFS

**Проблема:** Specialist Fund Segment (SFS) записан как тематический сегмент в метаданных, ячейку не порождает. Но SFS имеет собственные правила допуска (UKLR Chapter 11 area / бывший Listing Rules Chapter 15), отличающиеся от базовых правил Main Market. Это не информационная метка.

**Обоснование:** SFS принимает closed-end investment funds и другие специализированные инструменты по собственным критериям, которые не совпадают с ESCC и не совпадают с CEF-категорией UKLR. У SFS собственные eligibility criteria, собственный disclosure regime. По тесту: «имеет ли сегмент собственные правила допуска, отличающиеся от базовых?» — да.

**Действие:** Добавить ячейку `GB_LSE_Main_Market_fund_SFS` с `segment=SFS`. Генерировать стандартные L3-промпты (3A/3B/3C).

HGS, Shanghai-London Stock Connect, SBM — остаются метаданными, ячеек не порождают (у них нет собственных admission criteria, только disclosure overlay или маркетинговая метка).

**Правило для промпта (добавить в L2):**

```
RULE — Segment cell generation:
A specialized segment generates a Level 3 cell ONLY IF it has its own
admission requirements that DIFFER from the base venue requirements.
If the segment is purely informational (marketing label, index membership,
disclosure overlay with no distinct admission criteria) — it does NOT
generate a cell; record it as metadata only.
```

---

## До масштабирования 1. admission_path=trading_only на AIM

**Проблема:** Все ячейки AIM маркированы `admission_path=trading_only`. На AIM это не «альтернативный путь» (как ADS Schedule 6 на Main Market), а единственный способ существования — AIM как MTF не имеет Official List. Текущая маркировка создаёт ложную аналогию с LSE Main Market и будет воспроизводиться на всех MTF.

**Действие:**
- Убрать `admission_path=trading_only` с ячеек AIM.
- На уровне VenueCard добавить поле `listing_architecture: "trading_only"` для площадок, где Official Listing не применяется в принципе (MTF, OTF).
- Поле `admission_path=trading_only` на уровне ячеек использовать только для случаев, когда на площадке с листингом существует альтернативный путь без листинга (ADS Schedule 6 на LSE Main Market).

---

## До масштабирования 2. Сегменты в массиве tiers[]

**Проблема:** SFS, HGS, Shanghai-London, SBM хранятся в `venue_card.tiers[]` с `segment_type=thematic_segment`. Тиры (А05) и сегменты (А04) — разные понятия с разной семантикой. Хранение в одном массиве создаст путаницу при масштабировании (когда на одной площадке будут и тиры, и сегменты одновременно — например, MOEX: три тира + четыре сегмента).

**Действие:** В VenueCard завести отдельный массив `segments[]` наряду с `tiers[]`. Или, если структура данных не допускает — переименовать `tiers[]` в `structure[]` с обязательным полем `type: "tier" | "segment"`.

---

## Ответы на вопросы из отчёта

**В01. ATT Only: per-instrument-class.** 9 ячеек для LSE Main Market — корректно. На L3 исследование по equity и по debt различается; одна инструмент-независимая ячейка дала бы кашу. Правило:

```
RULE — admission_path cells:
An alternative admission path generates separate cells for each instrument
class it covers. Do not merge instrument classes into one cell even if the
rulebook chapter is shared.
```

**В02. admission_path на MTF.** См. «До масштабирования 1» выше.

**В03. HKEX bonds.** См. «Блокер 1» выше.

**В04. Сегменты.** SFS — порождает ячейку. HGS, Shanghai-London, SBM — не порождают. См. «Блокер 2» выше.

---

## Ожидаемый результат после корректировок

| Площадка | Было ячеек | Стало ячеек | Изменение |
|---|---|---|---|
| LSE Main Market | 9 | 10 | +1 (SFS) |
| LSE AIM | 2 | 2 | без изменений (убран флаг с ячеек, добавлен на VenueCard) |
| Aquis | 6 | 6 | без изменений |
| HKEX Main Board | 5 | 6 | +1 (bond → bond_professional + bond_retail) |
| HKEX GEM | 2 | 2 | без изменений |
| **Итого** | **24** | **26** | **+2 ячейки, +6 L3-промптов** |

---

*После применения корректировок — повторный прогон затронутых площадок (LSE Main Market, HKEX Main Board). Остальные площадки перегона не требуют.*
