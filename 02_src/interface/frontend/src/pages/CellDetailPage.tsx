import { useState, useEffect, useCallback } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { fetchVenue } from '../api/venues'
import { fetchCellContent, fetchCellParameters, fetchMatrix } from '../api/cells'
import type {
  VenueCard,
  CellContent,
  CellParameters,
  MatrixView,
  ContentSection,
  ParameterValue,
} from '../api/types'
import styles from './CellDetailPage.module.css'
import SourceBlock from '../components/SourceBlock'

// ──────────────────────────────────────────────────────────────
// Phase display config
// ──────────────────────────────────────────────────────────────

const DISPLAY_PHASES = [
  { key: 'admission', label: 'Допуск' },
  { key: 'maintenance', label: 'Поддержание' },
  { key: 'delisting', label: 'Исключение' },
]

// ──────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────

type ViewMode = 'tabs' | 'matrix'

function getHostname(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

interface ParsedSource {
  url?: string
  text?: string
  title?: string
}

function phaseColor(phaseKey: string): string {
  const colors: Record<string, string> = {
    admission: '#3B82F6',    // blue
    maintenance: '#10B981',  // green
    delisting: '#F87171',    // red
    enforcement: '#94A3B8',  // slate (matrix only)
  }
  return colors[phaseKey] ?? '#9CA3AF'
}

// ──────────────────────────────────────────────────────────────
// ValidationBadge
// ──────────────────────────────────────────────────────────────

type ValidationStatus = 'green' | 'yellow' | 'red' | 'unknown'

interface ValidationBadgeProps {
  status: ValidationStatus
}

function ValidationBadge({ status }: ValidationBadgeProps) {
  const cls =
    status === 'green'
      ? styles.sbGreen
      : status === 'yellow'
        ? styles.sbYellow
        : status === 'red'
          ? styles.sbRed
          : styles.sbUnknown

  const label =
    status === 'green'
      ? 'Верифицировано'
      : status === 'yellow'
        ? 'Проверить источники'
        : status === 'red'
          ? 'Ненадёжно'
          : 'Статус неизвестен'

  return <span className={`${styles.statusBadge} ${cls}`}>{label}</span>
}

// ──────────────────────────────────────────────────────────────
// SectionCard
// ──────────────────────────────────────────────────────────────

interface SectionCardProps {
  section: ContentSection
  parameters?: ParameterValue[]
}

function SectionCard({ section, parameters }: SectionCardProps) {
  const paragraphs = section.text.split('\n\n').filter(Boolean)

  return (
    <div className={styles.sectionCard}>
      <div className={styles.sectionCardHd}>
        <span className={styles.sectionCardTitle}>{section.section_label}</span>
      </div>

      <div className={styles.sectionCardBody}>
        {paragraphs.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>

      {parameters && parameters.length > 0 && (
        <div className={styles.paramsStrip}>
          {parameters.map((p) => (
            <div key={p.parameter_id} className={styles.paramChip}>
              <span className={styles.paramCode}>{p.parameter_id}</span>
              <span>{p.parameter_name}</span>
              <span className={styles.paramVal}>{p.value}</span>
            </div>
          ))}
        </div>
      )}

      {section.citations && section.citations.length > 0 && (
        <SourceBlock
          sources={section.citations}
          blockId={`section-${section.section_key}`}
        />
      )}
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// ParamStrip (phase-level parameters below sections)
// ──────────────────────────────────────────────────────────────

interface ParamStripProps {
  phase: string
  parameters: CellParameters | null
}

function ParamStrip({ phase, parameters }: ParamStripProps) {
  if (!parameters) return null
  const filtered = parameters.parameters.filter(
    (p) =>
      (p.lifecycle_phase_key === phase || (p as ParameterValue & { phase_key?: string }).phase_key === phase) &&
      p.status === 'found',
  )
  if (filtered.length === 0) return null

  return (
    <div className={styles.paramsStrip}>
      {filtered.map((p) => (
        <div key={p.parameter_id} className={styles.paramChip}>
          <span className={styles.paramCode}>{p.parameter_id}</span>
          <span>{p.parameter_name || p.parameter_id}:</span>
          <span className={styles.paramVal}>{p.value}</span>
        </div>
      ))}
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// MatrixViewPanel
// ──────────────────────────────────────────────────────────────

// Matrix row keys shown (exclude 'suspension')
const MATRIX_DISPLAY_ROW_KEYS = new Set(['admission', 'continuing', 'delisting'])

// Map matrix row_key → tab phase_key for click navigation
const MATRIX_ROW_TO_TAB: Record<string, string> = {
  admission: 'admission',
  continuing: 'maintenance',
  delisting: 'delisting',
}

// Section key patterns per matrix column — order matters: first match wins
const COL_SECTION_PATTERNS: Record<string, string[]> = {
  requirements: [
    'eligibility_requirements',
    'instrument_requirements',
    'restrictions_and_lock_ups',
    'special_regimes',
    'continuing_obligations.quantitative_thresholds',
    'continuing_obligations.qualitative_obligations',
    'delisting_voluntary.conditions',
    'delisting_compulsory.shareholder_protection',
  ],
  procedures: [
    'procedure_and_timeline',
    'admission_overview',
    'sponsor_and_infrastructure',
    'continuing_obligations.periodic_reporting',
    'continuing_obligations.compliance_confirmation',
    'delisting_voluntary.procedure',
    'delisting_voluntary.shareholder_approval',
    'delisting_compulsory.procedure',
    'delisting_compulsory.grace_period',
  ],
  monitoring: [
    'ongoing_disclosure',
    'market_monitoring',
    'delisting_compulsory.grounds',
  ],
  sanctions: [
    'suspension_and_cancellation',
    'sanctions',
    'enforcement_actions',
  ],
  disclosure: [
    'disclosure_at_admission',
    'disclosure_obligations',
    'delisting_compulsory.disclosure',
  ],
}

/** Assigns each parameter to exactly one column per phase, in column order. */
function buildPhaseColPills(
  params: ParameterValue[],
  phaseKey: string,
  colOrder: string[],
): Map<string, ParameterValue[]> {
  const colMap = new Map<string, ParameterValue[]>()
  colOrder.forEach((c) => colMap.set(c, []))

  const phaseParams = params.filter(
    (p) =>
      (p.lifecycle_phase_key === phaseKey || p.lifecycle_phase_key === 'multiple') &&
      p.status === 'found',
  )

  const assigned = new Set<string>()

  for (const colKey of colOrder) {
    const patterns = COL_SECTION_PATTERNS[colKey] ?? []
    for (const param of phaseParams) {
      const pid = `${param.parameter_id}|${param.lifecycle_phase_key}`
      if (assigned.has(pid)) continue
      if (param.section_keys?.some((sk) => patterns.includes(sk))) {
        colMap.get(colKey)!.push(param)
        assigned.add(pid)
      }
    }
  }

  return colMap
}

interface MatrixViewPanelProps {
  matrix: MatrixView
  cellParameters: CellParameters | null
  onCellClick: (tabPhaseKey: string) => void
}

function MatrixViewPanel({ matrix, cellParameters, onCellClick }: MatrixViewPanelProps) {
  const displayRows = matrix.rows.filter((r) => MATRIX_DISPLAY_ROW_KEYS.has(r.row_key))
  const allCols = displayRows.length > 0 ? displayRows[0].columns : []
  const colOrder = allCols.map((c) => c.col_key)

  return (
    <div className={styles.matrixWrap}>
      <table className={styles.mxTable}>
        <thead>
          <tr>
            <th>Фаза</th>
            {allCols.map((col) => (
              <th key={col.col_key}>{col.col_label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {displayRows.map((row) => {
            const colPills = cellParameters
              ? buildPhaseColPills(cellParameters.parameters, row.row_key, colOrder)
              : null

            return (
              <tr key={row.row_key}>
                <td className={styles.mxPhaseLabel}>
                  <span className={styles.mxPhaseName}>{row.row_label}</span>
                </td>
                {row.columns.map((col) => {
                  const tabKey = MATRIX_ROW_TO_TAB[row.row_key] ?? row.row_key

                  if (col.status === 'not_applicable') {
                    return (
                      <td key={col.col_key} className={styles.mxCellNa}>
                        <span className={styles.mxNaLabel}>—</span>
                      </td>
                    )
                  }

                  if (col.status === 'filled') {
                    const pills = (colPills?.get(col.col_key) ?? []).slice(0, 3)
                    return (
                      <td
                        key={col.col_key}
                        className={styles.mxCell}
                        onClick={() => onCellClick(tabKey)}
                      >
                        <div className={styles.mxPills}>
                          {pills.length > 0 ? (
                            pills.map((p) => (
                              <div key={`${p.parameter_id}|${p.lifecycle_phase_key}`} className={styles.mxPill}>
                                <span className={styles.mxPillCode}>{p.parameter_id}</span>
                                <span className={styles.mxPillVal}>{p.value}</span>
                              </div>
                            ))
                          ) : (
                            <div className={styles.mxPill}>
                              <span className={styles.mxPillVal} style={{ color: 'var(--text-dim)', fontStyle: 'italic' }}>
                                данные есть
                              </span>
                            </div>
                          )}
                        </div>
                      </td>
                    )
                  }

                  // not_filled
                  return <td key={col.col_key} />
                })}
              </tr>
            )
          })}
        </tbody>
      </table>

      {/* Legend */}
      <div className={styles.mxLegend}>
        <span className={styles.mxLegendItem}>
          <span className={styles.mxLegendDotFilled} />
          Данные есть — кликните для просмотра
        </span>
        <span className={styles.mxLegendItem}>
          <span className={styles.mxLegendDotNa} />
          Не применимо
        </span>
      </div>
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// Source Drawer
// ──────────────────────────────────────────────────────────────

interface SourceDrawerProps {
  sources: ParsedSource[] | null
  onClose: () => void
}

function SourceDrawer({ sources, onClose }: SourceDrawerProps) {
  const isOpen = sources !== null

  return (
    <>
      {isOpen && <div className={styles.drawerOverlay} onClick={onClose} />}
      <div className={`${styles.sourceDrawer} ${isOpen ? styles.drawerOpen : ''}`}>
        <div className={styles.drawerHd}>
          <span>Источники раздела</span>
          <button className={styles.drawerClose} onClick={onClose}>
            ✕
          </button>
        </div>
        <div className={styles.drawerBody}>
          {(sources ?? []).map((src, i) => (
            <div className={styles.drawerSourceRow} key={i}>
              <span className={styles.drawerSrcNum}>{i + 1}</span>
              {src.url ? (
                <a href={src.url} target="_blank" rel="noopener noreferrer">
                  {src.title || getHostname(src.url)} ↗
                </a>
              ) : (
                <span>{src.text}</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

// ──────────────────────────────────────────────────────────────
// Skeleton helpers
// ──────────────────────────────────────────────────────────────

function SkeletonBlock({ height = 18, width = '100%' }: { height?: number; width?: string | number }) {
  return (
    <div
      className={styles.skeleton}
      style={{ height, width, marginBottom: 8 }}
    />
  )
}

// ──────────────────────────────────────────────────────────────
// CellDetailPage
// ──────────────────────────────────────────────────────────────

export default function CellDetailPage() {
  const { venueKey, cellId } = useParams<{ venueKey: string; cellId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()

  const viewMode: ViewMode = (searchParams.get('view') as ViewMode) ?? 'tabs'
  const phaseParam = searchParams.get('phase') ?? 'admission'

  // Data state
  const [venue, setVenue] = useState<VenueCard | null>(null)
  const [cellContent, setCellContent] = useState<CellContent | null>(null)
  const [cellParameters, setCellParameters] = useState<CellParameters | null>(null)
  const [matrixData, setMatrixData] = useState<MatrixView | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)

  // Active phase key (URL-controlled)
  const [activePhaseKey, setActivePhaseKey] = useState<string>(phaseParam)

  // Drawer
  const [drawerSources, setDrawerSources] = useState<ParsedSource[] | null>(null)

  const load = useCallback(() => {
    if (!venueKey || !cellId) return
    setLoading(true)
    setError(null)
    setNotFound(false)

    fetchVenue(venueKey)
      .then((v) => {
        setVenue(v)

        // Find cell in venue
        const foundCell = v.cells.find((c) => c.cell_id === cellId)
        if (!foundCell) {
          setNotFound(true)
          setLoading(false)
          return Promise.reject(new Error('__not_found__'))
        }

        const nameRu = v.jurisdiction_ru
        return Promise.all([
          fetchCellContent(cellId, nameRu, venueKey),
          fetchCellParameters(cellId, nameRu, venueKey).catch(() => null),
          fetchMatrix(cellId, nameRu, venueKey).catch(() => null),
        ])
      })
      .then((results) => {
        if (!results) return
        const [content, params, matrix] = results
        setCellContent(content)
        setCellParameters(params)
        setMatrixData(matrix)

        // Determine active phase — always use one of the 3 DISPLAY_PHASES keys
        const requestedPhase = phaseParam
        const validDisplayKey = DISPLAY_PHASES.some((dp) => dp.key === requestedPhase)
        const defaultKey = validDisplayKey ? requestedPhase : 'admission'
        setActivePhaseKey(defaultKey)
      })
      .catch((e: Error) => {
        if (e.message !== '__not_found__') {
          setError(e.message)
        }
      })
      .finally(() => setLoading(false))
  }, [venueKey, cellId, phaseParam])

  useEffect(load, [load])

  // URL param updaters
  const handlePhaseChange = useCallback(
    (key: string) => {
      setActivePhaseKey(key)
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          next.set('phase', key)
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  const handleViewToggle = useCallback(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.set('view', viewMode === 'matrix' ? 'tabs' : 'matrix')
        return next
      },
      { replace: true },
    )
  }, [viewMode, setSearchParams])

  const switchToPhase = useCallback(
    (phaseKey: string) => {
      setActivePhaseKey(phaseKey)
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          next.set('view', 'tabs')
          next.set('phase', phaseKey)
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  // ── Render states ───────────────────────────────────────────

  if (loading) {
    return (
      <div className={styles.page}>
        <SkeletonBlock height={14} width={320} />
        <SkeletonBlock height={36} width={400} />
        <SkeletonBlock height={14} width={200} />
        <div style={{ marginTop: 24 }}>
          <SkeletonBlock height={200} />
          <SkeletonBlock height={200} />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={styles.page}>
        <div className={styles.emptyPhase}>
          Ошибка загрузки данных: {error}
        </div>
      </div>
    )
  }

  if (notFound || !venue || !cellContent) {
    return (
      <div className={styles.page}>
        <div className={styles.emptyPhase}>
          Ячейка не найдена. Проверьте адрес страницы.
        </div>
      </div>
    )
  }

  const venueName = venue.venue_name_ru ?? venue.venue_name_english
  const jurisdictionRu = venue.jurisdiction_ru
  const listingArchitecture = venue.listing_architecture

  // Find cell metadata from venue
  const cellMeta = venue.cells.find((c) => c.cell_id === cellId)

  return (
    <div className={styles.page}>
      {/* Breadcrumb */}
      <nav className={styles.breadcrumb}>
        <Link to="/jurisdictions">Справочник</Link>
        <span className={styles.breadcrumbSep}>→</span>
        {jurisdictionRu && (
          <>
            <Link to={`/jurisdictions/${encodeURIComponent(jurisdictionRu)}`}>
              {jurisdictionRu}
            </Link>
            <span className={styles.breadcrumbSep}>→</span>
          </>
        )}
        <Link to={`/venues/${encodeURIComponent(venueKey ?? '')}`}>{venueName}</Link>
        <span className={styles.breadcrumbSep}>→</span>
        <span>{cellContent.tier}</span>
      </nav>

      {/* Detail header */}
      <div className={styles.detailHd}>
        <div>
          <h1 className={styles.detailTitle}>{cellContent.tier}</h1>
          <div className={styles.detailSub}>
            {cellContent.instrument_class_label} · {venueName}
          </div>
          <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {cellMeta && <ValidationBadge status={cellMeta.validation_status} />}
            {listingArchitecture && (
              <span className={styles.statusBadge} style={{ background: 'var(--bg3)', color: 'var(--text-dim)', border: '1px solid var(--border2)' }}>
                {listingArchitecture}
              </span>
            )}
          </div>
        </div>
        <button className={styles.matrixBtn} onClick={handleViewToggle}>
          {viewMode === 'matrix' ? '← Обратно к разделам' : 'Вид: матрица'}
        </button>
      </div>

      {/* Tabs view */}
      {viewMode === 'tabs' && (
        <>
          <div className={styles.phaseTabs}>
            {DISPLAY_PHASES.map((dp) => (
              <button
                key={dp.key}
                className={`${styles.phaseTab} ${dp.key === activePhaseKey ? styles.phaseTabActive : ''}`}
                onClick={() => handlePhaseChange(dp.key)}
              >
                <span
                  className={styles.ptDot}
                  style={{ background: phaseColor(dp.key) }}
                />
                {dp.label}
              </button>
            ))}
          </div>

          {(() => {
            const activePhaseContent = cellContent.phases.find(
              (p) => p.phase_key === activePhaseKey,
            )
            if (!activePhaseContent) {
              const phaseLabel =
                DISPLAY_PHASES.find((dp) => dp.key === activePhaseKey)?.label ?? activePhaseKey
              return (
                <div className={styles.emptyPhase}>
                  Данные по фазе «{phaseLabel}» не извлечены
                </div>
              )
            }
            if (!activePhaseContent.has_data) {
              return <div className={styles.emptyPhase}>Данные в работе</div>
            }
            return (
              <>
                {activePhaseContent.sections.map((s) => {
                  const sectionParams = (cellParameters?.parameters ?? []).filter(
                    (p) => p.status === 'found' && p.section_keys?.includes(s.section_key),
                  )
                  return (
                    <SectionCard
                      key={s.section_key}
                      section={s}
                      parameters={sectionParams}
                    />
                  )
                })}
              </>
            )
          })()}
        </>
      )}

      {/* Matrix view */}
      {viewMode === 'matrix' && (
        matrixData ? (
          <MatrixViewPanel matrix={matrixData} cellParameters={cellParameters} onCellClick={switchToPhase} />
        ) : (
          <div className={styles.emptyPhase}>Матрица недоступна</div>
        )
      )}

      {/* Right source drawer */}
      <SourceDrawer
        sources={drawerSources}
        onClose={() => setDrawerSources(null)}
      />
    </div>
  )
}
