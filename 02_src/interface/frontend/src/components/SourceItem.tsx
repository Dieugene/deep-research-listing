import { useState } from 'react'
import styles from './SourceItem.module.css'

export interface SourceData {
  url?: string | null
  title: string
  type?: string | null
  excerpts?: string[]
}

interface SourceItemProps {
  source: SourceData
}

function typeClass(type: string | null | undefined): string {
  const map: Record<string, string> = {
    legislation: 'tLegislation',
    rulebook: 'tRulebook',
    government: 'tGovernment',
    consultation: 'tConsultation',
    research: 'tResearch',
  }
  return map[type ?? ''] ?? 'tOther'
}

function typeLabel(type: string | null | undefined): string {
  const map: Record<string, string> = {
    legislation: 'Законодательство',
    rulebook: 'Правила биржи',
    government: 'Регулятор',
    consultation: 'Консультация',
    research: 'Исследование',
    other: 'Другое',
  }
  return map[type ?? ''] ?? 'Другое'
}

export default function SourceItem({ source }: SourceItemProps) {
  const [excerptOpen, setExcerptOpen] = useState(false)

  const hasExcerpts = !!(source.excerpts && source.excerpts.length > 0)
  const n = source.excerpts?.length ?? 0

  const hdClass = [styles.srcHd, hasExcerpts ? styles.clickable : ''].filter(Boolean).join(' ')

  const hostname = (() => {
    if (!source.url) return null
    try {
      return new URL(source.url).hostname
    } catch {
      return null
    }
  })()

  return (
    <div className={styles.srcBlock}>
      <div
        className={hdClass}
        onClick={hasExcerpts ? () => setExcerptOpen(v => !v) : undefined}
      >
        <span className={styles.srcTitle}>{source.title}</span>

        {hostname ? (
          <a
            className={styles.srcLink}
            href={source.url!}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
          >
            {hostname} ↗
          </a>
        ) : null}

        {hasExcerpts && (
          <button
            className={styles.excerptToggle}
            onClick={e => { e.stopPropagation(); setExcerptOpen(v => !v) }}
          >
            {excerptOpen ? 'свернуть ↑' : `${n} выдержки ↓`}
          </button>
        )}
      </div>

      {hasExcerpts && excerptOpen && (
        <div className={styles.excerpts}>
          {source.excerpts!.map((text, i) => (
            <div key={i} className={styles.excerptItem}>{text}</div>
          ))}
        </div>
      )}
    </div>
  )
}
