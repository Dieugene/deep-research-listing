import { Link } from 'react-router-dom'
import type { ParameterComparison, ParameterComparisonEntry } from '../../api/types'
import EmptyState from '../common/EmptyState'
import styles from './ParameterTable.module.css'

interface Props {
  data: ParameterComparison
}

type ConstructionType = 'percentage' | 'monetary' | 'numeric' | 'qualitative'

const TYPE_LABELS: Record<ConstructionType, string> = {
  percentage: 'Процентный показатель',
  monetary: 'Денежный показатель',
  numeric: 'Числовой показатель',
  qualitative: 'Качественный / описательный',
}

const TYPE_ORDER: ConstructionType[] = ['percentage', 'monetary', 'numeric', 'qualitative']

function inferConstructionType(value: string): ConstructionType {
  if (/%/.test(value)) return 'percentage'
  if (/[$€£¥₽]|млн|млрд|тыс|mln|bln|thousand|million/.test(value)) return 'monetary'
  if (/^\d+[\s,.]?\d*$/.test(value.trim())) return 'numeric'
  return 'qualitative'
}

function extractLeadingNumber(value: string): number | null {
  const match = value.match(/[\d]+(?:[.,]\d+)?/)
  if (!match) return null
  return parseFloat(match[0].replace(',', '.'))
}

function sortByValue(
  entries: ParameterComparisonEntry[],
  type: ConstructionType,
): ParameterComparisonEntry[] {
  if (type === 'qualitative') return entries
  return [...entries].sort((a, b) => {
    const na = extractLeadingNumber(a.value)
    const nb = extractLeadingNumber(b.value)
    if (na === null && nb === null) return 0
    if (na === null) return 1
    if (nb === null) return -1
    return na - nb
  })
}

export default function ParameterTable({ data }: Props) {
  if (!data.entries.length) {
    return <EmptyState message="Данные по параметру не найдены" />
  }

  // Group entries by construction type
  const byType = new Map<ConstructionType, ParameterComparisonEntry[]>()
  for (const entry of data.entries) {
    const type = inferConstructionType(entry.value)
    const bucket = byType.get(type)
    if (bucket) {
      bucket.push(entry)
    } else {
      byType.set(type, [entry])
    }
  }

  return (
    <div className={styles.wrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Юрисдикция</th>
            <th>Площадка</th>
            <th>Тир</th>
            <th>Инструмент</th>
            <th>Фаза</th>
            <th>Значение</th>
            <th>Источник</th>
          </tr>
        </thead>
        <tbody>
          {TYPE_ORDER.filter((type) => byType.has(type)).map((type) => {
            const entries = sortByValue(byType.get(type)!, type)
            return (
              <>
                <tr
                  key={`group-${type}`}
                  className={styles.groupRow}
                >
                  <td colSpan={7}>{TYPE_LABELS[type]}</td>
                </tr>
                {entries.map((entry, i) => (
                  <tr key={`${entry.cell_id}-${entry.lifecycle_phase_key}-${i}`}>
                    <td className={styles.jurisdiction}>
                      <Link to={`/jurisdictions/${encodeURIComponent(entry.jurisdiction_ru)}`}>
                        {entry.jurisdiction_ru}
                      </Link>
                    </td>
                    <td>
                      <Link to={`/venues/${encodeURIComponent(entry.venue_key)}`}>
                        {entry.venue_name}
                      </Link>
                    </td>
                    <td className={styles.tier}>{entry.tier}</td>
                    <td>{entry.instrument_class_label}</td>
                    <td className={styles.phase}>{entry.lifecycle_phase_label}</td>
                    <td className={styles.value}>{entry.value}</td>
                    <td className={styles.source}>
                      {entry.source ? <em>{entry.source}</em> : '—'}
                    </td>
                  </tr>
                ))}
              </>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
