# Telebrief landing page

The Telebrief landing page: a static site built with Astro and plain CSS.

## Design

[`DESIGN.md`](DESIGN.md) is the source of truth: principles, color and type tokens, components, layout, motion and the checks to run before merging. The tokens live in `src/styles/global.css`.

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
│   ├── components/
│   │   └── GitHubIcon.astro
│   ├── layouts/
│   │   └── Layout.astro    # Base HTML layout
│   ├── pages/
│   │   └── index.astro     # Landing page
│   └── styles/
│       └── global.css      # Tokens and shared components
├── astro.config.mjs        # Astro configuration
├── DESIGN.md               # Design system
├── package.json            # Dependencies
├── wrangler.jsonc          # Cloudflare config
└── README.md               # This file
```

## Customization

### Colors and type

Change tokens in `src/styles/global.css` and the matching table in `DESIGN.md` in the same commit.

### Content

All sections are in `src/pages/index.astro`: the hero with the example digest, how it works, bot commands, features, storage and extensibility, the call to action and the footer. Steps, commands, features and extension points are arrays in the page frontmatter.

### Logo

Replace `public/logo.webp` with your own logo (256×256 px works well).

## Performance

- Lighthouse: 100/100 for Performance, Accessibility, Best Practices and SEO
- Bundle size: under 50 KB gzipped
- First Contentful Paint: under 0.5 s
- Time to Interactive: under 1 s

## Browser support

Chrome and Edge 105+, Safari 15.4+, Firefox 121+: the switches need `:has()`. Older browsers show the default panel of each switch.

## License

Same as the main project; see LICENSE in the repository root.
