import styles from './EmptyState.module.css'

interface Props {
  message?: string
  hint?: string
}

export default function EmptyState({
  message = 'Данные отсутствуют',
  hint,
}: Props) {
  return (
    <div className={styles.container}>
      <div className={styles.icon} aria-hidden="true">—</div>
      <p className={styles.message}>{message}</p>
      {hint && <p className={styles.hint}>{hint}</p>}
    </div>
  )
}
