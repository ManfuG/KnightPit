import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss(), {
    name: "publication-package-inventory",
    generateBundle(_options, bundle) {
      const packages = Object.values(bundle).flatMap(chunk => chunk.type === "chunk"
        ? Object.entries(chunk.modules).filter(([, info]) => info.renderedLength !== 0)
          .flatMap(([id]) => id.replaceAll("\\", "/").match(/\/node_modules\/((?:@[^/]+\/)?[^/]+)/g)?.slice(-1).map(path => path.slice("/node_modules/".length)) ?? [])
        : []);
      packages.push("tailwindcss"); // Its preflight CSS is copied into the stylesheet.
      this.emitFile({ type: "asset", fileName: "_bundled-packages.json", source: JSON.stringify([...new Set(packages)].sort()) });
    },
  }],
});
