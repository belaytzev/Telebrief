# Telebrief website design

The landing page sells one idea: you read one well-ordered message a day instead of every channel. The page is built around that message. Everything else stays quiet so the digest is the thing people remember.

This document is the source of truth for `src/styles/global.css` and every page. When the page and this document disagree, fix the page or change this document in the same commit.

## Audience and job

- **Who reads it:** self-hosters and developers who already live in Telegram and have too many channels. They run Docker, read YAML, and skim.
- **Primary job:** show what the digest looks like, then get them to the Quick Start.
- **Secondary job:** answer "can it do X?" (providers, private channels, storage, MCP) without making them open the README.

## Principles

1. **The digest is the hero.** The first screen shows a real digest message next to the headline, with the channel/topic switch on it. No stats strip, no badge, no particles.
2. **One bold thing.** The digest bubble is the only element with depth, a highlighted edge and an entrance animation. Everything else is flat: surfaces, hairlines, text.
3. **Structure carries information.** Numbers appear only on real sequences (the three pipeline steps). Labels appear only when they say something the heading does not. No eyebrow above section titles.
4. **Product surfaces look like the product.** Telegram things (the digest, bot commands) use the chat panel. Config things use the code block. A shell prompt never appears in front of a bot command.
5. **Left-aligned, one column of reading.** Text starts on the same left edge in every section. Line length stays under 72 characters.
6. **Motion answers the visitor.** Press, hover and focus give feedback. Nothing loops, floats or blinks.

## Color

Warm charcoal with the cerulean of the logo. One accent, used for actions, links, selected state and code keys. Never for decoration or for highlighting a word in a heading.

| Token | Value | Use |
| --- | --- | --- |
| `--ink` | `#141310` | Page background |
| `--surface` | `#1a1916` | Chat panel body, mobile menu, footer |
| `--nav-bg` | `--ink` at 88% | Sticky nav behind a blur |
| `--raised` | `#21201c` | Chat header, chips, segmented track |
| `--sunken` | `#0e0d0b` | Code blocks, text on accent |
| `--line` | `#3d3a36` | Hairlines, panel borders |
| `--line-strong` | `#524e48` | Ghost button border, hover borders |
| `--text` | `#e8e6e1` | Headings, primary text |
| `--text-muted` | `#a09d95` | Body copy, descriptions |
| `--text-subtle` | `#8a867d` | Timestamps, captions, step numbers |
| `--accent` | `#3da5db` | Primary action, links, selected state |
| `--accent-hover` | `#5bb8e8` | Hover on accent surfaces |
| `--accent-soft` | `rgb(61 165 219 / 0.1)` | Selected tab fill, accent chip fill, inline code fill |
| `--accent-line` | `rgb(61 165 219 / 0.3)` | Selected tab border, accent chip border, digest panel top edge |

Contrast on `--ink`: `--text` 14.9:1, `--text-muted` 6.9:1, `--text-subtle` 5.1:1, `--accent` 6.7:1. On `--raised` the lowest is `--text-subtle` at 4.5:1. `--sunken` on `--accent` is 7.0:1.

Rules:

- No hex or `rgb()` outside `:root` in `global.css`. The one exception is the `theme-color` meta tag, which cannot read a CSS variable.
- The page is dark only. `color-scheme: dark` and `theme-color` are set so browser chrome matches.

## Type

Two families.

- **Schibsted Grotesk** (400–800) for everything you read: headings and body. It was drawn for a news publisher, which suits a product that writes news briefs, and one family keeps the page calm.
- **JetBrains Mono** (400, 500) only for things you type or paste: commands, config keys, file names, code. Never for labels or decoration.

Scale, ratio about 1.25 from a 16px base:

| Token | Size | Use |
| --- | --- | --- |
| `--fs-xs` | 0.8125rem (13px) | Captions, chips, timestamps, footer, code blocks |
| `--fs-sm` | 0.9375rem (15px) | Feature and step body, digest text, buttons |
| `--fs-base` | 1rem (16px) | Body |
| `--fs-lg` | 1.1875rem (19px) | Lede under headings, h3, wordmark |
| `--fs-code` | 0.875em | Inline code, relative to its line |
| `--fs-xl` | clamp(1.5rem, 3vw, 1.875rem) | Sub-section titles inside a section |
| `--fs-2xl` | clamp(2rem, 4.5vw, 2.875rem) | Section titles (h2) |
| `--fs-3xl` | clamp(2.5rem, 6.5vw, 4.25rem) | Page title (h1) |

- Headings: weight 700 (h1 800), letter-spacing −0.02em (h1 −0.03em), line-height 1.1.
- Body: weight 400, line-height 1.65. Strong text 600.
- Sentence case everywhere. No all-caps labels, no tracked-out text.
- No arrows appended to button or link text. The only `→` on the page is inside the digest, because the real bot writes it.

## Space, radius, depth

Spacing is a 4px grid: `--space-1` 0.25rem through `--space-9` 6rem (0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6 rem). Sections use `--section-y: clamp(4rem, 9vw, 7rem)` top and bottom, and a single hairline between sections.

Radius follows hierarchy, three steps only:

- `--radius-s` 6px: chips, inline code, segment pills.
- `--radius-m` 10px: buttons, segmented track, code blocks, list containers.
- `--radius-l` 16px: chat panels.

Depth: one shadow token, `--shadow-panel`, used only on the hero digest panel. Every other surface is flat and separated by `--line`.

## Components

Each exists once in `global.css` and is reused as is.

