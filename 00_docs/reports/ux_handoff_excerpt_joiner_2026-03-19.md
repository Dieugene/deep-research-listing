# Отчёт для UX-разработчика: склейка фрагментированных выдержек

**Дата:** 2026-03-19
**От:** Tech Lead (пайплайн)
**Кому:** UX-разработчик

---

## Что изменилось

83 источника содержали выдержки, разбитые построчно (артефакт парсинга PDF и HTML-таблиц Parallel API). Вместо одного связного текста — 10–45 фрагментов по 1–3 слова.

Выдержки склеены LLM в связный текст. Пример (MarketAxess Rulebook):

**Было:** 45 отдельных excerpts (`"(a)"`, `"European high-grade bonds;"`, `"(b)"`, ...)

**Стало:** 1 excerpt с полным текстом:
```
INSTRUMENT ELIGIBILITY CRITERIA
10.1 The decision whether or not to admit an instrument to trading on the MTF
is at the sole discretion of MarketAxess.
10.2 The MTF facilitates secondary market trading only...
```

## Новое поле: `excerpts_joined`

Источники, прошедшие склейку, помечены `"excerpts_joined": true`:

```json
{
  "url": "https://www.marketaxess.com/pdf/MTF-Rulebook-UK.pdf",
  "title": "UK MTF RULEBOOK",
  "excerpts": ["INSTRUMENT ELIGIBILITY CRITERIA\n10.1 The decision..."],
  "excerpts_joined": true
}
```

- Без метки (или `excerpts_joined` отсутствует) — excerpts не обрабатывались
- `excerpts_joined: true` — excerpts склеены, количество изменилось (было много → стало 1–3)

## Действия для фронтенда

- [ ] Выдержки с `excerpts_joined: true` содержат `\n` (переносы строк). Рекомендуется рендерить с `white-space: pre-wrap` для сохранения структуры текста.
- [ ] Поле `excerpts_joined` можно игнорировать при отображении — оно для аудита данных.

## Масштаб

- 83 источника обработаны (из 8 284 с выдержками — 1%)
- 62 файла затронуты
- L1, L3 (_parallel_raw), L4
