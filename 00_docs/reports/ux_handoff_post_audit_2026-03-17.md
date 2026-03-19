# Отчёт для UX-разработчика: итоги аудита и исправлений пайплайна

**Дата:** 2026-03-17
**От:** Tech Lead (пайплайн)
**Кому:** UX-разработчик (02_src/interface/)

---

## Контекст

17 марта проведён полный аудит интерфейса на соответствие данным пайплайна. Аудит выявил **12 багов интерфейса** (F1–F12) и **10 проблем данных** (P1–P10).

- **Баги интерфейса** (F1–F12) — в зоне ответственности UX-разработчика.
- **Проблемы данных** (P1–P10) — исправлены Tech Lead в рамках Tasks 020–023. Все 10 проблем закрыты.

Настоящий отчёт содержит:
1. **Часть A** — баги интерфейса (F1–F12), которые нужно исправить в коде frontend/backend.
2. **Часть B** — что изменилось в данных после Tasks 020–023 и что нужно учесть в интерфейсе.

Полные отчёты аудита:
- `00_docs/reports/ux-audit/audit_frontend.md` — подробное описание всех F1–F12
- `00_docs/reports/ux-audit/audit_pipeline.md` — подробное описание всех P1–P10

---

# Часть A. Баги интерфейса (F1–F12)

## Сводная таблица

| ID | Приоритет | Описание | Зона |
|----|-----------|----------|------|
| F1 | 🔴 | NESTED секции 3B/3C не рендерятся | Frontend |
| F2 | 🔴 | Вкладка «Исключение» показывает 3A вместо 3C | Frontend |
| F3 | 🔴 | Параметры дублируются под каждой секцией (section_keys игнорируется) | Frontend |
| F4 | 🔴 | `admission_architecture` и `admission_architecture_ru` оба рендерятся | Frontend |
| F5 | 🔴 | `contradictions.resolution` (EN) вместо `resolution_ru` | Frontend |
| F6 | 🟡 | Сырой ключ `common_obligations_common` как заголовок | Backend labels |
| F7 | 🟡 | `notes` без приоритета `notes_ru` | Frontend |
| F8 | 🟡 | Дата-артефакт «Jul 5, 2023 —» в выдержке | Frontend |
| F9 | 🟡 | Нет фильтра «Другое» для `type: "other"` | Frontend |
| F10 | 🟡 | Несоответствие меток: «Регулятор» (фильтр) vs «Правит.» (бейдж) | Frontend |
| F11 | 🟡 | `VENUE_TYPE_LABELS` не находит lowercase ключи | Backend labels |
| F12 | 🟢 | Source pills не показываются в матрице | Frontend |

---

### F1 — NESTED секции 3B/3C не рендерятся

**Критичность: 🔴 Блокирующий — ~30% контента 3B/3C недоступно пользователю**

Фронтенд обрабатывает только FLAT-формат секций (`{description, source}`), но молча пропускает NESTED-формат (`{subkey: {description, source}}`).

**Скрытые секции в 3B:** `suspension`, `continuing_obligations`, `delisting_compulsory`, `delisting_voluntary`, `terminology`
**Скрытые секции в 3C:** `sanctions`, `monitoring_regime`, `enforcement_practice`

Каждая из этих секций содержит 2–6 подключей с описанием и источниками. Примеры подключей `suspension`:
```json
{
  "suspension": {
    "procedure": { "description": "...", "description_ru": "...", "source": "..." },
    "grounds": { "description": "...", "description_ru": "...", "source": "..." },
    "duration_limits": { "description": "...", "description_ru": "...", "source": "..." },
    "disclosure": { "description": "...", "description_ru": "...", "source": "..." }
  }
}
```

**Исправление:** В компоненте рендеринга секций добавить обработку NESTED: если значение секции — объект без ключа `description`, итерировать подключи и рендерить каждый отдельным блоком (или конкатенировать).

**Важно:** После исправления P1 (Task 021) у каждого подключа теперь есть `description_ru` — отображать с приоритетом `description_ru ?? description`.

