import { Link } from 'react-router-dom'
import type { VenueInJurisdiction } from '../../api/types'
import styles from './VenueCard.module.css'

interface Props {
  venue: VenueInJurisdiction
  jurisdictionNameRu: string
}

export default function VenueCard({ venue, jurisdictionNameRu }: Props) {
  const { venue_key, name, name_ru, venue_type, cell_count } = venue

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div>
          <h4 className={styles.name}>{name_ru || name}</h4>
          {name_ru && name_ru !== name && (
            <p className={styles.nameEn}>{name}</p>
          )}
        </div>
        <span className={styles.type}>{venue_type}</span>
      </div>

      <div className={styles.meta}>
        <span className={styles.cellCount}>
          {cell_count} {cell_count === 1 ? 'ячейка' : cell_count < 5 ? 'ячейки' : 'ячеек'}
        </span>
      </div>

      <Link
        to={`/venues/${encodeURIComponent(venue_key)}?name_ru=${encodeURIComponent(jurisdictionNameRu)}`}
        className={styles.link}
      >
        Открыть площадку
      </Link>
    </div>
  )
}
