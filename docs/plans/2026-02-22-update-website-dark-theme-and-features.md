# Update Website: Dark Theme + Feature Content Refresh

## Overview
Switch the Telebrief landing page from its current light skeuomorphic design to a dark/black theme inspired by ralphex.com (dark background, terminal-style code blocks, developer-focused aesthetic). Also update content to reflect current features: add /help command, Table of Contents navigation feature card, and any other gaps between README and website.

## Context
- Files involved:
  - `website/src/styles/global.css` — all CSS variables and base styles
  - `website/src/pages/index.astro` — page content + inline component styles
  - `website/src/layouts/Layout.astro` — HTML shell (meta tags, no styles)
- ralphex.com design: dark backgrounds, developer-focused, clean monospace code blocks, accent color is teal/green
- Current theme: light blue/white skeuomorphic
- Missing from website vs README: `/help` command, Table of Contents Navigation feature card

## Development Approach
- Testing approach: Regular (visual inspection after build)
- No Python tests needed for website-only changes
- Build command: `cd website && npm run build` (verify no Astro errors)
- Preview command: `cd website && npm run dev`

## Implementation Steps

### Task 1: Redesign global.css with dark theme

**Files:**
- Modify: `website/src/styles/global.css`

- [x] Replace color palette variables with dark theme:
  - `--color-bg-base`: `#0d0d0d` (near-black body background)
  - `--color-bg-surface`: `#161616` (card/panel background)
  - `--color-bg-raised`: `#1e1e1e` (elevated surfaces)
  - `--color-primary`: `#127A9C` (keep blue brand color, adjust as needed for contrast)
  - `--color-primary-light`: `#1db4e0`
  - `--color-accent`: `#00c8a0` (teal accent, inspired by ralphex terminal green)
  - `--color-text-primary`: `#f0f0f0`
  - `--color-text-secondary`: `#a0a0a0`
  - `--color-border`: `rgba(255,255,255,0.08)`
- [x] Update `body` background to use `--color-bg-base` (dark)
- [x] Update `h1`–`h6` and `p` colors to use dark-theme text variables
- [x] Update shadow variables for dark theme (darker, more subtle glows)
- [x] Update `.card` styles: dark background, subtle border, no white fill
- [x] Update `.btn-primary` and `.btn-secondary` for dark theme contrast
- [x] Update `.icon` for dark theme
- [x] Run `cd website && npm run build` — must complete with no errors

### Task 2: Update inline styles in index.astro for dark theme

**Files:**
- Modify: `website/src/pages/index.astro`

- [x] Update `.nav` background: dark surface with blur, not white
- [x] Update `.nav-title` and `.nav-link` colors for dark background
- [x] Update `.hero` background: dark gradient (dark to slightly lighter dark)
- [x] Update `.features` section background: dark surface
- [x] Update `.how-it-works` section background: slightly different dark shade for contrast
- [x] Update `.bot-commands` background: dark surface
- [x] Update `.command-card` background: dark raised surface
- [x] Update `.command-card code` color: teal accent instead of blue primary
- [x] Update `.cta` section: keep gradient but adapt to dark-friendly colors
- [x] Update `.footer` background: deepest dark color
- [x] Update `--color-gray-light` references to use dark equivalents inline
- [x] Run `cd website && npm run build` — must complete with no errors

### Task 3: Update website content to match current features

**Files:**
- Modify: `website/src/pages/index.astro`

- [x] Add `/help` command card to the bot commands grid (currently missing; README shows it exists)
- [x] Add "Table of Contents Navigation" feature card (summary message with inline buttons per channel) to the features grid — use 🗂️ or 📋 emoji
- [x] Update hero stat "3 AI Providers" label stays correct (OpenAI, Ollama, Anthropic)
- [x] Verify hero description mentions Ollama (local AI) — update if missing
- [x] Update footer copyright year if needed (currently 2026, OK)
- [x] Run `cd website && npm run build` — must complete with no errors

### Task 4: Verify acceptance criteria

- [x] Manual check: run `cd website && npm run build` — zero errors
- [x] Visual verify: `cd website && npm run dev` — open in browser and confirm dark theme renders correctly
- [x] Confirm nav bar is dark (not white)
- [x] Confirm cards have dark background
- [x] Confirm text is readable (light on dark)
- [x] Confirm /help command card is present in bot commands section
- [x] Confirm "Table of Contents Navigation" feature card is present
- [x] Confirm code blocks / command codes use accent teal color

### Task 5: Update documentation

- [ ] Move this plan to `docs/plans/completed/`
