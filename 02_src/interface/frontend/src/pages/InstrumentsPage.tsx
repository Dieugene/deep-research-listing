import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchInstrumentSummaries, fetchInstrumentComparison } from '../api/instruments'
import type { InstrumentSummary, InstrumentComparison, InstrumentRegime, ParameterSummary } from '../api/types'
import styles from './InstrumentsPage.module.css'

// ── Constants ──────────────────────────────────────────────────────────────────

const INSTR_ORDER = ['equity', 'bond', 'fund', 'depositary_receipt']

const INSTR_ICONS: Record<string, string> = {
  equity: '\u{1F4C8}',            // 📈
  bond: '\u{1F4C4}',              // 📄
  fund: '\u{1F3E6}',              // 🏦
  depositary_receipt: '\u{1F517}', // 🔗
}

const PHASES = [
  { key: 'admission', label: '\u0414\u043E\u043F\u0443\u0441\u043A', dotClass: 'ptBlue' as const },
  { key: 'maintenance', label: '\u041F\u043E\u0434\u0434\u0435\u0440\u0436\u0430\u043D\u0438\u0435', dotClass: 'ptGreen' as const },
  { key: 'delisting', label: '\u0418\u0441\u043A\u043B\u044E\u0447\u0435\u043D\u0438\u0435', dotClass: 'ptRed' as const },
] as const

const PHASE_DOT_COLORS: Record<string, string> = {
  admission: '#3B82F6',
  maintenance: '#10B981',
  delisting: '#F87171',
}

const PHASE_HEADER_CLASS: Record<string, string> = {
  admission: 'phAdmission',
  maintenance: 'phMaintenance',
  delisting: 'phDelisting',
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    green: 'var(--green)',
    yellow: 'var(--yellow)',
    red: '#DC2626',
    unknown: 'var(--text-dim)',
  }
  return (
    <span
      className={styles.statusDot}
      style={{ background: colors[status] ?? 'var(--text-dim)' }}
    />
  )
}

function SearchIcon() {
  return (
    <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.35-4.35" />
    </svg>
  )
}

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

// ── Component ──────────────────────────────────────────────────────────────────

