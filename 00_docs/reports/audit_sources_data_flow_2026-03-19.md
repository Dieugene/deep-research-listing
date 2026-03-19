# Аудит перетока данных: источники/выдержки/URL

**Дата:** 2026-03-19
**Автор:** Tech Lead (пайплайн)

---

## 1. Перечень типов файлов с `parallel_output`

| Файл | Уровень | `parallel_output.basis[]` | `citations[]` (derived) | `sources[]` (derived) |
|------|---------|--------------------------|------------------------|-----------------------|
| `1A_architecture.json` | L1 | ✅ | — | — |
| `1B_institutional.json` | L1 | ✅ (все кроме GB) / ❌ (GB — legacy import) | — | — |
| `1C_venues.json` | L1 | ✅ | — | — |
| `jurisdiction_card.json` | L1 | — | — | ✅ (pipeline) |
| `2A_structure.json` | L2 | ✅ | — | — |
| `venue_card.json` | L2 | ✅ (Phase 2) | — | ✅ (pipeline) |
| `3A/3B/3C_raw.json` (cell dirs) | L3 Ph1 | ✅ | ✅ (pipeline) | — |
| `_parallel_raw/*_raw.json` | L3 Ph2 | ✅ | ✅ (pipeline) | — |
| `matrix.json` | L3 | — | ✅ (embedded per cell) | — |
| `pass2.json` / `pass2_ru.json` | L3 | — | — | — (только text `source`) |
| `4A_raw.json` | L4 | ✅ | — | — |
| `level4.json` | L4 | — | — | ✅ (pipeline) |

---

## 2. Структура источников в basis (единая для всех типов)

```json
{
  "parallel_output": {
    "basis": [
      {
        "field": "instrument_requirements",
        "reasoning": "The analysis of instrument-level requirements was derived from...",
        "citations": [
          {
            "url": "https://handbook.fca.org.uk/...",
            "title": "FCA Handbook",
            "excerpts": ["Rule 5.5.2R: At least 10% of shares..."],
            "confidence": "high"
          }
        ],
        "confidence": "medium"
      }
    ]
  }
}
```

Поля, присутствующие в basis, но **не переносимые** в derived-файлы:
- `reasoning` — обоснование исследования
- `confidence` — уровень уверенности (basis-level и citation-level)

---

## 3. Переток: basis → derived-файлы

### L1: basis → jurisdiction_card.json `sources[]`

| Шаг | Функция | Что делает | Потери |
|-----|---------|-----------|--------|
| Extraction | `extract_sources_from_raw()` | Читает basis, дедуплицирует по URL, мержит excerpts | field (first-seen only) |
| Merge | `merge_sources_dedup()` | Сливает sources из 1A + 1B + 1C | URL-дедупликация |
| Write | `process_level1_citations()` | Записывает в jurisdiction_card.json | — |

### L2: basis → venue_card.json `sources[]`

Аналогично L1, но один файл (2A) → без merge.

### L3: basis → citations[] → matrix.json

| Шаг | Функция | Что делает | Потери |
|-----|---------|-----------|--------|
| Extraction | `extract_sources_from_raw()` | Дедупликация по URL | Multi-field привязки |
| Filtering | `_filter_citations_by_content()` | Удаление citations к пустым секциям | **Ложные срабатывания** (tiers, reasoning-only) |
| Write | `_add_citations_to_raw_file()` | Записывает `citations[]` в 3A/3B/3C_raw.json | — |
| Distribution | `_distribute_citations()` | Из `citations[]` в matrix.json по ячейкам | Unmapped fields пропускаются |

### L4: basis → level4.json `sources[]`

Extraction + merge (аналогично L1).

---

## 4. Потери: полный перечень

### A. Дедупликация по URL (extract_sources_from_raw, sources.py:188)

Когда один URL фигурирует в нескольких basis-записях (привязан к разным field), сохраняется только первый field. Excerpts мержатся, но привязка к остальным секциям теряется.

### B. Фильтрация orphaned citations (sources.py:107)

`_filter_citations_by_content()` удаляет citations к пустым секциям. Включает ложные срабатывания:
- `content.tiers` (list) — 2009 citations, фильтр считает list за пустую секцию
- Секции с reasoning + citations, но пустым description — 52 случая

### C. Unmapped fields в matrix distribution (matrix_builder.py:260)

Citations с field, отсутствующим в `_CITATION_FIELD_MAP`, пропускаются при распределении в матрицу.

### D. reasoning и confidence не переносятся

Из basis в derived-файлы не попадают поля `reasoning` и `confidence`. Reasoning содержит обоснование исследования. Confidence коррелирует с наличием excerpts.

### E. 1B_institutional.json (Великобритания) — legacy import

Файл Великобритании не содержит `parallel_output` (legacy import из ранней версии пайплайна). Все остальные юрисдикции имеют полноценный `parallel_output.basis[]` в 1B.

---

## 5. Количественная оценка

### Весь датасет:

| Метрика | Значение |
|---------|----------|
| Citations в `parallel_output.basis[]` | 4434 |
| Citations в derived `citations[]`/`sources[]` | 1320 |
| **Потеря** | **3114 (70%)** |

### L1 Великобритания:

| Файл | basis citations | Excerpts |
|------|----------------|----------|
| 1A | 30 | 0 |
| 1B | 0 (legacy) | 0 |
| 1C | 33 | 227 |
| **Итого basis** | **63** | **227** |
| **jurisdiction_card.json** | **57** | **~228** |
| **Потеря** | **10%** | **~0%** |

### L3 GB LSE Main Market equity:

| Файл | basis citations | Unique URLs | `citations[]` | Потеря |
|------|----------------|-------------|---------------|--------|
| 3A | 18 | 6 | 5 | 72% |
| 3B | 8 | 4 | 4 | 50% |
| 3C | 7 | 5 | 3 | 57% |
| **Итого** | **33** | **13** | **12** | **64%** |

---

## 6. Особые находки

### 6.1. 1B_institutional.json (Великобритания) — нет parallel_output

GB 1B имеет структуру legacy import:
```json
{
  "jurisdiction": "United Kingdom",
  "source": "...",
  "source_file": "...",
  "imported_at": "...",
  "qualitative_factors": {...}
}
```
Все остальные юрисдикции (AU, DE, HK, SG, FR) имеют полноценный `parallel_output.basis[]` в 1B. **Вероятный след legacy-обработки** — данные были импортированы, а не получены из Parallel API.

### 6.2. pass2.json — текстовые ссылки, не потеря

`pass2.json` содержит поле `source` в каждом параметре, но это **текстовая ссылка на нормативный документ** (например, `"UKLR 5.5.2R–5.5.3R"`), а не citation-объект с URL и excerpts.

Эти ссылки **генерируются LLM** (Phase 2 Pass 2) при структурировании параметров из контента 3A/3B. Это другой слой данных — LLM извлекает параметры и указывает нормативные основания в текстовом формате.

**Это не потеря** — pass2 никогда не должен был содержать citations из basis. Это отдельный продукт (параметры), а не перенос источников.

### 6.3. confidence — не потеря данных, потеря метаданных

Поле `confidence` из basis не переносится в derived-файлы. Это **потеря метаданных**, а не источников. Данные (URL, excerpts) сохраняются; теряется только индикатор достоверности.

Корреляция: `confidence=low` ↔ `excerpts=[]`. Поэтому отсутствие confidence в derived-файлах можно компенсировать проверкой наличия excerpts.
