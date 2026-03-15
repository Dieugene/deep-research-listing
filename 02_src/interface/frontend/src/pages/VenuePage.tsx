import React, { useEffect, useState } from 'react'
import { useParams, useSearchParams, useNavigate, Link } from 'react-router-dom'
import { fetchVenue } from '../api/venues'
import type { VenueCard, CellInVenue } from '../api/types'
import LoadingState from '../components/common/LoadingState'
import ErrorState from '../components/common/ErrorState'
import styles from './VenuePage.module.css'

// ──────────────────────────────────────────────────────────────
// Constants
// ──────────────────────────────────────────────────────────────

const INSTRUMENT_ORDER = ['equity', 'bond', 'fund', 'depositary_receipt']

const SOURCES_INITIAL_COUNT = 5

// ──────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────

function getHostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

// ──────────────────────────────────────────────────────────────
// Validation badge sub-component
// ──────────────────────────────────────────────────────────────

interface ValidationBadgeProps {
  status: CellInVenue['validation_status']
}

function ValidationBadge({ status }: ValidationBadgeProps) {
  const map: Record<string, { cls: string; label: string }> = {
    green:   { cls: styles.validGreen,   label: 'Верифицировано' },
    yellow:  { cls: styles.validYellow,  label: 'Проверить'      },
    red:     { cls: styles.validRed,     label: 'Ненадёжно'      },
    unknown: { cls: styles.validUnknown, label: 'Неизвестно'     },
  }
  const { cls, label } = map[status] ?? map.unknown
  return (
    <span className={`${styles.validBadge} ${cls}`}>
      <span className={styles.validDot} />
      {label}
    </span>
  )
}

// ──────────────────────────────────────────────────────────────
// Cell card sub-component
// ──────────────────────────────────────────────────────────────

interface CellCardProps {
  cell: CellInVenue
  venueKey: string
}

function CellCard({ cell, venueKey }: CellCardProps) {
  const tierLabel = cell.tier && cell.tier !== cell.instrument_class_label
    ? cell.tier
    : cell.instrument_class_label

  return (
    <Link
      to={`/venues/${venueKey}/${cell.cell_id}`}
      className={styles.cellCard}
    >
      <div className={styles.cellCardHd}>
        <span className={styles.cellTierName}>{tierLabel}</span>
        <ValidationBadge status={cell.validation_status} />
        <span className={styles.cellArrow}>→</span>
      </div>
      <div className={styles.cellBody}>
        <div className={styles.cellCol}>
          <span className={styles.cellColLabel}>Допуск</span>
          {cell.has_admission_data
            ? <span className={styles.cellColCheck}>✓</span>
            : <span className={styles.cellColDash}>—</span>}
        </div>
        <div className={styles.cellCol}>
          <span className={styles.cellColLabel}>Поддержание</span>
          {cell.has_maintenance_data
            ? <span className={styles.cellColCheck}>✓</span>
            : <span className={styles.cellColDash}>—</span>}
        </div>
        <div className={styles.cellCol}>
          <span className={styles.cellColLabel}>Исключение</span>
          {cell.has_enforcement_data
            ? <span className={styles.cellColCheck}>✓</span>
            : <span className={styles.cellColDash}>—</span>}
        </div>
      </div>
    </Link>
  )
}

// ──────────────────────────────────────────────────────────────
// Sources section sub-component
// ──────────────────────────────────────────────────────────────

interface SourceItem {
  url: string
  title: string
  field?: string
}

interface SourcesSectionProps {
  sources: SourceItem[]
}

function SourcesSection({ sources }: SourcesSectionProps) {
  const [expanded, setExpanded] = useState(false)

  if (!sources.length) return null

  const visible = expanded ? sources : sources.slice(0, SOURCES_INITIAL_COUNT)
  const hidden = sources.length - SOURCES_INITIAL_COUNT

  return (
    <section className={styles.sourcesSection}>
      <h3 className={styles.sourcesSectionTitle}>Источники</h3>
      <ol className={styles.sourcesList}>
        {visible.map((src, i) => {
          const hostname = getHostname(src.url)
          const label = src.title || hostname
          return (
            <li key={i} className={styles.sourceItem}>
              <span className={styles.sourceNum}>{i + 1}</span>
              <span className={styles.sourceLabel}>{label}</span>
              <a
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.sourceLink}
              >
                {hostname} ↗
              </a>
            </li>
          )
        })}
      </ol>
      {!expanded && hidden > 0 && (
        <button
          className={styles.sourcesToggle}
          onClick={() => setExpanded(true)}
        >
          показать все {sources.length}
        </button>
      )}
    </section>
  )
}

// ──────────────────────────────────────────────────────────────
// Main page component
// ──────────────────────────────────────────────────────────────

