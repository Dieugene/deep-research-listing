import { useState, useEffect } from 'react'
import type { CellContent, CellParameters } from '../../api/types'
import styles from './CellDetailPanel.module.css'

interface Props {
  cellContent: CellContent | null
  cellParameters: CellParameters | null
  activePhaseKey: string | null
  onClose: () => void
  loading?: boolean
}

type TabKey = 'content' | 'parameters'

export default function CellDetailPanel({
  cellContent,
  cellParameters,
  activePhaseKey,
  onClose,
  loading = false,
}: Props) {
  const [activeTab, setActiveTab] = useState<TabKey>('content')
  const [activePhase, setActivePhase] = useState<string | null>(activePhaseKey)

  // Sync external phase selection
  useEffect(() => {
    if (activePhaseKey) setActivePhase(activePhaseKey)
  }, [activePhaseKey])

  // Default to first phase with data
  useEffect(() => {
    if (!activePhase && cellContent?.phases.length) {
      const firstWithData = cellContent.phases.find((p) => p.has_data)
      if (firstWithData) setActivePhase(firstWithData.phase_key)
      else setActivePhase(cellContent.phases[0]?.phase_key ?? null)
    }
  }, [cellContent, activePhase])

  const currentPhase = cellContent?.phases.find((p) => p.phase_key === activePhase)

  const foundParams =
    cellParameters?.parameters.filter((p) => p.status === 'found') ?? []

  return (
    <aside className={styles.panel}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h3 className={styles.title}>
            {cellContent
              ? `${cellContent.tier} — ${cellContent.instrument_class_label}`
              : 'Детали ячейки'}
          </h3>
        </div>
        <button className={styles.closeBtn} onClick={onClose} aria-label="Закрыть">
          ×
        </button>
      </div>

      {/* Tabs */}
      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'content' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('content')}
        >
          Содержание
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'parameters' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('parameters')}
        >
          Параметры
          {foundParams.length > 0 && (
            <span className={styles.tabBadge}>{foundParams.length}</span>
          )}
        </button>
      </div>

      {/* Body */}
      <div className={styles.body}>
        {loading && (
          <div className={styles.loadingOverlay}>
            <div className={styles.spinner} />
          </div>
        )}

        {activeTab === 'content' && (
          <div className={styles.contentTab}>
            {/* Phase tabs */}
            {cellContent && cellContent.phases.length > 0 && (
              <div className={styles.phaseTabs}>
                {cellContent.phases.map((phase) => (
                  <button
                    key={phase.phase_key}
                    className={`${styles.phaseTab} ${activePhase === phase.phase_key ? styles.phaseTabActive : ''} ${!phase.has_data ? styles.phaseTabEmpty : ''}`}
                    onClick={() => setActivePhase(phase.phase_key)}
                  >
                    {phase.phase_label}
                    {!phase.has_data && <span className={styles.noDataDot} />}
                  </button>
                ))}
              </div>
            )}

            {/* Phase content */}
            {currentPhase ? (
              currentPhase.has_data ? (
                <div className={styles.sections}>
                  {currentPhase.sections.map((section) => (
                    <div key={section.section_key} className={styles.section}>
                      <h4 className={styles.sectionTitle}>{section.section_label}</h4>
                      <div className={styles.sectionText}>
                        {section.text.split('\n').map((line, i) => (
                          <p key={i} className={styles.textParagraph}>
                            {line || <br />}
                          </p>
                        ))}
                      </div>
                      {section.source && (
                        <p className={styles.source}>
                          <em>Источник: {section.source}</em>
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className={styles.noData}>
                  <p>Данные по этой фазе отсутствуют</p>
                </div>
              )
            ) : (
              !loading && (
                <div className={styles.noData}>
                  <p>Выберите ячейку матрицы для просмотра содержимого</p>
                </div>
              )
            )}
          </div>
        )}

        {activeTab === 'parameters' && (
          <div className={styles.parametersTab}>
            {foundParams.length > 0 ? (
              <table className={styles.paramTable}>
                <thead>
                  <tr>
                    <th>Параметр</th>
                    <th>Фаза</th>
                    <th>Значение</th>
                    <th>Источник</th>
                  </tr>
                </thead>
                <tbody>
                  {foundParams.map((p, i) => (
                    <tr key={`${p.parameter_id}-${p.lifecycle_phase_key}-${i}`}>
                      <td className={styles.paramName}>{p.parameter_name}</td>
                      <td className={styles.paramPhase}>{p.lifecycle_phase_label}</td>
                      <td className={styles.paramValue}>{p.value}</td>
                      <td className={styles.paramSource}>
                        {p.source ? <em>{p.source}</em> : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className={styles.noData}>
                <p>Параметры не найдены</p>
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  )
}
