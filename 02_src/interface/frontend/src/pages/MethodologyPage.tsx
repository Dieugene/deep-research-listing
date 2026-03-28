import { useEffect, useRef, useState, useCallback } from 'react'
import s from './MethodologyPage.module.css'

/* ── Section definitions for sidebar nav ─────────────────── */
interface NavItem {
  id: string
  label: string
  level: 'h2' | 'h3'
  num?: string
}

const NAV_ITEMS: NavItem[] = [
  { id: 'about', label: 'О проекте', level: 'h2' },

  { id: 'coverage', label: 'Охват исследования', level: 'h2', num: '1' },
  { id: 'coverage-jurisdictions', label: 'Юрисдикции', level: 'h3', num: '1.1' },
  { id: 'coverage-venues', label: 'Площадки', level: 'h3', num: '1.2' },
  { id: 'coverage-cells', label: 'Ячейки исследования', level: 'h3', num: '1.3' },

  { id: 'architecture', label: 'Архитектура сбора данных', level: 'h2', num: '2' },
  { id: 'architecture-levels', label: 'Уровни исследования', level: 'h3', num: '2.1' },
  { id: 'architecture-parallel', label: 'Parallel API', level: 'h3', num: '2.2' },
  { id: 'architecture-llm', label: 'LLM-обработка', level: 'h3', num: '2.3' },

  { id: 'process', label: 'Процесс сбора и обработки', level: 'h2', num: '3' },
  { id: 'process-l1', label: 'Level 1 — Юрисдикция', level: 'h3', num: '3.1' },
  { id: 'process-l2', label: 'Level 2 — Площадка', level: 'h3', num: '3.2' },
  { id: 'process-l3', label: 'Level 3 — Ячейка', level: 'h3', num: '3.3' },
  { id: 'process-phase2', label: 'Phase 2 — Параметры', level: 'h3', num: '3.4' },
  { id: 'process-l4', label: 'Level 4 — Анализ', level: 'h3', num: '3.5' },

  { id: 'matrix', label: 'Матрица жизненного цикла', level: 'h2', num: '4' },
  { id: 'matrix-structure', label: 'Структура матрицы', level: 'h3', num: '4.1' },
  { id: 'matrix-build', label: 'Построение матрицы', level: 'h3', num: '4.2' },

  { id: 'sources', label: 'Источники и верификация', level: 'h2', num: '5' },
  { id: 'sources-types', label: 'Типология источников', level: 'h3', num: '5.1' },
  { id: 'sources-excerpts', label: 'Выдержки', level: 'h3', num: '5.2' },
  { id: 'sources-confidence', label: 'Уровень уверенности', level: 'h3', num: '5.3' },
  { id: 'sources-stats', label: 'Количественные показатели', level: 'h3', num: '5.4' },

  { id: 'translation', label: 'Перевод и локализация', level: 'h2', num: '6' },
  { id: 'translation-what', label: 'Что переводится', level: 'h3', num: '6.1' },
  { id: 'translation-display', label: 'Принцип отображения', level: 'h3', num: '6.2' },

  { id: 'quality', label: 'Контроль качества', level: 'h2', num: '7' },
  { id: 'quality-validation', label: 'Валидация данных', level: 'h3', num: '7.1' },
  { id: 'quality-idempotent', label: 'Идемпотентность', level: 'h3', num: '7.2' },
  { id: 'quality-atomic', label: 'Атомарная запись', level: 'h3', num: '7.3' },

  { id: 'roadmap', label: 'Направления развития', level: 'h2', num: '8' },
  { id: 'roadmap-data', label: 'Доп. данные для отображения', level: 'h3', num: '8.1' },
  { id: 'roadmap-extensions', label: 'Потенциальные расширения', level: 'h3', num: '8.2' },
  { id: 'roadmap-institutional', label: 'Институциональные факторы', level: 'h3', num: '8.3' },

  { id: 'tech', label: 'Техническая архитектура', level: 'h2', num: '9' },
  { id: 'tech-stack', label: 'Стек', level: 'h3', num: '9.1' },
  { id: 'tech-pipeline', label: 'Порядок запуска', level: 'h3', num: '9.2' },
]

