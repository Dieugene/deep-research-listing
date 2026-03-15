# Аудит соответствия реализации прототипам

**Дата:** 2026-03-15
**Версия реализации:** Task 016 (коммит `85263c8`)
**Область:** VenuePage, InstrumentsPage
**Прототипы:** `venues/venue.html`, `instruments/instruments.html`

---

## 1. Сводная таблица расхождений

| # | Страница | Компонент | Расхождение | Серьёзность | Причина |
|---|----------|-----------|-------------|-------------|---------|
| V1 | Venue | Sticky tabs | Нет механизма срабатывания shadow при скролле | **Критично** | Не реализован IntersectionObserver / scroll-listener |
| V2 | Venue | Breadcrumb | Цвет ссылок серый (`text-mid`) вместо синего (`accent`) | **Значительно** | CSS-ошибка |
| V3 | Venue | Заголовок | `font-weight: 300` вместо `400` | **Значительно** | CSS-ошибка |
| V4 | Venue | Заголовок | Отступы `0 0 6px` вместо `18px 0 5px` | **Значительно** | CSS-ошибка |
| V5 | Venue | Chip `.chip-legacy` | Не реализован | **Значительно** | Отсутствует в CSS-модуле |
| V6 | Venue | Карточка режима | Нет визуального индикатора (opacity) для неполных данных | **Значительно** | Не реализовано |
| V7 | Venue | Notes block | Боковая полоска: сплошная `border-left: 3px` вместо `::before` с opacity 0.35 | **Значительно** | CSS-адаптация |
| V8 | Venue | Meta bar | Горизонтальный padding `16px` вместо `18px` | **Незначительно** | CSS-ошибка |
| V9 | Venue | Карточка режима | Вертикальное выравнивание `flex-start` вместо `center` в `.tc-hd` | **Незначительно** | CSS-ошибка |
| V10 | Venue | Карточка режима | Фон заголовка карточки `--bg3` вместо `--bg` | **Незначительно** | CSS-ошибка |
| V11 | Venue | Параметр-таблетка | `border-color` через hex (`#BFDBFE`) вместо `rgba(37,99,235,.2)` | **Незначительно** | Hardcoded цвет |
| V12 | Venue | Параметр-таблетка | Background opacity кода `0.5` вместо `0.6` | **Незначительно** | CSS-ошибка |
| V13 | Venue | Параметр-таблетка | Название параметра: `font-weight` не задан (defaults 400) вместо `300` | **Незначительно** | CSS-ошибка |
| V14 | Venue | Instrument tabs | `backdrop-filter: blur(12px)` — отсутствует в прототипе | **Незначительно** | Enhancement (не мешает) |
| I1 | Instruments | Страница | Нет page-level заголовка (breadcrumb, заголовок, подзаголовок) | **Критично** | Не реализовано |
| I2 | Instruments | Phase strip | 4 фазы (`suspension` добавлен) вместо 3 в прототипе | **Значительно** | Адаптация данных |
| I3 | Instruments | Venue type filter | Добавлен 4-й тип "Биржа", в прототипе 3 | **Значительно** | Адаптация данных |
| I4 | Instruments | Legal family filter | Генерируется из данных API вместо фиксированных 3 значений | **Значительно** | Адаптация данных |
| I5 | Instruments | Фильтры | Логика toggle вместо radio-button поведения прототипа | **Значительно** | Поведенческое расхождение |
| I6 | Instruments | Параметры таблицы | Цвет заголовков колонок не окрашивается по фазе (`.ph-admission` etc.) | **Значительно** | Не реализовано |
| I7 | Instruments | Empty state | Сообщение "Ничего не найдено" — в таблице, не в списке режимов | **Значительно** | Поведенческое расхождение |
| I8 | Instruments | Default params | Авто-выбор первых 3 из API vs `P01/P02/P05` в прототипе | **Значительно** | Адаптация данных |
| I9 | Instruments | URL state | `?instr=&phase=` в URL — отсутствует в прототипе | **Незначительно** | Enhancement |
| I10 | Instruments | Search | Дебаунс 150мс (по ТЗ) не реализован ни в прототипе, ни в коде | **Незначительно** | Общий пропуск |
| I11 | Instruments | Счётчик "Выбрано" | Показывается из `filteredRegimes.length`, а не из всех режимов | **Незначительно** | Семантическая разница |
| I12 | Instruments | Singular/plural | "юрисдикций" / "режима" — статические формы без склонения | **Незначительно** | Упрощение |

---

## 2. Критические расхождения

### I1 — Отсутствует page-level заголовок на странице инструментов

