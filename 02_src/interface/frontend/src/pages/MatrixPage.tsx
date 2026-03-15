import { useEffect, useState, useCallback } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { fetchMatrix, fetchCellContent, fetchCellParameters } from '../api/cells'
import type { MatrixView, CellContent, CellParameters } from '../api/types'
import LoadingState from '../components/common/LoadingState'
import ErrorState from '../components/common/ErrorState'
import ValidationBadge from '../components/common/ValidationBadge'
import LifecycleMatrix from '../components/matrix/LifecycleMatrix'
import CellDetailPanel from '../components/matrix/CellDetailPanel'
import styles from './MatrixPage.module.css'

export default function MatrixPage() {
  const { venueKey, cellId } = useParams<{ venueKey: string; cellId: string }>()
  const [searchParams] = useSearchParams()
  const nameRu = searchParams.get('name_ru') ?? ''
  const venueKeyParam = searchParams.get('venue_key') ?? venueKey ?? ''

  // Matrix
  const [matrix, setMatrix] = useState<MatrixView | null>(null)
  const [matrixLoading, setMatrixLoading] = useState(true)
  const [matrixError, setMatrixError] = useState<string | null>(null)

  // Selected cell
  const [activeRow, setActiveRow] = useState<string | null>(null)
  const [activeCol, setActiveCol] = useState<string | null>(null)
  const [activePhaseKey, setActivePhaseKey] = useState<string | null>(null)

  // Panel data
  const [cellContent, setCellContent] = useState<CellContent | null>(null)
  const [cellParameters, setCellParameters] = useState<CellParameters | null>(null)
  const [panelLoading, setPanelLoading] = useState(false)
  const [panelOpen, setPanelOpen] = useState(false)

  const loadMatrix = useCallback(() => {
    if (!cellId || !venueKeyParam) return
    setMatrixLoading(true)
    setMatrixError(null)
    fetchMatrix(cellId, nameRu, venueKeyParam)
      .then(setMatrix)
      .catch((e: Error) => setMatrixError(e.message))
      .finally(() => setMatrixLoading(false))
  }, [cellId, nameRu, venueKeyParam])

  useEffect(loadMatrix, [loadMatrix])

  // Load panel content when a cell is clicked
  const handleCellClick = useCallback(
    (rowKey: string, colKey: string) => {
      setActiveRow(rowKey)
      setActiveCol(colKey)
      setPanelOpen(true)
      setPanelLoading(true)
      setCellContent(null)
      setCellParameters(null)

      // Map rowKey → phase key (row is lifecycle phase)
      // The rowKey from MatrixRow corresponds to the phase
      setActivePhaseKey(rowKey)

      if (!cellId || !venueKeyParam) return

      Promise.all([
        fetchCellContent(cellId, nameRu, venueKeyParam),
        fetchCellParameters(cellId, nameRu, venueKeyParam),
      ])
        .then(([content, params]) => {
          setCellContent(content)
          setCellParameters(params)
          // Set active phase based on rowKey
          setActivePhaseKey(rowKey)
        })
        .catch(() => {
          // Panel shows empty state
        })
        .finally(() => setPanelLoading(false))
    },
    [cellId, nameRu, venueKeyParam],
  )

  if (matrixLoading) return <LoadingState message="Загрузка матрицы..." />
  if (matrixError) return <ErrorState message={matrixError} onRetry={loadMatrix} />
  if (!matrix) return <ErrorState message="Данные матрицы не найдены" />

  return (
    <div className={styles.page}>
      <div className={styles.inner}>
        {/* Breadcrumb */}
        <nav className={styles.breadcrumb}>
          <Link to="/jurisdictions">Справочник</Link>
          <span className={styles.sep}>→</span>
          {nameRu && (
            <>
              <Link to={`/jurisdictions/${encodeURIComponent(nameRu)}`}>
                {nameRu}
              </Link>
              <span className={styles.sep}>→</span>
            </>
          )}
          {venueKey && (
            <>
              <Link
                to={`/venues/${encodeURIComponent(venueKey)}?name_ru=${encodeURIComponent(nameRu)}`}
              >
                {venueKey}
              </Link>
              <span className={styles.sep}>→</span>
            </>
          )}
          <span className={styles.breadcrumbCurrent}>
            {matrix.tier} · {matrix.instrument_class_label}
          </span>
        </nav>

        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <h1 className={styles.title}>
              {matrix.tier}
              <span className={styles.titleSep}>/</span>
              {matrix.instrument_class_label}
            </h1>
            <div className={styles.headerMeta}>
              <span className={styles.metaTag}>
                <code>{matrix.cell_id}</code>
              </span>
              <span className={styles.metaTag}>{matrix.venue_key}</span>
            </div>
          </div>
          <ValidationBadge status={matrix.validation_status} />
        </div>

        {/* Instruction hint */}
        {!panelOpen && (
          <div className={styles.hint}>
            Нажмите на заполненную ячейку матрицы для просмотра требований
          </div>
        )}

        {/* Matrix + Panel layout */}
        <div className={`${styles.workspace} ${panelOpen ? styles.workspaceWithPanel : ''}`}>
          <div className={styles.matrixArea}>
            <LifecycleMatrix
              data={matrix}
              activeRow={activeRow}
              activeCol={activeCol}
              onCellClick={handleCellClick}
            />
          </div>

          {panelOpen && (
            <div className={styles.panelArea}>
              <CellDetailPanel
                cellContent={cellContent}
                cellParameters={cellParameters}
                activePhaseKey={activePhaseKey}
                loading={panelLoading}
                onClose={() => {
                  setPanelOpen(false)
                  setActiveRow(null)
                  setActiveCol(null)
                }}
              />
            </div>
          )}
        </div>

        {/* Matrix stats */}
        <div className={styles.stats}>
          <div className={styles.statsItem}>
            <span className={styles.statsLabel}>Строк (фаз):</span>
            <span className={styles.statsValue}>{matrix.rows.length}</span>
          </div>
          <div className={styles.statsItem}>
            <span className={styles.statsLabel}>Столбцов (аспектов):</span>
            <span className={styles.statsValue}>{matrix.rows[0]?.columns.length ?? 0}</span>
          </div>
          <div className={styles.statsItem}>
            <span className={styles.statsLabel}>Заполненных ячеек:</span>
            <span className={styles.statsValue}>
              {matrix.rows
                .flatMap((r) => r.columns)
                .filter((c) => c.status === 'filled').length}
            </span>
          </div>
          <div className={styles.statsItem}>
            <span className={styles.statsLabel}>Общий объём:</span>
            <span className={styles.statsValue}>
              {matrix.rows
                .flatMap((r) => r.columns)
                .reduce((s, c) => s + c.text_volume, 0)
                .toLocaleString('ru-RU')}{' '}
              симв.
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
