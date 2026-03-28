import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { fetchJurisdictions, fetchJurisdiction } from '../api/jurisdictions'
import type { JurisdictionSummary, VenueInJurisdiction } from '../api/types'
import WorldMap from '../components/map/WorldMap'
import styles from './HomePage.module.css'

export default function HomePage() {
  const navigate = useNavigate()
  const [jurisdictions, setJurisdictions] = useState<JurisdictionSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [venueMap, setVenueMap] = useState<Record<string, VenueInJurisdiction[]>>({})
  const [activeIndex, setActiveIndex] = useState(0)
  const [previewVisible, setPreviewVisible] = useState(false)

  useEffect(() => {
    fetchJurisdictions()
      .then(setJurisdictions)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  // Pre-fetch venues for active jurisdictions
  useEffect(() => {
    if (jurisdictions.length === 0) return
    jurisdictions.filter((j) => j.has_full_data).forEach(async (j) => {
      try {
        const card = await fetchJurisdiction(j.name_ru)
        setVenueMap((prev) => ({ ...prev, [j.name_ru]: card.venues }))
      } catch {
        // ignore per-jurisdiction fetch errors
      }
    })
  }, [jurisdictions])

  // Only jurisdictions with full data participate in the cycle
  const activeJurisdictions = jurisdictions.filter((j) => j.has_full_data)

  // Auto-cycle every 4 seconds with fade transition
  useEffect(() => {
    if (activeJurisdictions.length === 0) return
    const id = setInterval(() => {
      setPreviewVisible(false)
      setTimeout(() => {
        setActiveIndex((i) => (i + 1) % activeJurisdictions.length)
        setPreviewVisible(true)
      }, 300)
    }, 4000)
    return () => clearInterval(id)
  }, [activeJurisdictions.length])

  // Show initial preview once jurisdictions are loaded
  useEffect(() => {
    if (loading || activeJurisdictions.length === 0) return
    setActiveIndex(0)
    setPreviewVisible(true)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading])

  const currentJurisdiction: JurisdictionSummary | null =
    activeJurisdictions[activeIndex] ?? null

  const currentVenues: VenueInJurisdiction[] =
    currentJurisdiction ? (venueMap[currentJurisdiction.name_ru] ?? []) : []

  const totalVenues = jurisdictions.reduce((sum, j) => sum + j.venue_count, 0)

  // Compute real cell count and instrument class count from loaded venue data
  const totalCells = Object.values(venueMap).reduce(
    (sum, venues) => sum + venues.reduce((s, v) => s + v.cell_count, 0),
    0,
  )
  const venuesFullyLoaded = Object.keys(venueMap).length === activeJurisdictions.length && activeJurisdictions.length > 0

  // Determine venue type badge label — use venueKey suffix heuristics
  const getVenueTag = (venueKey: string): string => {
    const key = venueKey.toLowerCase()
    if (key.includes('aim') || key.includes('mtf') || key.includes('growth') || key.includes('aquis')) {
      return 'MTF'
    }
    return 'REG'
  }

  return (
    <div className={styles.page}>
      {/* ── HERO ── */}
      <section className={styles.hero}>
        {/* Dot-grid decorative background */}
        <div className={styles.heroGrid} />

        {/* World map fills the entire hero */}
        <div className={styles.mapBackdrop}>
          <WorldMap
            jurisdictions={jurisdictions}
            activeJurisdiction={currentJurisdiction?.name_ru ?? null}
          />
        </div>

        {/* Gradient overlay — left heavy for text readability */}
        <div className={styles.heroOverlay} />

        {/* Left content block */}
        <div className={styles.heroInner}>
          <div className={styles.heroEyebrow}>Research Database</div>

          <h1 className={styles.heroTitle}>
            Глобальный справочник
            <br />
            <em>листинговых режимов</em>
          </h1>

          <p className={styles.heroSubtitle}>
            Структурированная аналитическая база регуляторных требований к листингу
            ценных бумаг: акций, облигаций, фондов, депозитарных расписок.
            Охватывает весь жизненный цикл: допуск, поддержание, исключение.
          </p>

          <div className={styles.heroActions}>
            <Link to="/jurisdictions" className={styles.btnPrimary}>
              <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
              Юрисдикции
            </Link>
            <Link to="/parameters" className={styles.btnSecondary}>
              Инструменты
              <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </Link>
          </div>

          {/* Stats strip */}
          <div className={styles.statsStrip}>
            <div className={styles.statItem}>
              <div className={styles.statVal}>{loading ? '—' : jurisdictions.length}</div>
              <div className={styles.statLabel}>Юрисдикций</div>
            </div>
            <div className={styles.statItem}>
              <div className={styles.statVal}>{loading ? '—' : totalVenues}</div>
              <div className={styles.statLabel}>Площадок</div>
            </div>
            <div className={styles.statItem}>
              <div className={styles.statVal}>{loading || !venuesFullyLoaded ? '—' : totalCells}</div>
              <div className={styles.statLabel}>Режимов</div>
            </div>
          </div>
        </div>

        {/* Preview panel — right side floating card, fully clickable */}
        {currentJurisdiction && (
          <div
            className={`${styles.previewPanel} ${previewVisible ? styles.previewVisible : styles.previewHidden}`}
            onClick={() => navigate(`/jurisdictions/${encodeURIComponent(currentJurisdiction.name_ru)}`)}
            style={{ cursor: 'pointer' }}
          >
            <div className={styles.previewHeader}>
              <div>
                <div className={styles.previewTitle}>{currentJurisdiction.name_ru}</div>
              </div>
              <span className={styles.previewVerified}>Верифицировано</span>
            </div>

            <div className={styles.previewSub}>
              {currentJurisdiction.name_en}
              {currentJurisdiction.legal_family ? ` · ${currentJurisdiction.legal_family}` : ''}
            </div>

            <div className={styles.previewRow}>
              <span className={styles.previewRowLabel}>Торговых площадок</span>
              <span className={styles.previewRowVal}>{currentJurisdiction.venue_count}</span>
            </div>

            {currentVenues.length > 0 && (
              <div className={`${styles.venueList} ${styles.venueListScrollable}`}>
                {currentVenues.map((v) => (
                  <div key={v.venue_key} className={styles.venueChip}>
                    <span className={styles.venueChipName}>{v.name}</span>
                    <span className={styles.venueChipTag}>{getVenueTag(v.venue_key)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
