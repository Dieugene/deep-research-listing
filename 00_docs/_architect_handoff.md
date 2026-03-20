# Передача дел: Tech Lead (пайплайн)

**Дата:** 2026-03-20
**Контекст:** Сессия по аудиту и исправлению пайплайна данных (Tasks 020-027)

## Что сделано

### Tasks 020-024: Постобработка L3
- Добавлены description_ru для всех L3 секций (Task 021)
- Добавлены _ru поля: tier_ru, driver_ru, opposition_ru, problem_addressed_ru, param_label_ru, notes_ru (Task 022)
- Удалены артефакты из excerpts: даты, "Read more" (Task 024)
- Классификация типов L3 citations + fix "Fetched web page" titles (Task 020)

### Task 025: Аудит и восстановление источников
- Убрана дедупликация по URL в extract_sources_from_raw (сохраняет каждую пару URL×field)
- Убран фильтр orphaned citations (_filter_citations_by_content удалён полностью)
- Добавлены confidence и reasoning из Parallel basis
- Перезапрошены 1B для UK, HK, RU (были legacy imports)
- L3 citations живут ТОЛЬКО в _parallel_raw/, НЕ в cell-dir и НЕ в matrix.json

### Task 026: Склейка фрагментированных excerpts
- 83 источника с построчными excerpts из PDF/таблиц → склеены LLM, помечены excerpts_joined=true

### Task 027: Канонический маппинг тиров
- tier_mapper.py: LLM (gpt-5) reconciles tier names across 3A/3B/3C → tier_map.json
- update_cells_list_from_tier_maps(): обновляет cells_list.json из tier_map (flat → реальные тиры, создаёт новые ячейки)
- postprocess_l3.py: использует tier_map вместо per-file LLM маппинга
- Результат: 119 cells (было 101), 117 с pass2_ru (было 93)

### Исправление порядка шагов
- В run_pipeline.py translate (Step 11) перемещён ПЕРЕД matrix (Step 12), иначе matrix создаётся без description_ru

## Текущий статус

Пайплайн полностью прогнан, 119 ячеек, 100% description_ru в matrix.json. Готов к передаче UX-разработчику и к перепрогону на чистых данных.

## Ключевые решения

- **L3 citations живут в _parallel_raw, не в cell-dir:** Parallel API отдаёт данные per-venue×instrument, а cell-dir — per-tier. Копирование citations в cell-dir создавало мультипликацию. Бэкенд должен читать citations из _parallel_raw.
- **Дедупликация по URL убрана:** Один URL может быть источником для нескольких секций (field). Каждая пара (URL, field) — отдельная citation.
- **Порядок шагов L3:** translate ПЕРЕД matrix, иначе description_ru не попадает в matrix.json.
- **tier_map + cells_list update:** Три Parallel запроса (3A/3B/3C) дают разные имена тиров. LLM reconciles их в единую карту. cells_list обновляется из tier_map перед дезагрегацией.

## Что важно знать преемнику

- **Бэкап данных** в `03_data/countries_backup_2026-03-20/` — можно удалить после подтверждения
- **4 ячейки без pass2_ru** — validation red из-за tier name mismatch в валидаторе (не блокирующе)
- **BÖAG дубль** `freverke` удалён, `freiverke` — основной
- **При ручном перепрогоне** — строго следовать порядку шагов из run_pipeline.py, не пропускать validation
- **Phase 2 extraction quality** — системная проблема: ~20-30% параметров not_found, не зависит от наших доработок
- **L4 excerpts = 0** — ограничение формата запроса (type=text), не баг пайплайна
- **Россия** — нет jurisdiction_card.json, 1B перезапрошен, но обработка L1 не завершена

## Следующие шаги

1. **Закоммитить** обновлённый backlog.md и исправление порядка шагов в run_pipeline.py
2. **Сообщить UX-разработчику** пересобрать SQLite — 119 ячеек, 100% description_ru в matrix
3. **Задача 015/016** (WGI метрики, схожие юрисдикции) — Low priority, не начаты
4. **Phase 2 quality** — системный вопрос, может потребовать улучшения промптов Pass 2
5. **Полный перепрогон** на чистых данных — пользователь планирует

## Файлы для чтения

- `00_docs/backlog.md` — текущий статус всех задач
- `00_docs/specs/04_interface/data_registry.md` — полный реестр расположения данных для бэкенда
- `00_docs/methodology.md` — описание методологии исследования
- `00_docs/reports/audit_sources_data_flow_2026-03-19.md` — аудит перетока данных по источникам
- `00_docs/specs/05_pipeline/prompt_canonical_tier_mapping.md` — промпт для tier mapping (от архитектора)
- `00_docs/specs/05_pipeline/escalation_tier_mapping_2026-03-20.md` — описание проблемы tier mapping
- `02_src/run_pipeline.py` — порядок всех шагов пайплайна (52 шага)
- `02_src/pipeline/tier_mapper.py` — канонический маппинг тиров + обновление cells_list
- `02_src/pipeline/sources.py` — извлечение citations (без дедупликации)
- `00_docs/reports/ux_handoff_sources_restored_2026-03-19.md` — handoff для UX-разработчика по источникам