export default function MethodologyPage() {
  const [activeId, setActiveId] = useState<string>('about')
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
        // Find the topmost visible entry
        const visible = entries.filter((e) => e.isIntersecting)
        if (visible.length > 0) {
          // Pick the one closest to the top
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
        <h1 className={s.pageTitle}>Методология исследования</h1>

        {/* ═══ О проекте ═══ */}
        <h2 id="about" className={s.h2}>О проекте</h2>
        <p>
          Listing Research — база данных требований к листингу ценных бумаг на биржах мира.
          Проект собирает, структурирует и анализирует регуляторные требования к допуску,
          поддержанию, приостановке и исключению ценных бумаг из листинга.
        </p>
        <p>
          Данные собираются автоматизированным пайплайном на основе deep research AI (Parallel API)
          с последующей постобработкой, структурированием и переводом.
        </p>

        <hr className={s.hr} />

        {/* ═══ 1. Охват исследования ═══ */}
        <h2 id="coverage" className={s.h2}>1. Охват исследования</h2>

        <h3 id="coverage-jurisdictions" className={s.h3}>1.1. Юрисдикции</h3>
        <p>Исследование охватывает юрисдикции с организованными рынками ценных бумаг. На текущем этапе обработаны:</p>
        <table className={s.table}>
          <thead>
            <tr>
              <th>Юрисдикция</th>
              <th>Правовая семья</th>
              <th>Регулятор</th>
              <th>Площадки</th>
            </tr>
          </thead>
          <tbody>
            <tr><td>Австралия</td><td>Common law</td><td>ASX</td><td>4</td></tr>
            <tr><td>Великобритания</td><td>Common law</td><td>FCA</td><td>3</td></tr>
            <tr><td>Германия</td><td>Civil law</td><td>Deutsche Boerse AG</td><td>5</td></tr>
            <tr><td>Гонконг</td><td>Common law</td><td>SEHK</td><td>2</td></tr>
            <tr><td>Россия</td><td>Civil law</td><td>Банк России</td><td>—</td></tr>
            <tr><td>Сингапур</td><td>Common law</td><td>SGX-ST</td><td>1</td></tr>
            <tr><td>Франция</td><td>Civil law</td><td>Euronext Paris</td><td>5</td></tr>
          </tbody>
        </table>
        <p>Перечень юрисдикций расширяется по мере продвижения исследования.</p>

        <h3 id="coverage-venues" className={s.h3}>1.2. Площадки</h3>
        <p>
          20 площадок, включая регулируемые рынки (Regulated Markets), многосторонние торговые системы (MTF)
          и рынки, регулируемые биржей (Exchange Regulated Markets).
        </p>

        <h3 id="coverage-cells" className={s.h3}>1.3. Ячейки исследования</h3>
        <p>
          Минимальная единица исследования — <strong>ячейка</strong> (cell): пересечение площадки,
          тира листинга и класса инструмента.
        </p>
        <p>Четыре класса инструментов:</p>
        <ul>
          <li><strong>equity</strong> — акции</li>
          <li><strong>bond</strong> — облигации</li>
          <li><strong>fund</strong> — фонды и ETF</li>
          <li><strong>depositary_receipt</strong> — депозитарные расписки</li>
        </ul>
        <p>Всего: <strong>~105 ячеек</strong> по всем юрисдикциям.</p>

        <hr className={s.hr} />

        {/* ═══ 2. Архитектура сбора данных ═══ */}
        <h2 id="architecture" className={s.h2}>2. Архитектура сбора данных</h2>

        <h3 id="architecture-levels" className={s.h3}>2.1. Уровни исследования</h3>
        <p>Данные собираются на четырёх уровнях, каждый из которых отвечает на свой класс вопросов:</p>
        <table className={s.table}>
          <thead>
            <tr>
              <th>Уровень</th>
              <th>Объект</th>
              <th>Что исследуется</th>
              <th>Источник</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>L1</strong></td>
              <td>Юрисдикция</td>
              <td>Регуляторная архитектура, институциональный фреймворк, перечень площадок</td>
              <td>Parallel API (pro)</td>
            </tr>
            <tr>
              <td><strong>L2</strong></td>
              <td>Площадка</td>
              <td>Структура площадки: тиры, сегменты, покрытие инструментов</td>
              <td>Parallel API (pro)</td>
            </tr>
            <tr>
              <td><strong>L3</strong></td>
              <td>Ячейка</td>
              <td>Детальные требования по трём фазам: допуск (3A), поддержание/приостановка/исключение (3B), мониторинг и enforcement (3C)</td>
              <td>Parallel API (pro)</td>
            </tr>
            <tr>
              <td><strong>Phase 2</strong></td>
              <td>Ячейка</td>
              <td>Извлечение количественных параметров из контента L3</td>
              <td>LLM (gpt-5)</td>
            </tr>
            <tr>
              <td><strong>L4</strong></td>
              <td>Юрисдикция</td>
              <td>Аналитика: проблемы, противоречия, реформы, параметры как инструменты</td>
              <td>Parallel API (pro)</td>
            </tr>
          </tbody>
        </table>

        <h3 id="architecture-parallel" className={s.h3}>2.2. Parallel API</h3>
        <p>
          Parallel API — инструмент глубокого исследования (deep research), который автономно ищет
          информацию в интернете, анализирует найденные документы и формирует структурированный ответ.
        </p>
        <p>Для каждого запроса API возвращает:</p>
        <ul>
          <li><strong>content</strong> — структурированный ответ (текст или JSON)</li>
          <li><strong>basis[]</strong> — массив обоснований: для каждой секции ответа — reasoning (логика рассуждения), citations (ссылки на документы) и excerpts (выдержки из документов)</li>
          <li><strong>confidence</strong> — уровень уверенности (high / medium / low)</li>
        </ul>
        <p>
          Excerpts — это прямые цитаты из найденных документов, на которых основаны выводы.
          Они позволяют верифицировать каждое утверждение.
        </p>

        <h3 id="architecture-llm" className={s.h3}>2.3. LLM-обработка</h3>
        <p>
          Для задач, не требующих deep research (извлечение параметров, переводы, классификация),
          используются модели LLM:
        </p>
        <table className={s.table}>
          <thead>
            <tr><th>Модель</th><th>Задачи</th></tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>gpt-5</strong> (SMART)</td>
              <td>Извлечение параметров из текста (Phase 2), аналитика L4</td>
            </tr>
            <tr>
              <td><strong>gpt-5-mini</strong> (FAST)</td>
              <td>Переводы, классификация типов источников, распределение санкций по фазам матрицы</td>
            </tr>
          </tbody>
        </table>
        <p>
          LLM не используется для задач, решаемых алгоритмически (нормализация, очистка артефактов, маппинг секций).
        </p>

        <hr className={s.hr} />

        {/* ═══ 3. Процесс сбора и обработки ═══ */}
        <h2 id="process" className={s.h2}>3. Процесс сбора и обработки</h2>

        <h3 id="process-l1" className={s.h3}>3.1. Level 1 — Юрисдикция</h3>
        <p><strong>Три запроса к Parallel API:</strong></p>
        <table className={s.table}>
          <thead>
            <tr><th>Запрос</th><th>Что исследуется</th><th>Формат ответа</th></tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>1A</strong></td>
              <td>Регуляторная архитектура: кто регулирует листинг, какова правовая основа, как устроен процесс допуска</td>
              <td>Свободный текст</td>
            </tr>
            <tr>
              <td><strong>1B</strong></td>
              <td>Институциональный фреймворк: качественные факторы, влияющие на листинг (судебная система, корпоративное управление, защита инвесторов)</td>
              <td>JSON с 3 секциями</td>
            </tr>
            <tr>
              <td><strong>1C</strong></td>
              <td>Перечень площадок: какие биржи и торговые системы существуют, их типы, покрытие инструментов</td>
              <td>JSON с массивом venues</td>
            </tr>
          </tbody>
        </table>
        <p><strong>Постобработка:</strong></p>
        <ol>
          <li>Агрегация результатов в <code className={s.code}>jurisdiction_card.json</code> — единую карточку юрисдикции</li>
          <li>Извлечение источников и выдержек из <code className={s.code}>basis[]</code></li>
          <li>Классификация источников по типу документа</li>
          <li>Очистка артефактов в выдержках</li>
          <li>Перевод примечаний на русский язык</li>
        </ol>

        <h3 id="process-l2" className={s.h3}>3.2. Level 2 — Площадка</h3>
        <p><strong>Один запрос к Parallel API на площадку:</strong></p>
        <p>
          Исследует структуру площадки: тиры листинга, сегменты, покрытие инструментов, архитектуру листинга.
          Ответ — JSON со списком тиров.
        </p>
        <p><strong>Постобработка:</strong></p>
        <ol>
          <li>Формирование <code className={s.code}>venue_card.json</code> — карточки площадки</li>
          <li>Формирование <code className={s.code}>cells_list.json</code> — перечня ячеек (venue x tier x instrument_class)</li>
          <li>Извлечение источников и выдержек</li>
          <li>Нормализация типа площадки (<code className={s.code}>venue_type</code>)</li>
        </ol>

        <h3 id="process-l3" className={s.h3}>3.3. Level 3 — Ячейка (детальные требования)</h3>
        <p><strong>Три запроса на каждую комбинацию venue x instrument_class:</strong></p>
        <table className={s.table}>
          <thead>
            <tr><th>Запрос</th><th>Фаза</th><th>Секции контента</th></tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>3A</strong></td>
              <td>Допуск</td>
              <td>admission_overview, eligibility_requirements, instrument_requirements, sponsor_and_infrastructure, restrictions_and_lock_ups, special_regimes, procedure_and_timeline, disclosure_at_admission</td>
            </tr>
            <tr>
              <td><strong>3B</strong></td>
              <td>Поддержание, приостановка, исключение</td>
              <td>continuing_obligations (4 подсекции), suspension (4 подсекции), delisting_compulsory (5 подсекций), delisting_voluntary (3 подсекции), terminology</td>
            </tr>
            <tr>
              <td><strong>3C</strong></td>
              <td>Мониторинг и enforcement</td>
              <td>monitoring_regime (4 подсекции), sanctions (4 подсекции), enforcement_practice (2 подсекции)</td>
            </tr>
          </tbody>
        </table>
        <p>
          Parallel API возвращает данные на уровне venue x instrument_class (например, «LSE Main Market / equity»).
          Один ответ может содержать данные по нескольким тирам (например, «Equity Shares (Commercial Companies)»
          и «Equity Shares (International Companies)»).
        </p>
        <p><strong>Постобработка:</strong></p>
        <ol>
          <li><strong>Дезагрегация по тирам:</strong> Ответ Parallel содержит массив <code className={s.code}>tiers[]</code>. LLM маппит названия тиров на идентификаторы ячеек (cell_id) из cells_list.json. Контент каждого тира сохраняется в отдельную cell-директорию.</li>
          <li><strong>Валидация:</strong> Каждый файл проверяется на полноту (completeness_score), соответствие скоупу, наличие источников. Присваивается статус: green / yellow / red.</li>
          <li><strong>Извлечение источников и выдержек</strong> из basis[].</li>
          <li><strong>Классификация типов источников</strong> и исправление заголовков «Fetched web page».</li>
          <li><strong>Очистка артефактов</strong> в выдержках.</li>
          <li><strong>Построение матрицы 4x5</strong> — контент распределяется по ячейкам матрицы жизненного цикла (см. раздел 4).</li>
          <li><strong>Перевод описаний</strong> секций на русский язык.</li>
        </ol>

        <h3 id="process-phase2" className={s.h3}>3.4. Phase 2 — Извлечение параметров</h3>
        <p>На основе контента L3 (3A/3B/3C) извлекаются количественные параметры листинга:</p>
        <table className={s.table}>
          <thead>
            <tr><th>Этап</th><th>Модель</th><th>Что делает</th></tr>
          </thead>
          <tbody>
            <tr><td>Pass 1</td><td>gpt-5</td><td>Определяет, какие из стандартных параметров (П01–П23) применимы к данной группе ячеек</td></tr>
            <tr><td>Pass 2</td><td>gpt-5</td><td>Извлекает конкретные значения параметров для каждой ячейки</td></tr>
            <tr><td>Перевод</td><td>gpt-5-mini</td><td>Переводит значения и метки параметров на русский</td></tr>
            <tr><td>Section keys</td><td>Алгоритм</td><td>Привязывает параметры к секциям контента</td></tr>
            <tr><td>Normalize</td><td>Алгоритм</td><td>Нормализует идентификаторы параметров к кириллице (П01, П02, ...)</td></tr>
          </tbody>
        </table>
        <p>
          <strong>Стандартные параметры (П01–П23):</strong>
        </p>
        <p>
          Набор из 23 параметров, покрывающих ключевые количественные требования листинга: free float,
          минимальная капитализация, количество акционеров, аудиторские стандарты, корпоративное управление, и т.д.
        </p>
        <p>
          Помимо стандартных, Parallel API может обнаружить дополнительные параметры (ADDITIONAL_1, ADDITIONAL_2, ...),
          специфичные для конкретной площадки.
        </p>

        <h3 id="process-l4" className={s.h3}>3.5. Level 4 — Регуляторный анализ</h3>
        <p><strong>Один запрос на юрисдикцию</strong> — аналитический обзор регуляторного фреймворка:</p>
        <table className={s.table}>
          <thead>
            <tr><th>Секция</th><th>Что содержит</th></tr>
          </thead>
          <tbody>
            <tr><td><strong>problems[]</strong></td><td>Проблемы регуляторного фреймворка: что не работает, что критикуется</td></tr>
            <tr><td><strong>contradictions[]</strong></td><td>Противоречия между целями регулирования</td></tr>
            <tr><td><strong>reforms[]</strong></td><td>Реформы: driver (что движет), opposition (контраргументы), год</td></tr>
            <tr><td><strong>parameters_as_tools[]</strong></td><td>Как параметры используются как инструменты регулирования</td></tr>
          </tbody>
        </table>
        <p>Каждая запись содержит описание (EN + RU), источники с URL, и метку для отображения.</p>

        <hr className={s.hr} />

        {/* ═══ 4. Матрица жизненного цикла ═══ */}
        <h2 id="matrix" className={s.h2}>4. Матрица жизненного цикла</h2>

        <h3 id="matrix-structure" className={s.h3}>4.1. Структура матрицы</h3>
        <p>Контент L3 организуется в матрицу 4 строки x 5 столбцов:</p>
        <p><strong>Строки — фазы жизненного цикла:</strong></p>
        <table className={s.table}>
          <thead>
            <tr><th>Фаза</th><th>Описание</th><th>Источник данных</th></tr>
          </thead>
          <tbody>
            <tr><td>G07_1 — Первичный допуск</td><td>Подача заявления, рассмотрение, принятие решения</td><td>3A</td></tr>
            <tr><td>G07_2 — Поддержание</td><td>Обязанности после допуска: пороги, отчётность, управление</td><td>3B (continuing_obligations) + 3C (monitoring, sanctions)</td></tr>
            <tr><td>G07_3 — Приостановка</td><td>Временное прекращение торгов, условия возобновления</td><td>3B (suspension)</td></tr>
            <tr><td>G07_4 — Исключение</td><td>Принудительное или добровольное прекращение допуска</td><td>3B (delisting_compulsory, delisting_voluntary)</td></tr>
          </tbody>
        </table>
        <p><strong>Столбцы — типы содержания:</strong></p>
        <table className={s.table}>
          <thead>
            <tr><th>Тип</th><th>Описание</th></tr>
          </thead>
          <tbody>
            <tr><td>D01 — Требования</td><td>Количественные пороги, качественные критерии</td></tr>
            <tr><td>D02 — Процедуры</td><td>Последовательность действий: подача, рассмотрение, решение</td></tr>
            <tr><td>D03 — Мониторинг</td><td>Кто и как проверяет соблюдение</td></tr>
            <tr><td>D04 — Санкции</td><td>Меры воздействия при нарушениях</td></tr>
            <tr><td>D05 — Раскрытие</td><td>Проспект, отчётность, уведомления</td></tr>
          </tbody>
        </table>

        <h3 id="matrix-build" className={s.h3}>4.2. Построение матрицы</h3>
        <p>Распределение контента по ячейкам матрицы выполняется в два этапа:</p>
        <ol>
          <li>
            <strong>Алгоритмический маппинг</strong> (основной объём): каждая секция L3 однозначно маппится
            на ячейку матрицы по таблице маппинга.
          </li>
          <li>
            <strong>LLM-маппинг</strong> (пограничные случаи):
            <ul>
              <li>Санкции из 3C: LLM определяет, к какой фазе относится каждая конкретная санкция (штраф за отчётность → G07_2, делистинг как санкция → G07_4)</li>
              <li>Мониторинг при приостановке: LLM проверяет, есть ли упоминание мониторинга в период suspension</li>
              <li>Additional findings: LLM определяет фазу и тип содержания</li>
            </ul>
          </li>
        </ol>

        <hr className={s.hr} />

        {/* ═══ 5. Источники и верификация ═══ */}
        <h2 id="sources" className={s.h2}>5. Источники и верификация</h2>

        <h3 id="sources-types" className={s.h3}>5.1. Типология источников</h3>
        <p>Каждый источник классифицируется по типу документа:</p>
        <table className={s.table}>
          <thead>
            <tr><th>Тип</th><th>Примеры</th></tr>
          </thead>
          <tbody>
            <tr><td><strong>legislation</strong></td><td>legislation.gov.uk, legifrance.gouv.fr, gesetze-im-internet.de</td></tr>
            <tr><td><strong>rulebook</strong></td><td>handbook.fca.org.uk, docs.londonstockexchange.com, rulebook.sgx.com</td></tr>
            <tr><td><strong>government</strong></td><td>fca.org.uk, mas.gov.sg, bafin.de, sfc.hk</td></tr>
            <tr><td><strong>consultation</strong></td><td>Консультативные документы регуляторов</td></tr>
            <tr><td><strong>research</strong></td><td>oecd.org, worldbank.org, академические публикации</td></tr>
            <tr><td><strong>other</strong></td><td>Прочие источники</td></tr>
          </tbody>
        </table>
        <p>Классификация выполняется алгоритмически по домену URL.</p>

        <h3 id="sources-excerpts" className={s.h3}>5.2. Выдержки (excerpts)</h3>
        <p>
          Выдержки — прямые цитаты из документов-источников, извлечённые Parallel API.
          Позволяют верифицировать каждое утверждение без перехода к исходному документу.
        </p>
        <p>
          Выдержки проходят очистку от артефактов поисковых систем (дата-префиксы, маркеры «Read more»).
        </p>

        <h3 id="sources-confidence" className={s.h3}>5.3. Уровень уверенности (confidence)</h3>
        <p>Каждый источник имеет уровень уверенности:</p>
        <ul>
          <li><strong>high</strong> — источник содержит прямые выдержки, подтверждающие утверждение</li>
          <li><strong>medium</strong> — источник релевантен, выдержки частично подтверждают</li>
          <li><strong>low</strong> — источник найден, но выдержки отсутствуют (только URL и заголовок)</li>
        </ul>

        <h3 id="sources-stats" className={s.h3}>5.4. Количественные показатели</h3>
        <table className={s.table}>
          <thead>
            <tr><th>Уровень</th><th>Источники</th><th>Выдержки</th></tr>
          </thead>
          <tbody>
            <tr><td>L1 (юрисдикции)</td><td>555</td><td>1 244</td></tr>
            <tr><td>L2 (площадки)</td><td>78</td><td>35</td></tr>
            <tr><td>L3 (ячейки)</td><td>3 720</td><td>14 874</td></tr>
            <tr><td>L4 (анализ)</td><td>203</td><td>0*</td></tr>
            <tr><td><strong>Итого</strong></td><td><strong>4 556</strong></td><td><strong>16 153</strong></td></tr>
          </tbody>
        </table>
        <p className={s.footnote}>*L4 источники не содержат выдержек из-за формата запроса (свободный текст).</p>

        <hr className={s.hr} />

        {/* ═══ 6. Перевод и локализация ═══ */}
        <h2 id="translation" className={s.h2}>6. Перевод и локализация</h2>

        <h3 id="translation-what" className={s.h3}>6.1. Что переводится</h3>
        <table className={s.table}>
          <thead>
            <tr><th>Данные</th><th>Откуда</th><th>Куда</th><th>Модель</th></tr>
          </thead>
          <tbody>
            <tr><td>Описания секций L3</td><td><code className={s.code}>description</code></td><td><code className={s.code}>description_ru</code></td><td>gpt-5-mini</td></tr>
            <tr><td>Примечания юрисдикций</td><td><code className={s.code}>notes</code></td><td><code className={s.code}>notes_ru</code></td><td>gpt-5-mini</td></tr>
            <tr><td>Названия тиров</td><td><code className={s.code}>tier_name</code></td><td><code className={s.code}>tier_ru</code></td><td>gpt-5-mini</td></tr>
            <tr><td>Метки доп. параметров</td><td><code className={s.code}>parameter_name</code></td><td><code className={s.code}>param_label_ru</code></td><td>gpt-5-mini</td></tr>
            <tr><td>Реформы L4</td><td><code className={s.code}>driver</code>, <code className={s.code}>opposition</code></td><td><code className={s.code}>driver_ru</code>, <code className={s.code}>opposition_ru</code></td><td>gpt-5-mini</td></tr>
            <tr><td>Параметры как инструменты L4</td><td><code className={s.code}>problem_addressed</code>, <code className={s.code}>calibration_debate</code></td><td><code className={s.code}>_ru</code></td><td>gpt-5-mini</td></tr>
            <tr><td>Значения параметров Phase 2</td><td><code className={s.code}>value</code> (EN)</td><td><code className={s.code}>value</code> (RU) в pass2_ru.json</td><td>gpt-5-mini</td></tr>
          </tbody>
        </table>

        <h3 id="translation-display" className={s.h3}>6.2. Принцип отображения</h3>
        <p>
          Интерфейс использует паттерн <code className={s.code}>field_ru ?? field</code> — показывает
          русский перевод, если доступен, иначе английский оригинал.
        </p>

        <hr className={s.hr} />

        {/* ═══ 7. Контроль качества ═══ */}
        <h2 id="quality" className={s.h2}>7. Контроль качества</h2>

        <h3 id="quality-validation" className={s.h3}>7.1. Валидация данных</h3>
        <p>Каждый файл L3 (3A, 3B, 3C) проходит автоматическую валидацию:</p>
        <table className={s.table}>
          <thead>
            <tr><th>Метрика</th><th>Описание</th></tr>
          </thead>
          <tbody>
            <tr><td><strong>validation_status</strong></td><td>green / yellow / red — общая оценка качества</td></tr>
            <tr><td><strong>completeness_score</strong></td><td>0.0–1.0 — доля заполненных секций</td></tr>
            <tr><td><strong>scope_ok</strong></td><td>Соответствие скоупу (venue x tier x instrument_class)</td></tr>
            <tr><td><strong>missing_topics</strong></td><td>Список пропущенных тем</td></tr>
            <tr><td><strong>suspicious_sources</strong></td><td>Секции без источников</td></tr>
          </tbody>
        </table>

        <h3 id="quality-idempotent" className={s.h3}>7.2. Идемпотентность</h3>
        <p>
          Все шаги пайплайна идемпотентны — повторный запуск не изменяет данные, если они уже обработаны. Это обеспечивает:
        </p>
        <ul>
          <li>Безопасность повторных прогонов</li>
          <li>Возможность добавления новых юрисдикций без влияния на существующие</li>
          <li>Возобновление после сбоев</li>
        </ul>

        <h3 id="quality-atomic" className={s.h3}>7.3. Атомарная запись</h3>
        <p>
          Файлы записываются через <code className={s.code}>tempfile + os.replace</code> — атомарная операция,
          исключающая повреждение данных при сбое.
        </p>

        <hr className={s.hr} />

        {/* ═══ 8. Направления развития ═══ */}
        <h2 id="roadmap" className={s.h2}>8. Направления развития</h2>

        <h3 id="roadmap-data" className={s.h3}>8.1. Данные, доступные для дополнительного отображения</h3>
        <p>Следующие данные собраны пайплайном, но пока не отображаются в интерфейсе:</p>
        <table className={s.table}>
          <thead>
            <tr><th>Данные</th><th>Уровень</th><th>Описание</th><th>Приоритет</th></tr>
          </thead>
          <tbody>
            <tr><td>content[].source</td><td>L3</td><td>Текстовая ссылка на нормативный документ в каждой секции</td><td>Высокий</td></tr>
            <tr><td>parameter.source</td><td>L3</td><td>Нормативное основание значения параметра (UKLR 5.5.2R)</td><td>Высокий</td></tr>
            <tr><td>parameter.calculation_methodology</td><td>L3</td><td>Методология расчёта параметра</td><td>Высокий</td></tr>
            <tr><td>parameter.alternatives</td><td>L3</td><td>Допустимые альтернативы</td><td>Высокий</td></tr>
            <tr><td>parameter.variations</td><td>L3</td><td>Различия по сегментам/тирам</td><td>Высокий</td></tr>
            <tr><td>parameter.linkages[]</td><td>L3</td><td>Связи между параметрами</td><td>Средний</td></tr>
            <tr><td>metadata.terminology</td><td>L3</td><td>Локальные термины для приостановки/исключения</td><td>Средний</td></tr>
            <tr><td>venue_name_local</td><td>L2</td><td>Название площадки на местном языке</td><td>Средний</td></tr>
            <tr><td>validation.completeness_score</td><td>L3</td><td>Числовая полнота данных</td><td>Средний</td></tr>
            <tr><td>validation.missing_topics[]</td><td>L3</td><td>Пропущенные темы</td><td>Средний</td></tr>
            <tr><td>confidence</td><td>Все</td><td>Уровень уверенности источника</td><td>Низкий</td></tr>
            <tr><td>reasoning</td><td>L3</td><td>Обоснование исследования Parallel API</td><td>Низкий</td></tr>
          </tbody>
        </table>

        <h3 id="roadmap-extensions" className={s.h3}>8.2. Потенциальные расширения</h3>
        <ul>
          <li><strong>L4 выдержки:</strong> Текущие L4 запросы не содержат выдержек из-за формата (свободный текст). Перевод на JSON-формат с output_schema позволит получать excerpts.</li>
          <li><strong>Схожие юрисдикции:</strong> Алгоритм определения наиболее схожих юрисдикций по набору параметров.</li>
          <li><strong>Расширение охвата:</strong> Добавление юрисдикций Emerging Markets (Бразилия, Индия, Южная Корея и др.).</li>
        </ul>

        <h3 id="roadmap-institutional" className={s.h3}>8.3. Количественные институциональные факторы</h3>
        <p>
          Для сравнительного анализа юрисдикций планируется интеграция количественных институциональных индикаторов
          из открытых датасетов. Источники данных и методики обработки:
        </p>
        <table className={s.table}>
          <thead>
            <tr>
              <th>Индикатор</th>
              <th>Источник</th>
              <th>URL датасета</th>
              <th>Формат</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Regulatory Quality, Rule of Law, Political Stability (Ф4–Ф6)</td>
              <td>Worldwide Governance Indicators (WGI), World Bank</td>
              <td><a href="https://databank.worldbank.org/source/worldwide-governance-indicators" target="_blank" rel="noopener noreferrer">databank.worldbank.org</a></td>
              <td>CSV/Excel — интерактивная выгрузка по юрисдикциям, индикаторам и годам</td>
            </tr>
            <tr>
              <td>Market capitalization / GDP (Ф7)</td>
              <td>World Development Indicators (WDI), World Bank</td>
              <td><a href="https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS" target="_blank" rel="noopener noreferrer">data.worldbank.org</a></td>
              <td>CSV — прямая выгрузка по юрисдикциям</td>
            </tr>
            <tr>
              <td>Number of listed companies</td>
              <td>World Development Indicators (WDI), World Bank</td>
              <td><a href="https://data.worldbank.org/indicator/CM.MKT.LDOM.NO" target="_blank" rel="noopener noreferrer">data.worldbank.org</a></td>
              <td>CSV — прямая выгрузка по юрисдикциям</td>
            </tr>
            <tr>
              <td>Anti-Self-Dealing Index (Ф2)</td>
              <td>Djankov et al. (Harvard)</td>
              <td><a href="https://dash.harvard.edu/bitstreams/7312037c-56f0-6bd4-e053-0100007fdf3b/download" target="_blank" rel="noopener noreferrer">dash.harvard.edu</a></td>
              <td>PDF статьи с таблицами III и IV (72 юрисдикции). Исторический Excel: post.economics.harvard.edu/faculty/shleifer/data.html (доступность нестабильна). Альтернатива — <a href="https://archive.doingbusiness.org/en/data/exploretopics/protecting-minority-investors" target="_blank" rel="noopener noreferrer">World Bank Doing Business: Protecting Minority Investors</a> (методология на базе Djankov, данные до 2020 г.)</td>
            </tr>
            <tr>
              <td>Доли рынка по биржам (Ф10)</td>
              <td>World Federation of Exchanges (WFE)</td>
              <td><a href="https://www.world-exchanges.org/our-work/statistics" target="_blank" rel="noopener noreferrer">world-exchanges.org</a></td>
              <td>Ежемесячная и годовая статистика по биржам-членам WFE (бесплатная регистрация)</td>
            </tr>
          </tbody>
        </table>

        <hr className={s.hr} />

        {/* ═══ 9. Техническая архитектура ═══ */}
        <h2 id="tech" className={s.h2}>9. Техническая архитектура</h2>

        <h3 id="tech-stack" className={s.h3}>9.1. Стек</h3>
        <table className={s.table}>
          <thead>
            <tr><th>Компонент</th><th>Технология</th></tr>
          </thead>
          <tbody>
            <tr><td>Deep research</td><td>Parallel API (processor: pro)</td></tr>
            <tr><td>LLM (complex)</td><td>gpt-5 через LangChain</td></tr>
            <tr><td>LLM (simple)</td><td>gpt-5-mini через LangChain</td></tr>
            <tr><td>Пайплайн</td><td>Python, batch-обработка (max_concurrency=50)</td></tr>
            <tr><td>Хранение</td><td>JSON-файлы на диске, SQLite для интерфейса</td></tr>
            <tr><td>Бэкенд</td><td>Python (FastAPI)</td></tr>
            <tr><td>Фронтенд</td><td>React + TypeScript</td></tr>
          </tbody>
        </table>

        <h3 id="tech-pipeline" className={s.h3}>9.2. Порядок запуска пайплайна</h3>
        <pre className={s.codeBlock}>{`Level 1: EU Framework → 1A → 1B → 1C → Postprocess → Citations → Normalize → Classify → Clean → Translate
Level 2: Prompts → 2A → Postprocess → Citations → Normalize → Classify → Clean
Level 3: Prompts → 3A/3B/3C → Postprocess → Validate → Citations → Classify → Clean → Matrix → Translate
Phase 2: Groups → Pass 1 → Pass 2 → Translate → Section keys → Tier names → Normalize IDs
Level 4: 4A → Citations → Record sources → Labels → Classify → Clean → Translate`}</pre>
        <p>
          Каждый уровень может быть запущен независимо. Catchup-скрипты позволяют прогнать
          отдельные шаги постобработки на уже собранных данных.
        </p>
      </article>
    </div>
  )
}
