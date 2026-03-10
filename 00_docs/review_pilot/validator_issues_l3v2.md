# Отчёт об ошибках валидатора L3 v2

**Дата:** 2026-03-10
**Контекст:** Пилотный прогон L3 v2 (venue×instrument_class архитектура), 45 Parallel задач, 74 per-cell файла после постпроцессинга.

---

## Проблема 1 — Completeness checklist не разделён по query_type (критическая)

### Описание

В `02_src/level_3/validator.py` определён единый `_COMPLETENESS_CHECKLIST` по классам инструментов:

```python
_COMPLETENESS_CHECKLIST = {
    "equity": ["free float", "market capitalisation", "financial history", ...],
    "bond":   ["minimum issue size", "issuer eligibility", "prospectus", ...],
    ...
}
```

Этот чеклист содержит **исключительно топики 3A** (условия допуска к листингу). Однако валидатор применяет его ко **всем трём query_type** — 3A, 3B, 3C.

### Следствие

- **3B** (ongoing obligations: reporting, disclosure, corporate events) — топики 3A в этом контенте отсутствуют → `completeness ≈ 0.00–0.25`
- **3C** (enforcement, suspension, delisting) — то же → `completeness = 0.00`
- Итог: `overall_flag=True` ("нужна проверка") генерируется автоматически для ~88% ячеек, большинство из них — ложноположительные

### Доказательства из лога

```
REVIEW NEEDED: GB_LSE_Main_Market_debt_and_debtlike_securities_bond 3B — completeness=0.20
REVIEW NEEDED: GB_LSE_Main_Market_debt_and_debtlike_securities_bond 3C — completeness=0.00
REVIEW NEEDED: GB_LSE_Main_Market_fund_sfs 3B — completeness=0.00
REVIEW NEEDED: GB_LSE_Main_Market_fund_sfs 3C — completeness=0.00
REVIEW NEEDED: HK_HKEX_Main_Board_fund 3B — completeness=0.00
REVIEW NEEDED: HK_HKEX_Main_Board_fund 3C — completeness=0.00
```

При этом 3A по тем же ячейкам нередко проходит нормально:

```
OK: GB_LSE_Main_Market_debt_and_debtlike_securities_bond 3A (completeness=1.00)
```

### Необходимое исправление

Чеклист должен быть трёхмерным: `instrument_class × query_type`. Пример структуры:

```python
_COMPLETENESS_CHECKLIST = {
    ("equity", "3A"): ["free float", "market capitalisation", ...],
    ("equity", "3B"): ["periodic reporting", "disclosure of major shareholdings", ...],
    ("equity", "3C"): ["suspension criteria", "delisting procedure", ...],
    ("bond",   "3A"): ["minimum issue size", "issuer eligibility", "prospectus", ...],
    ("bond",   "3B"): ["periodic reporting", "price-sensitive disclosure", ...],
    ("bond",   "3C"): ["suspension", "delisting", "event of default handling", ...],
    ...
}
```

Содержимое чеклистов для 3B и 3C необходимо определить на основе спецификации пайплайна (схемы `SCHEMA_3B_V2`, `SCHEMA_3C_V2` в `venue_runner.py`).

---

## Проблема 2 — Противоречивые результаты scope + completeness

### Описание

Ряд ячеек получает `scope_ok=False` при высоком `completeness_score`, что логически противоречиво: если контент не о той площадке/уровне, он не может одновременно полностью покрывать ожидаемые топики.

### Примеры

```
REVIEW NEEDED: GB_Aquis_Stock_Exchange_bond 3A — scope=False completeness=1.00 source=False
REVIEW NEEDED: GB_LSE_Main_Market_admission_to_trading_only_att_bond 3A — scope=False completeness=1.00 source=False
REVIEW NEEDED: HK_HKEX_GEM_bond 3A — scope=False completeness=1.00 source=False
```

`completeness=1.00` означает, что LLM нашёл все ожидаемые топики в контенте. Одновременный `scope_ok=False` указывает на то, что LLM-валидатор применяет избыточно строгий критерий scope — скорее всего, ложноположительно флажит cross-venue ссылки (например, сравнительные упоминания других площадок в рамках описания одного инструмента).

### Необходимое исправление

Уточнить формулировку scope check в промпте: разграничить **основной предмет** результата (должен быть target venue/tier) и **допустимые упоминания** других площадок в сравнительном контексте.

---

## Итоговая статистика прогона

| Метрика | Значение |
|---|---|
| Всего ячеек валидировано | 74 |
| OK | 9 (12%) |
| REVIEW NEEDED | 65 (88%) |
| Предположительно ложноположительных (проблема 1+2) | ~55 |

---

## Рекомендации для архитектора

1. **Определить чеклисты для 3B и 3C** по каждому instrument_class на основе схем `SCHEMA_3B_V2` / `SCHEMA_3C_V2`
2. **Скорректировать промпт scope check** — разрешить упоминания других площадок в сравнительном контексте
3. **Рассмотреть порог `overall_flag`**: возможно, completeness < 0.5 как критерий стоит применять только для query_type, для которого определён чеклист
