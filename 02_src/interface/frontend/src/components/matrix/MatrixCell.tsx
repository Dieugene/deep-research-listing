import type { MatrixCellStatus } from '../../api/types'
import styles from './MatrixCell.module.css'

interface Props {
  status: MatrixCellStatus
  textVolume: number
  isActive: boolean
  rowLabel?: string
  colLabel?: string
  onClick: () => void
}

function getCellClass(status: MatrixCellStatus, textVolume: number): string {
  if (status === 'not_applicable') return styles.notApplicable
  if (status === 'not_filled') return styles.notFilled
  // filled — intensity based on textVolume
  if (textVolume > 5000) return styles.filledHigh
  if (textVolume > 1000) return styles.filledMed
  return styles.filledLow
}

export default function MatrixCell({
  status,
  textVolume,
  isActive,
  rowLabel,
  colLabel,
  onClick,
}: Props) {
  const cellClass = getCellClass(status, textVolume)
  const isClickable = status === 'filled'

  const title =
    rowLabel && colLabel
      ? `${rowLabel} × ${colLabel}${textVolume ? ` (${textVolume.toLocaleString('ru-RU')} симв.)` : ''}`
      : undefined

  return (
    <div
      className={`${styles.cell} ${cellClass} ${isActive ? styles.active : ''} ${isClickable ? styles.clickable : ''}`}
      onClick={isClickable ? onClick : undefined}
      title={title}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={
        isClickable
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onClick()
              }
            }
          : undefined
      }
    >
      {status === 'filled' && textVolume > 0 && (
        <span className={styles.volume}>
          {textVolume > 1000
            ? `${(textVolume / 1000).toFixed(1)}k`
            : textVolume}
        </span>
      )}
      {status === 'not_applicable' && (
        <span className={styles.naLabel}>н/п</span>
      )}
    </div>
  )
}
