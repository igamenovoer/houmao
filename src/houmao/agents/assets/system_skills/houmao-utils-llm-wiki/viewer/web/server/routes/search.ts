import fs from "node:fs";
import path from "node:path";
import type { Request, Response } from "express";
import type { ServerConfig } from "../config.js";

export interface SearchDocument {
  path: string;
  title: string;
  headings: string;
  text: string;
  preview: string;
}

export interface SearchIndexResponse {
  documents: SearchDocument[];
}

const FRONTMATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/;
const HEADING_RE = /^#{1,6}\s+(.+?)\s*#*\s*$/gm;
const WIKILINK_RE = /\[\[([^\]|#]+)(?:#([^\]|]+))?(?:\|([^\]]+))?\]\]/g;
const MARKDOWN_LINK_RE = /!?\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g;

export function handleSearchIndex(cfg: ServerConfig) {
  return (_req: Request, res: Response) => {
    res.json(buildSearchIndex(cfg.wikiRoot));
  };
}

export function buildSearchIndex(wikiRoot: string): SearchIndexResponse {
  const root = path.resolve(wikiRoot);
  const wikiDir = path.join(root, "wiki");
  if (!isInsideRoot(root, wikiDir) || !fs.existsSync(wikiDir)) {
    return { documents: [] };
  }

  const documents = collectMarkdownFiles(root, wikiDir).map((filePath) =>
    buildSearchDocument(root, filePath),
  );
  return { documents };
}

export function buildSearchDocument(wikiRoot: string, filePath: string): SearchDocument {
  const root = path.resolve(wikiRoot);
  const full = path.resolve(filePath);
  if (!isInsideRoot(root, full)) {
    throw new Error(`search document path escapes wiki root: ${filePath}`);
  }

  const raw = fs.readFileSync(full, "utf-8");
  const body = stripFrontmatter(raw);
  const headings = extractHeadings(body);
  const title = extractTitle(raw, body) ?? path.basename(full, ".md");
  const text = normalizeMarkdownForSearch(body);
  const preview = makePreview(text);

  return {
    path: path.relative(root, full).split(path.sep).join("/"),
    title,
    headings: headings.join(" "),
    text,
    preview,
  };
}

function collectMarkdownFiles(wikiRoot: string, dir: string): string[] {
  if (!isInsideRoot(wikiRoot, dir)) return [];

  const files: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith(".")) continue;
    if (entry.name === "audit") continue;

    const full = path.join(dir, entry.name);
    if (!isInsideRoot(wikiRoot, full)) continue;

    if (entry.isDirectory()) {
      files.push(...collectMarkdownFiles(wikiRoot, full));
    } else if (entry.isFile() && entry.name.endsWith(".md")) {
      files.push(full);
    }
  }

  return files.sort((a, b) => a.localeCompare(b));
}

function isInsideRoot(root: string, candidate: string): boolean {
  const relative = path.relative(path.resolve(root), path.resolve(candidate));
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

function extractTitle(raw: string, body: string): string | null {
  const fm = FRONTMATTER_RE.exec(raw);
  if (fm) {
    const frontmatter = fm[1]!;
    const titleMatch = /^title:\s*(.+?)\s*$/m.exec(frontmatter);
    if (titleMatch) {
      return cleanTitle(titleMatch[1]!);
    }
  }

  const headingMatch = /^#\s+(.+?)\s*#*\s*$/m.exec(body);
  return headingMatch ? cleanTitle(headingMatch[1]!) : null;
}

function cleanTitle(value: string): string {
  return value.trim().replace(/^["']|["']$/g, "");
}

function stripFrontmatter(raw: string): string {
  return raw.replace(FRONTMATTER_RE, "");
}

function extractHeadings(body: string): string[] {
  const headings: string[] = [];
  HEADING_RE.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = HEADING_RE.exec(body))) {
    headings.push(cleanInlineMarkdown(match[1]!));
  }
  return headings;
}

export function normalizeMarkdownForSearch(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, (block) => block.replace(/```[^\n]*\n?/g, " "))
    .replace(/`([^`]+)`/g, "$1")
    .replace(
      WIKILINK_RE,
      (_all, target: string, anchor: string | undefined, alias: string | undefined) =>
        [alias, target, anchor].filter(Boolean).join(" "),
    )
    .replace(MARKDOWN_LINK_RE, (_all, label: string, href: string) => `${label} ${href}`)
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^>\s?/gm, "")
    .replace(/[*_~>#|[\]()`{}]/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&[a-zA-Z0-9#]+;/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function cleanInlineMarkdown(value: string): string {
  return normalizeMarkdownForSearch(value);
}

function makePreview(text: string): string {
  const compact = text.replace(/\s+/g, " ").trim();
  if (compact.length <= 220) return compact;
  return `${compact.slice(0, 217).trimEnd()}...`;
}
