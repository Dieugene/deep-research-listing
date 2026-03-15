import { Fragment } from 'react'
import type { MatrixView } from '../../api/types'
import MatrixCell from './MatrixCell'
import styles from './LifecycleMatrix.module.css'

interface Props {
  data: MatrixView
  activeRow: string | null
  activeCol: string | null
  onCellClick: (rowKey: string, colKey: string) => void
}

export default function LifecycleMatrix({ data, activeRow, activeCol, onCellClick }: Props) {
  const { rows } = data

  if (!rows.length) return null

  // Get column headers from first row
  const columns = rows[0]?.columns ?? []

  return (
    <div className={styles.wrapper}>
      <div
        className={styles.grid}
        style={{
          gridTemplateColumns: `180px repeat(${columns.length}, 1fr)`,
          gridTemplateRows: `auto repeat(${rows.length}, 1fr)`,
        }}
      >
        {/* Top-left corner */}
        <div className={styles.cornerCell} />

        {/* Column headers */}
        {columns.map((col) => (
          <div key={col.col_key} className={styles.colHeader}>
            {col.col_label}
          </div>
        ))}

        {/* Rows */}
        {rows.map((row) => (
          <Fragment key={row.row_key}>
            {/* Row header */}
            <div className={styles.rowHeader}>
              <span className={styles.rowIndex}>{row.row_index + 1}</span>
              {row.row_label}
            </div>

            {/* Cells */}
            {row.columns.map((col) => (
              <div key={`${row.row_key}-${col.col_key}`} className={styles.cellWrapper}>
                <MatrixCell
                  status={col.status}
                  textVolume={col.text_volume}
                  isActive={activeRow === row.row_key && activeCol === col.col_key}
                  rowLabel={row.row_label}
                  colLabel={col.col_label}
                  onClick={() => onCellClick(row.row_key, col.col_key)}
                />
              </div>
            ))}
          </Fragment>
        ))}
      </div>

      {/* Legend */}
      <div className={styles.legend}>
        <span className={styles.legendTitle}>Объём данных:</span>
        <span className={`${styles.legendItem} ${styles.legendHigh}`}>Высокий (&gt;5000)</span>
        <span className={`${styles.legendItem} ${styles.legendMed}`}>Средний (&gt;1000)</span>
        <span className={`${styles.legendItem} ${styles.legendLow}`}>Низкий</span>
        <span className={`${styles.legendItem} ${styles.legendEmpty}`}>Нет данных</span>
        <span className={`${styles.legendItem} ${styles.legendNa}`}>Не применимо</span>
      </div>
    </div>
  )
}