---

### F2 — Вкладка «Исключение» показывает 3A вместо 3C

**Критичность: 🔴**

При `?view=tabs&phase=exclusion` загружаются данные из 3A вместо 3C. Матричный вид корректно отображает 3C — баг изолирован в tab-view.

**Исправление:** Проверить маппинг `phase=exclusion` → файл `3C_raw.json` на бэкенде или в логике фазы фронтенда.

---

### F3 — Параметры дублируются (section_keys игнорируется)

**Критичность: 🔴**

Все параметры показываются под каждой секцией. В данных поле `section_keys[]` указывает, к каким секциям относится параметр:

```json
{
  "param_id": "П16",
  "param_label_ru": "Проспект / информационный документ",
  "section_keys": ["admission_overview", "disclosure_at_admission"]
}
```

П16 должен показываться только под `admission_overview` и `disclosure_at_admission`.

**Исправление (backend):** Добавить `section_keys: list[str] = []` в модель `ParameterValue` (`backend/models/parameter.py`) и прокинуть из `get_cell_parameters()`.

**Исправление (frontend):** `params.filter(p => p.section_keys.includes(currentSectionKey))`.

---

### F4 — Дублирование `admission_architecture` / `admission_architecture_ru`

**Критичность: 🔴**

На странице юрисдикции рендерятся оба поля — русский и английский тексты подряд.

**Исправление:** `{card.admission_architecture_ru ?? card.admission_architecture}`

---

### F5 — `contradictions.resolution` (EN) вместо `resolution_ru`

**Критичность: 🔴**

В L4 «Противоречия» показывается английский `resolution`, хотя `resolution_ru` заполнен.

**Исправление:** `{record.resolution_ru ?? record.resolution}`

---

### F6 — Сырой ключ `common_obligations_common` как заголовок

**Критичность: 🟡**

Ключ отсутствует в `SECTION_LABELS` в `backend/core/labels.py`.

**Исправление:** Добавить в `SECTION_LABELS`:
```python
"common_obligations_common": "Общие обязательства",
"common_monitoring_common": "Общий мониторинг",
```

---

### F7 — `notes` без приоритета `notes_ru`

**Критичность: 🟡**

После Task 022 поле `notes_ru` теперь заполнено во всех юрисдикциях. Фронтенд должен отображать его приоритетно.

**Исправление:** `{card.notes_ru ?? card.notes}`

---

### F8 — Дата-артефакт в выдержке

**Критичность: 🟡 (требует диагностики)**

Выдержка отображается с датой-префиксом `"Jul 5, 2023 —"`. В хранимых данных `excerpts[]` такой даты нет.

**Гипотеза:** Фронтенд делает live-fetch URL для preview вместо использования хранимых `excerpts[]`.

---

### F9 — Нет фильтра «Другое» для `type: "other"`

**Критичность: 🟡**

На вкладке «Источники» нет кнопки фильтра для `type: "other"`. Если источники с таким типом есть — нужна кнопка.

---

### F10 — Несоответствие меток типов

**Критичность: 🟡**

| Тип | Фильтр | Бейдж |
|-----|--------|-------|
| `government` | «Регулятор» | «Правит.» |
| `rulebook` | «Правила биржи» | «Правила» |

Унифицировать одним из вариантов.

---

### F11 — `VENUE_TYPE_LABELS` не находит lowercase ключи

**Критичность: 🟡**

После нормализации данных `venue_type` приходит в lowercase. `VENUE_TYPE_LABELS` содержит старые ключи.

**Исправление** (`backend/core/labels.py`):
```python
VENUE_TYPE_LABELS = {
    "regulated_market": "Regulated Market",
    "mtf": "MTF",
    "otf": "OTF",
    "exchange_regulated": "Exchange Regulated Market",
}
```

---

### F12 — Source pills в матрице

**Критичность: 🟢**

В матричном виде ячейки не показывают source pills. Уточнить — дизайн-решение или пропуск.

---

