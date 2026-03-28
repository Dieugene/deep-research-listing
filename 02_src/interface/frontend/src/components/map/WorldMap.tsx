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

// ISO alpha-2 → approximate centroid [lon, lat]
const ISO_COORDS: Record<string, [number, number]> = {
  AU: [133, -27], AT: [13.3, 47.5], BE: [4.4, 50.5], BR: [-51, -10],
  CA: [-106, 56], CL: [-71, -33], CN: [104, 35], CO: [-74, 4],
  CZ: [15.5, 49.8], DK: [10, 56], EG: [30, 27], FI: [26, 64],
  FR: [2.3, 46.6], DE: [10.5, 51.2], GR: [22, 39], HK: [114.1, 22.3],
  HU: [19.5, 47.2], IN: [79, 22], ID: [118, -2], IE: [-8, 53.5],
  IL: [35, 31.5], IT: [12.5, 42.5], JP: [138, 36], KW: [47.5, 29.3],
  MY: [102, 4], MX: [-102, 23.5], NL: [5.3, 52.2], NZ: [174, -41],
  NO: [10, 62], PE: [-76, -10], PH: [122, 12.5], PL: [20, 52],
  PT: [-8, 39.5], QA: [51.2, 25.3], RU: [100, 60], SA: [45, 24],
  SG: [103.8, 1.35], ZA: [25, -29], KR: [128, 36], ES: [-3.7, 40.4],
  SE: [15, 62], CH: [8.2, 46.8], TW: [121, 23.7], TH: [101, 14],
  TR: [35, 39], AE: [54, 24], GB: [-2, 54], US: [-95, 38],
}

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

  // Build points dynamically from jurisdictions prop
  const points: JurisdictionPoint[] = (jurisdictions ?? [])
    .filter((j) => j.iso_code && ISO_COORDS[j.iso_code])
    .map((j) => ({
      nameEn: j.name_en,
      nameRu: j.name_ru,
      coords: ISO_COORDS[j.iso_code!],
      active: j.has_full_data,
      legalFamily: j.legal_family,
      venueCount: j.venue_count,
    }))

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
