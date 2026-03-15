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
  SourceCitation,
} from '../api/types'
import styles from './CellDetailPage.module.css'

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

function parseSrcString(source: string): ParsedSource[] {
  return source
    .split(';')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((fragment) => {
      if (fragment.includes('http')) {
        return { url: fragment }
      }
      return { text: fragment }
    })
}

function getSources(section: ContentSection): ParsedSource[] {
  if (section.citations && section.citations.length > 0) {
    return section.citations.map((c: SourceCitation) => ({
      url: c.url || undefined,
      text: c.title || undefined,
      title: c.title || undefined,
    }))
  }
  if (section.source) {
    return parseSrcString(section.source)
  }
  return []
}

function phaseColor(phaseKey: string): string {
  switch (phaseKey) {
    case 'admission':
      return '#3B82F6'
    case 'continuing':
      return '#10B981'
    case 'suspension':
      return '#F59E0B'
    case 'delisting':
      return '#F87171'
    default:
      return '#9CA3AF'
  }
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
  parameters: ParameterValue[]
  phaseKey: string
  onOpenDrawer: (sources: ParsedSource[]) => void
}

function SectionCard({ section, parameters, phaseKey, onOpenDrawer }: SectionCardProps) {
  const [expanded, setExpanded] = useState(false)

  const allSources = getSources(section)
  const sourcesCount = allSources.length
  const displayedSources = expanded ? allSources : allSources.slice(0, 3)

  const paragraphs = section.text.split('\n\n').filter(Boolean)

  const sectionParams = parameters.filter(
    (p) =>
      (p.lifecycle_phase_key === phaseKey || (p as ParameterValue & { phase_key?: string }).phase_key === phaseKey) &&
      p.status === 'found',
  )
  const hasParameters = sectionParams.length > 0

  return (
    <div className={styles.sectionCard}>
      <div className={styles.sectionCardHd}>
        <span className={styles.sectionCardTitle}>{section.section_label}</span>
        {sourcesCount > 0 && (
          <button className={styles.srcBtn} onClick={() => onOpenDrawer(allSources)}>
            {sourcesCount} источника(ов)
          </button>
        )}
      </div>

      <div className={styles.sectionCardBody}>
        {paragraphs.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>

      {hasParameters && (
        <div className={styles.paramsStrip}>
          {sectionParams.map((p) => (
            <div key={p.parameter_id} className={styles.paramChip}>
              <span className={styles.paramCode}>{p.parameter_id}</span>
              <span>{p.parameter_name || p.parameter_id}:</span>
              <span className={styles.paramVal}>{p.value}</span>
            </div>
          ))}
        </div>
      )}

      {sourcesCount > 0 && (
        <div className={styles.sourcesFooter}>
          {displayedSources.map((src, i) => (
            <div className={styles.sourceRow} key={i}>
              <span className={styles.srcNum}>{i + 1}</span>
              <span className={styles.srcTxt}>
                {src.url ? (
                  <a
                    className={styles.srcLnk}
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {src.title || getHostname(src.url)} ↗
                  </a>
                ) : (
                  src.text
                )}
              </span>
            </div>
          ))}
          {allSources.length > 3 && (
            <button
              className={styles.srcExpandBtn}
              onClick={() => setExpanded((prev) => !prev)}
            >
              {expanded ? '↑ Свернуть' : `Показать ещё ${allSources.length - 3}`}
            </button>
          )}
        </div>
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

const MATRIX_COL_LABELS: Record<string, string> = {
  requirements: 'Требования',
  procedures: 'Процедуры',
  monitoring: 'Мониторинг и надзор',
  sanctions: 'Санкции',
  disclosure: 'Раскрытие информации',
}

interface MatrixViewPanelProps {
  matrix: MatrixView
  onCellClick: (phaseKey: string) => void
}

function MatrixViewPanel({ matrix, onCellClick }: MatrixViewPanelProps) {
  const allCols = matrix.rows.length > 0 ? matrix.rows[0].columns : []

  return (
    <div className={styles.matrixWrap}>
      <table className={styles.mxTable}>
        <thead>
          <tr>
            <th>Фаза</th>
            {allCols.map((col) => (
              <th key={col.col_key}>
                {MATRIX_COL_LABELS[col.col_key] ?? col.col_label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.rows.map((row) => (
            <tr key={row.row_key}>
              <td className={styles.mxPhaseLabel}>
                <span className={styles.mxPhaseName}>{row.row_label}</span>
              </td>
              {row.columns.map((col) => {
                if (col.status === 'not_applicable') {
                  return (
                    <td key={col.col_key} className={styles.mxCellNa}>
                      <span className={styles.mxNaLabel}>—</span>
                    </td>
                  )
                }
                if (col.status === 'filled') {
                  return (
                    <td
                      key={col.col_key}
                      className={styles.mxCell}
                      onClick={() => onCellClick(row.row_key)}
                    >
                      <div className={styles.mxPills}>
                        <div className={styles.mxPill}>
                          <span className={styles.mxPillCode}>{col.col_key}</span>
                          <span className={styles.mxPillVal}>
                            {col.text_volume > 0
                              ? `${col.text_volume.toLocaleString('ru-RU')} симв.`
                              : MATRIX_COL_LABELS[col.col_key] ?? col.col_label}
                          </span>
                        </div>
                      </div>
                    </td>
                  )
                }
                // not_filled
                return <td key={col.col_key} />
              })}
            </tr>
          ))}
        </tbody>
      </table>
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

        // Determine active phase
        const requestedPhase = phaseParam
        const firstWithData = content.phases.find((p) => p.has_data)
        const defaultKey =
          (requestedPhase && content.phases.some((p) => p.phase_key === requestedPhase)
            ? requestedPhase
            : null) ??
          firstWithData?.phase_key ??
          content.phases[0]?.phase_key ??
          'admission'
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

  const activePhaseContent = cellContent.phases.find((p) => p.phase_key === activePhaseKey) ?? cellContent.phases[0]

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
            {cellContent.phases.map((p) => (
              <button
                key={p.phase_key}
                className={`${styles.phaseTab} ${p.phase_key === activePhaseKey ? styles.phaseTabActive : ''}`}
                onClick={() => handlePhaseChange(p.phase_key)}
              >
                <span
                  className={styles.ptDot}
                  style={{ background: phaseColor(p.phase_key) }}
                />
                {p.phase_label}
              </button>
            ))}
          </div>

          {activePhaseContent ? (
            !activePhaseContent.has_data ? (
              <div className={styles.emptyPhase}>Данные в работе</div>
            ) : (
              <>
                {activePhaseContent.sections.map((section) => (
                  <SectionCard
                    key={section.section_key}
                    section={section}
                    parameters={cellParameters?.parameters ?? []}
                    phaseKey={activePhaseKey}
                    onOpenDrawer={(sources) => setDrawerSources(sources)}
                  />
                ))}
                <ParamStrip phase={activePhaseKey} parameters={cellParameters} />
              </>
            )
          ) : (
            <div className={styles.emptyPhase}>Фаза не найдена</div>
          )}
        </>
      )}

      {/* Matrix view */}
      {viewMode === 'matrix' && (
        matrixData ? (
          <MatrixViewPanel matrix={matrixData} onCellClick={switchToPhase} />
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
