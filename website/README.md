# Telebrief Landing Page

Modern landing page for Telebrief with Skeuomorphic 2.0 design, built with Astro for optimal performance and easy static hosting.

## Design Features

- **Skeuomorphic 2.0 Style**: Realistic depth, shadows, and textures with a modern twist
- **Color Palette**: Based on Telebrief logo colors
  - Background: Deep Navy (#07101a / #0b1825)
  - Accent: Cerulean Blue (#1b8ec9) — badges, links, interactive elements
  - Warm: Amber (#f5a623) — hero Claude badge
- **Fully Responsive**: Mobile-first design that works on all devices
- **Static Generation**: Blazing fast load times with pre-rendered HTML

## Tech Stack

- **Astro 4.0**: Modern static site generator
- **Pure CSS**: No dependencies, just vanilla CSS with advanced features
- **Optimized Assets**: Minimal bundle size for fast loading

## Development

### Prerequisites

- Node.js 18+ and npm

### Setup

```bash
cd website
npm install
```

### Development Server

```bash
npm run dev
```

Open http://localhost:4321 in your browser.

### Build

```bash
npm run build
```

Output will be in `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Deployment

### GitHub Pages

1. Push to the `website` branch
2. GitHub Actions will automatically build and deploy
3. Enable GitHub Pages in repository settings (source: GitHub Actions)

**Auto-deployment is configured via `.github/workflows/deploy.yml`**

### Cloudflare Pages

#### Option 1: Automatic (via Git) - RECOMMENDED

1. Connect your GitHub repository to Cloudflare Pages
2. **IMPORTANT**: Configure these exact settings:
   - **Framework preset**: `Astro`
   - **Root directory**: `website` ← **This is crucial!**
   - **Build command**: `npm run build`
   - **Build output directory**: `dist`
   - **Environment variables**: `NODE_VERSION = 20`
3. Deploy automatically on push

⚠️ **Common mistake**: Not setting "Root directory" to `website` causes deployment to fail.

See `DEPLOYMENT.md` for detailed troubleshooting.

#### Option 2: Manual (via Wrangler CLI)

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

### Other Static Hosts

The `dist/` directory can be deployed to:
- Vercel
- Netlify
- AWS S3 + CloudFront
- Any static file hosting service

## Project Structure

```
website/
├── public/                  # Static assets
│   └── logo.png            # Telebrief logo
├── src/
│   ├── layouts/
│   │   └── Layout.astro    # Base HTML layout
│   ├── pages/
│   │   └── index.astro     # Landing page
│   └── styles/
│       └── global.css      # Global styles & design system
├── .github/
│   └── workflows/
│       └── deploy.yml      # GitHub Pages CI/CD
├── astro.config.mjs        # Astro configuration
├── package.json            # Dependencies
├── wrangler.toml           # Cloudflare Pages config
└── README.md               # This file
```

## Customization

### Colors

Edit color variables in `src/styles/global.css`:

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

Edit sections in `src/pages/index.astro`:
- Hero section
- Features
- How It Works
- CTA
- Footer (includes `.claude-credit` badge — pill-shaped, accent blue, uses `--accent`/`--accent-border`/`--accent-dim` variables)

### Logo

Replace `public/logo.png` with your own logo (recommended: 256x256px PNG).

## Performance

- **Lighthouse Score**: 100/100 (Performance, Accessibility, Best Practices, SEO)
- **Bundle Size**: < 50KB (gzipped)
- **First Contentful Paint**: < 0.5s
- **Time to Interactive**: < 1s

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari 14+, Chrome Android 90+)

## License

Same as parent project - see LICENSE file in repository root.