---

# Часть B. Изменения данных (Tasks 020–023) — что учесть в интерфейсе

Все 10 проблем данных (P1–P10) исправлены. Ниже — что именно изменилось и как это влияет на интерфейс.

## Сводная таблица

| ID | Проблема | Задача | Что изменилось в данных | Действие для интерфейса |
|----|----------|--------|------------------------|------------------------|
| P1 | Тексты секций 3A/3B/3C на английском | 021 | Добавлен `description_ru` во все секции | Отображать `description_ru ?? description` |
| P2 | L3 citations без `type` | 020 | Добавлен `type` во все citations | Использовать для фильтров/бейджей |
| P3 | Orphaned citations | 023 | Удалены 1594 orphaned citations | Нет действий — данные стали чище |
| P4 | «Fetched web page» как заголовок | 020 | Заменены на реальные `<title>` | Нет действий — заголовки исправлены |
| P5 | `tier` на английском | 022 | Добавлен `tier_ru` в `pass2_ru.json` | Отображать `tier_ru ?? tier` |
| P6 | reforms без `_ru` | 022 | Добавлены `driver_ru`, `opposition_ru` | Отображать `_ru ?? EN` |
| P7 | ptools без `_ru` | 022 | Добавлены `problem_addressed_ru`, `calibration_debate_ru` | Отображать `_ru ?? EN` |
| P8 | ADDITIONAL labels на EN | 022 | Заполнен `param_label_ru` для ADDITIONAL | Нет действий — поле уже используется |
| P9 | `notes_ru` не заполнен | 022 | `notes_ru` заполнен для всех юрисдикций | См. F7 — приоритет `notes_ru` |
| P10 | param_id: «П» vs «P» | 022 | Нормализовано к кириллице «П» | Нет действий — данные единообразны |

---

## B1. Новое поле `description_ru` в секциях 3A/3B/3C (Task 021)

**Масштаб:** Все ячейки, все юрисдикции, три фазы.

Каждая секция контента в `3A_raw.json`, `3B_raw.json`, `3C_raw.json` теперь содержит `description_ru`:

**FLAT-секция:**
```json
{
  "instrument_requirements": {
    "description": "As detailed above...",
    "description_ru": "Как указано выше...",
    "source": "UKLR 3.2.7R"
  }
}
```

**NESTED-секция (после исправления F1):**
```json
{
  "suspension": {
    "procedure": {
      "description": "The Exchange may suspend...",
      "description_ru": "Биржа может приостановить...",
      "source": "LR 5.1.1"
    },
    "grounds": {
      "description": "...",
      "description_ru": "...",
      "source": "..."
    }
  }
}
```

**Действие:** Везде где отображается текст секции — приоритет `description_ru ?? description`.

---

## B2. Поле `type` в L3 citations (Task 020)

Все записи `citations[]` в `3A/3B/3C_raw.json` теперь содержат поле `type`:

```json
{
  "url": "https://docs.londonstockexchange.com/...",
  "title": "ADMISSION AND DISCLOSURE STANDARDS",
  "field": "instrument_requirements",
  "type": "rulebook"
}
```

Допустимые значения: `"legislation"`, `"rulebook"`, `"government"`, `"consultation"`, `"research"`, `"other"`.

**Действие:** Использовать `type` для фильтров и бейджей на вкладках источников L3 — аналогично тому, как это уже работает для L1/L2 источников.

---

## B3. Новое поле `tier_ru` (Task 022)

В `pass2_ru.json` добавлено поле `tier_ru` на верхнем уровне:

```json
{
  "tier_ru": "Долговые и долгоподобные ценные бумаги",
  "parameters": [...]
}
```

**Где использовать:**
- Заголовок страницы ячейки (H1)
- Хлебные крошки
- Карточка ячейки на странице площадки

**Действие (backend):** Прокинуть `tier_ru` из `pass2_ru.json` через API. Если бэкенд читает `tier` из другого источника — добавить fallback на `tier_ru`.

