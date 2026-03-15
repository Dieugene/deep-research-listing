import styles from './ErrorState.module.css'

interface Props {
  message: string | null
  onRetry?: () => void
}

export default function ErrorState({ message, onRetry }: Props) {
  return (
    <div className={styles.container}>
      <div className={styles.icon} aria-hidden="true">!</div>
      <h3 className={styles.title}>Ошибка загрузки</h3>
      <p className={styles.message}>{message ?? 'Не удалось загрузить данные'}</p>
      {onRetry && (
        <button className={styles.retry} onClick={onRetry}>
          Повторить
        </button>
      )}
    </div>
  )
}
