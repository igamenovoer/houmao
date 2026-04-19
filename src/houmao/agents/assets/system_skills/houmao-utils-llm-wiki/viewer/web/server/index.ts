import express from "express";
import path from "node:path";
import url from "node:url";
import fs from "node:fs";
import { parseArgs } from "./config.js";
import { handleTree } from "./routes/tree.js";
import { handlePage, handleRaw } from "./routes/pages.js";
import { handleAuditList, handleAuditCreate, handleAuditResolve } from "./routes/audit.js";
import { handleSearchIndex } from "./routes/search.js";

const cfg = parseArgs(process.argv);

const app = express();
app.use(express.json({ limit: "2mb" }));

app.get("/api/tree", handleTree(cfg));
app.get("/api/search-index", handleSearchIndex(cfg));
app.get("/api/page", handlePage(cfg));
app.get("/api/raw", handleRaw(cfg));
app.get("/api/audit", handleAuditList(cfg));
app.post("/api/audit", handleAuditCreate(cfg));
app.patch("/api/audit/:id/resolve", handleAuditResolve(cfg));
app.get("/api/config", (_req, res) => {
  res.json({ author: cfg.author, wikiRoot: path.basename(cfg.wikiRoot) });
});

const here = path.dirname(url.fileURLToPath(import.meta.url));
const clientDist = path.resolve(here, "../dist/client");
if (!fs.existsSync(clientDist)) {
  console.warn(`warning: client bundle not found at ${clientDist}. Run 'npm run build' first.`);
}
app.use("/assets", express.static(path.join(clientDist, "assets")));
app.use("/katex", express.static(path.resolve(here, "../node_modules/katex/dist")));
app.get("/", (_req, res) => {
  const index = path.join(clientDist, "index.html");
  if (fs.existsSync(index)) {
    res.sendFile(index);
  } else {
    res.status(500).send("client bundle missing. Run: npm run build");
  }
});

app.listen(cfg.port, cfg.host, () => {
  console.log(`llm-wiki web server listening on http://${cfg.host}:${cfg.port}`);
  console.log(`  wiki root: ${cfg.wikiRoot}`);
  console.log(`  author:    ${cfg.author}`);
});
