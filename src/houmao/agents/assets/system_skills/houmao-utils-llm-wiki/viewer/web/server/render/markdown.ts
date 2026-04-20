import MarkdownIt from "markdown-it";
import anchor from "markdown-it-anchor";
import { katex as katexPlugin } from "@mdit/plugin-katex";
// @ts-expect-error - no types shipped
import attrs from "markdown-it-attrs";
import path from "node:path";
import fs from "node:fs";
import { wikilinksPlugin, type WikilinkResolver } from "./wikilinks.js";

export interface RenderedPage {
  html: string;
  frontmatter: Record<string, unknown> | null;
  rawMarkdown: string;
  title: string | null;
}

export interface RendererOptions {
  wikiRoot: string;
}

export function createRenderer(opts: RendererOptions) {
  const md = new MarkdownIt({
    html: false,
    linkify: true,
    typographer: false,
    breaks: false,
  });

  md.use(attrs, {});
  md.use(anchor, {
    permalink: anchor.permalink.linkInsideHeader({
      symbol: "§",
      placement: "before",
    }),
  });
  md.use(katexPlugin, {
    delimiters: "dollars",
    throwOnError: false,
    strict: false,
  });

  const resolver: WikilinkResolver = (target) => {
    const candidate = findPage(opts.wikiRoot, target);
    if (candidate) {
      const rel = canonicalTarget(opts.wikiRoot, candidate);
      return {
        href: `/?page=${encodeURIComponent(rel)}`,
        exists: true,
      };
    }
    return {
      href: `/?page=${encodeURIComponent(target)}`,
      exists: false,
    };
  };

  md.use(wikilinksPlugin, resolver);

  // Attach data-source-line to every top-level block token so the client can
  // map DOM selections back to source lines.
  md.core.ruler.push("source-line", (state) => {
    for (const tok of state.tokens) {
      if (tok.map && tok.level === 0 && tok.type.endsWith("_open")) {
        tok.attrSet("data-source-line", `${tok.map[0]},${tok.map[1]}`);
      }
    }
  });

  // Customize fence rendering so mermaid blocks are left for the client to render.
  const defaultFence = md.renderer.rules.fence!;
  md.renderer.rules.fence = (tokens, idx, options, env, self) => {
    const tok = tokens[idx]!;
    const info = (tok.info || "").trim();
    const lang = info.split(/\s+/)[0];
    if (lang === "mermaid") {
      const line =
        tok.map && tok.level === 0
          ? ` data-source-line="${tok.map[0]},${tok.map[1]}"`
          : "";
      return `<pre class="mermaid-block"${line}><code class="language-mermaid">${escapeHtml(tok.content)}</code></pre>\n`;
    }
    return defaultFence(tokens, idx, options, env, self);
  };

  return {
    render(rawMarkdown: string): RenderedPage {
      const { frontmatter, body, title } = stripFrontmatter(rawMarkdown);
      const html = md.render(body);
      return { html, frontmatter, rawMarkdown, title };
    },
  };
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const FRONTMATTER_RE = /^---\n([\s\S]*?)\n---\n?/;

function stripFrontmatter(text: string): {
  frontmatter: Record<string, unknown> | null;
  body: string;
  title: string | null;
} {
  const m = FRONTMATTER_RE.exec(text);
  let frontmatter: Record<string, unknown> | null = null;
  let body = text;
  if (m) {
    // We don't need full YAML parsing here — keep it for display only.
    frontmatter = {};
    for (const line of m[1]!.split("\n")) {
      const idx = line.indexOf(":");
      if (idx < 0) continue;
      frontmatter[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
    }
    body = text.slice(m[0].length);
  }
  const h1 = /^#\s+(.+?)\s*$/m.exec(body);
  const title =
    (frontmatter && typeof frontmatter.title === "string" && (frontmatter.title as string)) ||
    (h1 && h1[1]) ||
    null;
  return { frontmatter, body, title };
}

/**
 * Resolve a wikilink target to a file under wikiRoot. Vault-root paths are
 * primary. Legacy wiki-relative article links such as concepts/foo still work.
 */
export function findPage(wikiRoot: string, target: string): string | null {
  const normalized = safeTarget(target);
  if (!normalized) return null;

  const tryPath = (rel: string): string | null => {
    const full = path.join(wikiRoot, rel);
    if (fs.existsSync(full) && fs.statSync(full).isFile()) return full;
    return null;
  };

  const direct =
    tryPath(normalized) ||
    tryPath(normalized + ".md") ||
    tryPath(path.posix.join("wiki", normalized)) ||
    tryPath(path.posix.join("wiki", normalized + ".md"));
  if (direct) return direct;

  // Fallback: scan wiki/ for matching stem.
  const wikiDir = path.join(wikiRoot, "wiki");
  if (!fs.existsSync(wikiDir)) return null;
  const match = findByStem(wikiDir, normalized);
  return match;
}

function canonicalTarget(wikiRoot: string, filePath: string): string {
  let rel = path.relative(wikiRoot, filePath).split(path.sep).join("/");
  if (rel.endsWith(".md")) rel = rel.slice(0, -3);
  return rel;
}

function safeTarget(input: string): string | null {
  if (!input || path.isAbsolute(input)) return null;
  const normalized = path.posix.normalize(input).replace(/^\/+/, "");
  if (normalized === "." || normalized.startsWith("../") || normalized === "..") return null;
  return normalized;
}

function findByStem(dir: string, target: string): string | null {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) {
      const sub = findByStem(full, target);
      if (sub) return sub;
    } else if (e.isFile() && e.name.endsWith(".md")) {
      const stem = e.name.replace(/\.md$/, "");
      if (stem === target || e.name === target) return full;
    }
  }
  return null;
}