export default function InstrumentsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeInstr = searchParams.get('instr') ?? 'equity'
  const activePhase = searchParams.get('phase') ?? 'admission'

  // Session state (not in URL)
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set())
  const [activeParams, setActiveParams] = useState<Set<string>>(new Set())
  const [legalFamily, setLegalFamily] = useState('')
  const [venueType, setVenueType] = useState('')
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounce(search, 150)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [ddSearch, setDdSearch] = useState('')
  const ddRef = useRef<HTMLDivElement>(null)

  const [summaries, setSummaries] = useState<InstrumentSummary[]>([])
  const [comparison, setComparison] = useState<InstrumentComparison | null>(null)

  const instrStripRef = useRef<HTMLDivElement>(null)
  const prevInstrRef = useRef(activeInstr)

  // ── Click-outside handler for dropdown ──────────────────────────────────────
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ddRef.current && !ddRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('click', handleClickOutside)
    return () => document.removeEventListener('click', handleClickOutside)
  }, [])

  // ── Sticky shadow via IntersectionObserver ──────────────────────────────────
  useEffect(() => {
    const wrap = instrStripRef.current
    if (!wrap) return
    const sentinel = document.createElement('div')
    sentinel.style.cssText =
      'height:1px;margin-top:-1px;pointer-events:none'
    wrap.parentNode?.insertBefore(sentinel, wrap)
    const observer = new IntersectionObserver(
      ([e]) => wrap.classList.toggle(styles.stuck, e.intersectionRatio < 1),
      { threshold: [1], rootMargin: '-57px 0px 0px 0px' },
    )
    observer.observe(sentinel)
    return () => {
      observer.disconnect()
      sentinel.remove()
    }
  }, [])

  // ── Fetch summaries on mount ─────────────────────────────────────────────────
  useEffect(() => {
    fetchInstrumentSummaries()
      .then(setSummaries)
      .catch(() => setSummaries([]))
  }, [])

  // ── Fetch comparison on instr/phase change ──────────────────────────────────
  useEffect(() => {
    const instrChanged = prevInstrRef.current !== activeInstr
    prevInstrRef.current = activeInstr

    setComparison(null)
    fetchInstrumentComparison(activeInstr, activePhase)
      .then(data => {
        setComparison(data)
        // Only reset checked regimes on instrument change
        if (instrChanged) {
          setCheckedIds(new Set(data.regimes.slice(0, 3).map(r => r.cell_id)))
        }
        // Always reset params to first 3 on any change
        setActiveParams(new Set(data.parameters.slice(0, 3).map(p => p.parameter_id)))
      })
      .catch(() => setComparison(null))
  }, [activeInstr, activePhase])

  // ── Derived ────────────────────────────────────────────────────────────────────
  const orderedSummaries = useMemo(() => {
    if (!summaries.length) return []
    return [...summaries].sort(
      (a, b) =>
        INSTR_ORDER.indexOf(a.instrument_class_key) -
        INSTR_ORDER.indexOf(b.instrument_class_key),
    )
  }, [summaries])

  const activeInstrLabel = useMemo(() => {
    return (
      summaries.find(s => s.instrument_class_key === activeInstr)
        ?.instrument_class_label ?? activeInstr
    )
  }, [summaries, activeInstr])

  const activePhaseName = useMemo(() => {
    return PHASES.find(p => p.key === activePhase)?.label ?? activePhase
  }, [activePhase])

  const uniqueLegalFamilies = useMemo(() => {
    if (!comparison) return []
    return Array.from(
      new Set(comparison.regimes.map(r => r.legal_family).filter(Boolean) as string[]),
    ).sort()
  }, [comparison])

  const uniqueVenueTypes = useMemo(() => {
    if (!comparison) return []
    return Array.from(
      new Set(comparison.regimes.map(r => r.venue_type).filter(Boolean)),
    ).sort()
  }, [comparison])

  const filteredRegimes = useMemo(() => {
    if (!comparison) return []
    const q = debouncedSearch.toLowerCase()
    return comparison.regimes.filter((r: InstrumentRegime) => {
      if (legalFamily && r.legal_family !== legalFamily) return false
      if (venueType && r.venue_type !== venueType) return false
      if (
        q &&
        !r.venue_name.toLowerCase().includes(q) &&
        !r.jurisdiction_ru.toLowerCase().includes(q)
      )
        return false
      return true
    })
  }, [comparison, legalFamily, venueType, debouncedSearch])

  const checkedRegimes = useMemo(
    () => filteredRegimes.filter((r: InstrumentRegime) => checkedIds.has(r.cell_id)),
    [filteredRegimes, checkedIds],
  )

  const availableParams: ParameterSummary[] = useMemo(
    () => comparison?.parameters ?? [],
    [comparison],
  )

  const selectedParams = useMemo(
    () => availableParams.filter(p => activeParams.has(p.parameter_id)),
    [availableParams, activeParams],
  )

  // ── Handlers ──────────────────────────────────────────────────────────────────

  const selectInstr = useCallback((key: string) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('instr', key)
      return next
    })
    setLegalFamily('')
    setVenueType('')
    setSearch('')
  }, [setSearchParams])

  const selectPhase = useCallback((key: string) => {
    setSearchParams(
      prev => {
        const next = new URLSearchParams(prev)
        next.set('phase', key)
        return next
      },
      { replace: true },
    )
  }, [setSearchParams])

  const toggleRegime = useCallback((cellId: string) => {
    setCheckedIds(prev => {
      const next = new Set(prev)
      if (next.has(cellId)) next.delete(cellId)
      else next.add(cellId)
      return next
    })
  }, [])

  const toggleParam = useCallback((parameterId: string) => {
    setActiveParams(prev => {
      const next = new Set(prev)
      if (next.has(parameterId)) {
        // Must keep at least 1 active
        if (next.size > 1) next.delete(parameterId)
      } else {
        next.add(parameterId)
      }
      return next
    })
  }, [])

  const removeParam = useCallback((parameterId: string) => {
    setActiveParams(prev => {
      if (prev.size <= 1) return prev
      const next = new Set(prev)
      next.delete(parameterId)
      return next
    })
  }, [])

  const selectLegalFamily = useCallback((value: string) => {
    setLegalFamily(value)
  }, [])

  const selectVenueType = useCallback((value: string) => {
    setVenueType(value)
  }, [])

  // ── Render helpers ──────────────────────────────────────────────────────────

  const phaseThClass = PHASE_HEADER_CLASS[activePhase] ?? ''

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <>
      {/* Page header */}
      <div className={styles.pageHd}>
        <div className={styles.breadcrumb}>
          <Link to="/">Справочник</Link>
          <span>→</span>
          По инструментам
        </div>
        <h1 className={styles.pageTitle}>Сравнение по инструментам</h1>
        <p className={styles.pageSub}>
          Выберите инструмент → отберите листинговые режимы → сравните параметры регулирования
        </p>
      </div>

      {/* Instrument cards strip — sticky */}
      <div className={styles.instrStripWrap} ref={instrStripRef}>
        <div className={styles.instrStrip}>
          {orderedSummaries.length === 0
            ? INSTR_ORDER.map(key => (
                <div key={key} className={`${styles.icard} ${styles.skeleton}`} style={{ minHeight: 96 }} />
              ))
            : orderedSummaries.map(s => (
                <div
                  key={s.instrument_class_key}
                  className={`${styles.icard}${activeInstr === s.instrument_class_key ? ' ' + styles.icardActive : ''}`}
                  onClick={() => selectInstr(s.instrument_class_key)}
                >
                  <div className={styles.icardTop}>
                    <div className={styles.icardName}>{s.instrument_class_label}</div>
                    <div className={styles.icardIcon}>{INSTR_ICONS[s.instrument_class_key] ?? '\u{1F4C4}'}</div>
                  </div>
                  <div className={styles.icardStats}>
                    <div className={styles.icardStat}>
                      <div className={styles.icardStatVal}>{s.jurisdiction_count ?? '\u2014'}</div>
                      <div className={styles.icardStatLbl}>юрисдикций</div>
                    </div>
                    <div className={styles.icardStat}>
                      <div className={styles.icardStatVal}>{s.regime_count}</div>
                      <div className={styles.icardStatLbl}>режима</div>
                    </div>
                  </div>
                </div>
              ))}
        </div>
      </div>

      {/* Main content layout */}
      <div className={styles.mainWrap}>
        {/* Left panel */}
        <div className={styles.leftPanel}>
          {/* Filters */}
          <div className={styles.panelSection}>
            <div className={styles.panelLabel}>Правовая семья</div>
            <div className={styles.filterRow}>
              <button
                className={`${styles.filterChip}${legalFamily === '' ? ' ' + styles.filterChipActive : ''}`}
                onClick={() => selectLegalFamily('')}
              >
                Все
              </button>
              {uniqueLegalFamilies.map(f => (
                <button
                  key={f}
                  className={`${styles.filterChip}${legalFamily === f ? ' ' + styles.filterChipActive : ''}`}
                  onClick={() => selectLegalFamily(f)}
                >
                  {f}
                </button>
              ))}
            </div>

            <div className={styles.panelLabel} style={{ marginTop: 8 }}>Тип площадки</div>
            <div className={styles.filterRow}>
              <button
                className={`${styles.filterChip}${venueType === '' ? ' ' + styles.filterChipActive : ''}`}
                onClick={() => selectVenueType('')}
              >
                Все
              </button>
              {uniqueVenueTypes.map(t => (
                <button
                  key={t}
                  className={`${styles.filterChip}${venueType === t ? ' ' + styles.filterChipActive : ''}`}
                  onClick={() => selectVenueType(t)}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Venue list with checkboxes */}
          <div className={styles.panelSection} style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10, paddingBottom: 0 }}>
            <div className={styles.panelLabel} style={{ marginBottom: 0 }}>Листинговые режимы</div>

            <div className={styles.panelSearch}>
              <SearchIcon />
              <input
                type="text"
                placeholder="Поиск площадки..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>

            <div className={styles.selectedCount}>
              Выбрано: <strong>{checkedIds.size}</strong> из {filteredRegimes.length}
            </div>

            <div className={styles.venueList}>
              {filteredRegimes.map((regime: InstrumentRegime) => (
                <div
                  key={regime.cell_id}
                  className={`${styles.venueItem}${checkedIds.has(regime.cell_id) ? ' ' + styles.venueItemChecked : ''}`}
                  onClick={() => toggleRegime(regime.cell_id)}
                >
                  <div className={styles.venueCb}>
                    {checkedIds.has(regime.cell_id) && (
                      <span className={styles.venueCbCheck}>{'\u2713'}</span>
                    )}
                  </div>
                  <div className={styles.venueInfo}>
                    <span className={styles.venueName}>{regime.venue_name}</span>
                    <span className={styles.venueTierName}>{regime.tier}</span>
                    <span className={styles.venueJur}>{regime.jurisdiction_ru}</span>
                  </div>
                  <StatusDot status={regime.validation_status} />
                </div>
              ))}
              {filteredRegimes.length === 0 && comparison !== null && (
                <div className={styles.emptyListMsg}>
                  Нет режимов по выбранным фильтрам
                </div>
              )}
              {comparison === null && (
                <>
                  {[1, 2, 3, 4, 5].map(i => (
                    <div key={i} className={styles.skeleton} style={{ height: 52, borderRadius: 8, marginBottom: 2 }} />
                  ))}
                </>
              )}
            </div>
          </div>
        </div>

        {/* Right area */}
        <div className={styles.rightArea}>
          {/* Phase strip */}
          <div className={styles.phaseStrip}>
            {PHASES.map(p => (
              <button
                key={p.key}
                className={`${styles.phaseTabBtn}${activePhase === p.key ? ' ' + styles.phaseTabBtnActive : ''}`}
                onClick={() => selectPhase(p.key)}
              >
                <span
                  className={styles.ptDot}
                  style={{ background: PHASE_DOT_COLORS[p.key] }}
                />
                {p.label}
              </button>
            ))}
          </div>

          {/* Table header */}
          <div className={styles.tableHeader}>
            <div className={styles.tableHeaderLeft}>
              <span className={styles.tableTitle}>
                {activeInstrLabel} — {activePhaseName}
              </span>
              <span className={styles.tableCount}>{checkedRegimes.length} режима</span>
            </div>
            <div className={styles.colSelector}>
              {/* Active column chips */}
              {selectedParams.map(p => (
                <div key={p.parameter_id} className={styles.colActiveChip}>
                  <span className={styles.colChipCode}>{p.parameter_id}</span>
                  {p.parameter_name}
                  <span className={styles.colChipRemove} onClick={(e) => { e.stopPropagation(); removeParam(p.parameter_id) }}>{'\u00D7'}</span>
                </div>
              ))}

              {/* Add column button with dropdown */}
              <div className={styles.colAddBtn} ref={ddRef} onClick={() => { setDropdownOpen(o => !o); setDdSearch('') }}>
                <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                {'\u0414\u043E\u0431\u0430\u0432\u0438\u0442\u044C \u0441\u0442\u043E\u043B\u0431\u0435\u0446'}

                {dropdownOpen && (
                  <div className={styles.colDropdown} onClick={e => e.stopPropagation()}>
                    <div className={styles.colDdSearch}>
                      <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <circle cx="11" cy="11" r="8" />
                        <path d="m21 21-4.35-4.35" />
                      </svg>
                      <input
                        type="text"
                        placeholder={'\u041F\u043E\u0438\u0441\u043A \u043F\u0430\u0440\u0430\u043C\u0435\u0442\u0440\u0430...'}
                        value={ddSearch}
                        onChange={e => setDdSearch(e.target.value)}
                        onClick={e => e.stopPropagation()}
                        autoFocus
                      />
                    </div>
                    <div className={styles.colDdList}>
                      {availableParams
                        .filter(p => !ddSearch || p.parameter_id.toLowerCase().includes(ddSearch.toLowerCase()) || p.parameter_name.toLowerCase().includes(ddSearch.toLowerCase()))
                        .map(p => (
                          <div
                            key={p.parameter_id}
                            className={`${styles.colDdItem}${activeParams.has(p.parameter_id) ? ' ' + styles.colDdItemSelected : ''}`}
                            onClick={(e) => { e.stopPropagation(); toggleParam(p.parameter_id) }}
                          >
                            <span className={styles.colDdCode}>{p.parameter_id}</span>
                            <span>{p.parameter_name}</span>
                            <span className={styles.colDdCheck}>{'\u2713'}</span>
                          </div>
                        ))}
                      {availableParams.filter(p => !ddSearch || p.parameter_id.toLowerCase().includes(ddSearch.toLowerCase()) || p.parameter_name.toLowerCase().includes(ddSearch.toLowerCase())).length === 0 && (
                        <div className={styles.colDdEmpty}>{'\u041D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u043E'}</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Comparison table */}
          {checkedRegimes.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyStateIcon}>{'\u2B1C'}</div>
              <div className={styles.emptyStateTitle}>Нет выбранных режимов</div>
              <div className={styles.emptyStateSub}>Отметьте листинговые режимы в панели слева</div>
            </div>
          ) : (
            <div className={styles.cmpTableWrap}>
              <table className={styles.cmpTable}>
                <thead>
                  <tr>
                    <th>Листинговый режим</th>
                    {selectedParams.map(p => (
                      <th key={p.parameter_id} className={phaseThClass ? styles[phaseThClass] : undefined}>
                        {p.parameter_id}
                        <br />
                        <span>{p.parameter_name}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {checkedRegimes.map((regime: InstrumentRegime) => (
                    <tr className={styles.dataRow} key={regime.cell_id}>
                      <td>
                        <span className={styles.cellVenue}>{regime.venue_name}</span>
                        <span className={styles.cellTier}>{regime.tier}</span>
                        <span className={styles.cellJur}>
                          <StatusDot status={regime.validation_status} />
                          {regime.jurisdiction_ru} {'\u00B7'} {regime.venue_type}
                        </span>
                      </td>
                      {selectedParams.map(p => (
                        <td key={p.parameter_id}>
                          {regime.parameter_values[p.parameter_id] ? (
                            <span className={styles.cellVal}>
                              {regime.parameter_values[p.parameter_id]}
                            </span>
                          ) : (
                            <span className={styles.cellNa}>{'\u2014'}</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
