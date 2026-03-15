import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { fetchParameter } from '../api/parameters'
import type { ParameterComparison } from '../api/types'
import LoadingState from '../components/common/LoadingState'
import ErrorState from '../components/common/ErrorState'
import ParameterTable from '../components/parameter/ParameterTable'
import styles from './ParameterPage.module.css'

export default function ParameterPage() {
  const { parameterId } = useParams<{ parameterId: string }>()
  const [data, setData] = useState<ParameterComparison | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    if (!parameterId) return
    setLoading(true)
    setError(null)
    fetchParameter(parameterId)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [parameterId])

  if (loading) return <LoadingState message="Загрузка данных параметра..." />
  if (error) return <ErrorState message={error} onRetry={load} />
  if (!data) return <ErrorState message="Параметр не найден" />

  return (
    <div className={styles.page}>
      <div className={styles.inner}>
        {/* Breadcrumb */}
        <nav className={styles.breadcrumb}>
          <Link to="/parameters">Параметры</Link>
          <span className={styles.sep}>→</span>
          <span>{data.parameter_name}</span>
        </nav>

        {/* Header */}
        <div className={styles.header}>
          <div>
            <code className={styles.paramId}>{data.parameter_id}</code>
            <h1 className={styles.title}>{data.parameter_name}</h1>
          </div>
          <div className={styles.entryCount}>
            <span className={styles.entryCountValue}>{data.entries.length}</span>
            <span className={styles.entryCountLabel}>вхождений</span>
          </div>
        </div>

        {/* Comparison table */}
        <div className={styles.tableCard}>
          <div className={styles.tableCardHeader}>
            <h2 className={styles.tableTitle}>Сравнительная таблица значений</h2>
            <p className={styles.tableSubtitle}>
              Значения параметра по юрисдикциям, площадкам и инструментам
            </p>
          </div>
          <ParameterTable data={data} />
        </div>
      </div>
    </div>
  )
}
