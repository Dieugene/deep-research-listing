# Отчёт для UX-разработчика: matrix.json — источники + description_ru

**Дата:** 2026-03-17
**От:** Tech Lead (пайплайн)
**Кому:** UX-разработчик (02_src/interface/)

---

## Что изменилось

`matrix.json` теперь содержит:
1. **`description_ru`** в каждом content-элементе — русский перевод описания секции
2. **`citations[]`** в каждой ячейке матрицы — источники с выдержками, распределённые по фазам

Все 101 файл `matrix.json` перегенерированы. Файл полностью самодостаточен для отображения tab-view и matrix-view.

---

## Структура ячейки матрицы

Каждая ячейка (например, `matrix.G07_1.D01_requirements`) содержит два массива:

```json
{
  "content": [
    {
      "subtitle": "Требования к эмитенту",
      "description": "Financial History: No requirement for a 3-year revenue-earning track record...",
      "description_ru": "Финансовая история: Требование о трёхлетней истории выручки отсутствует...",
      "source": "https://...",
      "origin_field": "eligibility_requirements"
    }
  ],
  "citations": [
    {
      "url": "https://www.handbook.fca.org.uk/handbook/UKLR/22/",
      "title": "FCA Handbook",
      "type": "rulebook",
      "field": "instrument_requirements",
      "excerpts": [
        "a class of equity shares admitted to listing, a sufficient number..."
      ]
    }
  ]
}
```

### Поля content-элемента

| Поле | Тип | Описание |
|------|-----|----------|
| `subtitle` | string | Подзаголовок блока (на русском) |
| `description` | string | Описание на английском |
| `description_ru` | string? | Описание на русском. Есть у ~92% элементов. Отсутствует у LLM-routed sanctions (3 элемента на ячейку) |
| `source` | string | Текстовая ссылка на источник (может быть пустой) |
| `origin_field` | string | Из какого поля schema взято (для трассировки) |

**Правило отображения текста:** `description_ru ?? description` — показывать русский, fallback на английский.

### Поля citation

| Поле | Тип | Описание |
|------|-----|----------|
| `url` | string | URL источника |
| `title` | string | Заголовок документа |
| `type` | string | Тип: `legislation`, `rulebook`, `government`, `consultation`, `research`, `other` |
| `field` | string | К какой секции схемы относится (для трассировки) |
| `excerpts` | string[] | Выдержки из документа (может быть пустым) |

### Значения ячеек

| Значение | Означает |
|----------|----------|
| `{"content": [...], "citations": [...]}` | Ячейка заполнена |
| `{"content": [], "citations": []}` | Ячейка пуста (нет данных) |
| `null` | Не применимо (например, мониторинг при допуске) |

---

## Покрытие description_ru

Проверено на примере LSE Main Market / Equity:
- **33 из 36** content-элементов имеют `description_ru`
- **3 без description_ru** — LLM-routed sanctions (`origin_field = "sanctions_llm_routed"`). Это текст, сгенерированный LLM при распределении санкций по фазам — исходного `description_ru` для него нет. Для этих элементов используйте `description` (английский).

Все алгоритмически маппированные элементы (admission, continuing_obligations, suspension, delisting, monitoring, enforcement, additional_findings) имеют `description_ru`.

---

## Как citations распределены по фазам

| Фаза | Откуда citations | Примечание |
|------|-----------------|------------|
| G07_1 (Допуск) | 3A_raw.json | Все citations из 3A |
| G07_2 (Поддержание) | 3B: `field=continuing_obligations`; 3C: `field=monitoring_regime`, `sanctions`, `enforcement_practice` | Основной объём L3 citations |
| G07_3 (Приостановка) | 3B: `field=suspension` | |
| G07_4 (Исключение) | 3B: `field=delisting_compulsory`, `delisting_voluntary` | |

Citations с `field=additional_findings` маппятся по умолчанию: 3A->G07_1, 3B->G07_2, 3C->G07_2.

---

## Пример: LSE Main Market / Equity (Commercial Companies)

| Фаза | Тип | Content | Citations | description_ru |
|------|-----|---------|-----------|----------------|
| G07_1 | D01_requirements | 6 | 4 | 6/6 |
| G07_1 | D02_procedures | 1 | 0 | 1/1 |
| G07_1 | D05_disclosure | 1 | 1 | 1/1 |
| G07_2 | D01_requirements | 2 | 3 | 2/2 |
| G07_2 | D02_procedures | 2 | 0 | 2/2 |
| G07_2 | D03_monitoring | 4 | 1 | 4/4 |
| G07_2 | D04_sanctions | 5 | 2 | 4/5 (1 LLM-routed) |
| G07_2 | D05_disclosure | 1 | 0 | 1/1 |
| G07_3 | D01_requirements | 2 | 1 | 2/2 |
| G07_3 | D02_procedures | 1 | 0 | 1/1 |
| G07_3 | D04_sanctions | 1 | 0 | 0/1 (LLM-routed) |
| G07_3 | D05_disclosure | 1 | 0 | 1/1 |
| G07_4 | D01_requirements | 2 | 0 | 2/2 |
| G07_4 | D02_procedures | 5 | 0 | 5/5 |
| G07_4 | D04_sanctions | 1 | 0 | 0/1 (LLM-routed) |
| G07_4 | D05_disclosure | 1 | 0 | 1/1 |

---

## Действия для интерфейса

### Бэкенд
- [ ] При чтении `matrix.json` прокидывать `content[]` и `citations[]` из каждой ячейки в API-ответ
- [ ] Эндпоинт ячейки/фазы должен возвращать оба массива

### Фронтенд — контент
- [ ] Текст секции: `description_ru ?? description`
- [ ] `subtitle` — подзаголовок блока (всегда на русском)
- [ ] При переключении вкладок фаз — использовать данные из соответствующего `matrix.G07_X`

### Фронтенд — источники
- [ ] На вкладке фазы: показывать источники из `citations[]` соответствующей ячейки матрицы
- [ ] Использовать `type` для фильтров/бейджей (как уже реализовано для L1/L2)
- [ ] Показывать `excerpts[]` при раскрытии источника
- [ ] `title` — заголовок ссылки, `url` — href

### Что НЕ нужно делать
- **Не нужно** читать сырые `3A/3B/3C_raw.json` для tab-view — всё есть в `matrix.json`
- **Не нужно** маппить `field` к фазам на стороне фронтенда — маппинг уже выполнен в пайплайне
- **Не нужно** переводить текст на стороне фронтенда — `description_ru` предоставлен пайплайном
