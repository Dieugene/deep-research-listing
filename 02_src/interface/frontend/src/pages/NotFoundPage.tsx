import { Link, useLocation } from 'react-router-dom'
import styles from './NotFoundPage.module.css'

export default function NotFoundPage() {
  const location = useLocation()

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        <div className={styles.code}>404</div>
        <h1 className={styles.title}>Страница не найдена</h1>
        <p className={styles.desc}>
          Страница <code className={styles.path}>{location.pathname}</code> не существует
          или была перемещена.
        </p>
        <div className={styles.actions}>
          <Link to="/" className={styles.btnPrimary}>
            На главную
          </Link>
          <Link to="/jurisdictions" className={styles.btnSecondary}>
            Справочник
          </Link>
        </div>
      </div>
    </div>
  )
}
