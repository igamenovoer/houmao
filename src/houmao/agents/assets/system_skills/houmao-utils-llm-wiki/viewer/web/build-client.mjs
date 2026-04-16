#!/usr/bin/env node
// Bundle the browser client into dist/client/
import esbuild from "esbuild";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const here = path.dirname(url.fileURLToPath(import.meta.url));
const outDir = path.join(here, "dist/client");
const assetsDir = path.join(outDir, "assets");

fs.mkdirSync(assetsDir, { recursive: true });

// Bundle main.ts → assets/main.js
await esbuild.build({
  entryPoints: [path.join(here, "client/main.ts")],
  bundle: true,
  format: "esm",
  target: "es2020",
  platform: "browser",
  outfile: path.join(assetsDir, "main.js"),
  sourcemap: false,
  treeShaking: true,
  minify: true,
  logLevel: "info",
});

// Copy static files.
fs.copyFileSync(path.join(here, "client/index.html"), path.join(outDir, "index.html"));
fs.copyFileSync(path.join(here, "client/styles.css"), path.join(assetsDir, "styles.css"));

console.log(`✓ client bundled to ${outDir}`);
