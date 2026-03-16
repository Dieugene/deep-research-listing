import { useState } from 'react'
import styles from './SourceBlock.module.css'
import { SourceData } from './SourceItem'

interface SourceBlockProps {
  sources: SourceData[]
  blockId: string
}

// Russian pluralization helpers
function pluralSources(n: number): string {
  if (n % 10 === 1 && n % 100 !== 11) return `${n} источник`
  if (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20)) return `${n} источника`
  return `${n} источников`
}

function pluralExcerpts(n: number): string {
  if (n % 10 === 1 && n % 100 !== 11) return `${n} выдержка`
  if (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20)) return `${n} выдержки`
  return `${n} выдержек`
}

function dtClass(type: string | null | undefined): string {
  const map: Record<string, string> = {
    legislation: 'dtLegislation',
    rulebook: 'dtRulebook',
    government: 'dtGovernment',
    consultation: 'dtConsultation',
    research: 'dtResearch',
  }
  return map[type ?? ''] ?? 'dtOther'
}

function dtLabel(type: string | null | undefined): string {
  const map: Record<string, string> = {
    legislation: 'Законодательство',
    rulebook: 'Правила биржи',
    government: 'Регулятор',
    consultation: 'Консультация',
    research: 'Исследование',
  }
  return map[type ?? ''] ?? 'Другое'
}

export default function SourceBlock({ sources, blockId }: SourceBlockProps) {
  const [open, setOpen] = useState(false)
  const [openExcerpts, setOpenExcerpts] = useState<Set<number>>(new Set())

  const totalExcerpts = sources.reduce((sum, s) => sum + (s.excerpts?.length ?? 0), 0)
  const hasExcerpts = totalExcerpts > 0

  const countText = hasExcerpts
    ? `${pluralSources(sources.length)} · ${pluralExcerpts(totalExcerpts)}`
    : pluralSources(sources.length)

  function toggleExcerpt(idx: number) {
    setOpenExcerpts(prev => {
      const next = new Set(prev)
      if (next.has(idx)) {
        next.delete(idx)
      } else {
        next.add(idx)
      }
      return next
    })
  }

  const blockClass = [styles.srcBlock, hasExcerpts ? styles.hasExcerpts : ''].filter(Boolean).join(' ')
  const listClass = [styles.srcList, open ? styles.open : ''].filter(Boolean).join(' ')
  const chevronClass = [styles.srcChevron, open ? styles.open : ''].filter(Boolean).join(' ')

  return (
    <div className={blockClass} id={blockId}>
      <div className={styles.srcBlockHd} onClick={() => setOpen(v => !v)}>
        <div className={styles.srcBlockLeft}>
          <svg
            width="12"
            height="12"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
            style={{ color: 'var(--text-dim)', flexShrink: 0 }}
          >
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
          </svg>
          <span className={styles.srcBlockLabel}>Источники</span>
          <span className={styles.srcCount}>{countText}</span>
        </div>
        <span className={chevronClass}>▾</span>
      </div>

      <div className={listClass}>
        {sources.map((source, idx) => {
          const excerptCount = source.excerpts?.length ?? 0
          const isExcerptOpen = openExcerpts.has(idx)
          const hasSourceExcerpts = excerptCount > 0
          // Show "выдержки недоступны" only when excerpts is explicitly an empty array
          const showNoExcerpts = Array.isArray(source.excerpts) && source.excerpts.length === 0

          const hostname = (() => {
            if (!source.url) return null
            try {
              return new URL(source.url).hostname
            } catch {
              return null
            }
          })()

          const excerptToggleClass = [
            styles.excerptToggle,
            isExcerptOpen ? styles.active : '',
          ].filter(Boolean).join(' ')

          const excerptsWrapClass = [
            styles.excerptsWrap,
            isExcerptOpen ? styles.open : '',
          ].filter(Boolean).join(' ')

          return (
            <div key={idx} className={styles.srcRow}>
              <div className={styles.srcRowHd}>
                <span className={styles.srcNum}>{idx + 1}</span>
                <div className={styles.srcMeta}>
                  <div className={styles.srcTitleRow}>
                    {hostname ? (
                      <a
                        className={styles.srcLinkEl}
                        href={source.url!}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {source.title} ↗
                      </a>
                    ) : (
                      <span className={styles.srcLinkEl}>{source.title}</span>
                    )}
                    <span className={[styles.docType, styles[dtClass(source.type)]].join(' ')}>
                      {dtLabel(source.type)}
                    </span>
                  </div>

                  {hasSourceExcerpts && (
                    <div
                      className={excerptToggleClass}
                      onClick={() => toggleExcerpt(idx)}
                    >
                      <span className={styles.excerptIcon}>❝</span>
                      <span>{pluralExcerpts(excerptCount)} из документа</span>
                      <span className={styles.excerptCountBadge}>
                        {isExcerptOpen ? 'скрыть' : 'показать'}
                      </span>
                    </div>
                  )}

                  {showNoExcerpts && (
                    <div className={styles.noExcerpts}>выдержки недоступны</div>
                  )}
                </div>
              </div>

              {hasSourceExcerpts && (
                <div className={excerptsWrapClass}>
                  {source.excerpts!.map((text, ei) => (
                    <div key={ei} className={styles.excerptItem}>{text}</div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
