import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchInstrumentSummaries, fetchInstrumentComparison } from '../api/instruments'
import type { InstrumentSummary, InstrumentComparison } from '../api/types'
import styles from './InstrumentsPage.module.css'

// ── Constants ──────────────────────────────────────────────────────────────────

const INSTR_ORDER = ['equity', 'bond', 'fund', 'depositary_receipt']

const PHASES = [
  { key: 'admission', label: 'Допуск' },
  { key: 'maintenance', label: 'После допуска' },
  { key: 'enforcement', label: 'Мониторинг и надзор' },
]

// ── Helpers ────────────────────────────────────────────────────────────────────

function emojiForInstr(key: string): string {
  const map: Record<string, string> = {
    equity: '📈',
    bond: '📋',
    fund: '🏦',
    depositary_receipt: '🌐',
  }
  return map[key] ?? '📄'
}

function flagEmoji(jurisdiction_ru: string): string {
  const flags: Record<string, string> = {
    'Великобритания': '🇬🇧',
    'Гонконг': '🇭🇰',
    'Сингапур': '🇸🇬',
    'Германия': '🇩🇪',
    'Франция': '🇫🇷',
    'Австралия': '🇦🇺',
    'Россия': '🇷🇺',
  }
  return flags[jurisdiction_ru] ?? '🌐'
}

function phaseColor(key: string): string {
  const colors: Record<string, string> = {
    admission: '#3B82F6',
    maintenance: '#10B981',
    enforcement: '#94A3B8',
  }
  return colors[key] ?? '#9CA3AF'
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    green: 'var(--green)',
    yellow: 'var(--yellow)',
    red: 'var(--red)',
    unknown: 'var(--text-dim)',
  }
  return (
    <span
      style={{
        width: 6,
        height: 6,
        borderRadius: '50%',
        background: colors[status] ?? 'var(--text-dim)',
        display: 'inline-block',
        flexShrink: 0,
      }}
    />
  )
}

function SearchIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="9" cy="9" r="6" />
      <line x1="14" y1="14" x2="19" y2="19" />
    </svg>
  )
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

  const [summaries, setSummaries] = useState<InstrumentSummary[]>([])
  const [comparison, setComparison] = useState<InstrumentComparison | null>(null)

  const instrStripRef = useRef<HTMLDivElement>(null)

  // ── Sticky shadow via IntersectionObserver ──────────────────────────────────
  useEffect(() => {
    const wrap = instrStripRef.current
    if (!wrap) return
    const sentinel = document.createElement('div')
    sentinel.style.cssText =
      'height:1px;margin-top:-1px;pointer-events:none;position:absolute;top:56px;left:0;right:0'
    document.body.appendChild(sentinel)
    const observer = new IntersectionObserver(
      ([e]) => wrap.classList.toggle('stuck', e.intersectionRatio < 1),
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

  // ── Fetch comparison on instr/phase change ────────────────────────────────────
  useEffect(() => {
    setComparison(null)
    fetchInstrumentComparison(activeInstr, activePhase)
      .then(data => {
        setComparison(data)
        // Auto-select first 3 regimes and first 3 params
        const first3Ids = new Set(data.regimes.slice(0, 3).map(r => r.cell_id))
        setCheckedIds(first3Ids)
        const first3Params = new Set(data.parameters.slice(0, 3).map(p => p.parameter_id))
        setActiveParams(first3Params)
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

  const filteredRegimes = useMemo(() => {
    if (!comparison) return []
    return comparison.regimes.filter(r => {
      if (legalFamily && r.legal_family !== legalFamily) return false
      if (venueType && r.venue_type !== venueType) return false
      if (
        search &&
        !r.venue_name.toLowerCase().includes(search.toLowerCase()) &&
        !r.jurisdiction_ru.toLowerCase().includes(search.toLowerCase())
      )
        return false
      return true
    })
  }, [comparison, legalFamily, venueType, search])

  const checkedRegimes = useMemo(
    () => filteredRegimes.filter(r => checkedIds.has(r.cell_id)),
    [filteredRegimes, checkedIds],
  )

  const availableParams = useMemo(
    () => comparison?.parameters ?? [],
    [comparison],
  )

  const selectedParams = useMemo(
    () => availableParams.filter(p => activeParams.has(p.parameter_id)),
    [availableParams, activeParams],
  )

  // ── Handlers ──────────────────────────────────────────────────────────────────

  function selectInstr(key: string) {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('instr', key)
      return next
    })
    setLegalFamily('')
    setVenueType('')
    setSearch('')
  }

  function selectPhase(key: string) {
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
    setCheckedIds(prev => {
      const next = new Set(prev)
      if (next.has(cellId)) next.delete(cellId)
      else next.add(cellId)
      return next
    })
  }

  function toggleParam(parameterId: string) {
    setActiveParams(prev => {
      const next = new Set(prev)
      if (next.has(parameterId)) next.delete(parameterId)
      else next.add(parameterId)
      return next
    })
  }

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <>
      {/* Instrument cards strip — sticky at top:56px */}
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
                    <div className={styles.icardIcon}>{emojiForInstr(s.instrument_class_key)}</div>
                  </div>
                  <div className={styles.icardStats}>
                    <div className={styles.icardStat}>
                      <div className={styles.icardStatVal}>{s.jurisdiction_count ?? '—'}</div>
                      <div className={styles.icardStatLbl}>юрисдикций</div>
                    </div>
                    <div className={styles.icardStat}>
                      <div className={styles.icardStatVal}>{s.regime_count}</div>
                      <div className={styles.icardStatLbl}>режима</div>
                    </div>
                  </div>
                  <div className={styles.icardParams}>
                    {s.top_parameters.slice(0, 3).map(p => (
                      <span key={p.parameter_id} className={styles.icardParam}>
                        {p.parameter_id} {p.parameter_name}
                      </span>
                    ))}
                    {s.top_parameters.length > 3 && (
                      <span className={styles.icardParam}>+{s.top_parameters.length - 3}</span>
                    )}
                  </div>
                </div>
              ))}
        </div>
      </div>

      {/* Main content layout */}
      <div className={styles.mainWrap}>
        {/* Left panel */}
        <div className={styles.leftPanel}>
          {/* Legal family + venue type filters */}
          <div className={styles.panelSection}>
            <div className={styles.panelLabel}>Правовая семья</div>
            <div className={styles.filterRow}>
              <button
                className={`${styles.filterChip}${legalFamily === '' ? ' ' + styles.filterChipActive : ''}`}
                onClick={() => setLegalFamily('')}
              >
                Все
              </button>
              {uniqueLegalFamilies.map(f => (
                <button
                  key={f}
                  className={`${styles.filterChip}${legalFamily === f ? ' ' + styles.filterChipActive : ''}`}
                  onClick={() => setLegalFamily(f)}
                >
                  {f}
                </button>
              ))}
            </div>

            <div className={styles.panelLabel} style={{ marginTop: 8 }}>Тип площадки</div>
            <div className={styles.filterRow}>
              <button
                className={`${styles.filterChip}${venueType === '' ? ' ' + styles.filterChipActive : ''}`}
                onClick={() => setVenueType('')}
              >
                Все
              </button>
              <button
                className={`${styles.filterChip}${venueType === 'regulated_market' ? ' ' + styles.filterChipActive : ''}`}
                onClick={() => setVenueType('regulated_market')}
              >
                Regulated
              </button>
              <button
                className={`${styles.filterChip}${venueType === 'mtf' ? ' ' + styles.filterChipActive : ''}`}
                onClick={() => setVenueType('mtf')}
              >
                MTF
              </button>
              <button
                className={`${styles.filterChip}${venueType === 'exchange' ? ' ' + styles.filterChipActive : ''}`}
                onClick={() => setVenueType('exchange')}
              >
                Биржа
              </button>
            </div>
          </div>

          {/* Venue list with checkboxes */}
          <div className={`${styles.panelSection}`} style={{ flex: 1 }}>
            <div className={styles.panelLabel}>Листинговые режимы</div>

            <div className={styles.panelSearch}>
              <SearchIcon />
              <input
                type="text"
                placeholder="Поиск площадки..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>

            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-dim)', padding: '0 2px', marginBottom: '8px' }}>
              Выбрано: <strong style={{ color: 'var(--accent)' }}>{checkedIds.size}</strong> из {filteredRegimes.length}
            </div>

            <div className={styles.venueList}>
              {filteredRegimes.map(regime => (
                <div
                  key={regime.cell_id}
                  className={`${styles.venueItem}${checkedIds.has(regime.cell_id) ? ' ' + styles.venueItemChecked : ''}`}
                  onClick={() => toggleRegime(regime.cell_id)}
                >
                  <div className={styles.venueCb}>
                    {checkedIds.has(regime.cell_id) && (
                      <span className={styles.venueCbCheck}>✓</span>
                    )}
                  </div>
                  <div className={styles.venueInfo}>
                    <span className={styles.venueName}>
                      {flagEmoji(regime.jurisdiction_ru)} {regime.venue_name}
                    </span>
                    <span className={styles.venueTierName}>{regime.tier}</span>
                    <span className={styles.venueJur}>
                      {regime.jurisdiction_ru} · {regime.venue_type}
                    </span>
                  </div>
                  <StatusDot status={regime.validation_status} />
                </div>
              ))}
              {filteredRegimes.length === 0 && comparison !== null && (
                <div style={{ fontSize: 12, color: 'var(--text-dim)', padding: '12px 4px' }}>
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
                <span className={styles.ptDot} style={{ background: phaseColor(p.key) }} />
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
            <div className={styles.paramCols}>
              {availableParams.map(p => (
                <button
                  key={p.parameter_id}
                  className={`${styles.paramColBtn}${activeParams.has(p.parameter_id) ? ' ' + styles.paramColBtnActive : ''}`}
                  onClick={() => toggleParam(p.parameter_id)}
                >
                  <span style={{ fontSize: '9px', opacity: 0.7 }}>{p.parameter_id}</span>{' '}
                  {p.parameter_name}
                </button>
              ))}
            </div>
          </div>

          {/* Comparison table */}
          {checkedRegimes.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyStateIcon}>⬜</div>
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
                      <th key={p.parameter_id}>
                        {p.parameter_id}
                        <br />
                        <span>{p.parameter_name}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {checkedRegimes.map(regime => (
                    <tr className={styles.dataRow} key={regime.cell_id}>
                      <td>
                        <span className={styles.cellVenue}>
                          {flagEmoji(regime.jurisdiction_ru)} {regime.venue_name}
                        </span>
                        <span className={styles.cellTier}>{regime.tier}</span>
                        <span className={styles.cellJur}>
                          <StatusDot status={regime.validation_status} />
                          {regime.jurisdiction_ru} · {regime.venue_type}
                        </span>
                      </td>
                      {selectedParams.map(p => (
                        <td key={p.parameter_id}>
                          {regime.parameter_values[p.parameter_id] ? (
                            <span className={styles.cellVal}>
                              {regime.parameter_values[p.parameter_id]}
                            </span>
                          ) : (
                            <span className={styles.cellNa}>—</span>
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
