import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://telebrief.github.io',
  base: '/Telebrief',
  output: 'static',
  build: {
    assets: 'assets'
  }
});
