import type { ValidationStatus } from '../../api/types'
import styles from './ValidationBadge.module.css'

interface Props {
  status: ValidationStatus
  size?: 'sm' | 'md'
}

const LABELS: Record<ValidationStatus, string> = {
  green: 'Верифицировано',
  yellow: 'Проверить источники',
  red: 'Ненадёжно',
  unknown: 'Статус неизвестен',
}

export default function ValidationBadge({ status, size = 'md' }: Props) {
  return (
    <span className={`${styles.badge} ${styles[status]} ${styles[size]}`}>
      <span className={styles.dot} />
      {LABELS[status]}
    </span>
  )
}
