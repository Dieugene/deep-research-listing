import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchJurisdictions } from '../api/jurisdictions'
import type { JurisdictionSummary } from '../api/types'
import LoadingState from '../components/common/LoadingState'
import ErrorState from '../components/common/ErrorState'
import styles from './JurisdictionsPage.module.css'

// ── Helpers ──────────────────────────────────────────────────────────────────

const STATUS_ORDER: Record<string, number> = { full: 0, partial: 1, empty: 2 }
const STATUS_LABELS: Record<string, string> = {
  full: 'Верифицировано',
  partial: 'Частично',
  empty: 'В работе',
}

type SortField = 'name' | 'legal_family' | 'market_type' | 'venue_count' | 'data_status'
type SortDir = 'asc' | 'desc'
type MarketFilter = 'all' | 'DM' | 'EM'

// ── Component ─────────────────────────────────────────────────────────────────

export default function JurisdictionsPage() {
  const navigate = useNavigate()

  const [jurisdictions, setJurisdictions] = useState<JurisdictionSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [filterMarket, setFilterMarket] = useState<MarketFilter>('all')
  const [filterLegal, setFilterLegal] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState<SortField>('data_status')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [page, setPage] = useState(1)
  const PAGE_SIZE = 15

  const load = () => {
    setLoading(true)
    setError(null)
    fetchJurisdictions()
      .then(setJurisdictions)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  // ── Derived stats (always from full dataset) ─────────────────────────────
  const totalVenues = useMemo(
    () => jurisdictions.reduce((s, j) => s + j.venue_count, 0),
    [jurisdictions],
  )
  const fullCount = useMemo(
    () => jurisdictions.filter((j) => j.data_status === 'full').length,
    [jurisdictions],
  )

  // ── Unique legal families for filter ─────────────────────────────────────
  const legalFamilies = useMemo(() =>
    Array.from(new Set(
      jurisdictions
        .map(j => j.legal_family?.toLowerCase())
        .filter((f): f is string => Boolean(f))
    )).sort(),
    [jurisdictions]
  )

  // ── Filtered + sorted data ───────────────────────────────────────────────
  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()

    let result = jurisdictions.filter((j) => {
      if (filterMarket !== 'all' && j.market_type !== filterMarket) return false
      if (filterLegal !== 'all' && j.legal_family?.toLowerCase() !== filterLegal.toLowerCase())
        return false
      if (q && !j.name_ru.toLowerCase().includes(q) && !j.name_en.toLowerCase().includes(q))
        return false
      return true
    })

    result = [...result].sort((a, b) => {
      let av: string | number
      let bv: string | number

      switch (sortField) {
        case 'name':
          av = a.name_ru
          bv = b.name_ru
          break
        case 'legal_family':
          av = a.legal_family ?? ''
          bv = b.legal_family ?? ''
          break
        case 'market_type':
          av = a.market_type ?? ''
          bv = b.market_type ?? ''
          break
        case 'venue_count':
          av = a.venue_count
          bv = b.venue_count
          break
        case 'data_status':
          av = STATUS_ORDER[a.data_status] ?? 9
          bv = STATUS_ORDER[b.data_status] ?? 9
          break
        default:
          return 0
      }

      const dir = sortDir === 'asc' ? 1 : -1
      if (av < bv) return -dir
      if (av > bv) return dir
      return 0
    })

    return result
  }, [jurisdictions, filterMarket, filterLegal, search, sortField, sortDir])

  // ── Pagination ───────────────────────────────────────────────────────────
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const safePage = Math.min(page, totalPages)
  const pageStart = (safePage - 1) * PAGE_SIZE
  const pageRows = filtered.slice(pageStart, pageStart + PAGE_SIZE)

  // Reset page to 1 when filters/search change
  const handleFilterMarket = (v: MarketFilter) => {
    setFilterMarket(v)
    setPage(1)
  }
  const handleFilterLegal = (v: string) => {
    setFilterLegal(v)
    setPage(1)
  }
  const handleSearch = (v: string) => {
    setSearch(v)
    setPage(1)
  }

  // ── Sort toggle ──────────────────────────────────────────────────────────
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDir('asc')
    }
    setPage(1)
  }

  const sortArrow = (field: SortField) => {
    if (sortField !== field) return <span className={styles.sortArrow}>↕</span>
    return (
      <span className={`${styles.sortArrow} ${styles.sortArrowActive}`}>
        {sortDir === 'asc' ? '↑' : '↓'}
      </span>
    )
  }

  // ── Pagination buttons ───────────────────────────────────────────────────
  function renderPageButtons() {
    const btns: React.ReactNode[] = []
    for (let p = 1; p <= totalPages; p++) {
      const near = p === 1 || p === totalPages || Math.abs(p - safePage) <= 1
      const ellipsis = Math.abs(p - safePage) === 2
      if (near) {
        btns.push(
          <button
            key={p}
            className={`${styles.pageBtn} ${p === safePage ? styles.pageBtnActive : ''}`}
            onClick={() => setPage(p)}
          >
            {p}
          </button>,
        )
      } else if (ellipsis) {
        btns.push(
          <span key={`ellipsis-${p}`} className={styles.pageEllipsis}>
            …
          </span>,
        )
      }
    }
    return btns
  }

  // ── Render ───────────────────────────────────────────────────────────────
  if (loading) return <LoadingState message="Загрузка справочника юрисдикций..." />
  if (error) return <ErrorState message={error} onRetry={load} />

  return (
    <div className={styles.page}>
      {/* Page header */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.title}>Справочник юрисдикций</h1>
          <p className={styles.subtitle}>Регуляторные режимы листинга ценных бумаг по юрисдикциям</p>
        </div>
      </div>

      {/* Stats strip */}
      <div className={styles.statsStrip}>
        <div className={`${styles.statPill} ${styles.statPillAccent}`}>
          <span className={styles.statVal}>{jurisdictions.length}</span>
          <span className={styles.statLabel}>юрисдикций в периметре</span>
        </div>
        <div className={styles.statPill}>
          <span className={styles.statVal}>{fullCount}</span>
          <span className={styles.statLabel}>с полными данными</span>
        </div>
        <div className={styles.statPill}>
          <span className={styles.statVal}>{totalVenues}</span>
          <span className={styles.statLabel}>площадок в базе</span>
        </div>
        <div className={styles.statPill}>
          <span className={styles.statVal}>{filtered.length}</span>
          <span className={styles.statLabel}>показано</span>
        </div>
      </div>

      {/* Filter bar */}
      <div className={styles.filterBar}>
        {/* Search */}
        <div className={styles.filterSearchWrap}>
          <span className={styles.searchIcon}>⌕</span>
          <input
            className={styles.filterSearch}
            type="text"
            placeholder="Поиск юрисдикции..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
          />
        </div>

        <div className={styles.filterSep} />

        {/* Market filter */}
        <div className={styles.filterGroup}>
          {(['all', 'DM', 'EM'] as MarketFilter[]).map((v) => (
            <button
              key={v}
              className={`${styles.filterBtn} ${filterMarket === v ? styles.filterBtnActive : ''}`}
              onClick={() => handleFilterMarket(v)}
            >
              {v === 'all' ? 'Все рынки' : v === 'DM' ? 'DM — развитые' : 'EM — развивающиеся'}
            </button>
          ))}
        </div>

        <div className={styles.filterSep} />

        {/* Legal family filter */}
        <div className={styles.filterGroup}>
          <button
            className={`${styles.filterBtn} ${filterLegal === 'all' ? styles.filterBtnActive : ''}`}
            onClick={() => handleFilterLegal('all')}
          >
            Все семьи
          </button>
          {legalFamilies.map((v) => (
            <button
              key={v}
              className={`${styles.filterBtn} ${filterLegal === v ? styles.filterBtnActive : ''}`}
              onClick={() => handleFilterLegal(v)}
            >
              {v.toLowerCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th
                className={`${styles.th} ${sortField === 'name' ? styles.thSorted : ''}`}
                style={{ width: '260px' }}
                onClick={() => handleSort('name')}
              >
                Юрисдикция {sortArrow('name')}
              </th>
              <th
                className={`${styles.th} ${sortField === 'legal_family' ? styles.thSorted : ''}`}
                onClick={() => handleSort('legal_family')}
              >
                Правовая семья {sortArrow('legal_family')}
              </th>
              <th
                className={`${styles.th} ${sortField === 'market_type' ? styles.thSorted : ''}`}
                onClick={() => handleSort('market_type')}
              >
                Рынок {sortArrow('market_type')}
              </th>
              <th
                className={`${styles.th} ${styles.thCenter} ${sortField === 'venue_count' ? styles.thSorted : ''}`}
                onClick={() => handleSort('venue_count')}
              >
                Площадок {sortArrow('venue_count')}
              </th>
              <th
                className={`${styles.th} ${sortField === 'data_status' ? styles.thSorted : ''}`}
                onClick={() => handleSort('data_status')}
              >
                Данные {sortArrow('data_status')}
              </th>
            </tr>
          </thead>
          <tbody>
            {pageRows.length === 0 ? (
              <tr>
                <td colSpan={5}>
                  <div className={styles.emptyState}>
                    <div className={styles.emptyIcon}>⊘</div>
                    <p>Ничего не найдено. Измените фильтры.</p>
                  </div>
                </td>
              </tr>
            ) : (
              pageRows.map((j) => {
                const hasData = j.data_status !== 'empty'

                return (
                  <tr
                    key={j.name_ru}
                    className={!hasData ? `${styles.row} ${styles.rowNoData}` : styles.row}
                    onClick={hasData ? () => navigate(`/jurisdictions/${encodeURIComponent(j.name_ru)}`) : undefined}
                  >
                    {/* Flag + Name */}
                    <td className={styles.td}>
                      <div className={styles.jurCell}>
                        <div className={styles.jurFlag}>
                          {j.iso_code ? (
                            <img
                              src={`https://flagcdn.com/24x18/${j.iso_code.toLowerCase()}.png`}
                              srcSet={`https://flagcdn.com/48x36/${j.iso_code.toLowerCase()}.png 2x`}
                              width={24}
                              height={18}
                              alt={j.name_en}
                              style={{ display: 'block' }}
                            />
                          ) : (
                            <span style={{ fontSize: '16px' }}>🌐</span>
                          )}
                        </div>
                        <div>
                          <div className={styles.jurName}>{j.name_ru}</div>
                          <div className={styles.jurSub}>{j.name_en}</div>
                        </div>
                      </div>
                    </td>

                    {/* Legal family */}
                    <td className={styles.td}>
                      {j.legal_family ? (
                        <span className={styles.legalChip}>{j.legal_family?.toLowerCase()}</span>
                      ) : (
                        <span className={styles.dash}>—</span>
                      )}
                    </td>

                    {/* Market type */}
                    <td className={styles.td}>
                      {j.market_type ? (
                        <span
                          className={`${styles.marketBadge} ${
                            j.market_type === 'DM' ? styles.marketDm : styles.marketEm
                          }`}
                        >
                          {j.market_type}
                        </span>
                      ) : (
                        <span className={styles.dash}>—</span>
                      )}
                    </td>

                    {/* Venue count */}
                    <td className={`${styles.td} ${styles.tdCenter}`}>
                      {j.venue_count > 0 ? (
                        <span className={styles.venuesVal}>{j.venue_count}</span>
                      ) : (
                        <span className={styles.venuesValZero}>—</span>
                      )}
                    </td>

                    {/* Data status */}
                    <td className={styles.td}>
                      <span
                        className={`${styles.status} ${
                          j.data_status === 'full'
                            ? styles.statusFull
                            : j.data_status === 'partial'
                              ? styles.statusPartial
                              : styles.statusEmpty
                        }`}
                      >
                        {STATUS_LABELS[j.data_status] ?? j.data_status}
                      </span>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>

          {/* Pagination inside table footer */}
          {totalPages > 1 && (
            <tfoot>
              <tr>
                <td colSpan={5} className={styles.paginationCell}>
                  <div className={styles.pagination}>
                    <span className={styles.pageInfo}>
                      {pageStart + 1}–{Math.min(safePage * PAGE_SIZE, filtered.length)} из{' '}
                      {filtered.length}
                    </span>
                    <div className={styles.pageBtns}>
                      <button
                        className={styles.pageBtn}
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={safePage === 1}
                      >
                        ‹
                      </button>
                      {renderPageButtons()}
                      <button
                        className={styles.pageBtn}
                        onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                        disabled={safePage === totalPages}
                      >
                        ›
                      </button>
                    </div>
                  </div>
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  )
}
