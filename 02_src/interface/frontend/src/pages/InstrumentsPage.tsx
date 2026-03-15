import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchInstrumentSummaries, fetchInstrumentComparison } from '../api/instruments'
import type { InstrumentSummary, InstrumentComparison, InstrumentRegime } from '../api/types'
import LoadingState from '../components/common/LoadingState'
import styles from './InstrumentsPage.module.css'

// ── Constants ──────────────────────────────────────────────────────────────────

const INSTR_ORDER = ['equity', 'bond', 'fund', 'depositary_receipt']

const PHASES = [
  { key: 'admission', label: 'Допуск' },
  { key: 'continuing', label: 'Поддержание' },
  { key: 'delisting', label: 'Исключение' },
]

const STATUS_COLORS: Record<string, string> = {
  green: '#059669',
  yellow: '#D97706',
  red: '#DC2626',
  unknown: '#9CA3AF',
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function ValidationDot({ status }: { status: InstrumentRegime['validation_status'] }) {
  return (
    <span
      className={styles.regimeDot}
      style={{ background: STATUS_COLORS[status] ?? STATUS_COLORS.unknown }}
      title={status}
    />
  )
}

// ── Component ──────────────────────────────────────────────────────────────────

export default function InstrumentsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeInstr = searchParams.get('instr') ?? 'equity'
  const activePhase = searchParams.get('phase') ?? 'admission'

  const [summaries, setSummaries] = useState<InstrumentSummary[]>([])
  const [comparison, setComparison] = useState<InstrumentComparison | null>(null)
  const [loadingSummaries, setLoadingSummaries] = useState(true)
  const [loadingComparison, setLoadingComparison] = useState(true)

  const [selectedRegimes, setSelectedRegimes] = useState<Set<string>>(new Set())
  const [visibleParams, setVisibleParams] = useState<Set<string>>(new Set())
  const [filterLegal, setFilterLegal] = useState<string>('all')
  const [filterType, setFilterType] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  // ── Fetch summaries on mount ─────────────────────────────────────────────────
  useEffect(() => {
    setLoadingSummaries(true)
    fetchInstrumentSummaries()
      .then(setSummaries)
      .catch(() => setSummaries([]))
      .finally(() => setLoadingSummaries(false))
  }, [])

  // ── Fetch comparison on instr/phase change ────────────────────────────────────
  useEffect(() => {
    setLoadingComparison(true)
    fetchInstrumentComparison(activeInstr, activePhase)
      .then(data => {
        setComparison(data)
        const first3 = new Set(data.regimes.slice(0, 3).map(r => r.cell_id))
        setSelectedRegimes(first3)
        const top5 = new Set(data.parameters.slice(0, 5).map(p => p.parameter_id))
        setVisibleParams(top5)
      })
      .catch(() => setComparison(null))
      .finally(() => setLoadingComparison(false))
  }, [activeInstr, activePhase])

  // ── Reset filters when instrument changes ─────────────────────────────────────
  const prevInstrRef = { current: activeInstr }
  useEffect(() => {
    if (prevInstrRef.current !== activeInstr) {
      setFilterLegal('all')
      setFilterType('all')
      setSearchQuery('')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeInstr])

  // ── Derived: unique venue types ───────────────────────────────────────────────
  const uniqueVenueTypes = useMemo(() => {
    if (!comparison) return []
    return Array.from(new Set(comparison.regimes.map(r => r.venue_type))).sort()
  }, [comparison])

  // ── Filtered regimes ──────────────────────────────────────────────────────────
  const filteredRegimes = useMemo(() => {
    if (!comparison) return []
    return comparison.regimes.filter(r => {
      if (filterLegal !== 'all' && r.legal_family?.toLowerCase() !== filterLegal) return false
      if (filterType !== 'all' && r.venue_type !== filterType) return false
      if (searchQuery) {
        const q = searchQuery.toLowerCase()
        return (
          r.venue_name.toLowerCase().includes(q) ||
          r.jurisdiction_ru.toLowerCase().includes(q)
        )
      }
      return true
    })
  }, [comparison, filterLegal, filterType, searchQuery])

  // ── Ordered summaries ─────────────────────────────────────────────────────────
  const orderedSummaries = useMemo(() => {
    if (!summaries.length) return []
    return [...summaries].sort(
      (a, b) =>
        INSTR_ORDER.indexOf(a.instrument_class_key) -
        INSTR_ORDER.indexOf(b.instrument_class_key),
    )
  }, [summaries])

  // ── Visible parameters list (ordered by comparison.parameters) ────────────────
  const visibleParamList = useMemo(() => {
    if (!comparison) return []
    return comparison.parameters.filter(p => visibleParams.has(p.parameter_id))
  }, [comparison, visibleParams])

  // ── Selected regime objects (ordered) ────────────────────────────────────────
  const selectedRegimeObjects = useMemo(() => {
    if (!comparison) return []
    return comparison.regimes.filter(r => selectedRegimes.has(r.cell_id))
  }, [comparison, selectedRegimes])

  // ── Handlers ──────────────────────────────────────────────────────────────────

  function handleSelectInstr(key: string) {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('instr', key)
      return next
    })
    setFilterLegal('all')
    setFilterType('all')
    setSearchQuery('')
  }

  function handleSelectPhase(key: string) {
    setSearchParams(
      prev => {
        const next = new URLSearchParams(prev)
        next.set('phase', key)
        return next
      },
      { replace: true },
    )
  }

  function toggleRegime(cellId: string) {
    setSelectedRegimes(prev => {
      const next = new Set(prev)
      if (next.has(cellId)) {
        next.delete(cellId)
      } else {
        next.add(cellId)
      }
      return next
    })
  }

  function toggleParam(parameterId: string) {
    setVisibleParams(prev => {
      const next = new Set(prev)
      if (next.has(parameterId)) {
        next.delete(parameterId)
      } else {
        next.add(parameterId)
      }
      return next
    })
  }

  function toggleAllParams() {
    if (!comparison) return
    const allIds = comparison.parameters.map(p => p.parameter_id)
    if (allIds.every(id => visibleParams.has(id))) {
      setVisibleParams(new Set())
    } else {
      setVisibleParams(new Set(allIds))
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className={styles.page}>
      {/* Page header */}
      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>По инструментам</h1>
        <p className={styles.pageSub}>Сравнение листинговых режимов</p>
      </div>

      {/* Instrument strip */}
      <div className={styles.instrStrip}>
        <div className={styles.instrStripInner}>
          {loadingSummaries
            ? INSTR_ORDER.map(key => (
                <div key={key} className={styles.instrCard} style={{ opacity: 0.4 }} />
              ))
            : orderedSummaries.map(s => (
                <button
                  key={s.instrument_class_key}
                  className={`${styles.instrCard}${
                    activeInstr === s.instrument_class_key ? ' ' + styles.instrCardActive : ''
                  }`}
                  onClick={() => handleSelectInstr(s.instrument_class_key)}
                  type="button"
                >
                  <div className={styles.instrCardName}>{s.instrument_class_label}</div>
                  <div className={styles.instrCardStats}>
                    <div className={styles.instrCardStat}>
                      <span className={styles.instrCardStatVal}>{s.regime_count}</span>
                      <span className={styles.instrCardStatLabel}>режимов</span>
                    </div>
                  </div>
                  {s.top_parameters.length > 0 && (
                    <div className={styles.instrCardParams}>
                      {s.top_parameters.slice(0, 3).map(p => (
                        <span key={p.parameter_id} className={styles.instrCardParam}>
                          {p.parameter_name}
                        </span>
                      ))}
                    </div>
                  )}
                </button>
              ))}
        </div>
      </div>

      {/* Phase strip */}
      <div className={styles.phaseStrip}>
        {PHASES.map(ph => (
          <button
            key={ph.key}
            className={`${styles.phaseBtn}${
              activePhase === ph.key ? ' ' + styles.phaseBtnActive : ''
            }`}
            onClick={() => handleSelectPhase(ph.key)}
            type="button"
          >
            {ph.label}
          </button>
        ))}
      </div>

      {/* Main layout */}
      <div className={styles.mainLayout}>
        {/* Left panel */}
        <div className={styles.leftPanel}>
          <div className={styles.leftHeader}>Фильтры</div>

          {/* Legal family filter */}
          <div className={styles.filterGroup}>
            <div className={styles.filterLabel}>Правовая семья</div>
            <div className={styles.filterBtns}>
              {['all', 'common law', 'civil law', 'mixed'].map(v => (
                <button
                  key={v}
                  type="button"
                  className={`${styles.filterBtn}${
                    filterLegal === v ? ' ' + styles.filterBtnActive : ''
                  }`}
                  onClick={() => setFilterLegal(v)}
                >
                  {v === 'all' ? 'Все' : v}
                </button>
              ))}
            </div>
          </div>

          {/* Venue type filter */}
          {uniqueVenueTypes.length > 0 && (
            <div className={styles.filterGroup}>
              <div className={styles.filterLabel}>Тип площадки</div>
              <div className={styles.filterBtns}>
                <button
                  type="button"
                  className={`${styles.filterBtn}${
                    filterType === 'all' ? ' ' + styles.filterBtnActive : ''
                  }`}
                  onClick={() => setFilterType('all')}
                >
                  Все
                </button>
                {uniqueVenueTypes.map(vt => (
                  <button
                    key={vt}
                    type="button"
                    className={`${styles.filterBtn}${
                      filterType === vt ? ' ' + styles.filterBtnActive : ''
                    }`}
                    onClick={() => setFilterType(vt)}
                  >
                    {vt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Search */}
          <input
            className={styles.searchInput}
            type="text"
            placeholder="Поиск режима..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />

          {/* Regimes list */}
          <div className={styles.regimesHeader}>
            <span>Листинговые режимы</span>
          </div>
          <div className={styles.regimesCount}>
            Выбрано: {selectedRegimes.size} из {filteredRegimes.length}
          </div>

          <div className={styles.regimeList}>
            {filteredRegimes.map(r => (
              <label key={r.cell_id} className={styles.regimeItem}>
                <input
                  type="checkbox"
                  className={styles.regimeCheck}
                  checked={selectedRegimes.has(r.cell_id)}
                  onChange={() => toggleRegime(r.cell_id)}
                />
                <ValidationDot status={r.validation_status} />
                <div className={styles.regimeInfo}>
                  <div className={styles.regimeName}>{r.venue_name}</div>
                  <div className={styles.regimeMeta}>
                    {r.tier} — {r.jurisdiction_ru} · {r.venue_type}
                  </div>
                </div>
              </label>
            ))}
            {filteredRegimes.length === 0 && !loadingComparison && (
              <div className={styles.regimesCount} style={{ paddingTop: 8 }}>
                Нет режимов по выбранным фильтрам
              </div>
            )}
          </div>
        </div>

        {/* Right area */}
        <div className={styles.rightArea}>
          {loadingComparison ? (
            <div className={styles.loadingWrap}>
              <LoadingState message="Загрузка данных сравнения..." />
            </div>
          ) : (
            <>
              {/* Parameter selector */}
              {comparison && comparison.parameters.length > 0 && (
                <div className={styles.paramSelector}>
                  <button
                    type="button"
                    className={`${styles.paramBtn}${
                      comparison.parameters.every(p => visibleParams.has(p.parameter_id))
                        ? ' ' + styles.paramBtnActive
                        : ''
                    }`}
                    onClick={toggleAllParams}
                  >
                    Все параметры
                  </button>
                  {comparison.parameters.map(p => (
                    <button
                      key={p.parameter_id}
                      type="button"
                      className={`${styles.paramBtn}${
                        visibleParams.has(p.parameter_id) ? ' ' + styles.paramBtnActive : ''
                      }`}
                      onClick={() => toggleParam(p.parameter_id)}
                      title={p.parameter_name}
                    >
                      {p.parameter_id}
                    </button>
                  ))}
                </div>
              )}

              {/* Comparison table */}
              {selectedRegimeObjects.length === 0 ? (
                <div className={styles.emptyState}>
                  <div className={styles.emptyStateTitle}>Выберите режимы слева</div>
                  <div className={styles.emptyStateSub}>
                    Отметьте одну или несколько площадок для сравнения параметров
                  </div>
                </div>
              ) : (
                <div className={styles.tableWrap}>
                  <table className={styles.compTable}>
                    <thead>
                      <tr>
                        <th className={`${styles.compTh} ${styles.compThFirst}`}>
                          Листинговый режим
                        </th>
                        {visibleParamList.map(p => (
                          <th key={p.parameter_id} className={styles.compTh} title={p.parameter_name}>
                            {p.parameter_id}
                            <br />
                            <span style={{ fontFamily: 'var(--font-ui)', fontSize: 10, textTransform: 'none', letterSpacing: 0, fontWeight: 400, color: 'var(--text-secondary)', display: 'block', marginTop: 2 }}>
                              {p.parameter_name}
                            </span>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {selectedRegimeObjects.map(r => (
                        <tr key={r.cell_id}>
                          <td className={`${styles.compTd} ${styles.compTdFirst}`}>
                            <div style={{ fontWeight: 500, color: 'var(--text-primary)', marginBottom: 2 }}>
                              <ValidationDot status={r.validation_status} />
                              {r.venue_name}
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                              {r.tier} · {r.jurisdiction_ru}
                            </div>
                          </td>
                          {visibleParamList.map(p => (
                            <td key={p.parameter_id} className={styles.compTd}>
                              {r.parameter_values[p.parameter_id] ?? (
                                <span className={styles.compTdEmpty}>—</span>
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