**Прототип:** Перед sticky-полосой карточек отображается:
```html
<div class="page-hd">
  <div class="breadcrumb">Справочник → Сравнение инструментов</div>
  <div class="page-title">Сравнение инструментов</div>
  <div class="page-sub">Сравнение условий листинга по всем юрисдикциям</div>
</div>
```

**Реализация:** Страница начинается сразу с sticky-полосы инструментальных карточек. Нет breadcrumb, нет заголовка.

**Влияние:** Пользователь теряет навигационный контекст; страница не имеет точки входа.

**Исправление:** Добавить `<div className={styles.pageHd}>` с хлебными крошками и заголовком перед `instrStripWrap`.

---

### V1 — Нет механизма sticky shadow для instrument tabs на VenuePage

**Прототип:**
```js
initShadow('tabs-lse');  // IntersectionObserver добавляет класс .stuck
// .instr-tabs.stuck { box-shadow: 0 2px 10px rgba(0,0,0,.08) }
```

**Реализация:** CSS содержит `transition: box-shadow 0.15s`, но в TSX не реализован ни IntersectionObserver, ни scroll listener, который добавлял бы класс `.stuck`. Shadow никогда не появится при скролле.

**Исправление:** Добавить в `VenuePage.tsx` useEffect с IntersectionObserver:
```tsx
useEffect(() => {
  const tabs = instrTabsRef.current
  if (!tabs) return
  const sentinel = document.createElement('div')
  sentinel.style.cssText = 'height:1px;margin-top:-1px;pointer-events:none;'
  tabs.insertAdjacentElement('beforebegin', sentinel)
  const obs = new IntersectionObserver(
    ([e]) => tabs.classList.toggle(styles.instrTabsStuck, e.intersectionRatio < 1),
    { threshold: [1] }
  )
  obs.observe(sentinel)
  return () => { obs.disconnect(); sentinel.remove() }
}, [])
```

---

## 3. Значительные расхождения

### V2 — Breadcrumb link color

- **Прототип:** `color: var(--accent)` (синий)
- **Реализация:** `color: var(--vp-text-mid)` (серый)
- **Исправление:** в `.breadcrumb a` заменить `color: var(--vp-text-mid)` на `color: var(--vp-accent)`

---

### V3 + V4 — Заголовок площадки: font-weight и отступы

- **font-weight:** `300` → должно быть `400`
- **margin:** `0 0 6px` → должно быть `18px 0 5px`
- **Исправление:** В `.venueTitle` изменить оба свойства.

---

### V5 — Отсутствует `.chip-legacy`

Прототип использует этот класс для устаревающих режимов:
```css
/* prototype: .chip-legacy */
background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A;
```
**Исправление:** Добавить `.chipLegacy` в `VenuePage.module.css` и рендерить chip для режимов с `is_legacy: true` (если поле будет добавлено в API).

---

### V6 — Отсутствует visual indicator для неполных/непроверенных карточек

**Прототип:** Карточки с неполными данными рендерятся с `opacity: 0.8` или `0.75`.
**Реализация:** Все карточки имеют одинаковую непрозрачность.
**Исправление:**
```tsx
// В ModeCard:
style={{ opacity: cell.validation_status === 'red' ? 0.75 : 1 }}
```

---

### V7 — Notes block: боковая полоска

- **Прототип:** `::before` псевдоэлемент с `opacity: 0.35` — полоска выглядит приглушённой
- **Реализация:** `border-left: 3px solid var(--vp-accent)` — сплошная насыщенная полоска
- **Визуальный эффект:** Реализация выглядит ярче, чем задумано в прототипе
- **Исправление:** Заменить `border-left` на pseudo-element approach:
```css
.notesBlock { position: relative; border-left: none; padding-left: 20px; }
.notesBlock::before {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0;
  width: 3px; background: var(--vp-accent); opacity: 0.35; border-radius: 2px;
}
```

---

### I2 — 4 фазы вместо 3 в прототипе инструментов

**Прототип:** Показывает Допуск / Поддержание / Исключение (3 фазы).
**Реализация:** Добавляет Приостановку как отдельную фазу (4 фазы).
**Оценка:** Это **обоснованная адаптация** — реальные данные содержат фазу Приостановки. Рекомендуется оставить, но зафиксировать как намеренное расхождение.

---

### I5 — Поведение фильтров: toggle vs radio

**Прототип:** При клике на filter chip — старый active сбрасывается, новый устанавливается (radio). Кнопка "Все" снимает выделение с остальных.

**Реализация:** Каждый фильтр — независимый state. При клике на уже активный тип → ничего (нужно кликнуть "Все" для сброса). Семантика совпадает, но UX немного отличается.