- **Button** (`.btn`, `.btn-primary`, `.btn-ghost`): 44px minimum height, `--radius-m`, label says what happens ("Read the Quick Start", "View on GitHub").
- **Chip** (`.chip`, `.chip-accent`): mono, `--fs-xs`, `--radius-s`. Accent chips name the AI providers; nothing else is accent.
- **Inline code** (`code`): mono, accent text on `--accent-soft`.
- **Code block** (`.code-block`): `--sunken`, `--radius-m`, YAML keys in accent, values in `--text`. Scrolls sideways inside itself, never the page.
- **Segmented control** (`.segmented`): a radio group. Native radios inside labels, so arrow keys and screen readers work. The checked segment uses `--accent-soft` fill and `--accent-line` border. Panels switch with `:has()`.
- **Chat panel** (`.chat`): header with avatar, name and time on `--raised`, body on `--surface`, `--radius-l`. Used for the digest and the bot command menu.
- **Section head** (`.section-head`): h2 plus one lede paragraph, max 40rem wide.

## Layout

Container 1120px, gutters 1.25rem on phones and 2rem from 769px.

```text
┌ telebrief ............................. How it works  Features  Extend  GitHub ┐
│                                                                                │
│  AI digest bot for Telegram          ┌ Telebrief Bot          12:00 ┐         │
│  lede, two or three lines            │ ( By channel | By topic )    │         │
│  [Read the Quick Start] [GitHub]     │ Daily Digest - 02 May 2026   │         │
│  self-hosted, MIT, three providers   │ ...                          │         │
│                                      └──────────────────────────────┘         │
├────────────────────────────────────────────────────────────────────────────────┤
│  How it works        1 Collect   2 Summarize   3 Deliver   (three columns)     │
├────────────────────────────────────────────────────────────────────────────────┤
│  Bot commands        lede              ┌ command menu panel ┐                  │
├────────────────────────────────────────────────────────────────────────────────┤
│  Features            Reading   | Writing the digest | Running it   (groups)    │
├────────────────────────────────────────────────────────────────────────────────┤
│  Storage and extensibility   storage switch + YAML, extension points list     │
├────────────────────────────────────────────────────────────────────────────────┤
│  Try it   [Read the Quick Start] [View on GitHub]                              │
└ footer ────────────────────────────────────────────────────────────────────────┘
```

Below 961px the hero and the two-column sections stack: copy first, then the digest. Below 769px the nav collapses into a disclosure menu.

## Motion

Tokens: `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)`, `--dur-press: 120ms`, `--dur-hover: 150ms`, `--dur-enter: 500ms`.

| Interaction | Motion |
| --- | --- |
| Button and segment press | `scale(0.97)` on `:active`, `--dur-press` |
| Hover on links, buttons, segments | color, background, border only, `--dur-hover`, inside `@media (hover: hover) and (pointer: fine)` |
| Segment switch | none: the panel swaps instantly |
| Mobile menu | none |
| Hero digest panel | once on load: opacity 0 → 1 and 12px rise, `--dur-enter`, `--ease-out` |

Rules:

- Name every transitioned property. `transition: all` is not allowed.
- Anything that moves or scales uses `transform` and `opacity` only. Hover may also transition color, background and border.
- Under `prefers-reduced-motion: reduce` the hero entrance becomes a fade with no movement, press scaling is off, and smooth scrolling is off.

## Accessibility and mobile

- Every interactive element has a `:focus-visible` ring: 2px `--accent`, 2px offset.
- A skip link goes to `#main`.
- The mobile menu is a `<details>` disclosure, so it opens from the keyboard without JavaScript. A small script closes it after a link is followed.
- Touch: `-webkit-tap-highlight-color: transparent`, `touch-action: manipulation` on controls, press feedback via `:active`.
- Decorative glyphs and icons are `aria-hidden`. External links open in a new tab and say so to screen readers only through their accessible name when it is not obvious.
- No horizontal page scroll at 320px. Long code scrolls inside its block.

## Library choice

The site is static Astro with one dependency. Tabs, menu and code blocks are built from native elements and plain CSS, so no UI library is added. Revisit if the site grows an interactive docs section.

`:has()` drives the switches, so the floor is Chrome and Edge 105, Safari 15.4 and Firefox 121. Older browsers show the default panel of each switch.

## Where the rules come from

The design was set with these skills. Use them again for the next change of the same kind.

- `frontend-design`: the digest as the hero, one bold element, no eyebrows, no numbered markers outside a real sequence, no arrows on buttons, no accent on a single headline word, sentence case, left alignment.
- `emil-design-eng`: easing and duration tokens, press feedback with `scale(0.97)`, named transition properties.
- `remove-animations`: particles, background wash, blinking badge dot, blinking cursor and hover lifts removed; segment switches swap instantly because tab switches fail its frequency gate.
- `find-animation-opportunities`: the hero digest entrance as the single first-visit moment.
- `mobile-native`: hover gated to fine pointers, tap highlight off, `touch-action: manipulation`, 44px targets, `theme-color`.
- `break-ui`: layouts checked at 320px and with long code lines, which scroll inside their blocks.
- `pick-ui-library`: no library, see above.

## Checks

Run from `website/` before merging a design change:

```sh
rg -n '#[0-9a-fA-F]{3,8}\b|rgba?\(' src --glob '!src/styles/global.css' | rg -v theme-color
rg -n 'transition:\s*all' src
rg -n 'font-size:\s*[0-9]|border-radius:\s*[0-9]+(px|rem)' src
rg -n ':hover' src
npm run build
```

The first three must print nothing. Every `:hover` the third prints must sit inside the hover media query. Then check 1440px, 390px and 320px widths with fonts loaded.
