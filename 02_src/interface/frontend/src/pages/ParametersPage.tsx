import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchParameters } from '../api/parameters'
import type { ParameterSummary } from '../api/types'
import LoadingState from '../components/common/LoadingState'
import ErrorState from '../components/common/ErrorState'
import EmptyState from '../components/common/EmptyState'
import styles from './ParametersPage.module.css'

type MergedParameter = ParameterSummary & { altId?: string }

interface ParameterGroup {
  label: string
  items: MergedParameter[]
  dimmed?: boolean
}

function groupParameters(params: ParameterSummary[]): ParameterGroup[] {
  // Normalize: merge Latin P prefixes into Cyrillic П entries
  const merged = new Map<string, MergedParameter>()
  for (const p of params) {
    const cyrId = p.parameter_id.replace(/^P(\d+)$/, 'П$1') // P01 → П01
    const isLatinDup = /^P\d/.test(p.parameter_id)
    if (isLatinDup) {
      const existing = merged.get(cyrId)
      if (existing) {
        existing.occurrence_count += p.occurrence_count
      } else {
        // If no Cyrillic counterpart found yet, store with altId marker
        merged.set(cyrId, { ...p, parameter_id: cyrId, altId: p.parameter_id })
      }
    } else {
      const existing = merged.get(p.parameter_id)
      if (existing) {
        existing.occurrence_count += p.occurrence_count
      } else {
        merged.set(p.parameter_id, { ...p })
      }
    }
  }
  const allMerged = Array.from(merged.values())

  const groups: ParameterGroup[] = [
    {
      label: 'Количественные к инструменту',
      items: allMerged.filter((p) => /^П0[1-9]$/.test(p.parameter_id)),
    },
    {
      label: 'К эмитенту и истории торгов',
      items: allMerged.filter((p) => /^П1\d$/.test(p.parameter_id)),
    },
    {
      label: 'Структурные и процедурные',
      items: allMerged.filter((p) => /^П2\d$/.test(p.parameter_id)),
    },
    {
      label: 'Прочие числовые',
      items: allMerged.filter((p) => /^П[3-9]\d$/.test(p.parameter_id)),
    },
    {
      label: 'Дополнительные / нераспределённые',
      items: allMerged.filter((p) => p.parameter_id.startsWith('ADDITIONAL_')),
      dimmed: true,
    },
  ]
  return groups.filter((g) => g.items.length > 0)
}

export default function ParametersPage() {
  const [data, setData] = useState<ParameterSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    setError(null)
    fetchParameters()
      .then((d) =>
        setData([...d].sort((a, b) => a.parameter_id.localeCompare(b.parameter_id))),
      )
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  if (loading) return <LoadingState message="Загрузка каталога параметров..." />
  if (error) return <ErrorState message={error} onRetry={load} />

  const groups = groupParameters(data)
  const totalMerged = groups.reduce((sum, g) => sum + g.items.length, 0)

  return (
    <div className={styles.page}>
      <div className={styles.inner}>
        <div className={styles.header}>
          <h1 className={styles.title}>Каталог параметров</h1>
          <p className={styles.subtitle}>
            Количественные и квалитативные параметры требований к листингу
          </p>
        </div>

        {data.length === 0 ? (
          <EmptyState message="Параметры не найдены" />
        ) : (
          <div className={styles.tableWrapper}>
            <div className={styles.tableHeader}>
              <span className={styles.tableCount}>{totalMerged} параметров</span>
            </div>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>ID параметра</th>
                  <th>Название</th>
                  <th>Встречается в ячейках</th>
                </tr>
              </thead>
              <tbody>
                {groups.map((group) => (
                  <>
                    <tr key={`group-heading-${group.label}`} className={styles.groupHeadingRow}>
                      <td colSpan={3}>
                        <span className={`${styles.groupHeading}${group.dimmed ? ' ' + styles.groupDimmedHeading : ''}`}>
                          {group.label}
                        </span>
                      </td>
                    </tr>
                    {group.items.map((p) => (
                      <tr key={p.parameter_id} className={group.dimmed ? styles.groupDimmedRow : undefined}>
                        <td>
                          <code className={styles.paramId}>{p.parameter_id}</code>
                          {p.altId && (
                            <span className={styles.altIdNote}>+ {p.altId}</span>
                          )}
                        </td>
                        <td>
                          <Link
                            to={`/parameters/${encodeURIComponent(p.parameter_id)}`}
                            className={styles.paramLink}
                          >
                            {p.parameter_name}
                          </Link>
                        </td>
                        <td>
                          <span className={styles.occurrenceCount}>
                            {p.occurrence_count}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
