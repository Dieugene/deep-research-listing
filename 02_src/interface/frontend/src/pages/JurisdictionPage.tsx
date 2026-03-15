import React, { useEffect, useState, useCallback } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { fetchJurisdiction } from '../api/jurisdictions'
import type { JurisdictionCard, Level4Item, SourceCitation } from '../api/types'
import LoadingState from '../components/common/LoadingState'
import ErrorState from '../components/common/ErrorState'
import styles from './JurisdictionPage.module.css'

// ──────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────

type TabKey = 'jurisdiction' | 'analysis' | 'terms' | 'sources'
type ViewMode = 'timeline' | 'list'
type EventType = 'problem' | 'contradiction' | 'parameter' | 'reform'

interface TimelineEvent {
  id: number
  type: EventType
  start: number
  end: number
  label: string
  /** Full item for drawer */
  item: Level4Item
  lane: number
}

type DrawerContent = {
  kind: 'event'
  event: TimelineEvent
} | {
  kind: 'venue'
  venueKey: string
  name: string
  nameEn: string
  venueType: string
  cellCount: number
}

// ──────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────


function parsePeriod(
  period?: string,
  year?: string,
): { start: number; end: number } | null {
  if (year) {
    const y = parseInt(year, 10)
    return isNaN(y) ? null : { start: y, end: y }
  }
  if (!period) return null

  // "2015–2021" or "2015-2021" (en-dash, em-dash, hyphen)
  const rangeMatch = period.match(/(\d{4})\s*[–—-]\s*(\d{4})/)
  if (rangeMatch) {
    return { start: parseInt(rangeMatch[1], 10), end: parseInt(rangeMatch[2], 10) }
  }

  // single year "2015"
  const singleMatch = period.match(/^(\d{4})$/)
  if (singleMatch) {
    const y = parseInt(singleMatch[1], 10)
    return { start: y, end: y }
  }

  return null
}

function truncate(s: string | undefined, n = 35): string {
  if (!s) return ''
  return s.length > n ? s.slice(0, n - 1) + '…' : s
}

function getEventLabel(type: EventType, item: Level4Item): string {
  switch (type) {
    case 'problem':
      return truncate((item.description_ru as string) || (item.description as string))
    case 'contradiction': {
      const a = (item.objective_a as string) || ''
      const b = (item.objective_b as string) || ''
      return truncate(a && b ? `${a} vs ${b}` : a || b)
    }
    case 'parameter':
      return truncate(item.parameter_description as string)
    case 'reform':
      return truncate((item.driver as string) || (item.description as string))
  }
}

/** Greedy lane assignment: earliest free lane for each event (sorted by start) */
function assignLanes(events: Omit<TimelineEvent, 'lane'>[]): TimelineEvent[] {
  const sorted = [...events].sort((a, b) =>
    a.start !== b.start ? a.start - b.start : a.end - b.end,
  )
  const laneEnds: number[] = []
  return sorted.map((ev) => {
    const laneIdx = laneEnds.findIndex((endYear) => endYear < ev.start - 1)
    const lane = laneIdx === -1 ? laneEnds.length : laneIdx
    laneEnds[lane] = ev.end
    return { ...ev, lane }
  })
}

function parseSources(
  sourceStr: string | undefined,
): Array<{ label: string; url: string | null }> {
  if (!sourceStr) return []
  return sourceStr
    .split(';')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => {
      const urlMatch = s.match(/(https?:\/\/[^\s]+)/)
      const url = urlMatch ? urlMatch[1] : null
      const label =
        s
          .replace(/(https?:\/\/[^\s]+)/, '')
          .replace(/[—–-]\s*$/, '')
          .trim() ||
        url ||
        s
      return { label, url }
    })
}

function buildTimelineEvents(card: JurisdictionCard): TimelineEvent[] {
  let id = 0
  const raw: Omit<TimelineEvent, 'lane'>[] = []

  for (const item of card.level4?.problems ?? []) {
    const period = parsePeriod(item.period as string | undefined)
    if (!period) continue
    raw.push({
      id: ++id,
      type: 'problem',
      ...period,
      label: getEventLabel('problem', item),
      item,
    })
  }
  for (const item of card.level4?.contradictions ?? []) {
    const period = parsePeriod(item.period as string | undefined)
    if (!period) continue
    raw.push({
      id: ++id,
      type: 'contradiction',
      ...period,
      label: getEventLabel('contradiction', item),
      item,
    })
  }
  for (const item of card.level4?.parameters_as_tools ?? []) {
    const period = parsePeriod(item.period as string | undefined)
    if (!period) continue
    raw.push({
      id: ++id,
      type: 'parameter',
      ...period,
      label: getEventLabel('parameter', item),
      item,
    })
  }
  for (const item of card.level4?.reforms ?? []) {
    const period = parsePeriod(
      item.period as string | undefined,
      item.year as string | undefined,
    )
    if (!period) continue
    raw.push({
      id: ++id,
      type: 'reform',
      ...period,
      label: getEventLabel('reform', item),
      item,
    })
  }

  return assignLanes(raw)
}

const CAT_LABELS: Record<EventType, string> = {
  problem: 'Проблема',
  contradiction: 'Противоречие',
  parameter: 'Инструмент',
  reform: 'Реформа',
}

// ──────────────────────────────────────────────────────────────
// Sub-components
// ──────────────────────────────────────────────────────────────

/** Type badge for drawer / list view */
function TypeBadge({ type }: { type: EventType }) {
  const cls =
    type === 'problem'
      ? styles.tlCatProblem
      : type === 'contradiction'
      ? styles.tlCatContra
      : type === 'reform'
      ? styles.tlCatReform
      : styles.tlCatTool
  return <span className={`${styles.tlCat} ${cls}`}>{CAT_LABELS[type]}</span>
}

