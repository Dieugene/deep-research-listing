import { useEffect, useRef, useState, useCallback } from 'react'
import s from './AnalysisPage.module.css'

/* ── Section definitions for sidebar nav ─────────────────── */
interface NavItem {
  id: string
  label: string
  level: 'h2' | 'h3'
  num?: string
}

const NAV_ITEMS: NavItem[] = [
  { id: 'summary', label: 'Резюме', level: 'h2', num: '0' },

  { id: 'intro', label: 'Введение', level: 'h2', num: '1' },
  { id: 'intro-context', label: 'Контекст', level: 'h3', num: '1.1' },
  { id: 'intro-goal', label: 'Цель анализа', level: 'h3', num: '1.2' },
  { id: 'intro-scope', label: 'Границы исследования', level: 'h3', num: '1.3' },
  { id: 'intro-structure', label: 'Структура отчёта', level: 'h3', num: '1.4' },

  { id: 'data-methodology', label: 'Данные и методология', level: 'h2', num: '2' },
  { id: 'data-params', label: 'Описание параметров', level: 'h3', num: '2.1' },
  { id: 'data-prep', label: 'Подготовка данных', level: 'h3', num: '2.2' },
  { id: 'data-features', label: 'Итоговый набор признаков', level: 'h3', num: '2.3' },
  { id: 'data-correlation', label: 'Корреляционная структура', level: 'h3', num: '2.4' },
  { id: 'data-sample', label: 'Обзор выборки', level: 'h3', num: '2.5' },

  { id: 'stage1', label: 'Этап I: Статическая кластеризация', level: 'h2', num: '3' },
  { id: 'stage1-motivation', label: 'Мотивация', level: 'h3', num: '3.1' },
  { id: 'stage1-method', label: 'Метод', level: 'h3', num: '3.2' },
  { id: 'stage1-k', label: 'Выбор числа кластеров', level: 'h3', num: '3.3' },
  { id: 'stage1-dendrogram', label: 'Дендрограмма и структура', level: 'h3', num: '3.4' },
  { id: 'stage1-profiles', label: 'Профили кластеров', level: 'h3', num: '3.5' },
  { id: 'stage1-legal', label: 'Правовые семьи и кластеры', level: 'h3', num: '3.6' },
  { id: 'stage1-russia', label: 'Позиция России (Этап I)', level: 'h3', num: '3.7' },
  { id: 'stage1-alt', label: 'Альтернативные методы', level: 'h3', num: '3.8' },
  { id: 'stage1-pca', label: 'PCA', level: 'h3', num: '3.9' },
  { id: 'stage1-conclusions', label: 'Промежуточные выводы', level: 'h3', num: '3.10' },

  { id: 'stage2', label: 'Этап II: Линейная динамика WGI', level: 'h2', num: '4' },
  { id: 'stage2-motivation', label: 'Мотивация', level: 'h3', num: '4.1' },
  { id: 'stage2-data', label: 'Данные о динамике', level: 'h3', num: '4.2' },
  { id: 'stage2-patterns', label: 'Глобальные паттерны', level: 'h3', num: '4.3' },
  { id: 'stage2-components', label: 'Компонентный анализ динамики', level: 'h3', num: '4.4' },
  { id: 'stage2-clustering', label: 'Кластеризация с трендом', level: 'h3', num: '4.5' },
  { id: 'stage2-conclusions', label: 'Промежуточные выводы', level: 'h3', num: '4.6' },

  { id: 'stage3', label: 'Этап III: Траектории (2009–2024)', level: 'h2', num: '5' },
  { id: 'stage3-motivation', label: 'Мотивация', level: 'h3', num: '5.1' },
  { id: 'stage3-data', label: 'Данные', level: 'h3', num: '5.2' },
  { id: 'stage3-breakpoints', label: 'Структурные разрывы', level: 'h3', num: '5.3' },
  { id: 'stage3-preliminary', label: 'Предварительная кластеризация', level: 'h3', num: '5.4' },
  { id: 'stage3-split', label: 'Расщепление России', level: 'h3', num: '5.5' },
  { id: 'stage3-final', label: 'Финальная кластеризация', level: 'h3', num: '5.6' },
  { id: 'stage3-clusters', label: 'Состав кластеров (k=6)', level: 'h3', num: '5.7' },
  { id: 'stage3-silhouette', label: 'Силуэтный анализ', level: 'h3', num: '5.8' },
  { id: 'stage3-projections', label: 'PCA и t-SNE проекции', level: 'h3', num: '5.9' },
  { id: 'stage3-conclusions', label: 'Промежуточные выводы', level: 'h3', num: '5.10' },

  { id: 'stage4', label: 'Этап IV: Интегрированная (MFA)', level: 'h2', num: '6' },
  { id: 'stage4-motivation', label: 'Мотивация', level: 'h3', num: '6.1' },
  { id: 'stage4-method', label: 'Метод: MFA', level: 'h3', num: '6.2' },
  { id: 'stage4-contributions', label: 'Блоковые вклады', level: 'h3', num: '6.3' },
  { id: 'stage4-k', label: 'Выбор числа кластеров', level: 'h3', num: '6.4' },
  { id: 'stage4-clusters', label: 'Дендрограмма и состав', level: 'h3', num: '6.5' },
  { id: 'stage4-russia', label: 'Позиция России (Этап IV)', level: 'h3', num: '6.6' },
  { id: 'stage4-comparison', label: 'Сравнение через этапы', level: 'h3', num: '6.7' },
  { id: 'stage4-conclusions', label: 'Промежуточные выводы', level: 'h3', num: '6.8' },

  { id: 'russia', label: 'Сквозной анализ: Россия', level: 'h2', num: '7' },
  { id: 'russia-stages', label: 'Через четыре этапа', level: 'h3', num: '7.1' },
  { id: 'russia-gap', label: 'Количественная мера разрыва', level: 'h3', num: '7.2' },
  { id: 'russia-neighbors', label: 'Ближайшие соседи (Этап III)', level: 'h3', num: '7.3' },
  { id: 'russia-profile', label: 'Профиль России', level: 'h3', num: '7.4' },

  { id: 'synthesis', label: 'Синтез и выводы', level: 'h2', num: '8' },
  { id: 'synthesis-patterns', label: 'Основные паттерны', level: 'h3', num: '8.1' },
  { id: 'synthesis-evolution', label: 'Эволюция подхода', level: 'h3', num: '8.2' },
  { id: 'synthesis-russia', label: 'Россия: синтетическая оценка', level: 'h3', num: '8.3' },
  { id: 'synthesis-limitations', label: 'Ограничения', level: 'h3', num: '8.4' },
  { id: 'synthesis-stability', label: 'Устойчивость результатов', level: 'h3', num: '8.5' },
  { id: 'synthesis-next', label: 'Направления дальнейшего анализа', level: 'h3', num: '8.6' },

  { id: 'appendices', label: 'Приложения', level: 'h2' },
  { id: 'appendix-a', label: 'A. Визуализации', level: 'h3' },
  { id: 'appendix-b', label: 'B. Данные', level: 'h3' },
  { id: 'appendix-c', label: 'C. Скрипты', level: 'h3' },
  { id: 'appendix-d', label: 'D. Источники данных', level: 'h3' },
  { id: 'appendix-e', label: 'E. Рецензентский чеклист', level: 'h3' },
]