export default function VenuePage() {
  const { venueKey } = useParams<{ venueKey: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  const [data, setData] = useState<VenueCard | null>(null)
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
  if (error)   return <ErrorState message={error} onRetry={load} />
  if (!data)   return <ErrorState message="Площадка не найдена" />

  // ── Instrument tabs ──────────────────────────────────────────

  // Build ordered list of unique instrument tabs
  type InstrTab = { key: string; label: string; count: number }
  const tabMap = new Map<string, InstrTab>()
  for (const cell of data.cells) {
    const existing = tabMap.get(cell.instrument_class_key)
    if (existing) {
      existing.count += 1
    } else {
      tabMap.set(cell.instrument_class_key, {
        key:   cell.instrument_class_key,
        label: cell.instrument_class_label,
        count: 1,
      })
    }
  }

  // Order tabs by INSTRUMENT_ORDER, then any unrecognised keys appended
  const tabs: InstrTab[] = [
    ...INSTRUMENT_ORDER.flatMap(k => tabMap.has(k) ? [tabMap.get(k)!] : []),
    ...[...tabMap.values()].filter(t => !INSTRUMENT_ORDER.includes(t.key)),
  ]

  const activeTabKey = searchParams.get('tab') ?? (tabs[0]?.key ?? '')

  const setActiveTab = (key: string) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('tab', key)
      return next
    })
  }

  const activeCells = data.cells.filter(c => c.instrument_class_key === activeTabKey)

  // ── Meta bar ─────────────────────────────────────────────────

  const jurisdictionRu = data.jurisdiction_ru
  const totalCells = data.cells.length
  const instrCount = tabs.length

  // ── Notes ────────────────────────────────────────────────────

  const notesText = data.notes_ru || data.notes

  return (
    <div className={styles.page}>
      {/* ── Breadcrumb ──────────────────────────────────────── */}
      <nav className={styles.breadcrumb}>
        <Link to="/jurisdictions">Справочник</Link>
        <span className={styles.breadcrumbSep}>›</span>
        {jurisdictionRu && (
          <>
            <Link to={`/jurisdictions/${encodeURIComponent(jurisdictionRu)}`}>
              {jurisdictionRu}
            </Link>
            <span className={styles.breadcrumbSep}>›</span>
          </>
        )}
        <span>{data.venue_name_english}</span>
      </nav>

      {/* ── Header ──────────────────────────────────────────── */}
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.venueName}>
            {data.venue_name_ru || data.venue_name_english}
          </h1>
          <span className={styles.venueTypeBadge}>{data.venue_type}</span>
        </div>
        <p className={styles.venueSub}>
          {data.venue_name_english}
          {jurisdictionRu && (
            <> · {jurisdictionRu}</>
          )}
        </p>
      </header>

      {/* ── Meta bar ────────────────────────────────────────── */}
      <div className={styles.metaBar}>
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
            <span className={styles.metaBadge}>{data.listing_architecture}</span>
          </div>
        )}

        {data.secondary_listing_regime && (
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Вторичный листинг</span>
            <span className={styles.metaValue}>Предусмотрен ✓</span>
          </div>
        )}

        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Категорий</span>
          <span className={styles.metaValue}>
            {totalCells} <span className={styles.metaValueSub}>({instrCount} инструментов)</span>
          </span>
        </div>
      </div>

      {/* ── Notes ───────────────────────────────────────────── */}
      {notesText && (
        <div className={styles.notesSection}>
          <div className={styles.notesDivider} />
          <span className={styles.notesLabel}>Примечание</span>
          <p className={styles.notesText}>{notesText}</p>
        </div>
      )}

      {/* ── Instrument tabs ─────────────────────────────────── */}
      {tabs.length > 0 && (
        <div className={styles.instrTabs}>
          <div className={styles.instrTabsInner}>
            {tabs.map(tab => (
              <button
                key={tab.key}
                className={`${styles.instrTab} ${tab.key === activeTabKey ? styles.instrTabActive : ''}`}
                onClick={() => setActiveTab(tab.key)}
              >
                {tab.label}
                <span className={styles.instrTabCount}>{tab.count}</span>
              </button>
            ))}
          </div>
          <span className={styles.instrTabsTotal}>{totalCells} всего</span>
        </div>
      )}

      {/* ── Cell cards ──────────────────────────────────────── */}
      {activeCells.length > 0 ? (
        <div className={styles.cellsGrid}>
          {activeCells.map(cell => (
            <CellCard key={cell.cell_id} cell={cell} venueKey={data.venue_key} />
          ))}
        </div>
      ) : (
        <div className={styles.emptyInstr}>
          Нет данных для этого инструмента
        </div>
      )}

      {/* ── Sources ─────────────────────────────────────────── */}
      {data.sources && data.sources.length > 0 && (
        <SourcesSection sources={data.sources} />
      )}
    </div>
  )
}
