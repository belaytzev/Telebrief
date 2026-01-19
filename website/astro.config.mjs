import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://telebrief.ti1orn.com",
  output: "static",
  build: {
    assets: "assets",
  },
});
