import React, { useEffect, useState } from 'react'
import { useParams, useSearchParams, useNavigate, Link } from 'react-router-dom'
import { fetchVenue } from '../api/venues'
import type { VenueCard, CellInVenue, ParamPill } from '../api/types'
import styles from './VenuePage.module.css'

// ──────────────────────────────────────────────────────────────
// Constants
// ──────────────────────────────────────────────────────────────

const INSTRUMENT_ORDER = ['equity', 'bond', 'fund', 'depositary_receipt']

const INSTRUMENT_LABELS: Record<string, string> = {
  equity:              'Акции',
  bond:                'Облигации',
  fund:                'Фонды',
  depositary_receipt:  'Депозитарные расписки',
}

const VENUE_TYPE_LABELS: Record<string, string> = {
  regulated_market: 'Регулируемый рынок',
  mtf:              'МТП (многосторонняя торговая платформа)',
  exchange:         'Биржа',
}

const LISTING_ARCHITECTURE_LABELS: Record<string, string> = {
  split:  'Двухконтурная',
  merged: 'Единая',
}

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

function venueTypeRu(key: string): string {
  return VENUE_TYPE_LABELS[key] ?? key
}

function listingArchitectureRu(key: string): string {
  return LISTING_ARCHITECTURE_LABELS[key] ?? key
}

// ──────────────────────────────────────────────────────────────
// Skeleton placeholder
// ──────────────────────────────────────────────────────────────

function SkeletonBlock({ width, height }: { width: string; height: number }) {
  return (
    <div
      className={styles.skeleton}
      style={{ width, height: `${height}px`, borderRadius: 4 }}
    />
  )
}

