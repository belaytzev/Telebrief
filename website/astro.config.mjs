import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://telebrief.ti1orn.com",
  output: "static",
  build: {
    assets: "assets",
    inlineStylesheets: "auto",
  },
  image: {
    service: {
      entrypoint: "astro/assets/services/sharp",
    },
  },
  vite: {
    build: {
      cssCodeSplit: true,
    },
  },
});
