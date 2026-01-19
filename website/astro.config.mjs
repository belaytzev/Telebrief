import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://telebrief.github.io",
  output: "static",
  build: {
    assets: "assets",
  },
});
