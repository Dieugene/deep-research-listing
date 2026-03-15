import styles from './LoadingState.module.css'

interface Props {
  message?: string
}

export default function LoadingState({ message = 'Загрузка...' }: Props) {
  return (
    <div className={styles.container}>
      <div className={styles.spinner} aria-hidden="true" />
      <p className={styles.message}>{message}</p>
    </div>
  )
}
