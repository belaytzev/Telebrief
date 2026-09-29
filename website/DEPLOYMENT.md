# Deploying the Telebrief landing page

## Cloudflare Pages

### Dashboard settings

1. In the Cloudflare dashboard, open **Pages**.
2. Click **Create a project**, then **Connect to Git**.
3. Pick your repository.
4. Set the build settings:

**Framework preset**: `Astro`

**Build settings:**

- **Build command**: `npm run build`
- **Build output directory**: `dist`
- **Root directory (path)**: `website`

**Environment variables:**

- `NODE_VERSION`: `24`

5. Click **Save and Deploy**.

### What to check

- **Root directory** must be `website`. Nothing else works without it.
- The build command runs inside `website/`.
- The output ends up in `website/dist/`.
- Cloudflare detects Astro on its own and tunes the deployment for it.

### Deploying with the Wrangler CLI

To deploy from the command line instead:

```bash
cd website
npm run build
npx wrangler pages deploy dist --project-name=telebrief
```

### Troubleshooting

#### Error: "Expected output file at workers-site/index.js"

Cloudflare is deploying the site as a Worker instead of Pages. To fix it:

- make sure the project is in **Cloudflare Pages**, not Workers;
- set **Root directory** to `website` in the dashboard;
- remove the Wrangler config file or make Cloudflare ignore it, since Pages is configured differently.

#### The build succeeds but the site doesn't change

- Check the deployment logs in the Cloudflare dashboard.
- Make sure the build output directory is `dist`.
- Make sure the production branch is the right one (usually `website` or `main`).

## Testing locally

Before you deploy, build and preview the site:

```bash
cd website
npm install
npm run build
npm run preview
```

The production build is then at http://localhost:4321.

## Checking the build

To see what the build produced:

```bash
cd website
npm run build
ls -la dist/
```

`dist/` should contain:

- `dist/index.html`: the page itself
- `dist/assets/`: CSS and other assets
- `dist/logo.webp`: the logo

## Checklist

- [ ] The build succeeds locally
- [ ] The preview looks right
- [ ] The logo shows up
- [ ] All links work
- [ ] The layout works on mobile
- [ ] Root directory in Cloudflare is `website`
- [ ] Build command is `npm run build`
- [ ] Output directory is `dist`

## Further reading

- Cloudflare Pages docs: https://developers.cloudflare.com/pages/
- Astro deployment docs: https://docs.astro.build/en/guides/deploy/
