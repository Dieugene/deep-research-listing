# Патч: ATT Only, DEF-G04, самодостаточность промптов

**Дата:** 2026-03-09

---

## 1. ATT Only: решение

**Запрос:** LLM классифицировал Admission to Trading Only как distinct_regime для depositary_receipt. Оставить как ячейку или убрать в модификаторы?

**Ответ:** Оставить как отдельную ячейку. ATT Only — не modifier (не меняет параметры режима для типа эмитента, а обходит режим листинга целиком: другой rulebook — Admission and Disclosure Standards вместо UKLR, другой надзорный орган — LSE вместо FCA). Не distinct_regime по G06 (не вторичный допуск). Это отдельный путь допуска, порождённый тем, что в UK листинг и допуск к торгам — разные правовые институты.

Маркировка: `admission_path: "trading_only"` вместо `distinct_regime: true`.

Итого для LSE Main Market: 7 ячеек (корректно).

---

## 2. Отсутствует DEF-G04

В промпте для вопроса про ATT Only использована ссылка `per DEF-G04`, но DEF-G04 не существует в prompt_ready_definitions.md. Промпт с такой ссылкой — сломан: LLM не имеет определения и либо проигнорирует, либо галлюцинирует.

**Действие:** добавить в prompt_ready_definitions.md:

```
### DEF-G04: Listing/Admission Architecture

DEFINITION — Listing/Admission Architecture:
In some jurisdictions, "official listing" (inclusion in an official register
maintained by a listing authority) and "admission to trading" (permission to
trade on a venue) are TWO SEPARATE legal acts, performed by different bodies,
under different rules. In other jurisdictions, these are merged into a single
process.

VALUES:
- "merged" — listing and admission to trading are a single procedure,
  single decision-maker. Most jurisdictions.
- "split" — listing and admission are separate. An instrument can be admitted
  to trading without being officially listed. Example: UK (FCA Official List
  vs. LSE admission).
- "mixed" — varies by market type or venue within the jurisdiction.

This is recorded at Level 1 (jurisdiction). It determines whether the Level 2
prompt should ask about admission-without-listing paths.
```

**Действие:** добавить в промпт уровня 2 (только если Level 1 зафиксировал split или mixed):

```
QUESTION — Admission without listing:
[вставить DEF-G04 буквально]

If this jurisdiction separates official listing from admission to trading:
does this venue admit instruments to trading WITHOUT official listing?
If yes — this is a separate admission path with its own set of rules.
Record it as a separate cell with admission_path: "trading_only".
If this jurisdiction does NOT separate listing from admission — skip this
question.
```

---

## 3. Проверка

При подготовке промптов для со стороны разработчика концептуального ядра могли быть (но не обязательно) допущены ошибки в виде кросс-референса между промтами через идентификаторы (например DEF-G04).
Нужно пересмотреть все ранее выданные prompt-ready тексты и патчи на предмет ссылок на идентификаторы без вложенного определения. Если найдены — обязательно сообщить пользователю.
