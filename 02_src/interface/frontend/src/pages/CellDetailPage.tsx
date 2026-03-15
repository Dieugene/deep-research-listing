import { useState, useEffect, useCallback } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { fetchVenue } from '../api/venues'
import { fetchCellContent, fetchCellParameters, fetchMatrix } from '../api/cells'
import type {
  VenueCard,
  CellContent,
  CellParameters,
  MatrixView,
  PhaseContent,
  ParameterValue,
  MatrixColumn,
} from '../api/types'
import LoadingState from '../components/common/LoadingState'
import ErrorState from '../components/common/ErrorState'
import styles from './CellDetailPage.module.css'

// ──────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────

interface ParsedSource {
  label: string
  url: string | null
}

function parseSources(sourceStr: string | undefined): ParsedSource[] {
  if (!sourceStr) return []
  return sourceStr
    .split(';')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => {
      const urlMatch = s.match(/(https?:\/\/[^\s]+)/)
      const url = urlMatch ? urlMatch[1] : null
      const label =
        s
          .replace(/(https?:\/\/[^\s]+)/, '')
          .replace(/[—–-]\s*$/, '')
          .trim() ||
        url ||
        s
      return { label, url }
    })
}

function statusDotColor(status: PhaseContent['validation_status']): string {
  switch (status) {
    case 'green':
      return '#10B981'
    case 'yellow':
      return '#F59E0B'
    case 'red':
      return '#EF4444'
    default:
      return '#9CA3AF'
  }
}

// ──────────────────────────────────────────────────────────────
// Sub-components
// ──────────────────────────────────────────────────────────────

interface SectionProps {
  text: string
  source: string | null
}

function SectionContent({ text, source }: SectionProps) {
  const paragraphs = text.split(/\n\n+/).filter(Boolean)
  const sources = parseSources(source ?? undefined)

  return (
    <div className={styles.sectionBody}>
      {paragraphs.map((p, i) => (
        <p key={i} className={styles.sectionText}>
          {p}
        </p>
      ))}
      {sources.length > 0 && (
        <div className={styles.sectionSources}>
          {sources.map((src, i) =>
            src.url ? (
              <span key={i} className={styles.srcItem}>
                <a
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.srcLink}
                >
                  {src.label}
                </a>
              </span>
            ) : (
              <span key={i} className={styles.srcItem}>
                {src.label}
              </span>
            ),
          )}
        </div>
      )}
    </div>
  )
}

interface ParamStripProps {
  params: ParameterValue[]
  phaseKey: string
}