function VenuePageSkeleton() {
  return (
    <div className={styles.page}>
      <SkeletonBlock width="260px" height={14} />
      <div style={{ marginTop: 20 }}>
        <SkeletonBlock width="480px" height={40} />
      </div>
      <div style={{ marginTop: 8 }}>
        <SkeletonBlock width="220px" height={14} />
      </div>
      <div style={{ marginTop: 20, display: 'flex', gap: 1 }}>
        {[1, 2, 3, 4].map(i => (
          <div key={i} style={{ flex: 1, padding: '10px 16px', background: 'var(--bg2, #fff)', border: '1px solid rgba(0,0,0,.10)' }}>
            <SkeletonBlock width="60%" height={9} />
            <div style={{ marginTop: 5 }}>
              <SkeletonBlock width="80%" height={13} />
            </div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 20 }}>
        {[1, 2].map(i => (
          <div key={i} style={{ marginBottom: 10, background: 'var(--bg2, #fff)', border: '1px solid rgba(0,0,0,.10)', borderRadius: 12 }}>
            <div style={{ padding: '12px 18px', background: '#F0F2F7', borderRadius: '12px 12px 0 0' }}>
              <SkeletonBlock width="200px" height={14} />
            </div>
            <div style={{ padding: '12px 16px', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 0 }}>
              {[1, 2, 3].map(j => (
                <div key={j} style={{ padding: '0 16px' }}>
                  <SkeletonBlock width="50%" height={9} />
                  <div style={{ marginTop: 8 }}>
                    <SkeletonBlock width="90%" height={12} />
                  </div>
                  <div style={{ marginTop: 5 }}>
                    <SkeletonBlock width="75%" height={12} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// ValidationBadge
// ──────────────────────────────────────────────────────────────

interface ValidationBadgeProps {
  status: CellInVenue['validation_status']
}

function ValidationBadge({ status }: ValidationBadgeProps) {
  const map: Record<string, { cls: string; label: string }> = {
    green:   { cls: styles.sbGreen,   label: 'Верифицировано'      },
    yellow:  { cls: styles.sbYellow,  label: 'Проверить источники' },
    red:     { cls: styles.sbRed,     label: 'Ненадёжно'           },
    unknown: { cls: styles.sbUnknown, label: 'Статус неизвестен'   },
  }
  const { cls, label } = map[status] ?? map.unknown
  return (
    <span className={`${styles.statusBadge} ${cls}`}>
      {label}
    </span>
  )
}

// ──────────────────────────────────────────────────────────────
// ParamPillItem
// ──────────────────────────────────────────────────────────────

interface ParamPillItemProps {
  pill: ParamPill
}

function ParamPillItem({ pill }: ParamPillItemProps) {
  return (
    <div className={styles.tcPill}>
      <span className={styles.tcPillCode}>{pill.code}</span>
      <span className={styles.tcPillName}>{pill.label}:</span>
      <span className={styles.tcPillVal}>{pill.value}</span>
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// ColSection — reusable column inside ModeCard body
// ──────────────────────────────────────────────────────────────

interface ColSectionProps {
  colClass: string
  label: string
  pills: ParamPill[]
  hasData: boolean
}

function ColSection({ colClass, label, pills, hasData }: ColSectionProps) {
  return (
    <div className={`${styles.tcCol} ${colClass}`}>
      <div className={styles.tcColName}>{label}</div>
      <div className={styles.tcPills}>
        {pills.length > 0 ? (
          pills.map((p, i) => <ParamPillItem key={i} pill={p} />)
        ) : hasData ? (
          <div className={styles.tcNoParams}>Параметры не извлечены</div>
        ) : (
          <div className={styles.tcNoData}>Нет данных</div>
        )}
      </div>
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// ModeCard
// ──────────────────────────────────────────────────────────────

interface ModeCardProps {
  cell: CellInVenue
  venueKey: string
}

function ModeCard({ cell, venueKey }: ModeCardProps) {
  const navigate = useNavigate()

  // Ensure arrays exist (back-compat when API doesn't yet return these fields)
  const paramsAdmission    = cell.params_admission    ?? []
  const paramsMaintenance  = cell.params_maintenance  ?? []
  const paramsEnforcement  = cell.params_enforcement  ?? []

  return (
    <div
      className={styles.tierCard}
      onClick={() => navigate(`/venues/${venueKey}/${cell.cell_id}`)}
    >
      <div className={styles.tcHd}>
        <div className={styles.tcHdLeft}>
          <div className={styles.tcTierName}>{cell.tier}</div>
          <div className={styles.tcTierEn}>{cell.instrument_class_label}</div>
        </div>
        <div className={styles.tcHdRight}>
          <ValidationBadge status={cell.validation_status} />
          <span className={styles.tcArrow}>→</span>
        </div>
      </div>

      <div className={styles.tcBody}>
        <ColSection
          colClass={styles.colAdmission}
          label="Допуск"
          pills={paramsAdmission}
          hasData={cell.has_admission_data}
        />
        <ColSection
          colClass={styles.colMaintenance}
          label="Поддержание"
          pills={paramsMaintenance}
          hasData={cell.has_maintenance_data}
        />
        <ColSection
          colClass={styles.colDelisting}
          label="Исключение"
          pills={paramsEnforcement}
          hasData={cell.has_enforcement_data}
        />
      </div>
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// SourcesSection
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
  const hiddenCount = sources.length - SOURCES_INITIAL_COUNT

  return (
    <section className={styles.sourcesSection}>
      <div className={styles.sourcesSectionTitle}>Источники</div>
      <div className={styles.sourcesList}>
        {visible.map((src, i) => {
          const hostname = getHostname(src.url)
          const label = src.title || hostname
          return (
            <div key={i} className={styles.sourceItem}>
              <span className={styles.sourceNum}>{i + 1}</span>
              <span className={styles.sourceTitle}>{label}</span>
              <a
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.sourceLink}
                onClick={e => e.stopPropagation()}
              >
                {hostname} ↗
              </a>
            </div>
          )
        })}
      </div>
      {!expanded && hiddenCount > 0 && (
        <button
          className={styles.showMoreBtn}
          onClick={() => setExpanded(true)}
        >
          Показать ещё {hiddenCount}
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

  const [data, setData]       = useState<VenueCard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  useEffect(() => {
    if (!venueKey) return
    setLoading(true)
    setError(null)
    fetchVenue(venueKey)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [venueKey])

  // ── Loading ────────────────────────────────────────────────
  if (loading) return <VenuePageSkeleton />

  // ── Error ──────────────────────────────────────────────────
  if (error) {
    return (
      <div className={styles.page}>
        <div className={styles.emptyState}>
          <div className={styles.emptyStateTitle}>Ошибка загрузки</div>
          <div>{error}</div>
        </div>
      </div>
    )
  }

  // ── Not found ──────────────────────────────────────────────
  if (!data) {
    return (
      <div className={styles.page}>
        <div className={styles.emptyState}>
          <div className={styles.emptyStateTitle}>Площадка не найдена</div>
        </div>
      </div>
    )
  }

  // ── Build tabs ─────────────────────────────────────────────
  type InstrTab = { key: string; labelRu: string; count: number }

  const tabMap = new Map<string, InstrTab>()
  for (const cell of data.cells) {
    const existing = tabMap.get(cell.instrument_class_key)
    if (existing) {
      existing.count += 1
    } else {
      tabMap.set(cell.instrument_class_key, {
        key:     cell.instrument_class_key,
        labelRu: INSTRUMENT_LABELS[cell.instrument_class_key] ?? cell.instrument_class_label,
        count:   1,
      })
    }
  }

  const tabs: InstrTab[] = [
    ...INSTRUMENT_ORDER.flatMap(k => (tabMap.has(k) ? [tabMap.get(k)!] : [])),
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

  // ── Derived display values ─────────────────────────────────
  const displayName   = data.venue_name_ru || data.venue_name_english
  const jurisdictionRu = data.jurisdiction_ru
  const notesText     = data.notes_ru || data.notes
  const venueTypeLabel = venueTypeRu(data.venue_type)
  const archLabel      = data.listing_architecture
    ? listingArchitectureRu(data.listing_architecture)
    : null

  return (
    <div className={styles.page}>

      {/* ── Breadcrumb ────────────────────────────────────── */}
      <nav className={styles.breadcrumb}>
        <Link to="/jurisdictions">Справочник</Link>
        <span>›</span>
        {jurisdictionRu && (
          <>
            <Link to={`/jurisdictions/${encodeURIComponent(jurisdictionRu)}`}>
              {jurisdictionRu}
            </Link>
            <span>›</span>
          </>
        )}
        <span>{displayName}</span>
      </nav>

      {/* ── Title ─────────────────────────────────────────── */}
      <h1 className={styles.venueTitle}>
        {displayName}
        {data.venue_type && (
          <span className={`${styles.chip} ${styles.chipReg}`}>
            {venueTypeLabel}
          </span>
        )}
        {data.secondary_listing_regime && (
          <span className={`${styles.chip} ${styles.chipSecondary}`}>
            Вторичный листинг
          </span>
        )}
      </h1>
      <div className={styles.venueSub}>
        {data.venue_name_english}
        {jurisdictionRu && ` · ${jurisdictionRu}`}
      </div>

      {/* ── Meta bar ──────────────────────────────────────── */}
      <div className={styles.metaBar}>
        <div className={styles.metaItem}>
          <span className={styles.metaLbl}>Юрисдикция</span>
          <span className={styles.metaVal}>
            {jurisdictionRu ? (
              <Link to={`/jurisdictions/${encodeURIComponent(jurisdictionRu)}`}>
                {jurisdictionRu}
              </Link>
            ) : '—'}
          </span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLbl}>Оператор</span>
          <span className={styles.metaVal}>{data.operator || '—'}</span>
        </div>
        {archLabel && (
          <div className={styles.metaItem}>
            <span className={styles.metaLbl}>Архитектура</span>
            <span className={styles.metaVal}>{archLabel}</span>
          </div>
        )}
        <div className={styles.metaItem}>
          <span className={styles.metaLbl}>Тип</span>
          <span className={styles.metaVal}>{venueTypeLabel}</span>
        </div>
      </div>

      {/* ── Notes ─────────────────────────────────────────── */}
      {notesText && (
        <div className={styles.notesBlock}>
          {notesText}
        </div>
      )}

      {/* ── Instrument tabs ───────────────────────────────── */}
      {tabs.length > 0 && (
        <div className={styles.instrTabs}>
          {tabs.map(tab => (
            <button
              key={tab.key}
              className={`${styles.instrTab} ${tab.key === activeTabKey ? styles.instrTabActive : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.labelRu}
              <span className={styles.instrTabCount}>{tab.count}</span>
            </button>
          ))}
        </div>
      )}

      {/* ── Cells grid ────────────────────────────────────── */}
      {activeCells.length > 0 ? (
        <div className={styles.cellsGrid}>
          {activeCells.map(cell => (
            <ModeCard key={cell.cell_id} cell={cell} venueKey={data.venue_key} />
          ))}
        </div>
      ) : (
        <div className={styles.emptyState}>
          <div className={styles.emptyStateTitle}>
            Нет данных по выбранному инструменту
          </div>
        </div>
      )}

      {/* ── Sources ───────────────────────────────────────── */}
      {data.sources && data.sources.length > 0 && (
        <SourcesSection sources={data.sources} />
      )}
    </div>
  )
}
