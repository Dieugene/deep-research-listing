import { Link, NavLink } from 'react-router-dom'
import styles from './NavBar.module.css'

interface NavBarProps {
  isHome: boolean
  variant?: 'dark' | 'light'
}

export default function NavBar({ isHome, variant }: NavBarProps) {
  const isDark = variant === 'dark' || (variant === undefined && isHome)

  return (
    <nav className={`${styles.navbar} ${isDark ? styles.dark : styles.light}`}>
      <div className={styles.inner}>
        <Link to="/" className={styles.logo}>
          <span className={styles.logoMark}>LR</span>
          <span className={styles.logoText}>Listing Research</span>
        </Link>

        <ul className={styles.nav}>
          {/* Справочник — dropdown */}
          <li className={styles.dropdownItem}>
            <span className={styles.link}>
              Справочник
              <svg
                className={styles.dropdownChevron}
                viewBox="0 0 10 6"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M1 1l4 4 4-4" />
              </svg>
            </span>
            <div className={styles.dropdownMenu}>
              <NavLink
                to="/jurisdictions"
                className={({ isActive }) =>
                  `${styles.dropdownLink} ${isActive ? styles.active : ''}`
                }
              >
                По юрисдикциям
              </NavLink>
              <NavLink
                to="/parameters"
                className={({ isActive }) =>
                  `${styles.dropdownLink} ${isActive ? styles.active : ''}`
                }
              >
                По инструментам
              </NavLink>
            </div>
          </li>

          <li>
            <span className={`${styles.link} ${styles.inactiveLink}`}>
              Анализ
              <span className={styles.navBadge}>SOON</span>
            </span>
          </li>

          <li>
            <span className={`${styles.link} ${styles.inactiveLink}`}>
              Ассистент
              <span className={styles.navBadge}>SOON</span>
            </span>
          </li>
        </ul>
      </div>
    </nav>
  )
}
