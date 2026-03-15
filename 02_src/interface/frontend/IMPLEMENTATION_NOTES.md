# Frontend Implementation Notes

## Stack

- Vite 5 + React 18 + TypeScript (strict)
- React Router v6 (createBrowserRouter)
- D3.js v7 + topojson-client (world map)
- Recharts (dependency installed, not yet used — ready for future charts)
- CSS Modules throughout (no CSS-in-JS)

## Setup

```
cd 02_src/interface/frontend
npm install
npm run dev     # → http://localhost:3000
npm run build   # TypeScript check + Vite bundle
```

The Vite dev server proxies `/api/*` → `http://localhost:8000`.

---

## Files Created (63 total)

### Config
- `package.json` — includes `topojson-client` + `@types/topojson-client`
- `tsconfig.json`, `tsconfig.node.json`
- `vite.config.ts` — port 3000, proxy /api → 8000
- `index.html` — Google Fonts: Inter + JetBrains Mono

### Entry
- `src/main.tsx`
- `src/App.tsx`

### API layer (`src/api/`)
- `types.ts` — all TypeScript interfaces from spec
- `client.ts` — `apiFetch<T>()` wrapper
- `jurisdictions.ts`, `venues.ts`, `cells.ts`, `parameters.ts`

### Router (`src/router/index.tsx`)
All 8 routes as specified.

### Styles (`src/styles/`)
- `theme.css` — CSS variables (colors, spacing, radius, shadows, transitions, z-index)
- `global.css` — reset, typography, scrollbar, focus styles

### Layout components
- `AppLayout` — detects `/` route → applies dark theme to body, light otherwise
- `NavBar` — fixed top, dark/light variant, active link highlighting

### Common components
- `ValidationBadge` — green/yellow/red/unknown with dot indicator
- `LoadingState`, `ErrorState`, `EmptyState`

### Showcase
- `MetricsCounter` — IntersectionObserver + requestAnimationFrame easeOutCubic animation

### Map
- `WorldMap` — D3 NaturalEarth1 projection, loads world-atlas TopoJSON from CDN,
  pulse animation on active dots, tooltip, click navigation

### Matrix (core visual)
- `LifecycleMatrix` — CSS Grid, row/column headers, legend
- `MatrixCell` — 3 fill intensities (high/med/low), striped N/A, active border, hover scale
- `CellDetailPanel` — tabs (Content/Parameters), phase sub-tabs, section text, parameters table

### Jurisdiction
- `JurisdictionCard`, `TermsMappingTable`

### Venue
- `VenueCard`, `CellsGrid` — grouped by instrument_class_label

### Parameter
- `ParameterTable` — sorted by jurisdiction_ru

### Pages
- `HomePage` — dark hero + WorldMap + MetricsCounter × 4, nav cards (2 active / 2 disabled), coverage section
- `JurisdictionsPage` — table with summary bar
- `JurisdictionPage` — 2-column grid, accordion Level4 sections
- `VenuePage` — header + meta row + CellsGrid
- `MatrixPage` — breadcrumbs, matrix + sticky panel (2-col layout when open)
- `ParametersPage`, `ParameterPage`
- `NotFoundPage`

---

## Key Design Decisions

### MatrixPage layout
When a cell is clicked the detail panel slides in to the right as a sticky sidebar
(`grid-template-columns: 1fr 440px`). On narrow screens (< 1200px) it drops below.
The panel fetches both `/content` and `/parameters` in parallel on each click.

### Phase mapping in CellDetailPanel
The `rowKey` from `MatrixRow` is passed as the initial active phase key. The panel
component maps it to `PhaseContent.phase_key` via array find. If no match is found,
it defaults to the first phase that has data.

### WorldMap CDN dependency
The component loads `https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json`
at runtime. If offline, the map renders empty (no crash). Consider bundling the file
in `public/` for production.

### Validation status for Level4
`JurisdictionPage` manually maps the string `validation_status` from `Level4Data`
to the typed `ValidationStatus` union. The API field is untyped `string` in the spec.

### URL encoding
All `name_ru` and `venue_key` params use `encodeURIComponent()` when building URLs.
React Router's `useParams()` auto-decodes them.

---

## Known Limitations / TODOs

1. `WorldMap` — SVG animation (pulse) declared in CSS but the `r` attribute animation
   requires SMIL or a JS approach; currently uses a CSS class `.pulse` that animates
   opacity. Works visually, but for a true radius pulse a JS interval would be cleaner.

2. `LifecycleMatrix` uses React fragment shorthand inside `.map()` — each iteration
   returns `<>row header + N cells</>`. The fragment key is on the row header div,
   which is correct for React but may produce a warning in strict mode about
   fragment keys. Can be refactored to a `<React.Fragment key={row.row_key}>` wrapper.

