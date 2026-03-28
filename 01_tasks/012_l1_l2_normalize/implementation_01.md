# Отчёт о реализации: Task 012 — L1/L2 Normalizations

## Что реализовано

Модуль `l1_l2_normalize.py` нормализует поля в `jurisdiction_card.json` (L1) и `venue_card.json` (L2). Все операции идемпотентны.

**С-1: `legal_family` (алгоритмическая нормализация)**
- Приводит значение к нижнему регистру: `val.strip().lower()`
- Допустимые значения: `"common law"` | `"civil law"` | `"mixed"`
- Германия: `"Civil law"` → `"civil law"` (единственное исправление)
- Пропускает, если значение уже в нижнем регистре

**С-2: `market_type` (новое поле, lookup-таблица)**
- Добавляется только если поле отсутствует
- Все 6 юрисдикций получат `"DM"` (Developed Market)
- При отсутствии в lookup: предупреждение в лог, поле не добавляется

**Ю-1: `listing_authority_short` (новое поле, LLM gpt-5-mini)**
- Добавляется только если поле отсутствует
- LLM создаётся только при наличии юрисдикций без этого поля
- При ошибке LLM: ошибка в лог, поле не добавляется
- Результат обрезается до 30 символов

**П-2: `venue_type` (алгоритмическая нормализация, venue_card.json)**
- Нормализация через `_VENUE_TYPE_MAP`:
  - `"MTF"` → `"mtf"` (LSE_AIM, Tradegate_Berlin_Stock_Exchange, Aquis_Exchange_Europe, Euronext_Growth_Paris, Euronext_Access_Paris, MTS_France — 6 площадок)
  - `"other"` → `"exchange_regulated"` (BÖAG_Börsen, Börse_München, Börse_Stuttgart — 3 немецких площадки)
  - `"regulated_market"`, `"mtf"`, `"otf"`, `"exchange_regulated"` — уже нормализованы, пропускаются

## Файлы

### Новые
- `02_src/pipeline/l1_l2_normalize.py` — основной модуль нормализации
- `02_src/tools/run_l1_l2_normalize_catchup.py` — catch-up скрипт для существующих данных

### Изменённые
- `02_src/run_pipeline.py` — добавлены L1 Step 10 и L2 Step 6

## Изменения в данных (ожидаемые при запуске catch-up)

| Файл | Поле | До | После |
|------|------|----|-------|
| Германия/jurisdiction_card.json | `legal_family` | `"Civil law"` | `"civil law"` |
| Все 6/jurisdiction_card.json | `market_type` | отсутствует | `"DM"` |
| Все 6/jurisdiction_card.json | `listing_authority_short` | отсутствует | аббревиатура (LLM) |
| LSE_AIM/venue_card.json | `venue_type` | `"MTF"` | `"mtf"` |
| Tradegate_Berlin_Stock_Exchange/venue_card.json | `venue_type` | `"MTF"` | `"mtf"` |
| Aquis_Exchange_Europe/venue_card.json | `venue_type` | `"MTF"` | `"mtf"` |
| Euronext_Growth_Paris/venue_card.json | `venue_type` | `"MTF"` | `"mtf"` |
| Euronext_Access_Paris/venue_card.json | `venue_type` | `"MTF"` | `"mtf"` |
| MTS_France/venue_card.json | `venue_type` | `"MTF"` | `"mtf"` |
| BÖAG_Börsen/venue_card.json | `venue_type` | `"other"` | `"exchange_regulated"` |
| Börse_München/venue_card.json | `venue_type` | `"other"` | `"exchange_regulated"` |
| Börse_Stuttgart/venue_card.json | `venue_type` | `"other"` | `"exchange_regulated"` |

## Особенности реализации

- **LLM создаётся лениво**: `ChatOpenAI` инициализируется только если есть хотя бы одна юрисдикция без `listing_authority_short`
- **Идемпотентность**: все проверки через `"field" not in data` (L1) и `vt_raw in _VENUE_TYPE_NORMALIZED` (L2)
- **JSON сохранение**: `ensure_ascii=False, indent=2` для всех файлов
- **Формат логов**:
  - `[L1 UPDATED] {name_ru} — legal_family: '{old}' → '{new}', market_type: '{mt}', listing_authority_short: '{short}'`
  - `[L1 SKIP] {name_ru} — already normalized`
  - `[L2 UPDATED] {venue_key} — venue_type: '{old}' → '{new}'`
  - `[L2 SKIP] {venue_key} — already normalized`

## Известные проблемы

- Россия отсутствует в `_MARKET_TYPE_LOOKUP` (не входит в список 6 юрисдикций проекта) — при обнаружении директории будет логировано предупреждение и поле пропущено
- `listing_authority_short` зависит от качества LLM-ответа; при сбое сети поле не добавляется (без автоперезапуска, согласно правилу проекта по сетевым ошибкам)
