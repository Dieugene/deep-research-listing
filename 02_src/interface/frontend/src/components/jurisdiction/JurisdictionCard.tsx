import { Link } from 'react-router-dom'
import type { JurisdictionSummary } from '../../api/types'
import styles from './JurisdictionCard.module.css'

interface Props {
  jurisdiction: JurisdictionSummary
}

export default function JurisdictionCard({ jurisdiction }: Props) {
  const { name_ru, name_en, legal_family, venue_count, has_full_data } = jurisdiction

  return (
    <div className={`${styles.card} ${!has_full_data ? styles.dimmed : ''}`}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.nameRu}>{name_ru}</h3>
          <p className={styles.nameEn}>{name_en}</p>
        </div>
        {has_full_data ? (
          <span className={styles.badgeFull}>Данные</span>
        ) : (
          <span className={styles.badgePending}>Скоро</span>
        )}
      </div>

      <div className={styles.meta}>
        {legal_family && (
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Правовая семья</span>
            <span className={styles.metaValue}>{legal_family}</span>
          </div>
        )}
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Площадок</span>
          <span className={styles.metaValue}>{venue_count}</span>
        </div>
      </div>

      {has_full_data && (
        <Link
          to={`/jurisdictions/${encodeURIComponent(name_ru)}`}
          className={styles.link}
        >
          Открыть
        </Link>
      )}
    </div>
  )
}