3. The `Recharts` dependency is installed but not currently used. It is available for
   future mini-charts (e.g., text volume bar chart in MatrixPage stats).

4. Responsive breakpoints are minimal (desktop-first per spec). The primary breakpoints
   defined are 1280px (homepage nav cards → 2 col) and 1024px/1200px for detail pages.

---

## Changelog — Hero & Globe Redesign (2026-03-12)

### WorldMap.tsx

- **Props**: Added `WorldMapProps` interface (`jurisdictions?: JurisdictionSummary[]`, `jurisdictionDetails?: Record<string, { venues: string[] }>`).
- **Projection**: Replaced `d3.geoNaturalEarth1` with `d3.geoOrthographic` (globe view, scale = `min(w,h)/2 - 20`).
- **Background sphere**: Dark navy circle (`#0d1b2e`) drawn before countries so globe has a solid fill.
- **Glow filter**: SVG `<defs>` block with `#dot-glow` (`feGaussianBlur stdDeviation=4`) applied to active dot `<g>` elements.
- **Graticule**: Added class `graticule-path` for targeting in animation loop.
- **Arc line**: Great-circle arc UK ↔ HK (`arc-uk-hk`) with dashed blue stroke; redrawn each animation frame.
- **Dot differentiation**: Active r=7, fill `#3b82f6`, white stroke, glow filter, cursor pointer; inactive r=3.5, grey fill, no events.
- **Animation loop**: `requestAnimationFrame` rotating globe +0.05°/frame via `rotateXRef` (no re-renders). Paused when `isHoveringRef.current === true` (SVG mouseenter/mouseleave).
- **Dot visibility**: Checked each frame via `d3.geoDistance(coords, [-rot, 30]) <= PI/2`; display toggled to none when on the far hemisphere.
- **Rich tooltip**: React state object with `nameRu`, `nameEn`, `legalFamily`, `venueCount`, and `venueNames` (from `jurisdictionDetails`). Shows venue list when data is available.
- **Tooltip animation**: CSS `transition: opacity 0.2s ease, transform 0.2s ease` with translateY reveal.

### WorldMap.module.css

- `.wrapper` / `.svg`: unchanged (full container).
- `.pulse` keyframes updated to symmetric ease-in-out: `0%,100%{opacity:0.5; r:10} 50%{opacity:1; r:14}`.
- `.tooltip`: expanded to `border-radius: 8px; min-width: 200px; padding: 12px 16px; transition: opacity 0.2s, transform 0.2s`.
- New classes: `.tooltipName`, `.tooltipNameEn`, `.tooltipMeta`, `.tooltipVenues`, `.tooltipVenues li`.

### HomePage.tsx

- **Jurisdiction details pre-fetch**: `jurisdictionDetails` state; fires `fetchJurisdiction` for each `has_full_data` jurisdiction after jurisdictions list loads.
- **WorldMap receives props**: `jurisdictions` and `jurisdictionDetails` passed down.
- **Hero structure**: `.mapBackdrop` (absolute inset, full bleed) + `.heroGradient` overlay (z-index 1) + `.heroContent` (z-index 2) + `.metricsBar` (z-index 2, pinned to hero bottom).
- **Metrics**: Now 4 fixed counters (47 jurisdictions, 65 venues, 4 instrument classes, ~1000 regimes). Removed dynamic pilot-progress counter from hero section.
- **NAV_CARDS**: Updated descriptions; added `preview` and `eta` fields. Inactive cards show "Скоро" badge + `eta` hint.

### HomePage.module.css

- `.hero`: `position: relative; min-height: 100vh; overflow: hidden; display: flex; flex-direction: column; justify-content: flex-end`.
- `.mapBackdrop`: `position: absolute; inset: 0` (no z-index, sits behind gradient and content).
- `.heroGradient`: left-to-right gradient overlay for text readability, `z-index: 1`.
- `.heroContent`: `position: relative; z-index: 2; padding: 120px 0 80px var(--space-2xl); max-width: 560px`.
- `.metricsBar`: `z-index: 2; backdrop-filter: blur(12px); border-top: 1px solid rgba(255,255,255,0.08)`.
- Removed `.heroLeft` / `.heroRight` / grid layout (`.heroContent` was previously a 2-column grid).
- `.navCardDisabled`: opacity reduced from `0.5` to `0.75` (less aggressive fade).
- `.navCardBadge`: changed from grey to blue-tinted style matching accent.
- `.navCardEta`: new class for ETA hint text on coming-soon cards.
- Added 768px responsive breakpoint (single-column cards, full-width hero text).

