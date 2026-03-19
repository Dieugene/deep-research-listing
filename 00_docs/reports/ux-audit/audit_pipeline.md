# Аудит пайплайна: проблемы данных
_Сформирован: 2026-03-17 | Источник: аудиты sources_audit_2026-03-16, ui_audit_Великобритания_2026-03-16, audit_LSE_Main_Market_2026-03-17_

Содержит только те проблемы, **причина которых — в данных**: отсутствующие или некорректно заполненные поля в JSON-файлах пайплайна. Фронтенд работает корректно по отношению к имеющимся данным, но показывает неполный или неправильный контент из-за пробелов.

---

## Сводная таблица

| ID | Приоритет | Описание | Затронуто | Статус |
|----|-----------|----------|-----------|--------|
| P1 | 🔴 Высокий | Текст секций 3A/3B/3C на английском — нет `description_ru` | Все ячейки, все юрисдикции | ❌ |
| P2 | 🔴 Высокий | Отсутствует поле `type` в L3 citations → «ДРУГОЕ» для всех L3 источников | Все ячейки, все юрисдикции | ❌ |
| P3 | 🔴 Высокий | Orphaned citations в EQUITY-3: секции "not applicable" с реальными цитатами | EQUITY-3 (international_co) | ❌ |
| P4 | 🟡 Средний | «Fetched web page» как заголовок источника в L3 citations | EQUITY-1 + возможно все юрисдикции | ❌ |
| P5 | 🟡 Средний | `tier` ячеек на английском — нет `tier_ru` | Все ячейки | ❌ |
| P6 | 🟡 Средний | `reforms.driver` и `reforms.opposition` — нет `_ru` версий | Все L4 реформы | ❌ |
| P7 | 🟡 Средний | `parameters_as_tools` — нет `_ru` полей (`description`, `problem_solved`, `calibration_debate`) | Все L4 записи | ❌ |
| P8 | 🟡 Средний | `ADDITIONAL_X.param_label_ru` отсутствует — метка параметра на английском | Все дополнительные параметры | ❌ |
| P9 | 🟡 Средний | `notes_ru` отсутствует или не заполнен — поле «Примечания» показывается на EN | Юрисдикция Великобритания | ❌ |
| P10 | 🟢 Низкий | Разные форматы `param_id`: кириллица «П01» vs латиница «P01» в разных ячейках | Часть ячеек | ❌ |

---

## P1 — Текст секций 3A/3B/3C на английском

**Проблема:** Контент описательных секций (`instrument_requirements`, `admission_overview`, `eligibility_requirements`, `additional_findings` и т.д.) в файлах `3A_raw.json`, `3B_raw.json`, `3C_raw.json` содержит только поле `description` (английский). Поле `description_ru` отсутствует во всей структуре.

**Пример из BOND-1 3A:**
```json
"instrument_requirements": {
  "description": "As detailed above with exact rules: £200,000 min aggregate market value...",
  "source": "UKLR 3.2.7R..."
}
```
Поле `description_ru` не существует.

**Эффект на фронтенд:** Весь текст секций отображается на английском языке.

**Масштаб:** Все ячейки, все юрисдикции, три фазы (3A/3B/3C).

**Действие:** Реализовать шаг перевода в пайплайне для всех `content[section_key].description` → `description_ru` по аналогии с тем, как переводятся параметры в `pass2_ru.json`.

---

## P2 — Отсутствует поле `type` в L3 citations

**Проблема:** Ни одна запись в массиве `citations[]` файлов `3A_raw.json`, `3B_raw.json`, `3C_raw.json` не содержит поле `type`. Классификатор источников (`source_classifier`) охватил только L1/L2 данные (`jurisdiction_card.json`, `venue_card.json`) и не обработал L3.

**Пример из EQUITY-1 3A:**
```json
{
  "url": "https://docs.londonstockexchange.com/.../admission-and-disclosure-standards_1.pdf",
  "title": "ADMISSION AND DISCLOSURE STANDARDS",
  "field": "instrument_requirements"
  // ← поле "type" отсутствует
}
```
Это документ типа `rulebook`, но отображается как «ДРУГОЕ».

**Эффект на фронтенд:** Все L3 источники показываются с бейджем «ДРУГОЕ» вместо правильного типа (rulebook, government, regulator и т.д.).

**Масштаб:** Все L3 citations во всех ячейках и юрисдикциях.

**Действие:** Расширить `run_source_classifier_catchup.py` (или написать отдельный скрипт) для классификации `type` в `citations[]` полей `3A_raw.json`, `3B_raw.json`, `3C_raw.json`.

---

## P3 — Orphaned citations (секции "not applicable") — EQUITY-3

**Проблема:** В ячейке `equity_shares_international_co_equity` (EQUITY-3) ряд секций имеет `description = "not applicable"` с пустым `source`, но в массиве `citations[]` всё равно присутствуют связанные записи.

**Затронутые секции и данные:**
| Секция | description | Цитации |
|--------|-------------|---------|
| admission_overview | "not applicable" | 2 src · **5 exc** |
| additional_findings | "not applicable" | 0 |
| special_regimes | "not applicable" | 0 |
| disclosure_at_admission | "not applicable" | 2 src · 0 exc |

**Эффект на фронтенд:** Фронтенд правомерно не рендерит секции с "not applicable". В результате 4 цитации, включая 5 выдержек для `admission_overview`, полностью недоступны пользователю.

**Причина:** Пайплайн не смог добыть контент по этим секциям для EQUITY-3, записал "not applicable", но цитаты к этим секциям сохранил.