function ParamStrip({ params, phaseKey }: ParamStripProps) {
  const filtered = params.filter((p) => p.lifecycle_phase_key === phaseKey)
  if (filtered.length === 0) return null

  return (
    <div className={styles.paramStrip}>
      {filtered.map((p) => {
        const sources = parseSources(p.source ?? undefined)
        const firstSrc = sources.find((s) => s.url)
        return (
          <div key={p.parameter_id} className={styles.paramRow}>
            <span className={styles.paramCode}>{p.parameter_id}</span>
            <span className={styles.paramName}>{p.parameter_name}:</span>
            <span className={styles.paramValue}>{p.value}</span>
            {firstSrc?.url && (
              <a
                href={firstSrc.url}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.paramSrc}
                title={firstSrc.label}
              >
                ↗
              </a>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// TabsView
// ──────────────────────────────────────────────────────────────

interface TabsViewProps {
  content: CellContent
  parameters: CellParameters | null
  activePhaseKey: string
  onPhaseChange: (key: string) => void
}

function TabsView({ content, parameters, activePhaseKey, onPhaseChange }: TabsViewProps) {
  const activePhase = content.phases.find((p) => p.phase_key === activePhaseKey) ?? content.phases[0]

  return (
    <>
      <div className={styles.phaseTabs}>
        {content.phases.map((phase) => (
          <button
            key={phase.phase_key}
            className={`${styles.phaseTab} ${phase.phase_key === activePhase?.phase_key ? styles.phaseTabActive : ''}`}
            onClick={() => onPhaseChange(phase.phase_key)}
          >
            <span
              className={styles.phaseTabDot}
              style={{ background: statusDotColor(phase.validation_status) }}
            />
            {phase.phase_label}
          </button>
        ))}
      </div>

      {activePhase && (
        <div className={styles.phaseContent}>
          {!activePhase.has_data ? (
            <div className={styles.emptyPhase}>Данные в работе</div>
          ) : (
            <>
              {activePhase.sections.map((section) => (
                <div key={section.section_key} className={styles.sectionCard}>
                  <div className={styles.sectionHd}>
                    <span className={styles.sectionLabel}>{section.section_label}</span>
                  </div>
                  <SectionContent text={section.text} source={section.source} />
                </div>
              ))}
              {parameters && (
                <ParamStrip params={parameters.parameters} phaseKey={activePhase.phase_key} />
              )}
            </>
          )}
        </div>
      )}
    </>
  )
}

// ──────────────────────────────────────────────────────────────
// MatrixViewPanel
// ──────────────────────────────────────────────────────────────

interface MatrixViewPanelProps {
  matrix: MatrixView
  onCellClick: (phaseKey: string) => void
}

function MatrixViewPanel({ matrix, onCellClick }: MatrixViewPanelProps) {
  // Gather all unique columns across all rows
  const allCols: MatrixColumn[] = matrix.rows.length > 0
    ? matrix.rows[0].columns
    : []

  return (
    <div className={styles.matrixWrap}>
      <table className={styles.matrixTable}>
        <thead>
          <tr>
            <th className={styles.matrixTh}>Фаза</th>
            {allCols.map((col) => (
              <th key={col.col_key} className={styles.matrixTh}>
                {col.col_label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.rows.map((row) => (
            <tr key={row.row_key}>
              <td className={styles.matrixTd}>
                <strong>{row.row_label}</strong>
              </td>
              {row.columns.map((col) => (
                <td key={col.col_key} className={styles.matrixTd}>
                  {col.status === 'not_applicable' ? (
                    <span className={styles.matrixNa}>—</span>
                  ) : (
                    <span
                      className={`${styles.matrixCell} ${col.status === 'filled' ? styles.matrixCellClickable : ''}`}
                      onClick={col.status === 'filled' ? () => onCellClick(row.row_key) : undefined}
                      title={col.status === 'filled' ? `Перейти к фазе: ${row.row_label}` : undefined}
                    >
                      <span
                        className={`${styles.matrixDot} ${col.status === 'filled' ? styles.matrixDotFilled : styles.matrixDotEmpty}`}
                      />
                      {col.status === 'filled' && col.text_volume > 0 && (
                        <span className={styles.matrixVol}>
                          {col.text_volume.toLocaleString('ru-RU')}
                        </span>
                      )}
                    </span>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// CellDetailPage
// ──────────────────────────────────────────────────────────────

type ViewMode = 'tabs' | 'matrix'

export default function CellDetailPage() {
  const { venueKey, cellId } = useParams<{ venueKey: string; cellId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()

  const viewMode: ViewMode = (searchParams.get('view') as ViewMode) ?? 'tabs'
  const phaseParam = searchParams.get('phase')

  // Data state
  const [venue, setVenue] = useState<VenueCard | null>(null)
  const [cellContent, setCellContent] = useState<CellContent | null>(null)
  const [cellParameters, setCellParameters] = useState<CellParameters | null>(null)
  const [matrixData, setMatrixData] = useState<MatrixView | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Derived active phase key (controlled via URL)
  const [activePhaseKey, setActivePhaseKey] = useState<string>('')

  const load = useCallback(() => {
    if (!venueKey || !cellId) return
    setLoading(true)
    setError(null)

    // Step 1: fetch venue to get jurisdiction_ru
    fetchVenue(venueKey)
      .then((v) => {
        setVenue(v)
        const nameRu = v.jurisdiction_ru

        // Step 2: fetch content, params and matrix in parallel
        return Promise.all([
          fetchCellContent(cellId, nameRu, venueKey),
          fetchCellParameters(cellId, nameRu, venueKey),
          fetchMatrix(cellId, nameRu, venueKey),
        ])
      })
      .then(([content, params, matrix]) => {
        setCellContent(content)
        setCellParameters(params)
        setMatrixData(matrix)

        // Determine initial active phase
        const requestedPhase = phaseParam
        const firstWithData = content.phases.find((p) => p.has_data)
        const defaultPhaseKey =
          (requestedPhase && content.phases.some((p) => p.phase_key === requestedPhase)
            ? requestedPhase
            : null) ??
          firstWithData?.phase_key ??
          content.phases[0]?.phase_key ??
          'admission'
        setActivePhaseKey(defaultPhaseKey)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [venueKey, cellId, phaseParam])

  useEffect(load, [load])

  // Sync phase into URL
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

  // Switch to tabs view and activate phase (from matrix click)
  const handleMatrixCellClick = useCallback(
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

  const handleViewChange = useCallback(
    (mode: ViewMode) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          next.set('view', mode)
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  if (loading) return <LoadingState message="Загрузка данных ячейки..." />
  if (error) return <ErrorState message={error} onRetry={load} />
  if (!venue || !cellContent) return <ErrorState message="Данные ячейки не найдены" />

  const jurisdictionRu = venue.jurisdiction_ru
  const venueName = venue.venue_name_ru ?? venue.venue_name_english
  const cellLabel = `${cellContent.tier} · ${cellContent.instrument_class_label}`

  // Find phase with overview status for header chips
  const activePhase = cellContent.phases.find((p) => p.phase_key === activePhaseKey)

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
        <span>{cellLabel}</span>
      </nav>

      {/* Header */}
      <div className={styles.header}>
        <div>
          <h1 className={styles.cellTitle}>{cellContent.tier}</h1>
          <p className={styles.cellSub}>{cellContent.instrument_class_label}</p>
        </div>

        <div className={styles.headerRight}>
          {/* View toggle */}
          <div className={styles.viewToggle}>
            <button
              className={`${styles.viewBtn} ${viewMode === 'tabs' ? styles.viewBtnActive : ''}`}
              onClick={() => handleViewChange('tabs')}
            >
              Вкладки
            </button>
            <button
              className={`${styles.viewBtn} ${viewMode === 'matrix' ? styles.viewBtnActive : ''}`}
              onClick={() => handleViewChange('matrix')}
            >
              Матрица
            </button>
          </div>

          {/* Validation badge for active phase */}
          {activePhase && (
            <span
              className={styles.validBadge}
              style={{
                background:
                  activePhase.validation_status === 'green'
                    ? 'rgba(16, 185, 129, 0.08)'
                    : activePhase.validation_status === 'yellow'
                      ? 'rgba(245, 158, 11, 0.08)'
                      : activePhase.validation_status === 'red'
                        ? 'rgba(239, 68, 68, 0.08)'
                        : 'rgba(156, 163, 175, 0.08)',
                color:
                  activePhase.validation_status === 'green'
                    ? '#065F46'
                    : activePhase.validation_status === 'yellow'
                      ? '#92400E'
                      : activePhase.validation_status === 'red'
                        ? '#991B1B'
                        : '#4B5563',
                border: `1px solid ${
                  activePhase.validation_status === 'green'
                    ? 'rgba(16, 185, 129, 0.2)'
                    : activePhase.validation_status === 'yellow'
                      ? 'rgba(245, 158, 11, 0.2)'
                      : activePhase.validation_status === 'red'
                        ? 'rgba(239, 68, 68, 0.2)'
                        : 'rgba(156, 163, 175, 0.2)'
                }`,
              }}
            >
              <span
                style={{
                  display: 'inline-block',
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: statusDotColor(activePhase.validation_status),
                }}
              />
              {activePhase.validation_status === 'green'
                ? 'Верифицировано'
                : activePhase.validation_status === 'yellow'
                  ? 'Проверить источники'
                  : activePhase.validation_status === 'red'
                    ? 'Ненадёжно'
                    : 'Статус неизвестен'}
            </span>
          )}
        </div>
      </div>

      {/* Main content */}
      {viewMode === 'tabs' ? (
        <TabsView
          content={cellContent}
          parameters={cellParameters}
          activePhaseKey={activePhaseKey}
          onPhaseChange={handlePhaseChange}
        />
      ) : matrixData ? (
        <MatrixViewPanel matrix={matrixData} onCellClick={handleMatrixCellClick} />
      ) : (
        <div className={styles.emptyPhase}>Матрица недоступна</div>
      )}
    </div>
  )
}