/** Venue type badge */
function VenueTypeBadge({ venueType }: { venueType: string }) {
  const lower = venueType.toLowerCase()
  const cls = lower.includes('regulated')
    ? styles.vtypeReg
    : lower.includes('mtf')
    ? styles.vtypeMtf
    : styles.vtypeOther
  const label = lower.includes('regulated') ? 'REG' : lower.includes('mtf') ? 'MTF' : venueType
  return <span className={cls}>{label}</span>
}

// ──────────────────────────────────────────────────────────────
// Timeline component
// ──────────────────────────────────────────────────────────────

interface TimelineProps {
  events: TimelineEvent[]
  activeId: number | null
  onSelect: (id: number) => void
}

function Timeline({ events, activeId, onSelect }: TimelineProps) {
  if (events.length === 0) {
    return (
      <p className={styles.emptySection}>
        Нет событий с распарсированными периодами для отображения на шкале
      </p>
    )
  }

  const allYears = events.flatMap((e) => [e.start, e.end])
  const dataMin = Math.min(...allYears)
  const dataMax = Math.max(...allYears)
  // Pad by 1 year on each side for visual breathing room
  const Y0 = dataMin - 1
  const Y1 = dataMax + 2
  const SPAN = Y1 - Y0

  function pctNum(y: number) {
    return ((y - Y0) / SPAN) * 100
  }

  const maxLane = Math.max(...events.map((e) => e.lane))
  const LANE_H = 40
  const TOP_PAD = 24
  const canvasH = TOP_PAD + (maxLane + 1) * LANE_H + 8

  // Build axis year ticks (every 2 years)
  const axisTicks: number[] = []
  const startTick = Math.ceil(Y0 / 2) * 2
  for (let y = startTick; y <= Y1; y += 2) {
    axisTicks.push(y)
  }

  function renderEvent(ev: TimelineEvent) {
    const isSelected = activeId === ev.id
    const isPoint = ev.start === ev.end
    const barMid = TOP_PAD + ev.lane * LANE_H + Math.floor(LANE_H * 0.62)

    const LABEL_H = 12
    const TICK_H = 4
    const GAP = isPoint ? 6 : 3
    const labelTop = barMid - GAP - TICK_H - LABEL_H
    const leaderTop = barMid - GAP - TICK_H

    const leaderCls =
      ev.type === 'problem'
        ? styles.tlLeaderProblem
        : ev.type === 'contradiction'
        ? styles.tlLeaderContra
        : ev.type === 'reform'
        ? styles.tlLeaderReform
        : styles.tlLeaderTool

    const floatCls =
      ev.type === 'problem'
        ? styles.tlFloatLabelProblem
        : ev.type === 'contradiction'
        ? styles.tlFloatLabelContra
        : ev.type === 'reform'
        ? styles.tlFloatLabelReform
        : styles.tlFloatLabelTool

    if (isPoint) {
      const lp = pctNum(ev.start)
      const nearRight = lp > 90
      const diamondCls =
        ev.type === 'problem'
          ? styles.tlDiamondProblem
          : ev.type === 'contradiction'
          ? styles.tlDiamondContra
          : ev.type === 'reform'
          ? styles.tlDiamondReform
          : styles.tlDiamondTool

      const labelStyle: React.CSSProperties = nearRight
        ? { right: `${100 - lp}%`, textAlign: 'right', top: labelTop }
        : { left: `${lp}%`, transform: 'translateX(-50%)', textAlign: 'center', top: labelTop }

      return (
        <React.Fragment key={ev.id}>
          <div
            className={`${styles.tlDiamond} ${diamondCls} ${isSelected ? styles.tlDiamondSelected : ''}`}
            style={{ left: `${lp.toFixed(3)}%`, top: barMid - 5 }}
            onClick={() => onSelect(ev.id)}
            title={ev.label}
          />
          <div
            className={`${styles.tlLeader} ${leaderCls}`}
            style={{ left: `${lp.toFixed(3)}%`, top: leaderTop, height: TICK_H }}
          />
          <div
            className={`${styles.tlFloatLabel} ${floatCls}`}
            style={labelStyle}
            onClick={() => onSelect(ev.id)}
          >
            {ev.label}
          </div>
        </React.Fragment>
      )
    }

    // Segment (range)
    const sp = pctNum(ev.start)
    const ep = pctNum(ev.end)
    const wp = Math.max(ep - sp, 0.4)
    const lineH = wp > 15 ? 3 : 2
    const nearRight = sp + wp > 91

    const segCls =
      ev.type === 'problem'
        ? styles.tlSegProblem
        : ev.type === 'contradiction'
        ? styles.tlSegContra
        : ev.type === 'reform'
        ? styles.tlSegReform
        : styles.tlSegTool

    const labelStyle: React.CSSProperties = nearRight
      ? { right: `${100 - sp}%`, textAlign: 'right', top: labelTop }
      : { left: `${sp.toFixed(3)}%`, top: labelTop }

    return (
      <React.Fragment key={ev.id}>
        <div
          className={`${styles.tlSeg} ${segCls} ${isSelected ? styles.tlSegSelected : ''}`}
          style={{
            left: `${sp.toFixed(3)}%`,
            width: `${wp.toFixed(3)}%`,
            top: barMid - Math.ceil(lineH / 2),
            height: lineH,
          }}
          onClick={() => onSelect(ev.id)}
          title={ev.label}
        >
          <div
            className={styles.tlSegLine}
            style={{ height: lineH, borderRadius: Math.ceil(lineH / 2) }}
          />
          <div className={styles.tlSegDot} style={{ left: 0, transform: 'translate(-50%,-50%)' }} />
          <div className={styles.tlSegDot} style={{ right: 0, left: 'auto', transform: 'translate(50%,-50%)' }} />
        </div>
        <div
          className={`${styles.tlLeader} ${leaderCls}`}
          style={{ left: `${sp.toFixed(3)}%`, top: leaderTop, height: TICK_H }}
        />
        <div
          className={`${styles.tlFloatLabel} ${floatCls}`}
          style={labelStyle}
          onClick={() => onSelect(ev.id)}
        >
          {ev.label}
        </div>
      </React.Fragment>
    )
  }

  return (
    <div>
      {/* Legend */}
      <div className={styles.tlLegend}>
        <span className={styles.tlLeg}>
          <span className={styles.tlLegDot} style={{ background: '#EF4444' }} />
          Проблемы
        </span>
        <span className={styles.tlLeg}>
          <span className={styles.tlLegDot} style={{ background: '#F59E0B' }} />
          Противоречия
        </span>
        <span className={styles.tlLeg}>
          <span className={styles.tlLegDot} style={{ background: '#3B82F6' }} />
          Реформы
        </span>
        <span className={styles.tlLeg}>
          <span className={styles.tlLegDot} style={{ background: '#10B981' }} />
          Инструменты
        </span>
      </div>

      {/* Axis */}
      <div className={styles.tlAxisWrap}>
        <div className={styles.tlAxisLine} />
        {axisTicks.map((y) => (
          <React.Fragment key={y}>
            <div className={styles.tlTick} style={{ left: `${pctNum(y).toFixed(2)}%` }} />
            <div className={styles.tlYear} style={{ left: `${pctNum(y).toFixed(2)}%` }}>
              {y}
            </div>
          </React.Fragment>
        ))}
      </div>

      {/* Canvas */}
      <div className={styles.tlCanvas} style={{ height: canvasH, position: 'relative', overflowX: 'auto' }}>
        {events.map(renderEvent)}
      </div>
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// List view entry
// ──────────────────────────────────────────────────────────────

function truncateWords(text: string, maxWords = 12): string {
  const words = text.trim().split(/\s+/)
  if (words.length <= maxWords) return text
  return words.slice(0, maxWords).join(' ') + '\u2026'
}

function ListEntry({
  type,
  item,
  periodStr,
}: {
  type: EventType
  item: Level4Item
  periodStr: string | null
}) {
  const sources = parseSources(item.source as string | undefined)
  const description =
    (item.description_ru as string | undefined) ||
    (item.description as string | undefined) ||
    ''

  let titleText = ''
  switch (type) {
    case 'problem':
      titleText = truncateWords(description)
      break
    case 'contradiction': {
      const a = item.objective_a as string | undefined
      const b = item.objective_b as string | undefined
      titleText = a && b ? `${a} vs ${b}` : a || b || description
      break
    }
    case 'parameter':
      titleText = (item.parameter_description as string | undefined) || description
      break
    case 'reform':
      titleText = (item.driver as string | undefined) || description
      break
  }

  return (
    <div className={styles.analysisEntry}>
      <div className={styles.entryTop}>
        <div className={styles.entryTitle}>{titleText}</div>
        {periodStr && <span className={styles.periodTag}>{periodStr}</span>}
      </div>

      {type === 'contradiction' ? (
        <>
          {Boolean(item.objective_a || item.objective_b) && (
            <div className={styles.conflictGrid}>
              {Boolean(item.objective_a) && (
                <div className={styles.confSide}>
                  <div className={styles.confSideLabel}>Цель А</div>
                  <div className={styles.confSideText}>{item.objective_a as string}</div>
                </div>
              )}
              {Boolean(item.objective_b) && (
                <div className={styles.confSide}>
                  <div className={styles.confSideLabel}>Цель Б</div>
                  <div className={styles.confSideText}>{item.objective_b as string}</div>
                </div>
              )}
            </div>
          )}
          {(item.resolution as string | undefined) && (
            <div className={styles.resolution}>
              <div className={styles.resolutionLabel}>Разрешение</div>
              <div className={styles.resolutionText}>{item.resolution as string}</div>
            </div>
          )}
          {description && (
            <div className={styles.entryText}>{description}</div>
          )}
        </>
      ) : (
        <>
          {description && <div className={styles.entryText}>{description}</div>}
          {type === 'problem' && Boolean(item.articulated_by) && (
            <div style={{ marginTop: '8px' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9.5px', letterSpacing: '0.08em', textTransform: 'uppercase' as const, color: 'var(--text-dim)', marginBottom: '5px' }}>
                Поставили проблему
              </div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {(Array.isArray(item.articulated_by)
                  ? (item.articulated_by as string[])
                  : [String(item.articulated_by)]
                ).map((ab) => (
                  <span key={ab} style={{
                    fontFamily: 'var(--font-mono)', fontSize: '11px',
                    padding: '2px 8px', borderRadius: '4px',
                    background: 'var(--bg3)', border: '1px solid var(--border2)',
                    color: 'var(--text-dim)'
                  }}>
                    {ab === 'government' ? 'правительство'
                     : ab === 'academic' ? 'академическое сообщество'
                     : ab === 'regulator' ? 'регулятор'
                     : ab === 'market_participants' ? 'участники рынка'
                     : ab}
                  </span>
                ))}
              </div>
            </div>
          )}
          {type === 'parameter' && Boolean(item.problem_addressed) && (
            <div className={styles.confSide} style={{ marginTop: '8px' }}>
              <div className={styles.confSideLabel}>Какую проблему решает</div>
              <p className={styles.confSideText}>{String(item.problem_addressed)}</p>
            </div>
          )}
          {type === 'parameter' && Boolean(item.calibration_debate) && (
            <div className={styles.confSide} style={{ marginTop: '8px' }}>
              <div className={styles.confSideLabel}>Дискуссия о настройке</div>
              <p className={styles.confSideText}>{String(item.calibration_debate)}</p>
            </div>
          )}
          {type === 'reform' && Boolean(item.opposition) && (
            <div style={{
              background: 'rgba(220,38,38,0.04)',
              border: '1px solid rgba(220,38,38,0.15)',
              borderRadius: 'var(--r)',
              padding: '10px 12px',
              marginTop: '8px'
            }}>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '9.5px',
                letterSpacing: '0.08em', textTransform: 'uppercase' as const,
                color: 'var(--red)', marginBottom: '5px'
              }}>
                Контраргументы
              </div>
              <p style={{ fontSize: '12.5px', color: 'var(--text-mid)', lineHeight: '1.65', fontWeight: 300 }}>
                {String(item.opposition)}
              </p>
            </div>
          )}
        </>
      )}

      {sources.length > 0 && (
        <div className={styles.entrySources}>
          {sources.map((src, i) =>
            src.url ? (
              <a
                key={i}
                className={styles.esrc}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                {src.label} ↗
              </a>
            ) : (
              <span key={i} className={styles.esrc}>
                {src.label}
              </span>
            ),
          )}
        </div>
      )}
    </div>
  )
}

interface ListSectionProps {
  label: string
  type: EventType
  badgeCls: string
  items: Level4Item[]
}

function ListSection({ label, type, badgeCls, items }: ListSectionProps) {
  if (items.length === 0) return null
  return (
    <div className={styles.analysisTypeSection}>
      <div className={styles.typeHeader}>
        <span className={styles.typeLabel}>{label}</span>
        <span className={`${styles.countBadge} ${badgeCls}`}>{items.length}</span>
      </div>
      {items.map((item, i) => {
        const raw = (item.period as string | undefined) || (item.year as string | undefined)
        return (
          <ListEntry
            key={i}
            type={type}
            item={item}
            periodStr={raw ?? null}
          />
        )
      })}
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// Drawer
// ──────────────────────────────────────────────────────────────

function Drawer({
  content,
  onClose,
  jurisdictionNameRu,
}: {
  content: DrawerContent | null
  onClose: () => void
  jurisdictionNameRu: string
}) {
  const isOpen = content !== null

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return
    function handler(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  return (
    <>
      <div
        className={`${styles.drawerBackdrop} ${isOpen ? styles.drawerBackdropOpen : ''}`}
        onClick={onClose}
      />
      <div className={`${styles.drawer} ${isOpen ? styles.drawerOpen : ''}`}>
        {content?.kind === 'event' && <EventDrawerContent event={content.event} onClose={onClose} />}
        {content?.kind === 'venue' && (
          <VenueDrawerContent venue={content} onClose={onClose} jurisdictionNameRu={jurisdictionNameRu} />
        )}
      </div>
    </>
  )
}

function EventDrawerContent({
  event,
  onClose,
}: {
  event: TimelineEvent
  onClose: () => void
}) {
  const { type, item } = event
  const period =
    event.start === event.end
      ? String(event.start)
      : `${event.start} – ${event.end}`

  const description =
    (item.description_ru as string | undefined) ||
    (item.description as string | undefined) ||
    ''
  const sources = parseSources(item.source as string | undefined)

  return (
    <>
      <div className={styles.drawerHd}>
        <div className={styles.drawerHdLeft}>
          <div className={styles.drawerTitle}>
            {type === 'contradiction'
              ? ((item.objective_a as string | undefined) && (item.objective_b as string | undefined)
                  ? `${item.objective_a} vs ${item.objective_b}`
                  : truncateWords(description))
              : type === 'parameter'
              ? (item.parameter_description as string | undefined) || truncateWords(description)
              : type === 'reform'
              ? (item.driver as string | undefined) || truncateWords(description)
              : truncateWords(description)}
          </div>
          <div className={styles.drawerBadges}>
            <span className={styles.periodTag}>{period}</span>
            <TypeBadge type={type} />
          </div>
        </div>
        <button className={styles.drawerClose} onClick={onClose} aria-label="Закрыть">
          ✕
        </button>
      </div>
      <div className={styles.drawerBody}>
        {type === 'contradiction' ? (
          <>
            {Boolean(item.objective_a || item.objective_b) && (
              <div className={styles.drawerConflict}>
                {Boolean(item.objective_a) && (
                  <div className={styles.drawerConfSide}>
                    <div className={styles.drawerConfLabel}>Цель А</div>
                    <div className={styles.drawerConfText}>{item.objective_a as string}</div>
                  </div>
                )}
                {Boolean(item.objective_b) && (
                  <div className={styles.drawerConfSide}>
                    <div className={styles.drawerConfLabel}>Цель Б</div>
                    <div className={styles.drawerConfText}>{item.objective_b as string}</div>
                  </div>
                )}
              </div>
            )}
            {Boolean(item.resolution_ru ?? item.resolution) && (
              <div className={styles.drawerResolution}>
                <div className={styles.drawerResLabel}>Разрешение</div>
                <p className={styles.drawerResText}>
                  {String(item.resolution_ru ?? item.resolution)}
                </p>
              </div>
            )}
            {description && <div className={styles.drawerText}>{description}</div>}
          </>
        ) : (
          <>
            {description && <div className={styles.drawerText}>{description}</div>}
            {type === 'problem' && Boolean(item.articulated_by) && (
              <div style={{ marginBottom: '14px' }}>
                <div className={styles.drawerSourcesLabel} style={{ marginBottom: '6px' }}>
                  Поставили проблему
                </div>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {(Array.isArray(item.articulated_by)
                    ? (item.articulated_by as string[])
                    : [String(item.articulated_by)]
                  ).map((ab) => (
                    <span key={ab} className={styles.metaBadge ?? ''} style={{
                      fontFamily: 'var(--font-mono)', fontSize: '11px',
                      padding: '2px 8px', borderRadius: '4px',
                      background: 'var(--bg-subtle)', border: '1px solid var(--border-strong)',
                      color: 'var(--text-secondary)'
                    }}>
                      {ab === 'government' ? 'правительство'
                       : ab === 'academic' ? 'академическое сообщество'
                       : ab === 'regulator' ? 'регулятор'
                       : ab === 'market_participants' ? 'участники рынка'
                       : ab}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {type === 'parameter' && Boolean(item.problem_addressed) && (
              <div className={styles.confSide} style={{ marginBottom: '10px' }}>
                <div className={styles.confSideLabel}>Какую проблему решает</div>
                <p className={styles.confSideText}>{String(item.problem_addressed)}</p>
              </div>
            )}
            {type === 'parameter' && Boolean(item.calibration_debate) && (
              <div className={styles.confSide} style={{ marginBottom: '10px' }}>
                <div className={styles.confSideLabel}>Дискуссия о настройке</div>
                <p className={styles.confSideText}>{String(item.calibration_debate)}</p>
              </div>
            )}
            {type === 'reform' && Boolean(item.opposition) && (
              <div style={{
                background: 'rgba(220,38,38,0.04)',
                border: '1px solid rgba(220,38,38,0.15)',
                borderRadius: 'var(--radius-md)',
                padding: '12px 14px',
                marginBottom: '14px'
              }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '9.5px',
                  letterSpacing: '0.08em', textTransform: 'uppercase' as const,
                  color: 'var(--red)', marginBottom: '5px'
                }}>
                  Контраргументы
                </div>
                <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: '1.65', fontWeight: 300 }}>
                  {String(item.opposition)}
                </p>
              </div>
            )}
          </>
        )}
        {sources.length > 0 && (
          <>
            <div className={styles.drawerSourcesLabel}>Источники</div>
            <div className={styles.drawerSources}>
              {sources.map((src, i) =>
                src.url ? (
                  <a
                    key={i}
                    className={styles.drawerSrc}
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {src.label} ↗
                  </a>
                ) : (
                  <span key={i} className={styles.drawerSrc} style={{ color: 'var(--text-muted)' }}>
                    {src.label}
                  </span>
                ),
              )}
            </div>
          </>
        )}
      </div>
    </>
  )
}

function VenueDrawerContent({
  venue,
  onClose,
  jurisdictionNameRu,
}: {
  venue: Extract<DrawerContent, { kind: 'venue' }>
  onClose: () => void
  jurisdictionNameRu: string
}) {
  return (
    <>
      <div className={styles.drawerHd}>
        <div className={styles.drawerHdLeft}>
          <div className={styles.drawerTitle}>{venue.name}</div>
          <div className={styles.drawerBadges}>
            <VenueTypeBadge venueType={venue.venueType} />
          </div>
        </div>
        <button className={styles.drawerClose} onClick={onClose} aria-label="Закрыть">
          ✕
        </button>
      </div>
      <div className={styles.drawerBody}>
        <div className={styles.drawerVenueStats}>
          {venue.nameEn && venue.nameEn !== venue.name && (
            <div className={styles.drawerVenueStat}>
              <span className={styles.drawerVenueStatLabel}>English</span>
              <span className={styles.drawerVenueStatVal}>{venue.nameEn}</span>
            </div>
          )}
          <div className={styles.drawerVenueStat}>
            <span className={styles.drawerVenueStatLabel}>Тип</span>
            <span className={styles.drawerVenueStatVal}>{venue.venueType}</span>
          </div>
          <div className={styles.drawerVenueStat}>
            <span className={styles.drawerVenueStatLabel}>Ячеек</span>
            <span className={styles.drawerVenueStatVal}>{venue.cellCount}</span>
          </div>
        </div>
        <Link
          to={`/venues/${encodeURIComponent(venue.venueKey)}?name_ru=${encodeURIComponent(jurisdictionNameRu)}`}
          className={styles.drawerVenueLink}
        >
          Перейти к матрице →
        </Link>
      </div>
    </>
  )
}

// ──────────────────────────────────────────────────────────────
// Terms tab
// ──────────────────────────────────────────────────────────────

function TermsTab({ mapping }: { mapping: Record<string, string> }) {
  const entries = Object.entries(mapping)
  const [open, setOpen] = useState(true)

  if (entries.length === 0) {
    return <p className={styles.emptySection}>Терминологический справочник не заполнен</p>
  }

  return (
    <div>
      <button
        className={`${styles.termsToggle} ${open ? styles.termsToggleOpen : ''}`}
        onClick={() => setOpen((v) => !v)}
      >
        <span>
          Ключевые термины{' '}
          <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 400, marginLeft: 8 }}>
            {entries.length} терм.
          </span>
        </span>
        <span className={`${styles.termsArrow} ${open ? styles.termsArrowOpen : ''}`}>▼</span>
      </button>
      <div className={`${styles.termsBody} ${open ? styles.termsBodyOpen : ''}`}>
        <div className={styles.termsBodyInner}>
          <table className={styles.mapTable}>
            <thead>
              <tr>
                <th>Местный термин</th>
                <th>Определение / расшифровка</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(([key, val]) => (
                <tr key={key}>
                  <td>{key}</td>
                  <td>{val}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// Tab 1: Jurisdiction tab
// ──────────────────────────────────────────────────────────────

function JurisdictionTab({ data }: { data: JurisdictionCard }) {
  const navigate = useNavigate()
  const hasArch = Boolean(data.admission_architecture_ru || data.admission_architecture)

  return (
    <>
      {/* First screen: 2-column grid */}
      <div className={styles.jurisdictionLayout}>

        {/* Left column: Admission architecture card */}
        <div className={styles.card}>
          <div className={styles.cardHd}>
            <span className={styles.cardTitle}>Архитектура допуска</span>
          </div>

          <div className={styles.cardBody}>
            {hasArch ? (
              <>
                <p className={styles.archText}>
                  {data.admission_architecture_ru || data.admission_architecture}
                </p>
                {data.admission_architecture_ru &&
                  data.admission_architecture &&
                  data.admission_architecture !== data.admission_architecture_ru && (
                    <p className={styles.archNote}>{data.admission_architecture}</p>
                  )}
              </>
            ) : (
              <p className={styles.archEmpty}>Архитектура допуска не заполнена</p>
            )}
          </div>

          {/* Regulator strip */}
          {(data.regulator_name || data.regulator_type || data.legal_family) && (
            <>
              <div className={styles.cardDivider} />
              <div className={styles.regulatorStrip}>
                <span className={styles.regulatorLabel}>Регулятор</span>
                {data.regulator_name && (
                  <span className={styles.regulatorName}>{data.regulator_name}</span>
                )}
                {data.regulator_type && (
                  <span className={styles.metaBadge}>{data.regulator_type}</span>
                )}
                {data.listing_authority && (
                  <div className={styles.regulatorRow}>
                    <span className={styles.regulatorLabel}>Орган листинга</span>
                    <span
                      className={styles.regulatorName}
                      title={data.listing_authority}
                      style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'inline-block', verticalAlign: 'middle' }}
                    >
                      {data.listing_authority.length > 60
                        ? data.listing_authority.slice(0, 60) + '…'
                        : data.listing_authority}
                    </span>
                  </div>
                )}
                {data.legal_family && (
                  <span className={styles.metaBadge}>{data.legal_family}</span>
                )}
                {data.market_types && data.market_types.length > 0 && (
                  <div className={styles.regulatorRow}>
                    <span className={styles.regulatorLabel}>Типы рынков</span>
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      {data.market_types.map((mt) => (
                        <span key={mt} className={styles.metaBadge}>{mt}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Notes */}
          {(data.notes_ru || data.notes) && (
            <>
              <div className={styles.cardDivider} />
              <div className={styles.cardBody}>
                <div className={styles.cardTitle} style={{ marginBottom: '10px' }}>Примечания</div>
                <p className={`${styles.archNote}`}>{data.notes_ru || data.notes}</p>
              </div>
            </>
          )}
        </div>

        {/* Right column: Venues */}
        <div className={styles.venuesCol}>
          <div className={styles.venuesColHeader}>
            <span className={styles.venuesColTitle}>Торговые площадки</span>
            <span className={styles.venuesBadge}>{data.venues.length}</span>
          </div>
          {data.venues.length === 0 ? (
            <p className={styles.emptySection}>Площадки не найдены</p>
          ) : (
            data.venues.map((venue) => (
              <div
                key={venue.venue_key}
                className={styles.venueCard}
                onClick={() => navigate(`/venues/${encodeURIComponent(venue.venue_key)}`)}
              >
                <div className={styles.venueCardHd}>
                  <div>
                    <div className={styles.venueCardName}>{venue.name_ru || venue.name}</div>
                    <div className={styles.venueCardEn}>{venue.name}</div>
                  </div>
                  <VenueTypeBadge venueType={venue.venue_type} />
                </div>
                <div className={styles.venueCardFoot}>
                  <div className={styles.venueCardStats}>
                    <span>
                      Ячеек:{' '}
                      <span className={styles.venueCardStatsVal}>{venue.cell_count}</span>
                    </span>
                  </div>
                  <span className={styles.venueCardArrow}>→</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Supranational context */}
      {data.supranational_flag && data.supranational_framework && (
        <div className={styles.card} style={{ marginTop: 0 }}>
          <div className={styles.cardHd}>
            <span className={styles.cardTitle}>Наднациональный контекст</span>
            <span className={styles.metaBadge} style={{ background: 'rgba(37,99,235,0.08)', color: 'var(--accent-primary)', borderColor: 'rgba(37,99,235,0.2)' }}>EU</span>
          </div>
          <div className={styles.cardBody}>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.7', fontWeight: 300 }}>
              {data.supranational_framework}
            </p>
          </div>
        </div>
      )}

      {/* Bottom grid: placeholder cards */}
      <div className={styles.bottomGrid}>
        {/* World Bank metrics placeholder */}
        <div className={styles.placeholderCard}>
          <div className={styles.cardHd}>
            <span className={styles.cardTitle}>Метрики Мирового Банка</span>
          </div>
          <div className={styles.placeholderBody}>
            <div className={styles.placeholderMetrics}>
              {['Rule of Law', 'Reg. Quality', 'Gov. Eff.', 'M.Cap/GDP'].map((label) => (
                <div key={label} className={styles.placeholderMetric}>
                  <div className={styles.placeholderMetricLabel}>{label}</div>
                  <div className={styles.placeholderMetricVal}>—</div>
                </div>
              ))}
            </div>
            <div>В разработке</div>
          </div>
        </div>

        {/* Similar jurisdictions placeholder */}
        <div className={styles.placeholderCard}>
          <div className={styles.cardHd}>
            <span className={styles.cardTitle}>Похожие юрисдикции</span>
          </div>
          <div className={styles.placeholderBody}>
            В разработке
          </div>
        </div>
      </div>
    </>
  )
}

// ──────────────────────────────────────────────────────────────
// Sources tab
// ──────────────────────────────────────────────────────────────

function SourcesTab({ sources }: { sources: SourceCitation[] }) {
  const [expanded, setExpanded] = React.useState(false)
  const PREVIEW = 15
  const shown = expanded ? sources : sources.slice(0, PREVIEW)

  function getDisplay(src: SourceCitation): { label: string; href: string } {
    const label = src.title || (() => { try { return new URL(src.url).hostname } catch { return src.url } })()
    return { label, href: src.url }
  }

  return (
    <div style={{ maxWidth: '720px' }}>
      <div style={{
        background: 'var(--bg2)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)', overflow: 'hidden'
      }}>
        <div style={{
          padding: '10px 16px', background: 'var(--bg3)',
          borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', gap: '10px'
        }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
            Источники
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', background: 'var(--bg2)', border: '1px solid var(--border-strong)', borderRadius: '8px', padding: '1px 7px', color: 'var(--text-secondary)' }}>
            {sources.length}
          </span>
        </div>
        <div>
          {shown.map((src, i) => {
            const { label, href } = getDisplay(src)
            return (
              <div key={i} style={{
                display: 'flex', alignItems: 'baseline', gap: '12px',
                padding: '9px 16px', borderBottom: i < shown.length - 1 ? '1px solid var(--border)' : 'none',
                fontSize: '13px'
              }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', flexShrink: 0, width: '24px', textAlign: 'right' }}>{i + 1}</span>
                <span style={{ flex: 1, color: 'var(--text-secondary)', lineHeight: 1.55 }}>{label}</span>
                <a href={href} target="_blank" rel="noopener noreferrer"
                  style={{ fontFamily: 'var(--font-mono)', fontSize: '10.5px', color: 'var(--accent)', whiteSpace: 'nowrap', flexShrink: 0 }}>
                  {(() => { try { return new URL(href).hostname } catch { return '↗' } })()} ↗
                </a>
              </div>
            )
          })}
        </div>
        {sources.length > PREVIEW && (
          <div style={{ padding: '8px 16px', borderTop: '1px solid var(--border)', background: 'var(--bg3)' }}>
            <button
              onClick={() => setExpanded(!expanded)}
              style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
            >
              {expanded ? 'Свернуть' : `Показать все ${sources.length}`}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function L4SourcesSection({ sources }: { sources: SourceCitation[] }) {
  const [expanded, setExpanded] = React.useState(false)
  const PREVIEW = 5
  const shown = expanded ? sources : sources.slice(0, PREVIEW)

  return (
    <div style={{ maxWidth: '720px' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '10px' }}>
        Источники анализа · {sources.length}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {shown.map((src, i) => {
          const label = src.title || (() => { try { return new URL(src.url).hostname } catch { return src.url } })()
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'baseline', gap: '10px', fontSize: '12.5px' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', width: '20px', textAlign: 'right', flexShrink: 0 }}>{i + 1}</span>
              <span style={{ flex: 1, color: 'var(--text-secondary)' }}>{label}</span>
              <a href={src.url} target="_blank" rel="noopener noreferrer"
                style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--accent)', whiteSpace: 'nowrap', flexShrink: 0 }}>
                {(() => { try { return new URL(src.url).hostname } catch { return '↗' } })()} ↗
              </a>
            </div>
          )
        })}
      </div>
      {sources.length > PREVIEW && (
        <button
          onClick={() => setExpanded(!expanded)}
          style={{ marginTop: '8px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
        >
          {expanded ? 'Свернуть' : `Показать ещё ${sources.length - PREVIEW}`}
        </button>
      )}
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// Main page
// ──────────────────────────────────────────────────────────────

export default function JurisdictionPage() {
  const { nameRu } = useParams<{ nameRu: string }>()
  const [data, setData] = useState<JurisdictionCard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [activeTab, setActiveTab] = useState<TabKey>(() => {
    const hash = window.location.hash.slice(1)
    if (hash === 'analysis' || hash === 'terms' || hash === 'sources') return hash as TabKey
    return 'jurisdiction'
  })
  const [viewMode, setViewMode] = useState<ViewMode>('timeline')
  const [drawerContent, setDrawerContent] = useState<DrawerContent | null>(null)
  const [activeEventId, setActiveEventId] = useState<number | null>(null)

  const load = () => {
    if (!nameRu) return
    setLoading(true)
    setError(null)
    fetchJurisdiction(nameRu)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [nameRu])

  const tlEvents: TimelineEvent[] = data ? buildTimelineEvents(data) : []
  const totalL4 =
    (data?.level4?.problems.length ?? 0) +
    (data?.level4?.contradictions.length ?? 0) +
    (data?.level4?.parameters_as_tools.length ?? 0) +
    (data?.level4?.reforms.length ?? 0)

  const handleEventSelect = useCallback(
    (id: number) => {
      if (activeEventId === id) {
        setDrawerContent(null)
        setActiveEventId(null)
        return
      }
      setActiveEventId(id)
      const ev = tlEvents.find((e) => e.id === id)
      if (ev) setDrawerContent({ kind: 'event', event: ev })
    },
    [activeEventId, tlEvents],
  )

  const closeDrawer = useCallback(() => {
    setDrawerContent(null)
    setActiveEventId(null)
  }, [])

  if (loading) return <LoadingState message="Загрузка данных юрисдикции..." />
  if (error) return <ErrorState message={error} onRetry={load} />
  if (!data) return <ErrorState message="Юрисдикция не найдена" />

  const termsCount = Object.keys(data.key_terms_mapping).length
  const sourcesCount = data.sources?.length ?? 0
  const l4SourcesCount = data.level4?.sources?.length ?? 0

  return (
    <div className={styles.page}>
      {/* ── Breadcrumb ── */}
      <nav className={styles.breadcrumb} aria-label="Навигация">
        <Link to="/jurisdictions">← Юрисдикции</Link>
        <span className={styles.breadcrumbSep}>›</span>
        <span style={{ color: 'var(--text-secondary)' }}>{data.name_ru}</span>
      </nav>

      {/* ── Page header ── */}
      <div className={styles.pageHeader}>
        <div className={styles.phLeft}>
          <div className={styles.phTitleRow}>
            {data.iso_code && (
              <div className={styles.phFlag}>
                <img
                  src={`https://flagcdn.com/40x30/${data.iso_code.toLowerCase()}.png`}
                  srcSet={`https://flagcdn.com/80x60/${data.iso_code.toLowerCase()}.png 2x`}
                  width={40}
                  height={30}
                  alt={data.name_en}
                  style={{ display: 'block', borderRadius: '3px' }}
                />
              </div>
            )}
            <div>
              <h1 className={styles.title}>{data.name_ru}</h1>
              <div className={styles.titleSub}>
                {[data.name_en, data.legal_family].filter(Boolean).join(' · ')}
              </div>
            </div>
          </div>
        </div>
        {data.data_status === 'full' && (
          <span className={styles.verifiedBadge}>Верифицировано</span>
        )}
      </div>

      {/* ── Tab bar ── */}
      <div className={styles.tabsWrap}>
        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${activeTab === 'jurisdiction' ? styles.tabActive : ''}`}
            onClick={() => { setActiveTab('jurisdiction'); window.location.hash = 'jurisdiction' }}
          >
            Юрисдикция
          </button>
          <button
            className={`${styles.tab} ${activeTab === 'analysis' ? styles.tabActive : ''}`}
            onClick={() => { setActiveTab('analysis'); window.location.hash = 'analysis' }}
          >
            Регуляторный анализ
            {data.level4 && totalL4 > 0 && (
              <span className={styles.tabCount}>{totalL4}</span>
            )}
          </button>
          {termsCount > 0 && (
            <button
              className={`${styles.tab} ${activeTab === 'terms' ? styles.tabActive : ''}`}
              onClick={() => { setActiveTab('terms'); window.location.hash = 'terms' }}
            >
              Термины
              <span className={styles.tabCount}>{termsCount}</span>
            </button>
          )}
          {sourcesCount > 0 && (
            <button
              className={`${styles.tab} ${activeTab === 'sources' ? styles.tabActive : ''}`}
              onClick={() => { setActiveTab('sources'); window.location.hash = 'sources' }}
            >
              Источники
              <span className={styles.tabCount}>{sourcesCount}</span>
            </button>
          )}
        </div>
      </div>

      {/* ── Tab content ── */}
      <div className={styles.content}>

        {/* ═══ TAB: ЮРИСДИКЦИЯ ═══ */}
        {activeTab === 'jurisdiction' && (
          <JurisdictionTab data={data} />
        )}

        {/* ═══ TAB: РЕГУЛЯТОРНЫЙ АНАЛИЗ ═══ */}
        {activeTab === 'analysis' && (
          <>
            {data.level4 === null ? (
              <p className={styles.emptySection}>Регуляторный анализ отсутствует</p>
            ) : (
              <>
                {/* Toolbar */}
                <div className={styles.analysisToolbar}>
                  <div className={styles.viewToggle}>
                    <button
                      className={`${styles.vtBtn} ${viewMode === 'list' ? styles.vtBtnActive : ''}`}
                      onClick={() => setViewMode('list')}
                    >
                      <svg
                        width="13"
                        height="13"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        viewBox="0 0 24 24"
                      >
                        <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
                      </svg>
                      Список
                    </button>
                    <button
                      className={`${styles.vtBtn} ${viewMode === 'timeline' ? styles.vtBtnActive : ''}`}
                      onClick={() => setViewMode('timeline')}
                    >
                      <svg
                        width="13"
                        height="13"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        viewBox="0 0 24 24"
                      >
                        <line x1="3" y1="12" x2="21" y2="12" />
                        <circle cx="8" cy="12" r="2" fill="currentColor" stroke="none" />
                        <circle cx="16" cy="7" r="2" fill="currentColor" stroke="none" />
                        <circle cx="13" cy="17" r="2" fill="currentColor" stroke="none" />
                      </svg>
                      Таймлайн
                    </button>
                  </div>
                </div>

                {/* Timeline view */}
                {viewMode === 'timeline' && (
                  <Timeline
                    events={tlEvents}
                    activeId={activeEventId}
                    onSelect={handleEventSelect}
                  />
                )}

                {/* List view */}
                {viewMode === 'list' && (
                  <div>
                    <ListSection
                      label="Проблемы"
                      type="problem"
                      badgeCls={styles.countBadgeRed}
                      items={data.level4.problems}
                    />
                    <ListSection
                      label="Противоречия"
                      type="contradiction"
                      badgeCls={styles.countBadgeOrange}
                      items={data.level4.contradictions}
                    />
                    <ListSection
                      label="Параметры как инструменты"
                      type="parameter"
                      badgeCls={styles.countBadgeGray}
                      items={data.level4.parameters_as_tools}
                    />
                    <ListSection
                      label="Реформы"
                      type="reform"
                      badgeCls={styles.countBadgeBlue}
                      items={data.level4.reforms}
                    />
                  </div>
                )}

                {/* Источники анализа */}
                {l4SourcesCount > 0 && data.level4?.sources && (
                  <div style={{ marginTop: '32px' }}>
                    <L4SourcesSection sources={data.level4.sources} />
                  </div>
                )}
              </>
            )}
          </>
        )}

        {/* ═══ TAB: ТЕРМИНЫ ═══ */}
        {activeTab === 'terms' && (
          <TermsTab mapping={data.key_terms_mapping} />
        )}

        {/* ═══ TAB: ИСТОЧНИКИ ═══ */}
        {activeTab === 'sources' && (
          <SourcesTab sources={data.sources ?? []} />
        )}
      </div>

      {/* ── Drawer ── */}
      <Drawer
        content={drawerContent}
        onClose={closeDrawer}
        jurisdictionNameRu={data.name_ru}
      />
    </div>
  )
}
