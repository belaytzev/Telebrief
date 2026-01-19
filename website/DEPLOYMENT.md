# Deployment Guide for Telebrief Landing Page

## Cloudflare Pages Deployment

### Configuration in Cloudflare Dashboard

1. Go to your Cloudflare Dashboard → Pages
2. Click "Create a project" → "Connect to Git"
3. Select your repository
4. Configure the build settings:

**Framework preset**: `Astro`

**Build settings:**
- **Build command**: `npm run build`
- **Build output directory**: `dist`
- **Root directory (path)**: `website`

**Environment variables:**
- `NODE_VERSION`: `20`

5. Click "Save and Deploy"

### Important Notes

- ✅ **Root directory must be set to `website`** - This is crucial!
- ✅ The build command will run inside the `website/` directory
- ✅ Output goes to `website/dist/`
- ✅ Cloudflare will automatically detect Astro and optimize deployment

### Manual Deployment via Wrangler CLI

If you prefer to deploy via CLI:

```bash
cd website
npm run build
npx wrangler pages deploy dist --project-name=telebrief
```

### Troubleshooting

#### Error: "Expected output file at workers-site/index.js"

This means Cloudflare is trying to deploy as a Worker instead of Pages. Fix:
- Make sure you're using **Cloudflare Pages**, not Workers
- Set **Root directory** to `website` in dashboard
- Remove or ignore `wrangler.toml` (Pages uses different config)

#### Build succeeds but site doesn't update

- Check the deployment logs in Cloudflare dashboard
- Verify the build output directory is set to `dist`
- Make sure Git branch is correct (usually `website` or `main`)

## GitHub Pages Deployment

GitHub Pages deployment is automated via GitHub Actions.

1. Go to repository Settings → Pages
2. Source: **GitHub Actions**
3. Push to `website` branch
4. Workflow will automatically build and deploy

The workflow file is at `.github/workflows/deploy.yml`

## Local Testing

Before deploying, test locally:

```bash
cd website
npm install
npm run build
npm run preview
```

Visit http://localhost:4321 to preview the production build.

## Build Verification

Verify your build locally first:

```bash
cd website
npm run build
ls -la dist/
```

You should see:
- `dist/index.html` - Main page
- `dist/assets/` - CSS and other assets
- `dist/logo.png` - Logo file

## Deployment Checklist

- [ ] Build succeeds locally
- [ ] Preview looks correct
- [ ] Logo displays properly
- [ ] All links work
- [ ] Responsive design works on mobile
- [ ] Root directory is set to `website` in Cloudflare
- [ ] Build command is `npm run build`
- [ ] Output directory is `dist`

## Support

For issues:
- Check Cloudflare Pages docs: https://developers.cloudflare.com/pages/
- Check Astro deployment docs: https://docs.astro.build/en/guides/deploy/
