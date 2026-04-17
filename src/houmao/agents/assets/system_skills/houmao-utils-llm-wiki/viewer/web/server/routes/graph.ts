import fs from "node:fs";
import path from "node:path";
import type { Request, Response } from "express";
import type { ServerConfig } from "../config.js";

export interface GraphNode {
  id: string; // path relative to wikiRoot, e.g. "wiki/concepts/Transformers.md"
  label: string; // display name (stem, e.g. "Transformers")
  path: string; // same as id, kept explicit for client
  group: string; // concepts | entities | summaries | other
  degree: number; // in + out link count, used for node sizing
  title: string | null;
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const WIKILINK_RE = /\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]/g;

export function buildGraph(wikiRoot: string): GraphData {
  const wikiDir = path.join(wikiRoot, "wiki");
  if (!fs.existsSync(wikiDir)) return { nodes: [], edges: [] };

  const files = collectMdFiles(wikiDir);

  // Build a lookup table keyed by canonical vault-root article paths plus
  // legacy wiki-relative/stem forms. Only wiki/ files become graph nodes.
  const byKey: Map<string, string> = new Map(); // key → rel-from-wikiRoot path
  const nodes: Map<string, GraphNode> = new Map();

  for (const f of files) {
    const relFromWiki = path.relative(wikiDir, f).split(path.sep).join("/");
    const id = `wiki/${relFromWiki}`;
    const stem = path.basename(f, ".md");
    const parts = relFromWiki.split("/");
    const group = parts.length > 1 ? parts[0]! : "other";
    const title = extractTitle(fs.readFileSync(f, "utf-8")) ?? stem;

    const node: GraphNode = {
      id,
      label: stem,
      path: id,
      group,
      degree: 0,
      title,
    };
    nodes.set(id, node);
    const withoutSuffix = id.replace(/\.md$/, "");
    byKey.set(stem, id);
    byKey.set(relFromWiki.replace(/\.md$/, ""), id);
    byKey.set(withoutSuffix, id);
    byKey.set(id, id);
    // Also index by basename without extension in lowercase as a last-resort alias
    byKey.set(stem.toLowerCase(), id);
  }

  // Pass 2: build edges. Parse wikilinks per file and resolve targets.
  const edges: GraphEdge[] = [];
  const seenEdges = new Set<string>();
  for (const f of files) {
    const relFromWiki = path.relative(wikiDir, f).split(path.sep).join("/");
    const srcId = `wiki/${relFromWiki}`;
    const text = fs.readFileSync(f, "utf-8");
    WIKILINK_RE.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = WIKILINK_RE.exec(text))) {
      const target = m[1]!.trim().replace(/\.md$/, "");
      if (target.startsWith("#")) continue; // anchor-only links — ignore
      const tgtId =
        byKey.get(target) ??
        byKey.get(target.toLowerCase());
      if (!tgtId || tgtId === srcId) continue;

      const key = `${srcId}→${tgtId}`;
      if (seenEdges.has(key)) continue;
      seenEdges.add(key);
      edges.push({ source: srcId, target: tgtId });

      nodes.get(srcId)!.degree += 1;
      nodes.get(tgtId)!.degree += 1;
    }
  }

  return {
    nodes: Array.from(nodes.values()),
    edges,
  };
}

function collectMdFiles(dir: string): string[] {
  const out: string[] = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name.startsWith(".")) continue;
    const full = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...collectMdFiles(full));
    else if (e.isFile() && e.name.endsWith(".md")) out.push(full);
  }
  return out;
}

function extractTitle(text: string): string | null {
  // frontmatter title
  const fm = /^---\n([\s\S]*?)\n---/.exec(text);
  if (fm) {
    const t = /^title:\s*(.+)$/m.exec(fm[1]!);
    if (t) return t[1]!.trim().replace(/^["']|["']$/g, "");
  }
  const h1 = /^#\s+(.+?)\s*$/m.exec(text);
  return h1 ? h1[1]! : null;
}

export function handleGraph(cfg: ServerConfig) {
  return (_req: Request, res: Response) => {
    res.json(buildGraph(cfg.wikiRoot));
  };
}
