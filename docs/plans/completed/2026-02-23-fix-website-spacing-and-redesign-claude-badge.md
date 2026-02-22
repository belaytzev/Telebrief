# Fix Website Spacing and Redesign Claude Code Button

## Overview

Two fixes to the Telebrief website:

1. Center `.hero-title` and `.hero-desc` elements properly — they have `max-width` constraints but lack `margin: 0 auto`, so they align to the left edge of the container despite the parent having `text-align: center`.
2. Redesign the footer "Powered by Claude Code" link from a plain amber-colored text link into a styled blue pill/badge button using the site's accent blue (#1b8ec9), consistent with the hero `.claude-badge` aesthetic.

## Context

- Files involved: `website/src/pages/index.astro` (contains all page styles inline)
- Current color for both badge elements: `--warm` (#f5a623, amber/orange)
- Target color for redesigned button: `--accent` (#1b8ec9) and associated variables (`--accent-border`, `--accent-dim`, `--accent-light`)
- The `.claude-badge` in the hero already uses a correct `margin: 0 auto 2rem` pattern — the hero-title/desc need the same treatment
- No backend changes, no tests needed — pure CSS/layout fix

## Development Approach

- No testing framework for CSS — manual verification by building the Astro site
- Make changes in `website/src/pages/index.astro` only
- Build command: `cd website && npm run build` to verify no build errors

## Implementation Steps

### Task 1: Fix hero element centering

**Files:**
- Modify: `website/src/pages/index.astro`

- [x] In `.hero-title` CSS rule, change `margin-bottom: 1.5rem` to `margin: 0 auto 1.5rem` to add horizontal centering
- [x] In `.hero-desc` CSS rule, change `margin-bottom: 2.5rem` to `margin: 0 auto 2.5rem` to add horizontal centering
- [x] Verify hero section has symmetric vertical padding — currently `padding: 5.5rem 0 5rem`. Equalize to `5.5rem 0` for visual balance

### Task 2: Redesign "Powered by Claude Code" button

**Files:**
- Modify: `website/src/pages/index.astro`

The `.claude-credit` element at footer bottom-right needs to become a proper button-style badge in accent blue:

- [x] Change `.claude-credit` color from `var(--warm)` to `var(--accent)`
- [x] Add `border: 1px solid var(--accent-border)` to give it a bordered pill appearance
- [x] Add `background: var(--accent-dim)` for a subtle fill matching the `tag-a` style
- [x] Add `padding: 0.28rem 0.7rem` and `border-radius: 4px` to make it pill-shaped
- [x] Remove `opacity: 0.75` and the hover opacity trick — replace hover with `border-color: var(--accent)` and `color: var(--accent-light)` for a clean accent-on-hover
- [x] Keep the SVG code icon but match its color to the new accent scheme

### Task 3: Verify and build

- [x] Run `cd website && npm run build` — must complete without errors
- [x] Visually inspect `website/dist/index.html` or run `npm run dev` to check layout
- [x] Confirm hero title and description appear centered
- [x] Confirm "Powered by Claude Code" button appears blue and button-like
- [x] Move this plan to `docs/plans/completed/`