**Действие:** Пайплайн должен либо:
- Не записывать цитаты к секциям с пустым/недоступным контентом, или
- Привязывать «осиротевшие» цитаты к `additional_findings` как fallback.

---

## P4 — «Fetched web page» как заголовок источника

**Проблема:** Часть L3 citations имеет `"title": "Fetched web page"` — placeholder, записанный пайплайном когда веб-скрапер не смог получить заголовок HTML-страницы.

**Подтверждено в EQUITY-1 3A:**
```json
{
  "url": "https://www.handbook.fca.org.uk/handbook/UKLR/22/",
  "title": "Fetched web page",
  "field": "instrument_requirements"
}
```
Ожидаемый заголовок: «UKLR 22 — Continuing obligations».

**Эффект на фронтенд:** В панели источников отображается «Fetched web page» вместо названия документа.

**Масштаб:** Как минимум 2 записи в EQUITY-1. Реальный масштаб неизвестен — могут присутствовать в любых L3 citations по всем юрисдикциям.

**Действие:** Catchup-скрипт, который сканирует все `3A/3B/3C_raw.json`, находит citations с `"title": "Fetched web page"` и перезапрашивает заголовок из `<title>` HTML по URL.

---

## P5 — Заголовки ячеек (`tier`) на английском

**Проблема:** Поле `tier` в данных ячеек содержит только английский текст. Поле `tier_ru` отсутствует.

**Примеры:**
- `"Debt and debt-like securities"` → H1 на странице ячейки
- `"(no listing tiers — flat structure)"` → H1
- Хлебные крошки показывают английский tier

**Эффект на фронтенд:** Заголовки страниц ячеек и хлебные крошки — на английском.

**Действие:** Добавить `tier_ru` во все ячейки в пайплайне Pass 2.

---

## P6 — `reforms.driver` и `reforms.opposition` без `_ru`

**Проблема:** В записях L4 «Реформы» поля `driver` (движущая сила реформы) и `opposition` (контраргументы) существуют только на английском. Полей `driver_ru` и `opposition_ru` нет.

**Пример из level4.json:**
```json
{
  "driver": "Minority protection following ENRC/Bumi scandals.",
  "description_ru": "В 2014 году FCA реализовала...",
  "opposition": "Sell-side and some market participants opposed..."
  // нет driver_ru, нет opposition_ru
}
```

**Эффект на фронтенд:** Блоки «Движущая сила» и «Контраргументы» показываются на английском рядом с `description_ru` на русском.

**Действие:** Добавить перевод `driver` → `driver_ru` и `opposition` → `opposition_ru` в пайплайне L4.

---

## P7 — `parameters_as_tools` без `_ru` полей

**Проблема:** Записи L4 `parameters_as_tools` содержат поля `description`, `problem_solved`, `calibration_debate` исключительно на английском. Аналоги `_ru` отсутствуют.

**Пример:**
```
Free float requirement for equity shares was used as a competitive lever...
Какую проблему решает: Attracting listings while permitting higher...
Дискуссия о настройке: The FCA initially judged free float to be a blunt tool...
```
_(метки подразделов переведены, но сам контент — нет)_

**Действие:** Добавить перевод `description_ru`, `problem_solved_ru`, `calibration_debate_ru` в пайплайне L4 для `parameters_as_tools`.

---

## P8 — `ADDITIONAL_X.param_label_ru` отсутствует

**Проблема:** Дополнительные параметры (с ID `ADDITIONAL_1`, `ADDITIONAL_2` и т.д.) в `pass2_ru.json` имеют поле `param_label_ru: null`.

**Пример:**
```json
{
  "param_id": "ADDITIONAL_1",
  "param_label": "Entire class must be included in the application",
  "param_label_ru": null
}
```

**Эффект на фронтенд:** Метка параметра показывается на английском: `ADDITIONAL_1 Entire class must be included...`

**Действие:** Пайплайн Pass 2 должен переводить метки всех параметров, включая `ADDITIONAL_X`.

---

## P9 — Поле `notes_ru` не заполнено

**Проблема:** Блок «Примечания» в карточке юрисдикции (`jurisdiction_card.json`) содержит только поле `notes` (EN). Поле `notes_ru` либо отсутствует, либо не заполнено.

**Примечание:** Бэкенд поддерживает `notes_ru` в модели `JurisdictionCard` — значит это именно пробел данных, а не баг фронтенда.

**Действие:** Добавить перевод `notes` → `notes_ru` в пайплайне для всех `jurisdiction_card.json`.

---

## P10 — Разные форматы `param_id`

**Проблема:** В разных ячейках одной площадки применяются разные форматы идентификаторов параметров:

| Ячейка | Пример | Формат |
|--------|--------|--------|
| equity_shares_commercial_compa_equity | П01, П02, П12 | Кириллица |
| equity_shares_international_co_equity | P01, P02, P12 | Латиница |
| AIM equity | P01, P02, P03 | Латиница |

**Эффект:** Непоследовательный вид параметров в интерфейсе (смешивание П и P).

**Действие:** Нормализовать формат при генерации параметров в Pass 2. Рекомендуется использовать единый формат (кириллица «П» для русской локали).

---

## Рекомендуемый порядок реализации

1. **P2** (type в L3) — быстрая победа, catchup-скрипт по существующей логике
2. **P4** (Fetched web page) — catchup-скрипт, изолированная задача
3. **P1** (description_ru) — крупная задача, требует Phase 2 translate pipeline
4. **P5, P6, P7, P8, P9** — переводы, реализуются в рамках Phase 2 translate
5. **P3** (orphaned citations) — правка логики записи цитат в пайплайне
6. **P10** (param_id формат) — исправление в Pass 2, низкий приоритет
