import fs from "node:fs";
import path from "node:path";
import type { Request, Response } from "express";
import type { ServerConfig } from "../config.js";
import { createRenderer } from "../render/markdown.js";

export function handlePage(cfg: ServerConfig) {
  const renderer = createRenderer({ wikiRoot: cfg.wikiRoot });

  return (req: Request, res: Response) => {
    const relRaw = (req.query.path as string | undefined) ?? "";
    const rel = safeRel(relRaw);
    if (!rel) {
      res.status(400).json({ error: "missing or invalid `path` query" });
      return;
    }

    const full = resolveMarkdownFile(cfg.wikiRoot, rel);
    if (!fs.existsSync(full) || !fs.statSync(full).isFile()) {
      res.status(404).json({ error: "file not found", path: rel });
      return;
    }

    // Guarantee the resolved path is still inside wikiRoot.
    const relFromRoot = path.relative(cfg.wikiRoot, full);
    if (relFromRoot.startsWith("..") || path.isAbsolute(relFromRoot)) {
      res.status(403).json({ error: "path escapes wiki root" });
      return;
    }

    const rawMarkdown = fs.readFileSync(full, "utf-8");
    const rendered = renderer.render(rawMarkdown);
    res.json({
      path: relFromRoot.split(path.sep).join("/"),
      title: rendered.title,
      frontmatter: rendered.frontmatter,
      html: rendered.html,
      raw: rendered.rawMarkdown,
    });
  };
}

export function handleRaw(cfg: ServerConfig) {
  return (req: Request, res: Response) => {
    const relRaw = (req.query.path as string | undefined) ?? "";
    const rel = safeRel(relRaw);
    if (!rel) {
      res.status(400).send("bad path");
      return;
    }
    const full = path.join(cfg.wikiRoot, rel);
    if (!fs.existsSync(full) || !fs.statSync(full).isFile()) {
      res.status(404).send("not found");
      return;
    }
    res.type("text/markdown").send(fs.readFileSync(full));
  };
}

function safeRel(input: string): string | null {
  if (!input) return "wiki/index.md";
  // Reject absolute and ..
  if (path.isAbsolute(input)) return null;
  const normalized = path.posix.normalize(input);
  if (normalized.startsWith("..")) return null;
  return normalized;
}

function resolveMarkdownFile(wikiRoot: string, rel: string): string {
  // Vault-root paths are canonical. The wiki/<rel> fallback preserves older
  // article links such as ?path=concepts/foo during migration.
  for (const candidate of [rel, path.posix.join("wiki", rel)]) {
    let full = path.join(wikiRoot, candidate);
    if (fs.existsSync(full) && fs.statSync(full).isDirectory()) {
      full = path.join(full, "index.md");
    }
    if (!full.endsWith(".md")) full += ".md";
    if (fs.existsSync(full) && fs.statSync(full).isFile()) {
      return full;
    }
  }

  let fallback = path.join(wikiRoot, rel);
  if (!fallback.endsWith(".md")) fallback += ".md";
  return fallback;
}
