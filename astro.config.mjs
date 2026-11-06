import { defineConfig } from "astro/config";
import vercel from "@astrojs/vercel";

export default defineConfig({
  site: "https://bicul-website.vercel.app",
  output: "static",
  adapter: vercel(),
  trailingSlash: "ignore",
  build: { format: "directory" },
});
