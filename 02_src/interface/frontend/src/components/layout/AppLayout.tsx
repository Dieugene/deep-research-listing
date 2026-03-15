import { Outlet, useLocation } from 'react-router-dom'
import NavBar from './NavBar'
import styles from './AppLayout.module.css'

export default function AppLayout() {
  const location = useLocation()
  const isHome = location.pathname === '/'

  return (
    <div className={`${styles.layout} ${isHome ? styles.darkLayout : styles.lightLayout}`}>
      <NavBar isHome={isHome} />
      <main className={`${styles.main} ${isHome ? '' : styles.mainLight}`}>
        <Outlet />
      </main>
    </div>
  )
}