**Действие (frontend):** `{cell.tier_ru ?? cell.tier}`

---

## B4. Новые `_ru` поля в Level 4 (Task 022)

### reforms (level4.json → reforms[]):
```json
{
  "driver": "Minority protection following ENRC/Bumi scandals.",
  "driver_ru": "Защита миноритариев после скандалов ENRC/Bumi.",
  "opposition": "Sell-side and some market participants opposed...",
  "opposition_ru": "Продающая сторона и часть участников рынка выступили против..."
}
```

### parameters_as_tools (level4.json → parameters_as_tools[]):
```json
{
  "problem_addressed": "Attracting listings while permitting...",
  "problem_addressed_ru": "Привлечение листинга при допущении...",
  "calibration_debate": "The FCA initially judged free float...",
  "calibration_debate_ru": "FCA первоначально оценила свободный флоут..."
}
```

**Действие (frontend):** Для каждого из четырёх полей: `{record.field_ru ?? record.field}`.

---

## B5. `param_label_ru` для ADDITIONAL параметров (Task 022)

Ранее `param_label_ru: null` для параметров с ID `ADDITIONAL_*`. Теперь заполнено:

```json
{
  "param_id": "ADDITIONAL_1",
  "param_label": "Entire class must be included in the application",
  "param_label_ru": "Весь класс должен быть включён в заявку"
}
```

**Действие:** Нет действий если интерфейс уже использует `param_label_ru` с fallback на `param_label`. Если нет — добавить fallback.

---

## B6. Нормализация `param_id` к кириллице (Task 022)

Все `param_id` формата `P01`, `P02`, ... нормализованы к `П01`, `П02`, ... (кириллица).

**Масштаб:** 37 файлов `pass2_ru.json`, 1566 param_id нормализованы. Включая ссылки в поле `linkages[]`.

**Действие:** Нет действий — отображение стало единообразным. Если где-то в интерфейсе есть хардкод с латинскими `P01` — заменить на `П01`.

---

## B7. Orphaned citations удалены (Task 023)

Из `3A/3B/3C_raw.json` удалены 1594 citation записей, привязанных к секциям с пустым/«not applicable» описанием.

**Действие:** Нет действий — счётчики источников станут точнее. Если интерфейс кэширует count — сбросить кэш.

---

## B8. Исправлены заголовки «Fetched web page» (Task 020)

51 файл обновлён — placeholder-заголовки заменены на реальные `<title>` из HTML-страниц.

**Действие:** Нет действий — заголовки стали корректными.

---

---

# Чеклист для UX-разработчика

## Блокирующие (🔴):
- [ ] **F1** — Рендеринг NESTED секций 3B/3C
- [ ] **F2** — Маппинг phase=exclusion → 3C
- [ ] **F3** — Фильтрация параметров по `section_keys`
- [ ] **F4** — Приоритет `admission_architecture_ru`
- [ ] **F5** — Приоритет `resolution_ru`

## _ru fallback-паттерн (по итогам Tasks 020–022):
- [ ] **B1** — `description_ru ?? description` в секциях 3A/3B/3C
- [ ] **B3** — `tier_ru ?? tier` в заголовках ячеек
- [ ] **B4** — `driver_ru`, `opposition_ru`, `problem_addressed_ru`, `calibration_debate_ru`
- [ ] **F7** — `notes_ru ?? notes`

## Backend labels:
- [ ] **F6** — `SECTION_LABELS` += `common_obligations_common`, `common_monitoring_common`
- [ ] **F11** — `VENUE_TYPE_LABELS` lowercase ключи + `exchange_regulated`

## L3 citations:
- [ ] **B2** — Использовать `type` в L3 citations для фильтров/бейджей

## Средний приоритет:
- [ ] **F8** — Диагностика дата-артефакта в выдержках
- [ ] **F9** — Фильтр «Другое» для `type: "other"`
- [ ] **F10** — Унификация меток типов источников

## Низкий приоритет:
- [ ] **F12** — Source pills в матрице (уточнить требование)