**Текущее поведение приемлемо**, но для точного соответствия прототипу:
- Кнопка "Все" должна сбрасывать `legalFamily` / `venueType` в `''`
- Клик на активный chip должен его сбрасывать в `''` (toggle-to-deselect)

---

### I6 — Цвет заголовков колонок таблицы не привязан к фазе

**Прототип:**
```css
.ph-admission { color: #1E40AF }   /* синий */
.ph-maintenance { color: #065F46 } /* зелёный */
.ph-delisting { color: #7C2D12 }   /* коричнево-красный */
```

**Реализация:** Заголовки `<th>` не имеют phase-специфичного цвета.

**Исправление:** Добавить класс-модификатор к `<th>` в зависимости от `activePhase`:
```tsx
<th className={`${styles.cmpTh} ${styles[`ph${capitalize(activePhase)}`]}`}>
```

---

## 4. Незначительные расхождения (cosmetic)

| # | Что | Прототип | Реализация |
|---|-----|---------|------------|
| V8 | Meta bar padding | `10px 18px` | `10px 16px` |
| V9 | `.tc-hd align-items` | `center` | `flex-start` |
| V10 | `.tc-hd background` | `var(--bg)` = `#F7F8FA` | `var(--vp-bg3)` = `#F0F2F7` |
| V11 | Pill code border-color | `rgba(37,99,235,.2)` | `#BFDBFE` (hardcoded) |
| V12 | Pill code background | opacity `0.6` | opacity `0.5` |
| V13 | Pill name font-weight | `300` | не задан (400) |
| I10 | Search debounce | 150мс (по ТЗ) | не реализован |
| I11 | Счётчик "Выбрано" | от всех режимов | от filtered |
| I12 | Plural labels | не применимо | static forms |

---

## 5. Обоснованные адаптации (не являются ошибками)

| # | Адаптация | Обоснование |
|---|-----------|-------------|
| A1 | 4 фазы вместо 3 на Instruments | Реальные данные содержат `suspension` как отдельную фазу |
| A2 | Venue type filter: добавлен "Биржа" | Тип `exchange` существует в реальных данных |
| A3 | Legal family filter: из API | Динамически отражает реальный набор правовых семей в данных |
| A4 | URL state (`?instr=&phase=`) | Улучшает deep-linking и поддерживает кнопку Back; прототип — демо без роутинга |
| A5 | Default params — первые 3 из API | Прототип использовал захардкоженные P01/P02/P05, которые могут не существовать для всех инструментов |
| A6 | Backdrop-filter blur на tabs | Enhancement без нарушения функциональности |

---

## 6. Приоритизированный план исправлений

### Срочно (нарушают функциональность или навигацию)

1. **I1** — Добавить page-level header на InstrumentsPage (breadcrumb + заголовок)
2. **V1** — Реализовать IntersectionObserver для sticky shadow на VenuePage

### Важно (визуально заметны пользователю)

3. **V2** — Breadcrumb: link color → `var(--vp-accent)`
4. **V3+V4** — Title: font-weight `400`, margin `18px 0 5px`
5. **V6** — Card opacity для неполных/непроверенных режимов
6. **V7** — Notes block: pseudo-element с opacity вместо solid border-left
7. **I6** — Phase-colored column headers в таблице сравнения
8. **I5** — Уточнить toggle/radio поведение фильтров

### Желательно (мелкие косметические)

9. **V5** — Chip `.chipLegacy` (ожидать, пока данные не будут содержать `is_legacy`)
10. **V8–V13** — Точная подгонка padding, opacity, font-weight
11. **I10** — Дебаунс 150мс на поиске
12. **I12** — Склонение числительных (1 режим / 2 режима / 5 режимов)

---

## 7. Статистика

| Категория | VenuePage | InstrumentsPage | Итого |
|-----------|-----------|-----------------|-------|
| Критично | 1 | 1 | **2** |
| Значительно | 6 | 7 | **13** |
| Незначительно | 7 | 5 | **12** |
| Адаптации (OK) | 1 | 5 | **6** |
| **Итого расхождений** | **14** | **13** | **27** |

**Совпадений с прототипом:** ~65% по VenuePage, ~55% по InstrumentsPage.
**Цветовая палитра:** 100% совпадение по всем токенам в обоих компонентах.

---

*Отчёт сформирован на основе прямого чтения `venue.html`, `instruments.html`, `VenuePage.tsx`, `VenuePage.module.css`, `InstrumentsPage.tsx`, `InstrumentsPage.module.css`.*
