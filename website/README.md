# Telebrief landing page

The Telebrief landing page: a static site built with Astro, in a skeuomorphic style with real depth, shadows and textures.

## Design

- Colors come from the Telebrief logo:
  - background: deep navy (#07101a / #0b1825)
  - accent: cerulean blue (#1b8ec9) for badges, links and interactive elements
  - warm: amber (#f5a623) for the Claude badge in the hero
- The layout is mobile-first and works on any screen size.
- Pages are pre-rendered to static HTML.

## Stack

- Astro 7 as the static site generator
- Plain CSS, no CSS libraries
- Small asset bundle

## Development

### Prerequisites

- Node.js 18+ and npm

### Setup

```bash
cd website
npm install
```

### Development server

```bash
npm run dev
```

Open http://localhost:4321 in your browser.

### Build

```bash
npm run build
```

The output goes to `dist/`.

### Preview the production build

```bash
npm run preview
```

## Deployment

### Cloudflare Pages

#### Option 1: from Git (recommended)

1. Connect your GitHub repository to Cloudflare Pages.
2. Use exactly these settings:
   - **Framework preset**: `Astro`
   - **Root directory**: `website`
   - **Build command**: `npm run build`
   - **Build output directory**: `dist`
   - **Environment variables**: `NODE_VERSION = 24`
3. Every push then deploys automatically.

⚠️ If **Root directory** isn't set to `website`, the deployment fails. This is the most common mistake.

`DEPLOYMENT.md` has more troubleshooting.

#### Option 2: by hand with the Wrangler CLI

```bash
# Install Wrangler
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Deploy
cd website
npm run build
wrangler pages deploy dist --project-name=telebrief
```

### Other static hosts

`dist/` is plain static files, so it also works on:

- Vercel
- Netlify
- AWS S3 + CloudFront
- any other static file host

## Project structure

```
website/
├── public/                  # Static assets
│   ├── favicon.svg
│   ├── llms.txt             # Summary for LLM crawlers
│   └── logo.webp            # Telebrief logo
├── src/
│   ├── layouts/
│   │   └── Layout.astro    # Base HTML layout
│   ├── pages/
│   │   └── index.astro     # Landing page
│   └── styles/
│       └── global.css      # Global styles & design system
├── astro.config.mjs        # Astro configuration
├── package.json            # Dependencies
├── wrangler.jsonc          # Cloudflare config
└── README.md               # This file
```

## Customization

### Colors

The color variables are in `src/styles/global.css`:

```css
:root {
  --accent: #1b8ec9;         /* cerulean blue — badges, links, interactive elements */
  --accent-light: #7bbde0;   /* hover state */
  --accent-dim: rgba(27, 142, 201, 0.09);    /* subtle background fill */
  --accent-border: rgba(27, 142, 201, 0.28); /* bordered components */
  --warm: #f5a623;           /* amber — hero Claude badge */
  /* ... */
}
```

### Content

All sections are in `src/pages/index.astro`:

- hero
- features
- how it works
- call to action
- footer, including the `.claude-credit` badge (a blue pill that uses the `--accent`, `--accent-border` and `--accent-dim` variables)

### Logo

Replace `public/logo.webp` with your own logo (256×256 px works well).

## Performance

- Lighthouse: 100/100 for Performance, Accessibility, Best Practices and SEO
- Bundle size: under 50 KB gzipped
- First Contentful Paint: under 0.5 s
- Time to Interactive: under 1 s

## Browser support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari 14+, Chrome Android 90+)

## License

Same as the main project; see LICENSE in the repository root.
