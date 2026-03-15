import { Link } from 'react-router-dom'
import type { CellInVenue } from '../../api/types'
import ValidationBadge from '../common/ValidationBadge'
import styles from './CellsGrid.module.css'

interface Props {
  cells: CellInVenue[]
  venueKey: string
  jurisdictionNameRu: string
}

interface CellGroup {
  label: string
  cells: CellInVenue[]
}

function groupByInstrument(cells: CellInVenue[]): CellGroup[] {
  const map = new Map<string, CellInVenue[]>()
  for (const cell of cells) {
    const key = cell.instrument_class_label
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(cell)
  }
  return Array.from(map.entries()).map(([label, cells]) => ({ label, cells }))
}

function cellUrl(venueKey: string, cell: CellInVenue, jurisdictionNameRu: string) {
  return `/venues/${encodeURIComponent(venueKey)}/matrix/${encodeURIComponent(cell.cell_id)}?name_ru=${encodeURIComponent(jurisdictionNameRu)}&venue_key=${encodeURIComponent(venueKey)}`
}

interface PhaseIndicatorProps {
  hasData: boolean
  to: string
  title: string
}

function PhaseIndicator({ hasData, to, title }: PhaseIndicatorProps) {
  if (hasData) {
    return (
      <Link to={to} className={styles.phaseLink} title={title}>
        ●
      </Link>
    )
  }
  return <span className={styles.phaseEmpty} title="Нет данных">○</span>
}

export default function CellsGrid({ cells, venueKey, jurisdictionNameRu }: Props) {
  const groups = groupByInstrument(cells)

  if (!cells.length) {
    return <p className={styles.empty}>Ячейки не найдены</p>
  }

  return (
    <div className={styles.wrapper}>
      {groups.map((group) => (
        <div key={group.label} className={styles.group}>
          <h4 className={styles.groupTitle}>{group.label}</h4>
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Тир / Категория</th>
                  <th title="Допуск">Д</th>
                  <th title="Поддержание">П</th>
                  <th title="Мониторинг / Исключение">М</th>
                  <th title="Параметры">#</th>
                  <th>Статус</th>
                </tr>
              </thead>
              <tbody>
                {group.cells.map((cell) => {
                  const url = cellUrl(venueKey, cell, jurisdictionNameRu)
                  return (
                    <tr key={cell.cell_id}>
                      <td className={styles.tierName}>
                        <Link to={url} className={styles.tierLink}>
                          {cell.tier}
                        </Link>
                      </td>
                      <td>
                        <PhaseIndicator
                          hasData={cell.has_admission_data}
                          to={url}
                          title={`Допуск — ${cell.tier}`}
                        />
                      </td>
                      <td>
                        <PhaseIndicator
                          hasData={cell.has_maintenance_data}
                          to={url}
                          title={`Поддержание — ${cell.tier}`}
                        />
                      </td>
                      <td>
                        <PhaseIndicator
                          hasData={cell.has_enforcement_data}
                          to={url}
                          title={`Мониторинг/Исключение — ${cell.tier}`}
                        />
                      </td>
                      <td>
                        {cell.has_parameters ? (
                          <Link to={url} className={styles.paramsYes} title="Есть параметры">★</Link>
                        ) : (
                          <span className={styles.paramsNo} title="Параметры отсутствуют">☆</span>
                        )}
                      </td>
                      <td>
                        <ValidationBadge status={cell.validation_status} size="sm" />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  )
}
