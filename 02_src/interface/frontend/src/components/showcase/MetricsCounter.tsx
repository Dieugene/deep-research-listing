import { useEffect, useRef, useState } from 'react'
import styles from './MetricsCounter.module.css'

interface Props {
  target: number
  label: string
  prefix?: string
  suffix?: string
  duration?: number
}

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3)
}

export default function MetricsCounter({
  target,
  label,
  prefix = '',
  suffix = '',
  duration = 1500,
}: Props) {
  const [count, setCount] = useState(0)
  const [visible, setVisible] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const animatedRef = useRef(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !animatedRef.current) {
          setVisible(true)
          animatedRef.current = true
        }
      },
      { threshold: 0.3 },
    )

    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!visible) return

    const startTime = performance.now()

    const tick = (now: number) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      const easedProgress = easeOutCubic(progress)
      setCount(Math.round(easedProgress * target))

      if (progress < 1) {
        requestAnimationFrame(tick)
      }
    }

    const raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [visible, target, duration])

  return (
    <div ref={ref} className={styles.counter}>
      <div className={styles.number}>
        {prefix}
        <span className={styles.value}>{count.toLocaleString('ru-RU')}</span>
        {suffix}
      </div>
      <div className={styles.label}>{label}</div>
    </div>
  )
}
