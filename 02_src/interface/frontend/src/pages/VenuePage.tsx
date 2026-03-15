import { useEffect, useState } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { fetchVenue } from '../api/venues'
import type { VenueCard as VenueCardType } from '../api/types'
import LoadingState from '../components/common/LoadingState'
import ErrorState from '../components/common/ErrorState'
import CellsGrid from '../components/venue/CellsGrid'
import styles from './VenuePage.module.css'

export default function VenuePage() {
  const { venueKey } = useParams<{ venueKey: string }>()
  const [searchParams] = useSearchParams()
  const nameRu = searchParams.get('name_ru') ?? ''

  const [data, setData] = useState<VenueCardType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    if (!venueKey) return
    setLoading(true)
    setError(null)
    fetchVenue(venueKey)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [venueKey])

  if (loading) return <LoadingState message="Загрузка данных площадки..." />
  if (error) return <ErrorState message={error} onRetry={load} />
  if (!data) return <ErrorState message="Площадка не найдена" />

  const jurisdictionRu = data.jurisdiction_ru || nameRu

  return (
    <div className={styles.page}>
      <div className={styles.inner}>
        {/* Breadcrumb */}
        <nav className={styles.breadcrumb}>
          <Link to="/jurisdictions">Справочник</Link>
          <span className={styles.sep}>→</span>
          {jurisdictionRu && (
            <>
              <Link to={`/jurisdictions/${encodeURIComponent(jurisdictionRu)}`}>
                {jurisdictionRu}
              </Link>
              <span className={styles.sep}>→</span>
            </>
          )}
          <span>{data.venue_name_english}</span>
        </nav>

        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerInfo}>
            <div className={styles.headerTop}>
              <h1 className={styles.title}>{data.venue_name_ru || data.venue_name_english}</h1>
              <span className={styles.typeBadge}>{data.venue_type}</span>
            </div>
            {data.venue_name_local && (
              <p className={styles.nameLocal}>{data.venue_name_local}</p>
            )}
            {data.venue_name_ru && data.venue_name_ru !== data.venue_name_english && (
              <p className={styles.nameEn}>{data.venue_name_english}</p>
            )}
          </div>

          {/* Meta */}
          <div className={styles.meta}>
            {jurisdictionRu && (
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Юрисдикция</span>
                <Link
                  to={`/jurisdictions/${encodeURIComponent(jurisdictionRu)}`}
                  className={styles.metaLink}
                >
                  {jurisdictionRu}
                </Link>
              </div>
            )}
            {data.operator && (
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Оператор</span>
                <span className={styles.metaValue}>{data.operator}</span>
              </div>
            )}
            {data.listing_architecture && (
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Архитектура</span>
                <span className={styles.metaValue}>{data.listing_architecture}</span>
              </div>
            )}
            {data.secondary_listing_regime && (
              <div className={styles.metaItem}>
                <span className={styles.regimeBadge}>Вторичный листинг</span>
              </div>
            )}
          </div>
        </div>

        {/* Notes */}
        {(data.notes_ru || data.notes) && (
          <div className={styles.notes}>
            <p>{data.notes_ru || data.notes}</p>
          </div>
        )}

        {/* Cells */}
        <section className={styles.cellsSection}>
          <div className={styles.cellsHeader}>
            <h2 className={styles.cellsTitle}>
              Матрица ячеек
              <span className={styles.cellCount}>{data.cells.length}</span>
            </h2>
            <p className={styles.cellsHint}>
              Выберите ячейку для просмотра требований по фазам жизненного цикла
            </p>
          </div>
          <CellsGrid
            cells={data.cells}
            venueKey={data.venue_key}
            jurisdictionNameRu={jurisdictionRu}
          />
        </section>
      </div>
    </div>
  )
}
