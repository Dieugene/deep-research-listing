import { useState } from 'react'
import styles from './TermsMappingTable.module.css'

interface Props {
  mapping: Record<string, string>
}

const GROUPS: Array<{ label: string; keywords: string[] }> = [
  {
    label: 'Архитектурные понятия',
    keywords: ['listing', 'листинг', 'допуск', 'admission', 'regulator', 'регулятор', 'compliance', 'exchange', 'биржа', 'market', 'рынок'],
  },
  {
    label: 'Нормативные акты',
    keywords: ['act', 'закон', 'law', 'directive', 'директива', 'regulation', 'rule', 'правило'],
  },
  {
    label: 'Сегменты площадок',
    keywords: ['segment', 'сегмент', 'tier', 'уровень', 'board', 'section', 'секция'],
  },
]

function classifyEntry(key: string): number {
  const lower = key.toLowerCase()
  for (let i = 0; i < GROUPS.length; i++) {
    if (GROUPS[i].keywords.some((kw) => lower.includes(kw))) return i
  }
  return 3 // "Прочие"
}

interface EntryGroup {
  label: string
  entries: [string, string][]
}

function buildGroups(entries: [string, string][]): EntryGroup[] {
  const buckets: [string, string][][] = [[], [], [], []]
  for (const entry of entries) {
    buckets[classifyEntry(entry[0])].push(entry)
  }
  const labels = [...GROUPS.map((g) => g.label), 'Прочие']
  return labels
    .map((label, i) => ({ label, entries: buckets[i] }))
    .filter((g) => g.entries.length > 0)
}

const COLLAPSED_LIMIT = 6

export default function TermsMappingTable({ mapping }: Props) {
  const entries = Object.entries(mapping)
  const [expanded, setExpanded] = useState<boolean>(false)

  if (!entries.length) {
    return <p className={styles.empty}>Маппинг терминов не задан</p>
  }

  const groups = buildGroups(entries)

  // Flatten grouped entries to determine the first 6 for collapsed view
  const flatGrouped: Array<{ groupLabel: string; key: string; value: string }> = []
  for (const g of groups) {
    for (const [k, v] of g.entries) {
      flatGrouped.push({ groupLabel: g.label, key: k, value: v })
    }
  }

  const visibleFlat = expanded ? flatGrouped : flatGrouped.slice(0, COLLAPSED_LIMIT)
  const visibleKeys = new Set(visibleFlat.map((e) => e.key))

  // Build visible groups (only entries whose keys are in visibleKeys)
  const visibleGroups: EntryGroup[] = groups
    .map((g) => ({ label: g.label, entries: g.entries.filter(([k]) => visibleKeys.has(k)) }))
    .filter((g) => g.entries.length > 0)

  const needsToggle = entries.length > COLLAPSED_LIMIT

  return (
    <div className={styles.wrapper}>
      {visibleGroups.map((group) => (
        <div key={group.label}>
          <div className={styles.categoryLabel}>{group.label}</div>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Местный термин</th>
                <th>Определение / расшифровка</th>
              </tr>
            </thead>
            <tbody>
              {group.entries.map(([core, local]) => (
                <tr key={core}>
                  <td className={styles.coreTerm}>{core}</td>
                  <td className={styles.localTerm}>{local}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      {needsToggle && (
        <button className={styles.collapseBtn} onClick={() => setExpanded((v) => !v)}>
          {expanded ? 'Свернуть' : `Показать все (${entries.length})`}
        </button>
      )}
    </div>
  )
}