export default function AnalysisPage() {
  const [activeId, setActiveId] = useState<string>('summary')
  const observerRef = useRef<IntersectionObserver | null>(null)

  /* ── Scroll spy via IntersectionObserver ────────────────── */
  useEffect(() => {
    const ids = NAV_ITEMS.map((n) => n.id)
    const elements = ids
      .map((id) => document.getElementById(id))
      .filter(Boolean) as HTMLElement[]

    if (elements.length === 0) return

    observerRef.current = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting)
        if (visible.length > 0) {
          visible.sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
          setActiveId(visible[0].target.id)
        }
      },
      { rootMargin: '-80px 0px -60% 0px', threshold: 0 }
    )

    elements.forEach((el) => observerRef.current!.observe(el))
    return () => observerRef.current?.disconnect()
  }, [])

  const scrollTo = useCallback((id: string) => {
    const el = document.getElementById(id)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [])

  return (
    <div className={s.page}>
      {/* ── LEFT SIDEBAR ─────────────────────────────────── */}
      <nav className={s.sidebar}>
        <ul className={s.sidebarList}>
          {NAV_ITEMS.map((item) => (
            <li key={item.id}>
              <a
                className={`${item.level === 'h2' ? s.sidebarH2 : s.sidebarH3} ${
                  activeId === item.id ? s.sidebarActive : ''
                }`}
                onClick={() => scrollTo(item.id)}
              >
                {item.num && <span className={s.sidebarNum}>{item.num}</span>}
                {item.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      {/* ── MAIN CONTENT ─────────────────────────────────── */}
      <article className={s.content}>
        <h1 className={s.pageTitle}>Кластеризация юрисдикций по институциональным факторам листинговых режимов</h1>
        <p><strong>Аналитический отчёт (v3) — независимая верификация и синтез</strong></p>
        <p>Дата: 23 марта 2026 г.</p>

        <hr className={s.hr} />

        {/* ═══ 0. Резюме ═══ */}
        <section id="summary">
          <h2 className={s.h2}>0. Резюме</h2>
          <p>Настоящий отчёт представляет результаты <strong>независимой верификации</strong> кластерного анализа 48 юрисдикций по институциональным факторам, проведённого в рамках исследования подходов к регулированию листинга ценных бумаг. Верификация включала: аудит исходных данных, проверку вычислений во всех скриптах, воспроизведение ключевых результатов и дополнительный анализ чувствительности.</p>
          <p><strong>Общая оценка:</strong> исследование выполнено методологически корректно. Критических ошибок в данных и расчётах не обнаружено. Все ключевые числа воспроизведены. Ниже приводится систематизированное изложение трёх этапов кластеризации с рецензентскими комментариями и дополнительными визуализациями.</p>
          <p>Исследование прошло три последовательных этапа, каждый из которых расширял предыдущий:</p>
          <table className={s.table}>
            <thead>
              <tr>
                <th>Этап</th>
                <th>Метод</th>
                <th>Данные</th>
                <th>Объекты</th>
                <th>Оптимальное k</th>
                <th>Silhouette</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>I. Статика</td><td>Ward / Euclidean</td><td>6 признаков (F2x3, WGI, MktCap, Savings)</td><td>43 юрисдикции</td><td>7</td><td>0.226</td></tr>
              <tr><td>II. + Линейная динамика</td><td>Ward / Euclidean</td><td>7 признаков (+ OLS slope WGI)</td><td>43 юрисдикции</td><td>10</td><td>0.187</td></tr>
              <tr><td>III. Траектории WGI</td><td>Ward / Euclidean, DTW, k-Shape</td><td>12 признаков из траекторий WGI</td><td>49 объектов (47 + Russia_1 + Russia_2)</td><td>4 (стат.) / 6 (содерж.)</td><td>0.338 / 0.270</td></tr>
              <tr><td>IV. MFA (интеграция)</td><td>MFA + Ward / Euclidean</td><td>9 признаков (3 блока: F2, рынок, динамика)</td><td>49 объектов (все 48 + расщепление)</td><td>5</td><td>0.124</td></tr>
            </tbody>
          </table>
          <p><strong>Ключевые результаты:</strong></p>
          <ul>
            <li>Институциональные характеристики юрисдикций образуют <strong>непрерывный градиент</strong>, а не дискретные группы. Все варианты кластеризации дают невысокие silhouette scores (0.19–0.34), что подтверждается неспособностью DBSCAN выделить кластеры по плотности.</li>
            <li><strong>Правовая семья</strong> подтверждается как значимый структурный фактор: 13 из 15 юрисдикций common law группируются вместе без явного включения этого признака.</li>
            <li><strong>Россия</strong> в статической кластеризации входит в группу развивающихся рынков (China, Indonesia, Mexico, Peru, Turkey). Ближайшие юрисдикции — Turkey (1.94) и Mexico (2.30).</li>
            <li>При добавлении <strong>динамики WGI</strong> Россия перемещается к континентальной Европе: по характеру тренда (slope −0.104 на десятилетие) она ближе к западноевропейским юрисдикциям, чем к Mexico (−0.341) или Turkey (−0.307).</li>
            <li>Анализ <strong>годовых траекторий</strong> обнаруживает структурный разрыв (2022 г.) и разделяет Россию на два режима: Russia_1 (2009–2021, slope +0.013/год, кластер F5 — развивающиеся стабильные) и Russia_2 (2022–2024, slope −0.073/год, кластер F6 — снижающиеся). Расстояние между ними превышает 84% всех попарных расстояний в выборке.</li>
          </ul>
        </section>

        <hr className={s.hr} />

        {/* ═══ 1. Введение ═══ */}
        <section id="intro">
          <h2 className={s.h2}>1. Введение</h2>
        </section>

        <section id="intro-context">
          <h3 className={s.h3}>1.1. Контекст</h3>
          <p>Настоящий анализ является частью исследования подходов к регулированию листинга (допуска) ценных бумаг к биржевым торгам. Исследование охватывает 48 юрисдикций и ~65 торговых площадок.</p>
          <p>Институциональные факторы — характеристики юрисдикции, существующие <em>вне</em> листингового режима, медленно меняющиеся и не являющиеся результатом регуляторного выбора непосредственно в сфере листинга. К ним относятся правовая семья, качество институциональной среды, глубина рынка капитала и др.</p>
        </section>

        <section id="intro-goal">
          <h3 className={s.h3}>1.2. Цель анализа</h3>
          <p>Группировка юрисдикций по институциональной близости для:</p>
          <ol>
            <li><strong>Определения осмысленных сравнений.</strong> Сравнивать Россию с Великобританией «в лоб» бессмысленно — слишком разные базовые условия. Кластеризация выделяет юрисдикции с близкой конфигурацией институциональных факторов.</li>
            <li><strong>Калибровки рекомендаций.</strong> Если регуляторный механизм работает в определённом кластере, мы оцениваем, к какому кластеру ближе Россия, и делаем вывод о применимости.</li>
            <li><strong>Выявления паттернов.</strong> Какие комбинации институциональных условий ассоциируются с определёнными характеристиками листинговых режимов.</li>
          </ol>
        </section>

        <section id="intro-scope">
          <h3 className={s.h3}>1.3. Границы исследования</h3>
          <p>Кластеризация выполнялась на основе <strong>количественных</strong> институциональных параметров. Категориальный параметр «правовая семья» (Ф1) использовался для интерпретации, но не входил в набор признаков для кластеризации.</p>
          <p>Качественные факторы (Ф3 Private enforcement, Ф8 Концентрация владения, Ф9 Структура инвесторов, Ф10 Конкурентная структура площадок, Ф11 Тип регулятора, Ф12 Роль биржи как СРО) на момент анализа не были формализованы и не включены в расчёт.</p>
        </section>

        <section id="intro-structure">
          <h3 className={s.h3}>1.4. Структура отчёта</h3>
          <p>Отчёт последовательно описывает три этапа кластеризации, отражая эволюцию аналитического подхода:</p>
          <ul>
            <li><strong>Этап I</strong> — статическая кластеризация по 6 количественным признакам (раздел 3);</li>
            <li><strong>Этап II</strong> — расширение модели линейной динамикой WGI (раздел 4);</li>
            <li><strong>Этап III</strong> — кластеризация годовых траекторий WGI с обнаружением структурных разрывов (раздел 5);</li>
            <li>Раздел 6 — сквозной анализ позиции России;</li>
            <li>Раздел 7 — синтез результатов, ограничения и направления дальнейшего анализа.</li>
          </ul>
          <p>Каждый этап включает описание мотивации, методологии, результатов и рецензентских комментариев.</p>
        </section>

        <hr className={s.hr} />

        {/* ═══ 2. Данные и методология ═══ */}
        <section id="data-methodology">
          <h2 className={s.h2}>2. Данные и методология</h2>
        </section>

        <section id="data-params">
          <h3 className={s.h3}>2.1. Описание параметров</h3>
          <p>В анализе использовались следующие институциональные параметры:</p>
          <p><strong>Блок I. Защита инвесторов (Doing Business 2020, данные на 01.05.2019)</strong></p>
          <table className={s.table}>
            <thead>
              <tr><th>Параметр</th><th>Шкала</th><th>Покрытие</th><th>Описание</th></tr>
            </thead>
            <tbody>
              <tr><td>F2a — Extent of Disclosure Index</td><td>0–10</td><td>48/48</td><td>Требования к раскрытию информации при сделках с заинтересованностью</td></tr>
              <tr><td>F2b — Extent of Director Liability Index</td><td>0–10</td><td>48/48</td><td>Возможность привлечения директоров к ответственности</td></tr>
              <tr><td>F2c — Ease of Shareholder Suits Index</td><td>0–10</td><td>48/48</td><td>Процессуальные возможности миноритариев оспорить сделку</td></tr>
            </tbody>
          </table>
          <p><strong>Блок II. Качество институциональной среды (WGI, World Bank)</strong></p>
          <table className={s.table}>
            <thead>
              <tr><th>Параметр</th><th>Шкала</th><th>Покрытие</th><th>Описание</th></tr>
            </thead>
            <tbody>
              <tr><td>F4 — Regulatory Quality</td><td>−2.5…+2.5</td><td>48/48</td><td>Способность правительства формулировать обоснованные политики</td></tr>
              <tr><td>F5 — Rule of Law</td><td>−2.5…+2.5</td><td>48/48</td><td>Доверие к правилам общества, эффективность судебной системы</td></tr>
              <tr><td>F6 — Political Stability</td><td>−2.5…+2.5</td><td>48/48</td><td>Вероятность политической нестабильности</td></tr>
            </tbody>
          </table>
          <p>Три индекса WGI построены по единой методологии (агрегация 35+ источников) и сильно коррелируют (r = 0.85–0.90). Свёрнуты в WGI Composite = mean(F4, F5, F6).</p>
          <p>Данные WGI доступны в двух вариантах: (a) 5-летние срезы 2004–2024 — для оценки долгосрочного тренда; (b) годовые данные 2009–2024 (16 точек) — для анализа траекторий.</p>
          <p><strong>Блок III. Структура рынка (WDI, World Bank)</strong></p>
          <table className={s.table}>
            <thead>
              <tr><th>Параметр</th><th>Шкала</th><th>Покрытие</th><th>Описание</th></tr>
            </thead>
            <tbody>
              <tr><td>F7 — Market cap / GDP</td><td>%</td><td>43/48</td><td>Глубина фондового рынка</td></tr>
              <tr><td>Fx — Gross Domestic Savings / GDP</td><td>%</td><td>47/48</td><td>Валовые внутренние сбережения к ВВП</td></tr>
            </tbody>
          </table>
          <p><strong>Дополнительные параметры (для интерпретации):</strong></p>
          <table className={s.table}>
            <thead>
              <tr><th>Параметр</th><th>Тип</th><th>Покрытие</th><th>Использование</th></tr>
            </thead>
            <tbody>
              <tr><td>F1 — Правовая семья</td><td>Категориальный (English / French / German / Scandinavian)</td><td>48/48</td><td>Интерпретация кластеров</td></tr>
              <tr><td>Группа рынка (DM/EM)</td><td>Категориальный</td><td>48/48</td><td>Интерпретация кластеров</td></tr>
            </tbody>
          </table>
        </section>

        <section id="data-prep">
          <h3 className={s.h3}>2.2. Подготовка данных</h3>
          <p><strong>Временнóе покрытие.</strong> Данные F2 зафиксированы на 01.05.2019. Данные WGI — за 2024 г. Данные WDI (F7, Fx) — за последний доступный год для каждой юрисдикции (от 2017 до 2024, медиана — 2024). Поскольку институциональные параметры меняются медленно, разница в годах данных считается допустимой.</p>
          <p><strong>Пропуски.</strong> По F7 (Market cap/GDP) отсутствуют данные для 5 юрисдикций: Denmark, Finland, Italy, Sweden, Taiwan. На этапах I–II эти юрисдикции исключены (43 из 48). На этапе III (траектории WGI) все 48 юрисдикций включены.</p>
          <blockquote className={s.blockquote}>
            <p><strong>Рецензентский комментарий.</strong> Исключение 5 юрисдикций — все развитые европейские рынки (4 из 5) — может смещать результаты в сторону занижения представительства DM-кластера. Анализ доступных признаков (F2, WGI) для исключённых юрисдикций показывает, что все 5 по профилю ближе всего к кластерам A-1/A-2 (высокая защита, высокий WGI) — их исключение не влияет на положение России. См. рис. v3_excluded_jurisdictions.</p>
          </blockquote>
          <p><strong>Мультиколлинеарность WGI.</strong> Собственные значения корреляционной матрицы F4–F6: <code className={s.code}>λ₁=2.72</code>, <code className={s.code}>λ₂=0.16</code>, <code className={s.code}>λ₃=0.12</code>. PC1 объясняет {'>'}90% дисперсии — фактически единый латентный фактор «качество институтов». Использование трёх индексов раздельно привело бы к тройному взвешиванию одного конструкта. Свёртка в WGI Composite устраняет эту проблему.</p>
          <p><strong>Трансформации.</strong> Market cap/GDP и Savings/GDP: <code className={s.code}>log(1+x)</code> для нормализации правой асимметрии (skewness F7 {'>'} 3). Все признаки стандартизированы (Z-score: среднее 0, ст. откл. 1) перед кластеризацией.</p>
        </section>

        <section id="data-features">
          <h3 className={s.h3}>2.3. Итоговый набор признаков (Этапы I–II)</h3>
          <table className={s.table}>
            <thead>
              <tr><th>#</th><th>Признак</th><th>Источник</th><th>Трансформация</th></tr>
            </thead>
            <tbody>
              <tr><td>1</td><td>F2a Disclosure</td><td>Doing Business 2020</td><td>Z-score</td></tr>
              <tr><td>2</td><td>F2b Director Liability</td><td>Doing Business 2020</td><td>Z-score</td></tr>
              <tr><td>3</td><td>F2c Shareholder Suits</td><td>Doing Business 2020</td><td>Z-score</td></tr>
              <tr><td>4</td><td>WGI Composite</td><td>WGI 2024 (mean F4+F5+F6)</td><td>Z-score</td></tr>
              <tr><td>5</td><td><code className={s.code}>log(MktCap/GDP)</code></td><td>WDI, последний доступный год</td><td><code className={s.code}>log(1+x)</code>, Z-score</td></tr>
              <tr><td>6</td><td><code className={s.code}>log(Savings/GDP)</code></td><td>WDI, последний доступный год</td><td><code className={s.code}>log(1+x)</code>, Z-score</td></tr>
            </tbody>
          </table>
          <p>Матрица: 43 юрисдикции x 6 стандартизированных признаков.</p>
        </section>

        <section id="data-correlation">
          <h3 className={s.h3}>2.4. Корреляционная структура признаков</h3>
          <img src="/figures/correlation_matrix_pearson.png" alt="Корреляция Pearson" className={s.figure} />
          <p>Основные паттерны:</p>
          <ul>
            <li><strong>WGI-блок (F4–F6):</strong> r = 0.85–0.90. Фактически единый конструкт — свёртка обоснована.</li>
            <li><strong>F2b–F2c:</strong> умеренная корреляция (r ≈ 0.40). Ответственность директоров и доступность судебной защиты связаны, но измеряют различные аспекты.</li>
            <li><strong>F2a–WGI:</strong> слабая корреляция (r ≈ 0.10). Формальные требования к раскрытию не ассоциируются с качеством институтов (пример: Netherlands — WGI высокий, F2a = 2).</li>
            <li><strong>F7–WGI:</strong> положительная корреляция (r ≈ 0.45). Глубина рынка и качество институтов связаны, но связь не детерминистическая.</li>
            <li><strong>F2 sub-indices:</strong> умеренные корреляции (max F2b–F2c ≈ 0.40). Три суб-индекса несут различную информацию — использование раздельно обосновано.</li>
          </ul>
          <img src="/figures/distributions_boxplots.png" alt="Распределения признаков" className={s.figure} />
        </section>

        <section id="data-sample">
          <h3 className={s.h3}>2.5. Обзор выборки</h3>
          <p>Всего 48 юрисдикций: 22 Developed Markets (DM) и 26 Emerging Markets (EM).</p>
          <p>По правовым семьям: English (common law) — 15, French (civil law) — 19, German (civil law) — 10, Scandinavian — 4.</p>
          <p>Ключевые особенности распределений:</p>
          <ul>
            <li><strong>F2a (Disclosure):</strong> бимодальное — основная масса 7–10, но Netherlands (2), Switzerland (0), Austria (5) — юрисдикции с сильными институтами при слабом формальном требовании раскрытия.</li>
            <li><strong>WGI Composite:</strong> от −1.04 (Russia, 2024) до +1.61 (Singapore). Близко к нормальному.</li>
            <li><strong>F7 MktCap/GDP:</strong> экстремальная правая асимметрия — от 10% (Czech Republic) до 1118% (Hong Kong).</li>
          </ul>
        </section>

        <hr className={s.hr} />

        {/* ═══ 3. Этап I: Статическая кластеризация ═══ */}
        <section id="stage1">
          <h2 className={s.h2}>3. Этап I: Статическая кластеризация</h2>
        </section>

        <section id="stage1-motivation">
          <h3 className={s.h3}>3.1. Мотивация</h3>
          <p>Начальный подход: группировка юрисдикций по текущему «снимку» институциональных характеристик. Наиболее прямолинейный метод, не требующий временных рядов. Позволяет ответить на вопрос: <em>какие юрисдикции наиболее похожи на Россию прямо сейчас?</em></p>
        </section>

        <section id="stage1-method">
          <h3 className={s.h3}>3.2. Метод</h3>
          <p>Иерархическая кластеризация, Ward linkage, Euclidean distance. 43 юрисдикции x 6 стандартизированных признаков.</p>
          <p>Обоснование выбора Ward linkage:</p>
          <ul>
            <li>Минимизирует внутрикластерную дисперсию (оптимален для компактных кластеров).</li>
            <li>При 43 наблюдениях и 6 признаках — разумный баланс между чувствительностью и устойчивостью.</li>
            <li>Результаты сопоставлены с complete и average linkage — структура верхних уровней дендрограммы устойчива.</li>
          </ul>
        </section>

        <section id="stage1-k">
          <h3 className={s.h3}>3.3. Выбор числа кластеров</h3>
          <table className={s.table}>
            <thead>
              <tr><th>k</th><th>Silhouette</th></tr>
            </thead>
            <tbody>
              <tr><td>2</td><td>0.168</td></tr>
              <tr><td>3</td><td>0.200</td></tr>
              <tr><td>4</td><td>0.200</td></tr>
              <tr><td>5</td><td>0.200</td></tr>
              <tr><td>6</td><td>0.210</td></tr>
              <tr><td><strong>7</strong></td><td><strong>0.226</strong></td></tr>
              <tr><td>8</td><td>0.214</td></tr>
              <tr><td>9</td><td>0.207</td></tr>
              <tr><td>10</td><td>0.193</td></tr>
            </tbody>
          </table>
          <p>Оптимум: k=7 (silhouette = 0.226). Значение невысокое в абсолютном выражении — границы между кластерами нечёткие, что характерно для институциональных данных: непрерывный градиент, а не дискретные группы.</p>
          <blockquote className={s.blockquote}>
            <p><strong>Рецензентский комментарий.</strong> Silhouette = 0.226 указывает на слабую кластерную структуру. В литературе значения {'<'}0.25 трактуются как «кластеры не имеют существенной структуры» (Kaufman &amp; Rousseeuw, 1990). Тем не менее для <em>описательных</em> целей (группировка для сравнений) такие кластеры содержательно полезны — при условии, что их не интерпретируют как объективные границы.</p>
          </blockquote>
          <img src="/figures/silhouette_scores.png" alt="Silhouette scores" className={s.figure} />
        </section>

        <section id="stage1-dendrogram">
          <h3 className={s.h3}>3.4. Дендрограмма и структура кластеров</h3>
          <img src="/figures/clustering_A_dendrogram.png" alt="Дендрограмма Ward" className={s.figure} />
          <p>Дендрограмма показывает иерархическую структуру слияний. На верхнем уровне выделяются две макрогруппы: (1) юрисдикции с высоким F2 и/или высоким WGI; (2) юрисдикции с низким WGI и/или низким F2. Россия входит во вторую макрогруппу.</p>
        </section>

        <section id="stage1-profiles">
          <h3 className={s.h3}>3.5. Профили кластеров</h3>
          <img src="/figures/cluster_profiles_heatmap.png" alt="Профили кластеров" className={s.figure} />
          <table className={s.table}>
            <thead>
              <tr><th>Кл.</th><th>N</th><th>Состав</th><th>Профиль</th></tr>
            </thead>
            <tbody>
              <tr><td><strong>A-1</strong></td><td>2</td><td>Ireland, Singapore</td><td>Высочайшая защита инвесторов по всем трём F2 (+0.9…+1.1σ), высокий WGI (+1.35σ), высокие сбережения (+1.88σ). DM, English law.</td></tr>
              <tr><td><strong>A-2</strong></td><td>11</td><td>Canada, Hong Kong, India, Israel, Malaysia, New Zealand, Saudi Arabia, South Africa, Thailand, UK, USA</td><td>Сильная формальная защита (F2a +0.6σ, F2b +1.0σ, F2c +0.8σ), глубокий рынок (+0.9σ). Все 11 — English law. Включает DM (6) и EM (5).</td></tr>
              <tr><td><strong>A-3</strong></td><td>3</td><td>Netherlands, Qatar, Switzerland</td><td>Аномально низкое disclosure (F2a −2.2σ), но высокий WGI (+1.0σ) и глубокий рынок (+0.8σ). Модель «качество институтов компенсирует слабое формальное регулирование».</td></tr>
              <tr><td><strong>A-4</strong></td><td>14</td><td>Australia, Austria, Belgium, Chile, Czech Rep., France, Germany, Hungary, Japan, Norway, Poland, Portugal, South Korea, Spain</td><td>Самый многочисленный кластер. Средние значения. Смесь правовых семей (German 7, French 5, English 1, Scandinavian 1). «Континентальная» модель.</td></tr>
              <tr><td><strong>A-5</strong></td><td>4</td><td>Colombia, Egypt, Greece, Philippines</td><td>Низкий WGI (−1.1σ), неглубокий рынок (−1.0σ), низкие сбережения (−2.1σ). Все — French law, EM.</td></tr>
              <tr><td><strong>A-6</strong></td><td>6</td><td><strong>China, Indonesia, Mexico, Peru, Russia, Turkey</strong></td><td>Низкий WGI (−1.4σ), неглубокий рынок (−0.6σ), средние сбережения. Все EM. <strong>Кластер России.</strong></td></tr>
              <tr><td><strong>A-7</strong></td><td>3</td><td>Brazil, Kuwait, UAE</td><td>Высокая ответственность директоров (F2b +1.3σ), но низкая доступность судебной защиты (F2c −1.4σ).</td></tr>
            </tbody>
          </table>
        </section>

        <section id="stage1-legal">
          <h3 className={s.h3}>3.6. Правовые семьи и кластеры</h3>
          <table className={s.table}>
            <thead>
              <tr><th></th><th>A-1</th><th>A-2</th><th>A-3</th><th>A-4</th><th>A-5</th><th>A-6</th><th>A-7</th><th>Total</th></tr>
            </thead>
            <tbody>
              <tr><td><strong>English</strong></td><td>2</td><td>11</td><td>0</td><td>1</td><td>0</td><td>0</td><td>1</td><td>15</td></tr>
              <tr><td><strong>French</strong></td><td>0</td><td>0</td><td>2</td><td>5</td><td>4</td><td>5</td><td>2</td><td>18</td></tr>
              <tr><td><strong>German</strong></td><td>0</td><td>0</td><td>1</td><td>7</td><td>0</td><td>1</td><td>0</td><td>9</td></tr>
              <tr><td><strong>Scandinavian</strong></td><td>0</td><td>0</td><td>0</td><td>1</td><td>0</td><td>0</td><td>0</td><td>1</td></tr>
            </tbody>
          </table>
          <p><strong>Ключевое наблюдение:</strong> 13 из 15 English law юрисдикций группируются в кластерах A-1 и A-2 <em>без</em> явного включения правовой семьи в признаки. Это подтверждает гипотезу LLSV (La Porta et al., 1998) о связи правовой семьи с качеством корпоративного управления.</p>
          <p><strong>Отклонения от типа правовой семьи:</strong></p>
          <table className={s.table}>
            <thead>
              <tr><th>Юрисдикция</th><th>Правовая семья</th><th>Кластер</th><th>Особенность</th></tr>
            </thead>
            <tbody>
              <tr><td>Switzerland</td><td>German</td><td>A-3</td><td>WGI +1.51, MktCap/GDP 210%, но F2a=0. Институты высочайшего качества при формально отсутствующих требованиях к disclosure.</td></tr>
              <tr><td>Japan</td><td>German</td><td>A-4</td><td>MktCap/GDP 157%, F2c=8. Глубокий рынок и сильная судебная защита — нетипично для German law.</td></tr>
              <tr><td>South Korea</td><td>German</td><td>A-4</td><td>F2a=8 — высокое disclosure, нетипичное для German law.</td></tr>
              <tr><td>India, Thailand</td><td>English</td><td>A-2</td><td>WGI отрицательный, но F2 высокий — формальные правила без действенного правоприменения.</td></tr>
              <tr><td>Australia</td><td>English</td><td>A-4</td><td>Единственная English law в «континентальном» кластере — из-за низкого F2b (2).</td></tr>
            </tbody>
          </table>
        </section>

        <section id="stage1-russia">
          <h3 className={s.h3}>3.7. Позиция России (Этап I)</h3>
          <p><strong>Кластер A-6.</strong> Ближайшие юрисдикции по Евклидовой дистанции в 6D стандартизированном пространстве:</p>
          <table className={s.table}>
            <thead>
              <tr><th>#</th><th>Юрисдикция</th><th>Дистанция</th><th>Кластер</th><th>Правовая семья</th></tr>
            </thead>
            <tbody>
              <tr><td>1</td><td>Turkey</td><td>1.942</td><td>A-6</td><td>French</td></tr>
              <tr><td>2</td><td>Mexico</td><td>2.302</td><td>A-6</td><td>French</td></tr>
              <tr><td>3</td><td>Peru</td><td>2.463</td><td>A-6</td><td>French</td></tr>
              <tr><td>4</td><td>China</td><td>2.561</td><td>A-6</td><td>German</td></tr>
              <tr><td>5</td><td>Poland</td><td>2.649</td><td>A-4</td><td>German</td></tr>
              <tr><td>6</td><td>Hungary</td><td>2.690</td><td>A-4</td><td>German</td></tr>
              <tr><td>7</td><td>France</td><td>2.872</td><td>A-4</td><td>French</td></tr>
              <tr><td>8</td><td>Spain</td><td>2.911</td><td>A-4</td><td>French</td></tr>
              <tr><td>9</td><td>Portugal</td><td>2.942</td><td>A-4</td><td>French</td></tr>
              <tr><td>10</td><td>India</td><td>2.996</td><td>A-2</td><td>English</td></tr>
            </tbody>
          </table>
          <p>Ближайшие 4 юрисдикции — из того же кластера. Далее — кластер A-4 (континентальная Европа), к которому Россия ближе всего из «внешних» кластеров.</p>
          <p><strong>Профиль России относительно кластера A-6:</strong></p>
          <table className={s.table}>
            <thead>
              <tr><th>Признак</th><th>Россия (σ)</th><th>Среднее A-6 (σ)</th><th>Отклонение</th></tr>
            </thead>
            <tbody>
              <tr><td>F2a Disclosure</td><td>−0.55</td><td>+0.52</td><td><strong>−1.08</strong></td></tr>
              <tr><td>F2b Director Liability</td><td>−1.78</td><td>−0.67</td><td><strong>−1.11</strong></td></tr>
              <tr><td>F2c Shareholder Suits</td><td>+0.12</td><td>−0.82</td><td><strong>+0.94</strong></td></tr>
              <tr><td>WGI Composite</td><td>−2.09</td><td>−1.41</td><td>−0.68</td></tr>
              <tr><td><code className={s.code}>log(MktCap/GDP)</code></td><td>−0.74</td><td>−0.62</td><td>−0.13</td></tr>
              <tr><td><code className={s.code}>log(Savings/GDP)</code></td><td>+0.50</td><td>+0.36</td><td>+0.14</td></tr>
            </tbody>
          </table>
          <p>Россия отклоняется от кластера по трём параметрам:</p>
          <ul>
            <li><strong>F2b (Director Liability) значительно ниже</strong> — одна из юрисдикций с наиболее слабой формальной ответственностью директоров.</li>
            <li><strong>F2a (Disclosure) ниже</strong> — требования к раскрытию при сделках с заинтересованностью ниже, чем у других стран кластера.</li>
            <li><strong>F2c (Shareholder Suits) выше</strong> — доступность судебной защиты акционеров в России выше среднего по кластеру.</li>
          </ul>
          <img src="/figures/v3_radar_russia.png" alt="Radar: Россия vs кластер vs выборка" className={s.figure} />
          <img src="/figures/v3_parallel_coordinates.png" alt="Параллельные координаты: все юрисдикции" className={s.figure} />
        </section>

        <section id="stage1-alt">
          <h3 className={s.h3}>3.8. Проверка альтернативными методами</h3>
          <p><strong>DBSCAN (density-based):</strong> при 43 точках в 6D пространстве не даёт содержательных результатов. Во всём диапазоне гиперпараметров (eps 1.0–4.0, min_samples 3–5) алгоритм либо классифицирует {'>'}90% юрисдикций как шум, либо объединяет все в один кластер. Данные образуют непрерывный градиент без «островов плотности».</p>
          <p>Как детектор выбросов при eps=2.0 DBSCAN стабильно идентифицирует Egypt, Hong Kong, Ireland, Qatar, Singapore — юрисдикции с экстремальными профилями.</p>
          <p><strong>t-SNE (визуализация):</strong> проекция с различными значениями perplexity (5, 8, 12, 15, 20, 30) подтверждает устойчивость основных группировок.</p>
          <img src="/figures/tsne_best_annotated.png" alt="t-SNE проекция" className={s.figure} />
        </section>

        <section id="stage1-pca">
          <h3 className={s.h3}>3.9. PCA: что определяет структуру пространства</h3>
          <img src="/figures/pca_clusters.png" alt="PCA проекция с кластерами" className={s.figure} />
          <ul>
            <li><strong>PC1 (34% дисперсии):</strong> все признаки нагружаются положительно — это «общий индекс институциональной развитости». Россия находится в левой части (низкие значения).</li>
            <li><strong>PC2 (26% дисперсии):</strong> противопоставляет F2 (формальные правила) и WGI+Savings (институциональная среда). Россия — в центральной зоне по PC2.</li>
          </ul>
        </section>

        <section id="stage1-conclusions">
          <h3 className={s.h3}>3.10. Промежуточные выводы Этапа I</h3>
          <ol>
            <li><strong>Содержательно значимая группировка.</strong> Несмотря на невысокий silhouette, кластеры интерпретируемы и согласуются с предметным знанием (правовые семьи, уровни развития).</li>
            <li><strong>Россия — на границе кластеров A-6 и A-4.</strong> Пограничное положение означает, что опыт как развивающихся рынков (кластер A-6), так и континентальной Европы (кластер A-4) может быть релевантен.</li>
            <li><strong>Ограничение: статичность.</strong> Снимок не учитывает направление развития. Юрисдикции, находящиеся в одном кластере по текущему уровню, могут двигаться в противоположных направлениях.</li>
          </ol>
        </section>

        <hr className={s.hr} />

        {/* ═══ 4. Этап II: Линейная динамика WGI ═══ */}
        <section id="stage2">
          <h2 className={s.h2}>4. Этап II: Линейная динамика WGI (2004–2024, 5 срезов)</h2>
        </section>

        <section id="stage2-motivation">
          <h3 className={s.h3}>4.1. Мотивация</h3>
          <p>Статическая кластеризация фиксирует текущее состояние, но не учитывает, <em>откуда</em> юрисдикция пришла и <em>куда</em> движется. Юрисдикция с WGI = −0.5 и растущим трендом качественно отличается от юрисдикции с WGI = −0.5 и снижающимся трендом. Добавление линейного тренда WGI как дополнительного признака позволяет учесть направление институциональных изменений.</p>
        </section>

        <section id="stage2-data">
          <h3 className={s.h3}>4.2. Данные о динамике</h3>
          <p>Данные WGI доступны за 5 временных срезов с шагом 5 лет (2004, 2009, 2014, 2019, 2024) по всем 48 юрисдикциям. Для характеристики динамики рассчитаны:</p>
          <ul>
            <li><strong>d_20y</strong> — изменение за 20 лет (2024 минус 2004)</li>
            <li><strong>OLS slope</strong> — наклон линейной регрессии по 5 точкам, нормированный на десятилетие</li>
          </ul>
        </section>

        <section id="stage2-patterns">
          <h3 className={s.h3}>4.3. Глобальные паттерны</h3>
          <p>Преобладающий тренд — <strong>снижение экспертных оценок</strong>: из 48 юрисдикций только 11 показали рост WGI Composite за 20 лет, 37 — снижение.</p>
          <table className={s.table}>
            <thead>
              <tr><th>Тип траектории</th><th>Кол-во</th><th>Примеры</th></tr>
            </thead>
            <tbody>
              <tr><td>Устойчивый рост (≥3 периодов)</td><td>3</td><td>Saudi Arabia, Kuwait, Egypt</td></tr>
              <tr><td>Рост (≥2, 0 падений)</td><td>5</td><td>Indonesia, Czech Republic, Japan, South Korea, UAE</td></tr>
              <tr><td>Смешанная / стабильная</td><td>24</td><td>Russia, China, Singapore, Germany, USA, Poland, Israel</td></tr>
              <tr><td>Снижение (≥2 падений, 0 роста)</td><td>5</td><td>Australia, Belgium, Finland, Italy</td></tr>
              <tr><td>Устойчивое снижение (≥3 периодов)</td><td>11</td><td>Chile, Hungary, UK, Canada, Austria, Turkey, Mexico</td></tr>
            </tbody>
          </table>
          <p>Юрисдикции с наибольшим ростом: Indonesia (+0.75), Saudi Arabia (+0.64), Colombia (+0.35).</p>
          <p>Юрисдикции с наибольшим снижением: Mexico (−0.71), Hungary (−0.63), Chile (−0.61).</p>
          <blockquote className={s.blockquote}>
            <p><strong>Рецензентский комментарий.</strong> В числе юрисдикций со значительным снижением — развитые рынки (Chile, New Zealand, UK, Canada, Austria). Это указывает на <strong>глобальный</strong> характер тренда, а не на свойство отдельных стран. Возможная причина — ужесточение методологических стандартов WGI или изменение настроений экспертных панелей. Это важно для интерпретации: снижение WGI у России частично может быть артефактом глобального тренда, а не результатом исключительно национальных факторов.</p>
          </blockquote>
        </section>

        <section id="stage2-components">
          <h3 className={s.h3}>4.4. Компонентный анализ динамики</h3>
          <p>Разные компоненты WGI демонстрируют различную динамику:</p>
          <ul>
            <li><strong>F4 Regulatory Quality:</strong> наибольший разброс трендов. Лидеры роста — Qatar (+0.83), Saudi Arabia (+0.80), Indonesia (+0.63). Наибольшее падение — <strong>Россия (−0.91)</strong>, Hungary (−0.88), Spain (−0.76).</li>
            <li><strong>F5 Rule of Law:</strong> более консервативная динамика. Рост — Indonesia (+0.56), Czech Republic (+0.51). Падение — Hungary (−0.65), Greece (−0.62), Chile (−0.59), USA (−0.54).</li>
            <li><strong>F6 Political Stability:</strong> наибольшая волатильность. Рост — Indonesia (+1.05), Colombia (+1.02). Падение — Mexico (−0.56), Germany (−0.58).</li>
          </ul>
          <blockquote className={s.blockquote}>
            <p><strong>Рецензентский комментарий.</strong> Для России наибольшее снижение приходится именно на F4 (Regulatory Quality: −0.91 за 20 лет), тогда как F5 (Rule of Law) и F6 (Political Stability) демонстрируют более умеренную динамику. Это может указывать на то, что снижение WGI для России связано преимущественно с восприятием регуляторной среды, а не с общим качеством правоприменения.</p>
          </blockquote>
        </section>

        <section id="stage2-clustering">
          <h3 className={s.h3}>4.5. Кластеризация с линейным трендом (Вариант B)</h3>
          <p>OLS slope WGI Composite (на десятилетие) добавлен как 7-й признак.</p>
          <table className={s.table}>
            <thead>
              <tr><th>Параметр</th><th>Вариант A (статика)</th><th>Вариант B (+ динамика)</th></tr>
            </thead>
            <tbody>
              <tr><td>Число признаков</td><td>6</td><td>7</td></tr>
              <tr><td>Оптимальное k</td><td>7</td><td>10</td></tr>
              <tr><td>Silhouette</td><td>0.226</td><td>0.187</td></tr>
            </tbody>
          </table>
          <img src="/figures/clustering_AB_comparison.png" alt="Сравнение вариантов A и B" className={s.figure} />
          <p>Включение тренда привело к увеличению оптимального числа кластеров с 7 до 10 при снижении silhouette score. Кластеры стали более дробными — 7-мерное пространство при 43 наблюдениях даёт менее чёткие границы.</p>
          <p><strong>Ключевое изменение для России:</strong> перемещение из кластера A-6 (China, Indonesia, Mexico, Peru, Turkey) в <strong>кластер B-9</strong> (Australia, Austria, Belgium, Chile, France, Germany, Hungary, Poland, Portugal, Spain). По характеру динамики экспертных оценок WGI (slope = −0.104 на десятилетие) Россия ближе к западноевропейским юрисдикциям с умеренным снижением, чем к Mexico (−0.341) или Turkey (−0.307).</p>
          <p>При этом Россия в кластере B-9 является <strong>выбросом по абсолютному уровню WGI</strong>: −2.09σ при среднем кластера +0.17σ. Попадание обусловлено <em>близкой динамикой</em>, а не <em>близким уровнем</em>.</p>
          <p><strong>Устойчивые группировки</strong> (не зависят от включения динамики):</p>
          <ul>
            <li>Netherlands, Qatar, Switzerland — стабильны в обоих вариантах.</li>
            <li>Ядро English law (UK, New Zealand, Singapore, Ireland).</li>
            <li>China, Indonesia, Peru — устойчиво близки.</li>
          </ul>
          <p><strong>Новые группы, выявленные в Варианте B:</strong></p>
          <ul>
            <li>B-1 (Canada, Hong Kong, South Africa, USA) — развитые рынки English law с отрицательным трендом. «Снижающаяся элита».</li>
            <li>B-7 (Egypt, Greece, Mexico, Turkey) — юрисдикции с выраженным падением при низком текущем уровне.</li>
            <li>B-10 (Czech Republic — синглтон) — единственная юрисдикция с устойчивым ростом WGI при среднем абсолютном уровне.</li>
          </ul>
          <img src="/figures/wgi_trajectories.png" alt="Траектории WGI 2004–2024" className={s.figure} />
        </section>

        <section id="stage2-conclusions">
          <h3 className={s.h3}>4.6. Промежуточные выводы Этапа II</h3>
          <ol>
            <li><strong>Динамика — самостоятельное измерение</strong>, не сводимое к текущему уровню. Юрисдикции одного кластера по статике могут иметь противоположные тренды.</li>
            <li><strong>Перемещение России</strong> при добавлении динамики показывает, что по <em>характеру изменений</em> она ближе к континентальной Европе, чем к развивающимся рынкам.</li>
            <li><strong>Ограничение:</strong> 5 точек с шагом 5 лет не позволяют выявить нелинейности и структурные разрывы. Линейный тренд маскирует возможные резкие сдвиги. Silhouette снизился с 0.226 до 0.187 — добавление одного признака при малом размере выборки размывает кластерную структуру.</li>
          </ol>
          <blockquote className={s.blockquote}>
            <p><strong>Рецензентский комментарий.</strong> Перемещение России из кластера развивающихся рынков в кластер континентальной Европы при добавлении динамики — содержательно важный результат, но его интерпретация требует осторожности. Россия попадает в B-9 не потому, что её институциональная среда близка к европейской, а потому, что <em>темп изменения</em> WGI у неё умеренный (slope −0.104), в отличие от Mexico (−0.341) или Turkey (−0.307). Это различие в скорости, а не в направлении или уровне.</p>
          </blockquote>
        </section>

        <hr className={s.hr} />

        {/* ═══ 5. Этап III: Кластеризация годовых траекторий ═══ */}
        <section id="stage3">
          <h2 className={s.h2}>5. Этап III: Кластеризация годовых траекторий (2009–2024)</h2>
        </section>

        <section id="stage3-motivation">
          <h3 className={s.h3}>5.1. Мотивация</h3>
          <p>Этап II показал, что динамика — информативное измерение, но линейная аппроксимация по 5 точкам грубая. Переход к годовым данным (16 точек, 2009–2024) позволяет:</p>
          <ul>
            <li>Выявить <strong>нелинейности</strong> и <strong>структурные разрывы</strong> в траекториях.</li>
            <li>Применить методы <strong>кластеризации временных рядов</strong> (DTW, k-Shape, feature-based), которые группируют по <em>форме</em> траектории.</li>
            <li>Разделить юрисдикции с одинаковым текущим уровнем, но разной историей.</li>
          </ul>
          <blockquote className={s.blockquote}>
            <p><strong>Рецензентский комментарий.</strong> Этап III — наиболее методологически продвинутый. Применение нескольких подходов (DTW, k-Shape, feature extraction) и сравнение их результатов — сильная сторона исследования. Вместе с тем важно отметить: <strong>Этап III использует только траектории WGI, без признаков F2 и F7.</strong> Это означает, что кластеризация здесь отражает только динамику качества институтов, но не формальную защиту инвесторов или глубину рынка. Этап III не заменяет, а дополняет Этап I.</p>
          </blockquote>
        </section>

        <section id="stage3-data">
          <h3 className={s.h3}>5.2. Данные</h3>
          <p>Годовые данные WGI (F4, F5, F6) за 2009–2024. 16 точек, все 48 юрисдикций имеют полные ряды. WGI Composite = mean(F4, F5, F6) рассчитан для каждого года.</p>
          <img src="/figures/traj_overview.png" alt="Обзор траекторий" className={s.figure} />
        </section>

        <section id="stage3-breakpoints">
          <h3 className={s.h3}>5.3. Обнаружение структурных разрывов</h3>
          <p>Алгоритм <strong>PELT</strong> (Pruned Exact Linear Time) из библиотеки <code className={s.code}>ruptures</code>, модель RBF, штраф pen=3.0, min_size=3. Структурные разрывы обнаружены у <strong>26 из 48</strong> юрисдикций.</p>
          <p>Избранные разрывы:</p>
          <table className={s.table}>
            <thead>
              <tr><th>Юрисдикция</th><th>Год</th><th>Юрисдикция</th><th>Год</th></tr>
            </thead>
            <tbody>
              <tr><td><strong>Russia</strong></td><td><strong>2022</strong></td><td>Hong Kong</td><td>2019</td></tr>
              <tr><td>Canada</td><td>2021</td><td>Hungary</td><td>2014</td></tr>
              <tr><td>Chile</td><td>2019</td><td>Mexico</td><td>2017</td></tr>
              <tr><td>China</td><td>2017</td><td>United States</td><td>2019</td></tr>
            </tbody>
          </table>
          <p>22 юрисдикции разрывов не имеют (траектория аппроксимируется одним линейным сегментом).</p>
          <img src="/figures/traj_breakpoints.png" alt="Траектории с разрывами" className={s.figure} />
        </section>

        <section id="stage3-preliminary">
          <h3 className={s.h3}>5.4. Предварительная кластеризация (DTW, k-Shape, Feature-based)</h3>
          <p>Перед финальным анализом выполнены три варианта кластеризации полных (без расщепления) траекторий 48 юрисдикций:</p>
          <table className={s.table}>
            <thead>
              <tr><th>Метод</th><th>Оптимальное k</th><th>Silhouette</th><th>Характеристика</th></tr>
            </thead>
            <tbody>
              <tr><td><strong>DTW</strong> (Dynamic Time Warping)</td><td>2</td><td>0.423</td><td>Бинарное: «растущие» (20) vs «снижающиеся» (28). При k=4: silhouette=0.319</td></tr>
              <tr><td><strong>k-Shape</strong> (cross-correlation)</td><td>2</td><td>0.289</td><td>Аналогичное бинарное разделение. При k{'>'}2: silhouette {'<'}0</td></tr>
              <tr><td><strong>Feature-based</strong> (17 признаков)</td><td>6</td><td>0.254</td><td>Наиболее гранулярная группировка. Выделен кластер Hong Kong + Russia (резкий сдвиг)</td></tr>
            </tbody>
          </table>
          <p><strong>Вывод:</strong> DTW и k-Shape эффективны для бинарного разделения, но не дают достаточной гранулярности. Feature-based подход наиболее информативен, так как учитывает не только форму, но и волатильность, наличие разрывов и изменение тренда.</p>
          <img src="/figures/traj_comparison_tsne.png" alt="Сравнение методов на t-SNE" className={s.figure} />
        </section>

        <section id="stage3-split">
          <h3 className={s.h3}>5.5. Расщепление России</h3>
          <p>На основании результатов PELT (разрыв в 2022 г.) и наблюдаемого максимального годового скачка WGI Composite (−0.302 между 2021 и 2022 г.), Россия представлена двумя сущностями:</p>
          <ul>
            <li><strong>Russia_1</strong> — период 2009–2021 (13 точек)</li>
            <li><strong>Russia_2</strong> — период 2022–2024 (3 точки)</li>
          </ul>
          <table className={s.table}>
            <thead>
              <tr><th>Признак</th><th>Russia_1 (2009–2021)</th><th>Russia_2 (2022–2024)</th></tr>
            </thead>
            <tbody>
              <tr><td>mean (средний уровень WGI)</td><td>−0.648</td><td>−0.955</td></tr>
              <tr><td>std (волатильность)</td><td>0.072</td><td>0.063</td></tr>
              <tr><td>slope (наклон, /год)</td><td><strong>+0.013</strong></td><td><strong>−0.073</strong></td></tr>
              <tr><td>frac_positive (доля лет с ростом)</td><td><strong>0.50</strong></td><td><strong>0.00</strong></td></tr>
              <tr><td>max_rise</td><td>+0.096</td><td><strong>−0.031</strong></td></tr>
            </tbody>
          </table>
          <p>Ключевые различия:</p>
          <ul>
            <li><strong>Инверсия направления:</strong> slope с +0.013 на −0.073.</li>
            <li><strong>Полная потеря положительной динамики:</strong> frac_positive 50% → 0%.</li>
            <li><strong>Даже max_rise во втором периоде отрицательный</strong> (−0.031): ни одного года даже с минимальным ростом.</li>
          </ul>
          <img src="/figures/v3_russia_trajectory_annotated.png" alt="Траектория России с PELT-разрывом" className={s.figure} />
          <blockquote className={s.blockquote}>
            <p><strong>Рецензентский комментарий.</strong> Расщепление России на два объекта — методологически обоснованный приём для юрисдикции с очевидным структурным разрывом. Однако <strong>Russia_2 содержит всего 3 точки</strong> (2022, 2023, 2024). Признаки, извлечённые из 3 наблюдений, менее статистически надёжны: slope определяется фактически двумя приращениями, std и frac_positive также малоинформативны. Это следует учитывать при интерпретации.</p>
          </blockquote>
        </section>

        <section id="stage3-final">
          <h3 className={s.h3}>5.6. Финальная кластеризация (Feature-based с расщеплением)</h3>
          <p><strong>Параметры:</strong></p>
          <ul>
            <li>Объекты: 49 (47 юрисдикций + Russia_1 + Russia_2)</li>
            <li>Признаки: 12 (mean, std, start, end, range, slope, residual_std, mean_abs_delta, max_abs_delta, max_drop, max_rise, frac_positive)</li>
            <li>Метод: Ward linkage, Euclidean distance, Z-score стандартизация</li>
          </ul>
          <p><strong>Выбор числа кластеров:</strong></p>
          <table className={s.table}>
            <thead>
              <tr><th>k</th><th>Silhouette</th></tr>
            </thead>
            <tbody>
              <tr><td>2</td><td>0.290</td></tr>
              <tr><td>3</td><td>0.306</td></tr>
              <tr><td><strong>4</strong></td><td><strong>0.338</strong></td></tr>
              <tr><td>5</td><td>0.270</td></tr>
              <tr><td><strong>6</strong></td><td><strong>0.270</strong></td></tr>
              <tr><td>7</td><td>0.269</td></tr>
              <tr><td>8</td><td>0.262</td></tr>
            </tbody>
          </table>
          <p>Статистический оптимум — <strong>k=4</strong> (silhouette=0.338). Для содержательного анализа выбрано <strong>k=6</strong> (silhouette=0.270): более детальное разделение при умеренном снижении качества.</p>
          <blockquote className={s.blockquote}>
            <p><strong>Рецензентский комментарий.</strong> Выбор k=6 вместо статистического оптимума k=4 — содержательно мотивированный, но спорный. Разница в silhouette существенна (0.338 vs 0.270). При k=4 Россия_1 и Россия_2 по-прежнему попадают в разные кластеры (верифицировано), что сохраняет ключевой вывод о двух режимах. При k=6 появляются малые кластеры (F3 и F4 по 2 юрисдикции), что может указывать на переобучение. Рекомендуется рассматривать оба варианта (k=4 и k=6) при интерпретации, используя k=4 как основной, а k=6 — для дополнительной гранулярности.</p>
          </blockquote>
          <img src="/figures/final_silhouette_k.png" alt="Silhouette по k" className={s.figure} />
          <img src="/figures/final_dendrogram.png" alt="Дендрограмма финальной кластеризации" className={s.figure} />
        </section>

        <section id="stage3-clusters">
          <h3 className={s.h3}>5.7. Состав кластеров (k=6)</h3>
          <img src="/figures/final_profiles_heatmap.png" alt="Профили кластеров" className={s.figure} />

          <p><strong>Кластер F1 (10 юрисдикций): «Развитые, снижающиеся»</strong></p>
          <p><strong>Состав:</strong> Austria, Canada, France, Germany, Poland, Portugal, Qatar, Sweden, United Kingdom, United States.</p>
          <table className={s.table}>
            <thead>
              <tr><th>Признак</th><th>Среднее</th></tr>
            </thead>
            <tbody>
              <tr><td>mean WGI</td><td>1.115</td></tr>
              <tr><td>slope (/год)</td><td>−0.018</td></tr>
              <tr><td>frac_positive</td><td>0.36</td></tr>
            </tbody>
          </table>
          <p>Высокий уровень WGI при отрицательном наклоне. Менее 40% лет с положительной динамикой.</p>

          <p><strong>Кластер F2 (18 юрисдикций): «Развитые, стабильные»</strong></p>
          <p><strong>Состав:</strong> Australia, Belgium, Czech Republic, Denmark, Finland, Ireland, Italy, Japan, Malaysia, Netherlands, New Zealand, Norway, Singapore, South Korea, Spain, Switzerland, Taiwan, UAE.</p>
          <table className={s.table}>
            <thead>
              <tr><th>Признак</th><th>Среднее</th></tr>
            </thead>
            <tbody>
              <tr><td>mean WGI</td><td>1.215</td></tr>
              <tr><td>slope (/год)</td><td>0.000</td></tr>
              <tr><td>frac_positive</td><td>0.53</td></tr>
            </tbody>
          </table>
          <p>Наивысший средний уровень WGI, нулевой наклон, наименьшая волатильность. Наиболее стабильная группа.</p>

          <p><strong>Кластер F3 (2 юрисдикции): «Выраженное снижение»</strong></p>
          <p><strong>Состав:</strong> Chile, Turkey.</p>
          <table className={s.table}>
            <thead>
              <tr><th>Признак</th><th>Среднее</th></tr>
            </thead>
            <tbody>
              <tr><td>mean WGI</td><td>0.211</td></tr>
              <tr><td>slope (/год)</td><td>−0.049</td></tr>
              <tr><td>max_drop</td><td>−0.242</td></tr>
            </tbody>
          </table>
          <p>Наибольший наклон снижения, наибольший размах.</p>
          <blockquote className={s.blockquote}>
            <p><strong>Рецензентский комментарий.</strong> Кластер из 2 объектов — фактически пара выбросов, а не кластер. Chile и Turkey объединены экстремальной амплитудой снижения, но содержательно различны (Chile — DM, OECD; Turkey — EM). При k=4 эти юрисдикции распределяются по более крупным группам.</p>
          </blockquote>

          <p><strong>Кластер F4 (2 юрисдикции): «Резкий сдвиг с высокого уровня»</strong></p>
          <p><strong>Состав:</strong> Egypt, Hong Kong.</p>
          <table className={s.table}>
            <thead>
              <tr><th>Признак</th><th>Среднее</th></tr>
            </thead>
            <tbody>
              <tr><td>mean WGI</td><td>0.235</td></tr>
              <tr><td>std</td><td>0.215</td></tr>
              <tr><td>max_abs_delta</td><td>0.424</td></tr>
            </tbody>
          </table>
          <p>Объединены паттерном высокой волатильности и экстремального max_abs_delta. При этом абсолютные уровни WGI принципиально различны (Egypt ≈ −0.7, Hong Kong ≈ +1.1).</p>
          <blockquote className={s.blockquote}>
            <p><strong>Рецензентский комментарий.</strong> Кластер F4 — наиболее сомнительный: silhouette Hong Kong = 0.035, Egypt = 0.072. Оба объекта ближе к границе с другими кластерами, чем к друг другу. Объединение обусловлено исключительно высокой волатильностью, а не содержательной близостью.</p>
          </blockquote>

          <p><strong>Кластер F5 (12 юрисдикций): «Развивающиеся, стабильные или растущие»</strong></p>
          <p><strong>Состав:</strong> China, Colombia, Greece, India, Indonesia, Israel, Kuwait, Peru, Philippines, <strong>Russia_1</strong>, Saudi Arabia, Thailand.</p>
          <table className={s.table}>
            <thead>
              <tr><th>Признак</th><th>Среднее</th></tr>
            </thead>
            <tbody>
              <tr><td>mean WGI</td><td>−0.010</td></tr>
              <tr><td>slope (/год)</td><td>0.003</td></tr>
              <tr><td>frac_positive</td><td>0.53</td></tr>
            </tbody>
          </table>
          <p>Средний или низкий уровень WGI, наклон близок к нулю или слабоположительный. 53% лет с ростом. Стабильная группа.</p>
          <p><strong>Russia_1 в этом кластере:</strong> mean = −0.648, slope = +0.013/год, frac_positive = 0.50, silhouette = 0.329 (выше среднего). Объект хорошо вписывается в группу.</p>

          <p><strong>Кластер F6 (5 юрисдикций): «Снижение средних и низких»</strong></p>
          <p><strong>Состав:</strong> Brazil, Hungary, Mexico, <strong>Russia_2</strong>, South Africa.</p>
          <table className={s.table}>
            <thead>
              <tr><th>Признак</th><th>Среднее</th></tr>
            </thead>
            <tbody>
              <tr><td>mean WGI</td><td>−0.231</td></tr>
              <tr><td>slope (/год)</td><td>−0.039</td></tr>
              <tr><td>frac_positive</td><td>0.24</td></tr>
            </tbody>
          </table>
          <p>Устойчивое снижение, менее четверти лет с ростом.</p>
          <p><strong>Russia_2 в этом кластере:</strong> mean = −0.955, slope = −0.073/год, frac_positive = 0.00, silhouette = 0.247.</p>
          <blockquote className={s.blockquote}>
            <p><strong>Рецензентский комментарий.</strong> Hungary имеет отрицательный silhouette (−0.12) — она ошибочно отнесена к F6. Её средний WGI (0.556) значительно выше среднего F6 (−0.231) и ближе к кластерам F1 или F2. Привязка к F6 обусловлена отрицательным slope (−0.030) и низкой frac_positive (0.27), но по абсолютному уровню Hungary — выброс в своём кластере. Malaysia также имеет marginal silhouette (−0.009) в кластере F2.</p>
          </blockquote>
        </section>

        <section id="stage3-silhouette">
          <h3 className={s.h3}>5.8. Силуэтный анализ</h3>
          <img src="/figures/final_silhouette_entities.png" alt="Силуэт по объектам" className={s.figure} />
          <p>Распределение silhouette:</p>
          <ul>
            <li>≥0.3 (хорошо): 47% объектов</li>
            <li>0.1–0.3 (приемлемо): 45% объектов</li>
            <li>{'<'}0.1 (слабо): 4% объектов</li>
            <li>{'<'}0 (неверно отнесены): 4% объектов (Hungary, Malaysia)</li>
          </ul>
        </section>

        <section id="stage3-projections">
          <h3 className={s.h3}>5.9. PCA и t-SNE проекции</h3>
          <img src="/figures/final_pca.png" alt="PCA финальная" className={s.figure} />
          <img src="/figures/final_tsne.png" alt="t-SNE финальная" className={s.figure} />
        </section>

        <section id="stage3-conclusions">
          <h3 className={s.h3}>5.10. Промежуточные выводы Этапа III</h3>
          <ol>
            <li><strong>Feature-based подход</strong> наиболее информативен из трёх опробованных (DTW, k-Shape, features). DTW и k-Shape дают лишь бинарное разделение.</li>
            <li><strong>Расщепление России</strong> выявляет два качественно различных институциональных режима. Это устойчивый результат: при k=4 и k=6 Russia_1 и Russia_2 попадают в разные кластеры.</li>
            <li>При k=6 появляются <strong>малые кластеры</strong> (F3, F4 — по 2 объекта) с низким silhouette. Статистический оптимум k=4 даёт более надёжные группировки.</li>
            <li><strong>Ограничение:</strong> Этап III использует только WGI-траектории, без F2 (защита инвесторов) и F7 (глубина рынка). Это означает, что полученные кластеры отражают динамику восприятия качества институтов, но не полный институциональный профиль.</li>
          </ol>
          <img src="/figures/final_trajectories_by_cluster.png" alt="Траектории по кластерам" className={s.figure} />
        </section>

        <hr className={s.hr} />

        {/* ═══ 6. Этап IV: Интегрированная кластеризация (MFA) ═══ */}
        <section id="stage4">
          <h2 className={s.h2}>6. Этап IV: Интегрированная кластеризация (MFA)</h2>
        </section>

        <section id="stage4-motivation">
          <h3 className={s.h3}>6.1. Мотивация</h3>
          <p>Этапы I–III решали задачу последовательно, каждый раз расширяя аналитическую рамку. Однако они не были интегрированы: Этап I учитывал статический профиль (F2, MktCap, Savings, WGI₂₀₂₄), а Этап III — только динамику WGI-траекторий. Юрисдикции, близкие по динамике, могут иметь совершенно разную формальную защиту инвесторов или глубину рынка, и наоборот.</p>
          <p>Этап IV решает эту проблему: интегрирует статический институциональный профиль с динамическими характеристиками траекторий в единое пространство для кластеризации.</p>
          <p>Дополнительное преимущество: на Этапе IV включены <strong>все 48 юрисдикций</strong> (включая Denmark, Finland, Italy, Sweden, Taiwan, которые были исключены из Этапов I–II из-за отсутствия MktCap/GDP — для них применена медианная импутация).</p>
        </section>

        <section id="stage4-method">
          <h3 className={s.h3}>6.2. Метод: Multiple Factor Analysis (MFA)</h3>
          <p>MFA (Escofier &amp; Pages, 1994) — метод, специально разработанный для ситуации, когда <strong>несколько групп переменных описывают одни и те же объекты</strong>. В отличие от простой конкатенации, MFA уравнивает вклад каждого блока переменных, нормируя его на первое сингулярное значение. Это предотвращает ситуацию, когда блок с большим числом переменных доминирует.</p>
          <p><strong>Три блока признаков:</strong></p>
          <table className={s.table}>
            <thead>
              <tr><th>Блок</th><th>Переменные</th><th>Кол-во</th><th>Источник</th></tr>
            </thead>
            <tbody>
              <tr><td>A — Защита инвесторов</td><td>F2a, F2b, F2c</td><td>3</td><td>Doing Business 2020</td></tr>
              <tr><td>B — Рыночная структура</td><td><code className={s.code}>log(1+MktCap/GDP)</code>, <code className={s.code}>log(1+Savings/GDP)</code></td><td>2</td><td>WDI</td></tr>
              <tr><td>C — Динамика институтов</td><td>TrajPC1, TrajPC2, TrajPC3, TrajPC4</td><td>4</td><td>PCA от 11 trajectory features</td></tr>
            </tbody>
          </table>
          <p><strong>Особенности построения:</strong></p>
          <ul>
            <li>WGI₂₀₂₄ <strong>не включён</strong> в блок A или B, поскольку его информация содержится в <code className={s.code}>mean</code> траектории, который входит в PCA блока C. Включение привело бы к двойному взвешиванию одного конструкта.</li>
            <li>Блок C: из 12 исходных trajectory features удалён <code className={s.code}>mean</code> (дублирует WGI₂₀₂₄). Оставшиеся 11 признаков сжаты PCA до 4 компонент (89.7% дисперсии). TrajPC1 отражает волатильность/размах; TrajPC2 — наклон/направление тренда; TrajPC3 — начальный/конечный уровень; TrajPC4 — долю положительных изменений.</li>
            <li>Для 5 юрисдикций без MktCap/GDP (Denmark, Finland, Italy, Sweden, Taiwan) применена медианная импутация блока B.</li>
            <li>Russia_1 и Russia_2 получают <strong>одинаковые</strong> значения блоков A и B, но <strong>разные</strong> значения блока C. Это корректно: формальная защита инвесторов и глубина рынка не менялись между периодами, а траектория — менялась.</li>
          </ul>
          <p><strong>MFA-нормализация:</strong> каждый блок стандартизирован (Z-score), затем разделён на свое первое сингулярное значение (A: 1.27, B: 1.11, C: 1.01). Нормированные блоки конкатенированы, после чего выполнена глобальная PCA.</p>
          <p><strong>Кластеризация:</strong> Ward linkage, Euclidean distance в MFA-пространстве (9 измерений).</p>
        </section>

        <section id="stage4-contributions">
          <h3 className={s.h3}>6.3. Блоковые вклады в MFA-измерения</h3>
          <img src="/figures/s4_mfa_block_contributions.png" alt="Блоковые вклады" className={s.figure} />
          <table className={s.table}>
            <thead>
              <tr><th>MFA-измерение</th><th>Дисперсия</th><th>Доминирующий блок</th></tr>
            </thead>
            <tbody>
              <tr><td>Dim 1 (21.6%)</td><td>Сбалансировано</td><td>A ≈ B ≈ C</td></tr>
              <tr><td>Dim 2 (18.9%)</td><td>Динамика + рынок</td><td>C {'>'} B {'>'} A</td></tr>
              <tr><td>Dim 3 (15.0%)</td><td>Динамика</td><td>C ≫ A, B</td></tr>
              <tr><td>Dim 4 (13.2%)</td><td>Динамика</td><td>C ≫ A, B</td></tr>
              <tr><td>Dim 5 (10.8%)</td><td>Защита инвесторов</td><td>A ≫ B {'>'} C</td></tr>
            </tbody>
          </table>
          <p>Первое измерение MFA сбалансировано между блоками — MFA работает как задумано. Измерения 3–4 управляются траекторией (волатильность, наклон), а измерение 5 — защитой инвесторов. Это позволяет кластерам отражать <strong>все три аспекта</strong> институциональной среды.</p>
        </section>

        <section id="stage4-k">
          <h3 className={s.h3}>6.4. Выбор числа кластеров</h3>
          <img src="/figures/s4_silhouette_k.png" alt="Silhouette по k" className={s.figure} />
          <p>Для MFA: оптимум в диапазоне k=3–5 (silhouette 0.11–0.12). Выбрано <strong>k=5</strong> (silhouette=0.124). Для сравнения: простая конкатенация (без MFA-нормализации) даёт оптимум k=4 (silhouette=0.147).</p>
          <blockquote className={s.blockquote}>
            <p><strong>Рецензентский комментарий.</strong> Silhouette = 0.12 — ниже, чем на предыдущих этапах (I: 0.226, III: 0.270–0.338). Это ожидаемо: 9-мерное пространство при 49 объектах — проклятие размерности усиливается. Невысокий silhouette не обесценивает кластеризацию для описательных целей, но указывает, что границы между кластерами ещё менее чёткие, чем ранее.</p>
          </blockquote>
        </section>

        <section id="stage4-clusters">
          <h3 className={s.h3}>6.5. Дендрограмма и состав кластеров</h3>
          <img src="/figures/s4_dendrogram.png" alt="Дендрограмма MFA" className={s.figure} />
          <img src="/figures/s4_profiles_heatmap.png" alt="Профили кластеров" className={s.figure} />

          <p><strong>Кластер S4-1 (12 юрисдикций): «English law, средняя защита, растущие или стабильные»</strong></p>
          <p><strong>Состав:</strong> India, Ireland, Israel, Kuwait, Malaysia, New Zealand, Peru, Saudi Arabia, Singapore, Thailand, UAE, United Kingdom.</p>
          <table className={s.table}>
            <thead>
              <tr><th>Признак</th><th>Z-score</th></tr>
            </thead>
            <tbody>
              <tr><td>F2a</td><td>+0.66</td></tr>
              <tr><td>F2b</td><td>+1.10</td></tr>
              <tr><td>F2c</td><td>+0.32</td></tr>
              <tr><td>traj_slope</td><td>+0.58</td></tr>
              <tr><td>traj_frac_positive</td><td>+0.44</td></tr>
            </tbody>
          </table>
          <p>Высокая защита инвесторов (особенно F2b), положительный или нулевой тренд WGI, умеренная глубина рынка.</p>

          <p><strong>Кластер S4-2 (4 юрисдикции): «Глубокие рынки, высокая волатильность»</strong></p>
          <p><strong>Состав:</strong> Canada, Hong Kong, South Africa, United States.</p>
          <table className={s.table}>
            <thead>
              <tr><th>Признак</th><th>Z-score</th></tr>
            </thead>
            <tbody>
              <tr><td>log_mktcap</td><td>+1.81</td></tr>
              <tr><td>F2b</td><td>+1.21</td></tr>
              <tr><td>F2c</td><td>+1.04</td></tr>
              <tr><td>traj_std</td><td>+1.23</td></tr>
              <tr><td>traj_slope</td><td>−1.15</td></tr>
            </tbody>
          </table>
          <p>Глубочайшие рынки капитала, сильнейшая защита, но <strong>отрицательный тренд WGI</strong> и высокая волатильность. «Зрелые рынки с ухудшающимися экспертными оценками».</p>

          <p><strong>Кластер S4-3 (7 юрисдикций): «Развивающиеся, растущие»</strong></p>
          <p><strong>Состав:</strong> China, Colombia, Egypt, Greece, Indonesia, Philippines, <strong>Russia_1</strong>.</p>
          <table className={s.table}>
            <thead>
              <tr><th>Признак</th><th>Z-score</th></tr>
            </thead>
            <tbody>
              <tr><td>F2b</td><td>−0.71</td></tr>
              <tr><td>F2c</td><td>−0.82</td></tr>
              <tr><td>log_mktcap</td><td>−0.73</td></tr>
              <tr><td>traj_slope</td><td>+0.90</td></tr>
              <tr><td>traj_frac_positive</td><td>+0.71</td></tr>
            </tbody>
          </table>
          <p>Низкая формальная защита, неглубокие рынки, но <strong>положительный тренд</strong> WGI (slope {'>'} 0) и высокая доля лет с ростом. Группа юрисдикций с развивающейся институциональной средой.</p>
          <p><strong>Russia_1 в этом кластере:</strong> slope = +0.013, frac_positive = 0.50, silhouette = −0.07 (пограничный объект).</p>

          <p><strong>Кластер S4-4 (9 юрисдикций): «Снижающиеся, смешанные»</strong></p>
          <p><strong>Состав:</strong> Austria, Brazil, Chile, Czech Republic, Hungary, Mexico, Poland, <strong>Russia_2</strong>, Turkey.</p>
          <table className={s.table}>
            <thead>
              <tr><th>Признак</th><th>Z-score</th></tr>
            </thead>
            <tbody>
              <tr><td>F2a</td><td>−0.66</td></tr>
              <tr><td>log_mktcap</td><td>−1.00</td></tr>
              <tr><td>traj_slope</td><td>−1.21</td></tr>
              <tr><td>traj_frac_positive</td><td>−1.25</td></tr>
              <tr><td>traj_std</td><td>+0.79</td></tr>
            </tbody>
          </table>
          <p>Отрицательный тренд WGI, менее четверти лет с ростом, неглубокие рынки. Смесь EM и DM (Austria, Czech Republic, Poland — среднеевропейские юрисдикции с ухудшающимися оценками).</p>
          <p><strong>Russia_2 в этом кластере:</strong> slope = −0.073, frac_positive = 0.00. По тренду Russia_2 — экстремальный член кластера.</p>

          <p><strong>Кластер S4-5 (17 юрисдикций): «Развитые стабильные»</strong></p>
          <p><strong>Состав:</strong> Australia, Belgium, Denmark, Finland, France, Germany, Italy, Japan, Netherlands, Norway, Portugal, Qatar, South Korea, Spain, Sweden, Switzerland, Taiwan.</p>
          <table className={s.table}>
            <thead>
              <tr><th>Признак</th><th>Z-score</th></tr>
            </thead>
            <tbody>
              <tr><td>F2a</td><td>−0.44</td></tr>
              <tr><td>F2b</td><td>−0.54</td></tr>
              <tr><td>traj_std</td><td>−0.61</td></tr>
              <tr><td>traj_slope</td><td>+0.13</td></tr>
            </tbody>
          </table>
          <p>Самый многочисленный кластер. Средние или низкие показатели формальной защиты, низкая волатильность, околонулевой тренд. Ядро развитых рынков с континентальной моделью.</p>
        </section>

        <section id="stage4-russia">
          <h3 className={s.h3}>6.6. Позиция России (Этап IV)</h3>
          <img src="/figures/s4_pca.png" alt="PCA проекция MFA" className={s.figure} />
          <img src="/figures/s4_russia_neighbors.png" alt="Ближайшие соседи" className={s.figure} />
          <p><strong>Russia_1 → Кластер S4-3</strong> (развивающиеся, растущие). Ближайшие:</p>
          <table className={s.table}>
            <thead>
              <tr><th>#</th><th>Юрисдикция</th><th>Расстояние</th><th>Кластер</th></tr>
            </thead>
            <tbody>
              <tr><td>1</td><td>Italy</td><td>2.0</td><td>S4-5</td></tr>
              <tr><td>2</td><td>China</td><td>2.3</td><td>S4-3</td></tr>
              <tr><td>3</td><td>Spain</td><td>2.4</td><td>S4-5</td></tr>
              <tr><td>4</td><td>Peru</td><td>2.4</td><td>S4-1</td></tr>
              <tr><td>5</td><td>Mexico</td><td>2.6</td><td>S4-4</td></tr>
            </tbody>
          </table>
          <p>Примечательно: ближайший сосед Russia_1 в интегрированном пространстве — <strong>Italy</strong> (из другого кластера). Это обусловлено сочетанием похожей формальной защиты инвесторов (оба — низкие F2b) и стабильной динамики WGI.</p>
          <p><strong>Russia_2 → Кластер S4-4</strong> (снижающиеся). Ближайшие:</p>
          <table className={s.table}>
            <thead>
              <tr><th>#</th><th>Юрисдикция</th><th>Расстояние</th><th>Кластер</th></tr>
            </thead>
            <tbody>
              <tr><td>1</td><td>Mexico</td><td>4.2</td><td>S4-4</td></tr>
              <tr><td>2</td><td>Hungary</td><td>4.3</td><td>S4-4</td></tr>
              <tr><td>3</td><td>Austria</td><td>4.4</td><td>S4-4</td></tr>
              <tr><td>4</td><td>France</td><td>4.4</td><td>S4-5</td></tr>
              <tr><td>5</td><td>Peru</td><td>4.4</td><td>S4-1</td></tr>
            </tbody>
          </table>
          <p>Russia_2 остаётся более изолированной: расстояние до ближайшего 4.2 (vs 2.0 у Russia_1).</p>
        </section>

        <section id="stage4-comparison">
          <h3 className={s.h3}>6.7. Сравнение кластерных назначений через этапы</h3>
          <img src="/figures/s4_comparison_stages.png" alt="Сравнение этапов" className={s.figure} />
          <table className={s.table}>
            <thead>
              <tr><th>Объект</th><th>Этап I</th><th>Этап III</th><th>Этап IV</th><th>Интерпретация</th></tr>
            </thead>
            <tbody>
              <tr><td>Russia_1</td><td>A-6 (EM)</td><td>F5 (EM стабильные)</td><td><strong>S4-3 (EM растущие)</strong></td><td>Устойчиво в группе EM</td></tr>
              <tr><td>Russia_2</td><td>A-6 (EM)</td><td>F6 (снижающиеся)</td><td><strong>S4-4 (снижающиеся)</strong></td><td>Устойчиво в группе снижающихся</td></tr>
              <tr><td>Turkey</td><td>A-6</td><td>F3</td><td>S4-4</td><td>Из кластера России (I) → в снижающиеся</td></tr>
              <tr><td>China</td><td>A-6</td><td>F5</td><td>S4-3</td><td>Устойчиво рядом с Russia_1</td></tr>
              <tr><td>India</td><td>A-2</td><td>F5</td><td>S4-1</td><td>В Этапе III рядом с Russia_1, в Этапе IV — разошлись (из-за F2: India высокий, Russia низкий)</td></tr>
            </tbody>
          </table>
          <p>Этап IV разводит India и Russia_1, которые были близки в Этапах I–III: формальная защита инвесторов (F2) в India значительно выше. Это содержательно корректно — в интегрированном пространстве различие в правовых механизмах защиты становится значимым.</p>
        </section>

        <section id="stage4-conclusions">
          <h3 className={s.h3}>6.8. Промежуточные выводы Этапа IV</h3>
          <ol>
            <li><strong>Интеграция статики и динамики выявляет новые группировки.</strong> Russia_1 оказывается ближе к Italy и Spain (похожая формальная защита + стабильная динамика), чем к India (высокая защита, но другой правовой механизм).</li>
            <li><strong>Разделение Russia_1/Russia_2 устойчиво</strong> через все методы и все комбинации признаков.</li>
            <li><strong>MFA корректно балансирует блоки:</strong> Dim1 сбалансирована, а специфика каждого блока проявляется в последующих измерениях.</li>
            <li><strong>Silhouette ниже</strong> предыдущих этапов (0.12 vs 0.23–0.34). Это цена интеграции: больше измерений → менее чёткие границы. Для описательных целей кластеры остаются содержательно интерпретируемыми.</li>
            <li><strong>Включены все 48 юрисдикций</strong> (49 объектов с расщеплением России) — ранее исключённые Denmark, Finland, Italy, Sweden, Taiwan вошли в кластер S4-5 (развитые стабильные), что подтверждает предположение из Этапа I.</li>
          </ol>
        </section>

        <hr className={s.hr} />

        {/* ═══ 7. Сквозной анализ: позиция России ═══ */}
        <section id="russia">
          <h2 className={s.h2}>7. Сквозной анализ: позиция России</h2>
        </section>

        <section id="russia-stages">
          <h3 className={s.h3}>7.1. Россия через четыре этапа</h3>
          <img src="/figures/v3_stage_comparison.png" alt="Позиция России на трёх этапах, PCA" className={s.figure} />
          <table className={s.table}>
            <thead>
              <tr><th>Этап</th><th>Объект</th><th>Кластер</th><th>Ближайшие соседи</th><th>Интерпретация</th></tr>
            </thead>
            <tbody>
              <tr><td>I (статика)</td><td>Russia</td><td>A-6 (EM с низким WGI)</td><td>Turkey (1.94), Mexico (2.30), Peru (2.46), China (2.56)</td><td>По текущему «снимку» — развивающийся рынок</td></tr>
              <tr><td>II (+ тренд)</td><td>Russia</td><td>B-9 (конт. Европа)</td><td>Austria, Germany, France, Poland...</td><td>По характеру динамики WGI — ближе к европейским</td></tr>
              <tr><td>III (траектории)</td><td>Russia_1 (2009–2021)</td><td>F5 (EM стабильные)</td><td>India (1.71), Colombia (1.71), Thailand (1.83)</td><td>Слабоположительный тренд</td></tr>
              <tr><td>III (траектории)</td><td>Russia_2 (2022–2024)</td><td>F6 (снижающиеся)</td><td>Mexico (4.95), Brazil (5.63), South Africa (5.66)</td><td>Устойчивое снижение</td></tr>
              <tr><td>IV (MFA)</td><td>Russia_1</td><td>S4-3 (EM растущие)</td><td>Italy (2.0), China (2.3), Spain (2.4)</td><td>Статика + динамика: ближе к Южной Европе</td></tr>
              <tr><td>IV (MFA)</td><td>Russia_2</td><td>S4-4 (снижающиеся)</td><td>Mexico (4.2), Hungary (4.3), Austria (4.4)</td><td>Изолирована, экстремальный тренд</td></tr>
            </tbody>
          </table>
          <p><strong>Устойчивый результат через все этапы:</strong> Russia_1 и Russia_2 попадают в разные кластеры при любой комбинации признаков и методов (Этапы III и IV).</p>
          <p><strong>Новое наблюдение Этапа IV:</strong> интеграция статического профиля с динамикой сближает Russia_1 с Italy и Spain (похожие низкие F2b + стабильная динамика), тогда как в Этапах I–III ближайшими были Turkey, China, India. Это содержательно значимо: при учёте <em>всех</em> факторов одновременно юрисдикции с похожим правовым механизмом защиты оказываются ближе, чем юрисдикции с похожим уровнем WGI.</p>
        </section>

        <section id="russia-gap">
          <h3 className={s.h3}>7.2. Количественная мера разрыва</h3>
          <p>Евклидово расстояние между Russia_1 и Russia_2 в 12D стандартизированном пространстве:</p>
          <table className={s.table}>
            <thead>
              <tr><th>Метрика</th><th>Значение</th></tr>
            </thead>
            <tbody>
              <tr><td>Расстояние Russia_1 ↔ Russia_2</td><td><strong>6.693</strong></td></tr>
              <tr><td>Среднее попарное расстояние по выборке</td><td>4.498</td></tr>
              <tr><td>Медиана</td><td>4.161</td></tr>
              <tr><td>Перцентиль</td><td><strong>84.1%</strong></td></tr>
            </tbody>
          </table>
          <p>Два периода функционирования одной юрисдикции различаются больше, чем 84% пар <em>различных</em> юрисдикций.</p>
          <p>Russia_1 до ближайшего соседа (India): <strong>1.706</strong>. Russia_2 до ближайшего (Mexico): <strong>4.948</strong>. Russia_2 значительно более изолирована — её характеристики (3 точки, экстремальный наклон, 0% положительных лет) выделяют её из всех кластеров.</p>
        </section>

        <section id="russia-neighbors">
          <h3 className={s.h3}>7.3. Ближайшие соседи (Этап III)</h3>
          <p><strong>Russia_1:</strong></p>
          <table className={s.table}>
            <thead>
              <tr><th>#</th><th>Юрисдикция</th><th>Расстояние</th><th>Кластер</th></tr>
            </thead>
            <tbody>
              <tr><td>1</td><td>India</td><td>1.706</td><td>F5</td></tr>
              <tr><td>2</td><td>Colombia</td><td>1.714</td><td>F5</td></tr>
              <tr><td>3</td><td>Thailand</td><td>1.834</td><td>F5</td></tr>
              <tr><td>4</td><td>China</td><td>1.888</td><td>F5</td></tr>
              <tr><td>5</td><td>Peru</td><td>2.296</td><td>F5</td></tr>
            </tbody>
          </table>
          <p>Все 5 ближайших — из того же кластера F5.</p>
          <p><strong>Russia_2:</strong></p>
          <table className={s.table}>
            <thead>
              <tr><th>#</th><th>Юрисдикция</th><th>Расстояние</th><th>Кластер</th></tr>
            </thead>
            <tbody>
              <tr><td>1</td><td>Mexico</td><td>4.948</td><td>F6</td></tr>
              <tr><td>2</td><td>Brazil</td><td>5.633</td><td>F6</td></tr>
              <tr><td>3</td><td>South Africa</td><td>5.657</td><td>F6</td></tr>
              <tr><td>4</td><td>Hungary</td><td>5.914</td><td>F6</td></tr>
              <tr><td>5</td><td>Peru</td><td>6.624</td><td>F5</td></tr>
              <tr><td>6</td><td>Russia_1</td><td>6.693</td><td>F5</td></tr>
            </tbody>
          </table>
          <img src="/figures/final_russia_neighbors.png" alt="Соседи Russia_1 и Russia_2" className={s.figure} />
        </section>

        <section id="russia-profile">
          <h3 className={s.h3}>7.4. Профиль России: ключевые особенности</h3>
          <ol>
            <li><strong>Формальная защита инвесторов.</strong> Россия имеет аномально низкую ответственность директоров (F2b = 2 из 10 — 44-е место из 48) и низкое disclosure (F2a = 6 из 10). При этом доступность судебной защиты (F2c = 6 из 10) выше среднего по её кластеру.</li>
            <li><strong>Качество институциональной среды.</strong> WGI Composite = −1.04 (2024) — наиболее низкое значение в выборке из 48 юрисдикций. Россия — единственная юрисдикция с WGI Composite ниже −1.0.</li>
            <li><strong>Глубина рынка.</strong> Market cap/GDP = 24% — неглубокий рынок (при целевых 66% к 2030 г. по Указу Президента №309).</li>
            <li><strong>Динамика.</strong> До 2022 г. — слабоположительный тренд WGI (slope +0.013/год), с 50% лет показывающих рост. После 2022 г. — резкое ухудшение (slope −0.073/год), 0% лет с ростом.</li>
            <li><strong>Пограничное положение.</strong> Россия находится на границе между кластером развивающихся рынков и кластером континентальной Европы. Это означает, что опыт обеих групп может быть релевантен при формулировании рекомендаций.</li>
          </ol>
        </section>

        <hr className={s.hr} />

        {/* ═══ 8. Синтез и выводы ═══ */}
        <section id="synthesis">
          <h2 className={s.h2}>8. Синтез и выводы</h2>
        </section>

        <section id="synthesis-patterns">
          <h3 className={s.h3}>8.1. Основные паттерны, устойчивые через все этапы</h3>
          <ol>
            <li><strong>Правовая семья — значимый, но не абсолютный структурный фактор.</strong> 13 из 15 English law юрисдикций группируются вместе на всех этапах без явного включения этого признака. French law — наиболее гетерогенная группа (распределена по 5 кластерам).</li>
            <li><strong>Непрерывный градиент, а не дискретные группы.</strong> Silhouette scores 0.19–0.34 на всех этапах; DBSCAN не выявляет кластеров по плотности. Кластеры — инструмент описания, а не объективные границы.</li>
            <li><strong>Формальные правила ≠ правоприменение.</strong> India, Thailand (English law) имеют высокий F2 при отрицательном WGI. Switzerland — обратный пример: F2a=0, WGI среди высших. Оба вектора необходимы для полной характеристики.</li>
            <li><strong>Финансовые хабы — отдельная категория.</strong> Hong Kong, Singapore, Saudi Arabia объединены функциональной ролью рынка, а не институциональными характеристиками.</li>
          </ol>
        </section>

        <section id="synthesis-evolution">
          <h3 className={s.h3}>8.2. Эволюция подхода: чему учит каждый этап</h3>
          <table className={s.table}>
            <thead>
              <tr><th>Этап</th><th>Что показал</th><th>Новое знание</th><th>Ограничение</th></tr>
            </thead>
            <tbody>
              <tr><td>I. Статика</td><td>«Снимок» текущего положения</td><td>Россия — в кластере EM с Китаем, Турцией, Мексикой. Правовая семья — сильный предиктор</td><td>Не учитывает направление развития</td></tr>
              <tr><td>II. + Тренд</td><td>Направление изменений</td><td>Динамика — самостоятельное измерение. Россия по темпу изменений ближе к Европе</td><td>5 точек не ловят нелинейности. Silhouette упал</td></tr>
              <tr><td>III. Траектории</td><td>Форма развития, разрывы</td><td>Россия — две разные сущности до и после 2022. Feature-based {'>'} DTW {'>'} k-Shape</td><td>Только WGI, без F2 и F7</td></tr>
              <tr><td>IV. MFA</td><td>Интеграция статики и динамики</td><td>Russia_1 ближе к Южной Европе (Italy, Spain) при учёте всех факторов. Правовой механизм защиты становится значимым разделителем</td><td>Silhouette снижается до 0.12. Проклятие размерности</td></tr>
            </tbody>
          </table>
        </section>

        <section id="synthesis-russia">
          <h3 className={s.h3}>8.3. Россия: синтетическая оценка</h3>
          <ol>
            <li><strong>До 2022 г.</strong> Россия принадлежала к группе крупных развивающихся рынков со стабильными или слабо растущими институциональными оценками (India, China, Indonesia, Colombia). По полному институциональному профилю (включая F2) — кластер EM с низким WGI и неглубоким рынком. По динамике — ближе к европейским юрисдикциям с умеренным снижением.</li>
            <li><strong>После 2022 г.</strong> произошёл структурный сдвиг: Russia_2 перемещается в группу юрисдикций с устойчивым снижением (Brazil, Mexico, South Africa, Hungary). Расстояние между двумя периодами (6.693) превышает 84% всех попарных расстояний — это не постепенное изменение, а качественный переход.</li>
            <li><strong>Интегрированный анализ (Этап IV)</strong> показывает, что при совместном учёте формальной защиты, рыночной структуры и динамики Russia_1 оказывается ближе к <strong>Italy</strong> и <strong>Spain</strong> — юрисдикциям с похожим уровнем формальной защиты инвесторов и стабильной динамикой WGI. Это отличается от Этапов I–III, где ближайшими были Turkey, China, India.</li>
            <li><strong>Для целей сравнительного анализа</strong> наиболее релевантны:
              <ul>
                <li><strong>Первый круг (статика):</strong> Turkey, Mexico, Peru, China, Indonesia (кластер A-6) — по текущему институциональному профилю.</li>
                <li><strong>Второй круг (интегрированный):</strong> Italy, Spain, China, Peru (ближайшие в MFA-пространстве для Russia_1) — при учёте всех факторов.</li>
                <li><strong>Для анализа динамики:</strong> India, Colombia, Thailand (ближайшие соседи Russia_1 по траектории до 2022 г.).</li>
                <li><strong>Russia_2:</strong> Mexico, Hungary, Austria — ближайшие в MFA-пространстве для периода после 2022 г.</li>
              </ul>
            </li>
          </ol>
        </section>

        <section id="synthesis-limitations">
          <h3 className={s.h3}>8.4. Ограничения исследования</h3>
          <ol>
            <li><strong>Неполный набор факторов.</strong> Качественные институциональные факторы (Ф3 Private enforcement, Ф8–Ф12) не собраны и не включены. Их добавление может изменить группировки. Особенно критичен Ф8 (концентрация владения) — он непосредственно связан с правовой семьёй и моделью корпоративного управления.</li>
            <li><strong>Перцептивность WGI.</strong> Индексы WGI — экспертные оценки, а не прямые измерения. Глобальный тренд снижения (37 из 48 юрисдикций) может отражать изменение методологии или настроений экспертных панелей. Это не обесценивает анализ, но требует осторожности при интерпретации абсолютных значений.</li>
            <li><strong>Малый размер выборки.</strong> 43–49 объектов в 6–12-мерном пространстве — граничный случай для кластерного анализа. Silhouette scores невысоки отчасти из-за проклятия размерности.</li>
            <li><strong>Асимметрия сегментов России.</strong> Russia_1 содержит 13 точек, Russia_2 — 3. Признаки, извлечённые из 3 наблюдений, менее надёжны.</li>
            <li><strong>Разрыв Этапов I и III.</strong> Этап I использует F2 + WGI + F7; Этап III — только WGI-траектории. Нет интегрированной кластеризации, объединяющей статический профиль с динамикой. Это потенциальное направление дальнейшего анализа.</li>
            <li><strong>Исключение 5 юрисдикций.</strong> Denmark, Finland, Italy, Sweden, Taiwan не вошли в кластеризацию Этапов I–II. Все 5 по доступным признакам тяготеют к развитым кластерам — их исключение не влияет на позицию России, но обедняет представительство DM-группы.</li>
          </ol>
        </section>

        <section id="synthesis-stability">
          <h3 className={s.h3}>8.5. Сравнительная устойчивость результатов</h3>
          <img src="/figures/v3_cluster_stability.png" alt="Стабильность кластеров: silhouette по этапам" className={s.figure} />
          <table className={s.table}>
            <thead>
              <tr><th>Результат</th><th>Устойчив?</th><th>Этапы</th><th>Комментарий</th></tr>
            </thead>
            <tbody>
              <tr><td>Россия в кластере EM (статика)</td><td><strong>Да</strong></td><td>I, II</td><td>Устойчив при разных k (5–9) и методах linkage</td></tr>
              <tr><td>Правовая семья → кластеры</td><td><strong>Да</strong></td><td>I, II, III, IV</td><td>English law группируется вместе на всех этапах</td></tr>
              <tr><td>Russia_1 ≠ Russia_2</td><td><strong>Да</strong></td><td>III, IV</td><td>Разделение устойчиво при k=4, k=6, MFA, простой конкатенации</td></tr>
              <tr><td>Россия ↔ конт. Европа (динамика)</td><td><strong>Частично</strong></td><td>II</td><td>Зависит от включения тренда; обусловлено <em>темпом</em>, не уровнем</td></tr>
              <tr><td>Russia_1 ↔ Italy/Spain (MFA)</td><td><strong>Новый</strong></td><td>IV</td><td>Обусловлено сочетанием похожих F2 + стабильной динамики</td></tr>
              <tr><td>Конкретный состав малых кластеров</td><td><strong>Нет</strong></td><td>III</td><td>F3 (Chile+Turkey) и F4 (Egypt+Hong Kong) — артефакты k=6</td></tr>
            </tbody>
          </table>
        </section>

        <section id="synthesis-next">
          <h3 className={s.h3}>8.6. Направления дальнейшего анализа</h3>
          <ol>
            <li><strong>Расширение набора факторов.</strong> Сбор и формализация качественных факторов (Ф3 Private enforcement, Ф8–Ф12) с последующим переходом к Gower distance или k-prototypes для смешанных данных.</li>
            <li><strong>Fuzzy clustering.</strong> Учитывая непрерывный характер градиента (silhouette 0.12–0.34 на всех этапах), soft clustering (fuzzy c-means, Gaussian mixture models) может дать более адекватные результаты, чем жёсткое разбиение — каждая юрисдикция получит степень принадлежности к нескольким кластерам.</li>
            <li><strong>Обогащение анализа России.</strong> Для двух режимов (Russia_1, Russia_2) — привлечение дополнительных данных (потоки капитала, активность IPO, оценки инвестиционного климата) для валидации структурного разрыва «за пределами» WGI.</li>
          </ol>
        </section>

        <hr className={s.hr} />

        {/* ═══ Приложения ═══ */}
        <section id="appendices">
          <h2 className={s.h2}>Приложения</h2>
        </section>

        <section id="appendix-a">
          <h3 className={s.h3}>A. Визуализации</h3>
          <p><strong>Этап I — Статическая кластеризация:</strong></p>
          <table className={s.table}>
            <thead>
              <tr><th>Файл</th><th>Содержание</th></tr>
            </thead>
            <tbody>
              <tr><td><code className={s.code}>distributions_boxplots.png</code></td><td>Распределения исходных признаков</td></tr>
              <tr><td><code className={s.code}>correlation_matrix_pearson.png</code></td><td>Корреляционная матрица (Pearson)</td></tr>
              <tr><td><code className={s.code}>correlation_matrix_spearman.png</code></td><td>Корреляционная матрица (Spearman)</td></tr>
              <tr><td><code className={s.code}>clustering_A_dendrogram.png</code></td><td>Дендрограмма, Вариант A</td></tr>
              <tr><td><code className={s.code}>silhouette_scores.png</code></td><td>Silhouette score vs k</td></tr>
              <tr><td><code className={s.code}>cluster_profiles_heatmap.png</code></td><td>Профили кластеров (стандартизированные)</td></tr>
              <tr><td><code className={s.code}>pca_clusters.png</code></td><td>PCA-проекция с кластерами</td></tr>
              <tr><td><code className={s.code}>tsne_best_annotated.png</code></td><td>t-SNE проекция (perplexity=12)</td></tr>
              <tr><td><code className={s.code}>tsne_perplexity_grid.png</code></td><td>Сетка t-SNE: 6 perplexity x 3 seeds</td></tr>
              <tr><td><code className={s.code}>dbscan_results.png</code></td><td>Сравнение Ward / DBSCAN / Legal origin</td></tr>
              <tr><td><code className={s.code}>mktcap_structure.png</code></td><td>Структура MktCap/GDP</td></tr>
            </tbody>
          </table>
          <p><strong>Этап II — Линейная динамика:</strong></p>
          <table className={s.table}>
            <thead>
              <tr><th>Файл</th><th>Содержание</th></tr>
            </thead>
            <tbody>
              <tr><td><code className={s.code}>wgi_trajectories.png</code></td><td>Траектории WGI 2004–2024</td></tr>
              <tr><td><code className={s.code}>clustering_B_dendrogram.png</code></td><td>Дендрограмма, Вариант B</td></tr>
              <tr><td><code className={s.code}>clustering_B_profiles.png</code></td><td>Профили кластеров, Вариант B</td></tr>
              <tr><td><code className={s.code}>clustering_B_pca.png</code></td><td>PCA + t-SNE, Вариант B</td></tr>
              <tr><td><code className={s.code}>clustering_AB_comparison.png</code></td><td>Сравнение вариантов A и B</td></tr>
            </tbody>
          </table>
          <p><strong>Этап III — Траектории:</strong></p>
          <table className={s.table}>
            <thead>
              <tr><th>Файл</th><th>Содержание</th></tr>
            </thead>
            <tbody>
              <tr><td><code className={s.code}>traj_overview.png</code></td><td>Обзор годовых траекторий WGI</td></tr>
              <tr><td><code className={s.code}>traj_breakpoints.png</code></td><td>Траектории с обнаруженными разрывами</td></tr>
              <tr><td><code className={s.code}>traj_dtw_clustering.png</code></td><td>DTW-кластеризация</td></tr>
              <tr><td><code className={s.code}>traj_dtw_granular.png</code></td><td>DTW-кластеризация (гранулярная)</td></tr>
              <tr><td><code className={s.code}>traj_kshape_clustering.png</code></td><td>k-Shape кластеризация</td></tr>
              <tr><td><code className={s.code}>traj_feature_clustering.png</code></td><td>Feature-based кластеризация</td></tr>
              <tr><td><code className={s.code}>traj_comparison_tsne.png</code></td><td>Сравнение DTW / k-Shape / Feature</td></tr>
              <tr><td><code className={s.code}>traj_russia_break.png</code></td><td>Структурный разрыв России</td></tr>
              <tr><td><code className={s.code}>final_dendrogram.png</code></td><td>Дендрограмма финальной кластеризации</td></tr>
              <tr><td><code className={s.code}>final_silhouette_k.png</code></td><td>Silhouette vs k</td></tr>
              <tr><td><code className={s.code}>final_silhouette_entities.png</code></td><td>Силуэт по объектам</td></tr>
              <tr><td><code className={s.code}>final_profiles_heatmap.png</code></td><td>Профили кластеров</td></tr>
              <tr><td><code className={s.code}>final_pca.png</code></td><td>PCA финальная</td></tr>
              <tr><td><code className={s.code}>final_tsne.png</code></td><td>t-SNE финальная</td></tr>
              <tr><td><code className={s.code}>final_trajectories_by_cluster.png</code></td><td>Траектории по кластерам</td></tr>
              <tr><td><code className={s.code}>final_russia_neighbors.png</code></td><td>Соседи Russia_1 и Russia_2</td></tr>
            </tbody>
          </table>
          <p><strong>Этап IV — MFA:</strong></p>
          <table className={s.table}>
            <thead>
              <tr><th>Файл</th><th>Содержание</th></tr>
            </thead>
            <tbody>
              <tr><td><code className={s.code}>s4_silhouette_k.png</code></td><td>Silhouette vs k (MFA и простая конкатенация)</td></tr>
              <tr><td><code className={s.code}>s4_dendrogram.png</code></td><td>Дендрограмма MFA-кластеризации</td></tr>
              <tr><td><code className={s.code}>s4_pca.png</code></td><td>PCA-проекция MFA-пространства</td></tr>
              <tr><td><code className={s.code}>s4_profiles_heatmap.png</code></td><td>Профили кластеров (z-scores)</td></tr>
              <tr><td><code className={s.code}>s4_russia_neighbors.png</code></td><td>Ближайшие соседи Russia_1 и Russia_2</td></tr>
              <tr><td><code className={s.code}>s4_tsne.png</code></td><td>t-SNE MFA-пространства</td></tr>
              <tr><td><code className={s.code}>s4_mfa_block_contributions.png</code></td><td>Вклад блоков в MFA-измерения</td></tr>
              <tr><td><code className={s.code}>s4_comparison_stages.png</code></td><td>Сравнение кластерных назначений I / III / IV</td></tr>
            </tbody>
          </table>
          <p><strong>Дополнительные (v3):</strong></p>
          <table className={s.table}>
            <thead>
              <tr><th>Файл</th><th>Содержание</th></tr>
            </thead>
            <tbody>
              <tr><td><code className={s.code}>v3_radar_russia.png</code></td><td>Радар: Россия vs кластер vs выборка</td></tr>
              <tr><td><code className={s.code}>v3_parallel_coordinates.png</code></td><td>Параллельные координаты (43 юрисдикции)</td></tr>
              <tr><td><code className={s.code}>v3_stage_comparison.png</code></td><td>Позиция России на трёх этапах (PCA)</td></tr>
              <tr><td><code className={s.code}>v3_cluster_stability.png</code></td><td>Silhouette по этапам и k</td></tr>
              <tr><td><code className={s.code}>v3_russia_trajectory_annotated.png</code></td><td>Траектория России с PELT и сравнениями</td></tr>
              <tr><td><code className={s.code}>v3_excluded_jurisdictions.png</code></td><td>Исключённые юрисдикции vs кластеры</td></tr>
            </tbody>
          </table>
        </section>

        <section id="appendix-b">
          <h3 className={s.h3}>B. Данные</h3>
          <table className={s.table}>
            <thead>
              <tr><th>Файл</th><th>Содержание</th></tr>
            </thead>
            <tbody>
              <tr><td><code className={s.code}>master_factors.csv</code></td><td>Master table: 48 юрисдикций x 66 параметров</td></tr>
              <tr><td><code className={s.code}>cluster_assignments.csv</code></td><td>Кластерные принадлежности (варианты A и B)</td></tr>
              <tr><td><code className={s.code}>trajectory_panel.csv</code></td><td>Годовая панель WGI Composite (2009–2024)</td></tr>
              <tr><td><code className={s.code}>trajectory_cluster_assignments.csv</code></td><td>Кластерные принадлежности (DTW, k-Shape, feature)</td></tr>
              <tr><td><code className={s.code}>final_cluster_assignments.csv</code></td><td>Финальная кластеризация (49 объектов)</td></tr>
              <tr><td><code className={s.code}>final_features.csv</code></td><td>Извлечённые признаки траекторий (49 объектов)</td></tr>
              <tr><td><code className={s.code}>stage4_cluster_assignments.csv</code></td><td>Кластерные принадлежности Этап IV (MFA и простая конкатенация)</td></tr>
              <tr><td><code className={s.code}>stage4_features.csv</code></td><td>Признаки MFA (49 объектов, 9 признаков с блоковыми метками)</td></tr>
            </tbody>
          </table>
        </section>

        <section id="appendix-c">
          <h3 className={s.h3}>C. Скрипты</h3>
          <table className={s.table}>
            <thead>
              <tr><th>Файл</th><th>Назначение</th></tr>
            </thead>
            <tbody>
              <tr><td><code className={s.code}>build_master_table.py</code></td><td>Сборка master table из исходных датасетов</td></tr>
              <tr><td><code className={s.code}>correlation_analysis.py</code></td><td>Корреляционный анализ, распределения</td></tr>
              <tr><td><code className={s.code}>clustering.py</code></td><td>Кластеризация Этап I</td></tr>
              <tr><td><code className={s.code}>clustering_with_dynamics.py</code></td><td>Кластеризация Этап II</td></tr>
              <tr><td><code className={s.code}>clustering_alt.py</code></td><td>DBSCAN, t-SNE</td></tr>
              <tr><td><code className={s.code}>clustering_trajectories.py</code></td><td>DTW, k-Shape, feature-based</td></tr>
              <tr><td><code className={s.code}>clustering_final.py</code></td><td>Финальная кластеризация с расщеплением России</td></tr>
              <tr><td><code className={s.code}>analyze_mktcap_structure.py</code></td><td>Анализ структуры MktCap/GDP</td></tr>
              <tr><td><code className={s.code}>clustering_stage4.py</code></td><td>Этап IV: MFA-кластеризация (интеграция статики и динамики)</td></tr>
              <tr><td><code className={s.code}>verification_v3.py</code></td><td>Верификация и дополнительный анализ (v3)</td></tr>
            </tbody>
          </table>
        </section>

        <section id="appendix-d">
          <h3 className={s.h3}>D. Источники данных</h3>
          <table className={s.table}>
            <thead>
              <tr><th>Источник</th><th>Параметры</th><th>Год</th><th>Покрытие</th></tr>
            </thead>
            <tbody>
              <tr><td>Doing Business 2020 (World Bank)</td><td>F2a, F2b, F2c</td><td>01.05.2019</td><td>190 экономик</td></tr>
              <tr><td>WGI (World Bank)</td><td>F4, F5, F6</td><td>2004–2024</td><td>214 экономик</td></tr>
              <tr><td>WDI (World Bank)</td><td>F7, Fx</td><td>2017–2024</td><td>43–47 из 48</td></tr>
              <tr><td>La Porta et al. (LLSV)</td><td>F1, ASDI</td><td>1998/2008</td><td>72 экономики</td></tr>
            </tbody>
          </table>
        </section>

        <section id="appendix-e">
          <h3 className={s.h3}>E. Рецензентский чеклист</h3>
          <table className={s.table}>
            <thead>
              <tr><th>Проверка</th><th>Результат</th></tr>
            </thead>
            <tbody>
              <tr><td>Данные: корректность загрузки и мерджа</td><td>✓ Подтверждено</td></tr>
              <tr><td>WGI Composite для России 2024 = −1.04</td><td>✓ Подтверждено (−1.042696)</td></tr>
              <tr><td>5 исключённых юрисдикций</td><td>✓ Подтверждено</td></tr>
              <tr><td>Silhouette scores (все этапы)</td><td>✓ Воспроизведены</td></tr>
              <tr><td>Russia_1 → F5, Russia_2 → F6</td><td>✓ Подтверждено</td></tr>
              <tr><td>Расстояние Russia_1 ↔ Russia_2 = 6.693</td><td>✓ Подтверждено (6.6926)</td></tr>
              <tr><td>Перцентиль расстояния = 84%</td><td>✓ Подтверждено (84.2%)</td></tr>
              <tr><td>Чувствительность k=4 vs k=6</td><td>✓ Russia_1/Russia_2 разделены при обоих k</td></tr>
              <tr><td>Gower distance (с правовой семьёй)</td><td>✓ Разделение устойчиво</td></tr>
              <tr><td><code className={s.code}>merged_quantitative_factors.csv</code>: Qatar</td><td>⚠ Обнаружена ошибка (1000x). В <code className={s.code}>master_factors.csv</code> корректно</td></tr>
            </tbody>
          </table>
        </section>

      </article>
    </div>
  )
}
