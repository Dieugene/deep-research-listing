import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'
import * as topojson from 'topojson-client'
import type { Topology, GeometryCollection } from 'topojson-specification'
import type { JurisdictionSummary } from '../../api/types'
import styles from './WorldMap.module.css'

interface JurisdictionPoint {
  nameEn: string
  nameRu: string
  coords: [number, number]
  active: boolean
  legalFamily?: string | null
  venueCount?: number
}

export interface WorldMapProps {
  jurisdictions?: JurisdictionSummary[]
  activeJurisdiction?: string | null
}

const BASE_POINTS: JurisdictionPoint[] = [
  { nameEn: 'United Kingdom', nameRu: 'Великобритания', coords: [-2, 54], active: true },
  { nameEn: 'Hong Kong', nameRu: 'Гонконг', coords: [114.1, 22.3], active: true },
  { nameEn: 'Germany', nameRu: 'Германия', coords: [10.5, 51.2], active: true },
  { nameEn: 'Singapore', nameRu: 'Сингапур', coords: [103.8, 1.35], active: true },
  { nameEn: 'Australia', nameRu: 'Австралия', coords: [133, -27], active: true },
  { nameEn: 'France', nameRu: 'Франция', coords: [2.3, 46.6], active: true },
  // Future jurisdictions (placeholders)
  { nameEn: 'United States', nameRu: 'США', coords: [-95, 38], active: false },
  { nameEn: 'Japan', nameRu: 'Япония', coords: [138, 36], active: false },
  { nameEn: 'China', nameRu: 'Китай', coords: [104, 35], active: false },
]

const WORLD_ATLAS_URL =
  'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

export default function WorldMap({ jurisdictions, activeJurisdiction }: WorldMapProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const [renderKey, setRenderKey] = useState(0)

  // Keep activeJurisdiction in a ref so D3 effect can read latest value
  const activeJurisdictionRef = useRef(activeJurisdiction)
  activeJurisdictionRef.current = activeJurisdiction

  // Cache world atlas to avoid re-fetching on resize
  const worldDataRef = useRef<Topology | null>(null)

  // Merge jurisdiction data from props into points
  const points: JurisdictionPoint[] = BASE_POINTS.map((p) => {
    if (!jurisdictions) return p
    const found = jurisdictions.find(
      (j) => j.name_ru === p.nameRu || j.name_en === p.nameEn,
    )
    if (!found) return p
    return {
      ...p,
      legalFamily: found.legal_family,
      venueCount: found.venue_count,
    }
  })

  // ---- ResizeObserver: re-render map on container resize ----
  useEffect(() => {
    let resizeTimer: ReturnType<typeof setTimeout> | null = null
    const observer = new ResizeObserver(() => {
      if (resizeTimer) clearTimeout(resizeTimer)
      resizeTimer = setTimeout(() => {
        setRenderKey((k) => k + 1)
      }, 200)
    })
    if (wrapperRef.current) observer.observe(wrapperRef.current)
    return () => {
      observer.disconnect()
      if (resizeTimer) clearTimeout(resizeTimer)
    }
  }, [])

  // ---- D3 render effect ----
  useEffect(() => {
    let cancelled = false

    async function render() {
      if (!svgRef.current || !wrapperRef.current) return

      const svg = d3.select(svgRef.current)
      const rect = wrapperRef.current.getBoundingClientRect()
      const width = rect.width || 800
      const height = rect.height || 500

      svg.selectAll('*').remove()
      svg.attr('viewBox', `0 0 ${width} ${height}`)

      // ---- Projection ----
      const projection = d3.geoNaturalEarth1()
        .scale(Math.min(width / 6.3, height / 3.2))
        .translate([width / 2, height / 2])

      const pathGen = d3.geoPath().projection(projection)

      // ---- Load world atlas (cached after first fetch) ----
      if (!worldDataRef.current) {
        try {
          worldDataRef.current = (await d3.json<Topology>(WORLD_ATLAS_URL)) as Topology
        } catch {
          return
        }
      }

      if (cancelled) return
      const world = worldDataRef.current

      // ---- Defs: glow filter ----
      const defs = svg.append('defs')
      const filter = defs.append('filter')
        .attr('id', 'dot-glow')
        .attr('x', '-100%')
        .attr('y', '-100%')
        .attr('width', '300%')
        .attr('height', '300%')
      filter.append('feGaussianBlur')
        .attr('in', 'SourceGraphic')
        .attr('stdDeviation', 4)
        .attr('result', 'blur')
      const merge = filter.append('feMerge')
      merge.append('feMergeNode').attr('in', 'blur')
      merge.append('feMergeNode').attr('in', 'SourceGraphic')

      const countries = topojson.feature(
        world,
        world.objects['countries'] as GeometryCollection,
      )

      // ---- Graticule ----
      const graticule = d3.geoGraticule()
      svg
        .append('path')
        .datum(graticule())
        .attr('class', 'graticule-path')
        .attr('d', pathGen)
        .attr('fill', 'none')
        .attr('stroke', 'rgba(255,255,255,0.05)')
        .attr('stroke-width', 0.5)

      // ---- Countries ----
      svg
        .selectAll<SVGPathElement, unknown>('.country')
        .data((countries as d3.ExtendedFeatureCollection).features)
        .join('path')
        .attr('class', styles.country + ' country')
        .attr('d', pathGen)

      // ---- Dots ----
      const dotGroup = svg.append('g').attr('class', 'dots')
      const currentActive = activeJurisdictionRef.current

      points.forEach((jp) => {
        const projected = projection(jp.coords)
        if (!projected) return
        const [px, py] = projected

        const isHighlighted = jp.nameRu === currentActive

        const g = dotGroup
          .append('g')
          .attr('class', `dot-group dot-${jp.nameEn.replace(/\s+/g, '-')}`)
          .attr('transform', `translate(${px},${py})`)
          .style('cursor', 'default')

        if (jp.active) {
          if (isHighlighted) {
            // Pulse ring — only for highlighted (active) point
            g.append('circle')
              .attr('r', 10)
              .attr('fill', 'none')
              .attr('stroke', 'rgba(96,165,250,0.5)')
              .attr('stroke-width', 1.5)
              .attr('class', styles.pulse)

            // Main highlighted dot
            g.append('circle')
              .attr('r', 5)
              .attr('fill', 'rgba(96,165,250,0.95)')
              .attr('style', 'filter: drop-shadow(0 0 5px rgba(96,165,250,0.65))')

            g.attr('filter', 'url(#dot-glow)')
          } else {
            // Regular active dot (not highlighted)
            g.append('circle')
              .attr('r', 3)
              .attr('fill', 'rgba(96,165,250,0.55)')
          }
        } else {
          // Inactive dot
          g.append('circle')
            .attr('r', 2.5)
            .attr('fill', 'rgba(148,163,184,0.25)')
        }
      })
    }

    render()

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [renderKey, activeJurisdiction])

  return (
    <div ref={wrapperRef} className={styles.wrapper}>
      <svg ref={svgRef} className={styles.svg} />
    </div>
  )
}
