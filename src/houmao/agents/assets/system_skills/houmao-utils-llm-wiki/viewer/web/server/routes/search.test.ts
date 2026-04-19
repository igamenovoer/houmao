import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { buildSearchDocument, buildSearchIndex, normalizeMarkdownForSearch } from "./search.js";

test("buildSearchDocument extracts title, headings, text, wikilinks, and preview", () => {
  const root = makeWikiRoot();
  const page = path.join(root, "wiki", "concepts", "transformers.md");
  fs.mkdirSync(path.dirname(page), { recursive: true });
  fs.writeFileSync(
    page,
    [
      "---",
      'title: "Attention Models"',
      "---",
      "# Ignored H1",
      "",
      "## Core Idea",
      "",
      "Transformers use [[Self Attention|attention layers]] and [papers](https://example.com/paper).",
      "",
      "The decoder has residual streams.",
    ].join("\n"),
    "utf-8",
  );

  const doc = buildSearchDocument(root, page);

  assert.equal(doc.path, "wiki/concepts/transformers.md");
  assert.equal(doc.title, "Attention Models");
  assert.match(doc.headings, /Core Idea/);
  assert.match(doc.text, /attention layers Self Attention/);
  assert.match(doc.text, /papers https:\/\/example\.com\/paper/);
  assert.match(doc.preview, /Transformers use/);
});

test("buildSearchDocument falls back to H1 and basename", () => {
  const root = makeWikiRoot();
  const h1Page = path.join(root, "wiki", "h1.md");
  const basenamePage = path.join(root, "wiki", "basename-only.md");
  fs.writeFileSync(h1Page, "# H1 Title\n\nBody", "utf-8");
  fs.writeFileSync(basenamePage, "Body only", "utf-8");

  assert.equal(buildSearchDocument(root, h1Page).title, "H1 Title");
  assert.equal(buildSearchDocument(root, basenamePage).title, "basename-only");
});

test("buildSearchIndex indexes only non-hidden Markdown files under wiki", () => {
  const root = makeWikiRoot();
  write(root, "README.md", "# Root Schema");
  write(root, "audit/feedback.md", "# Audit");
  write(root, "wiki/index.md", "# Index");
  write(root, "wiki/concepts/model.md", "# Model");
  write(root, "wiki/concepts/data.txt", "not markdown");
  write(root, "wiki/.hidden.md", "# Hidden");
  write(root, "wiki/.hidden-dir/secret.md", "# Secret");
  write(root, "wiki/audit/local.md", "# Local Audit");

  const docs = buildSearchIndex(root).documents.map((doc) => doc.path);

  assert.deepEqual(docs, ["wiki/concepts/model.md", "wiki/index.md"]);
});

test("buildSearchDocument rejects paths outside wiki root", () => {
  const root = makeWikiRoot();
  const outside = path.join(os.tmpdir(), `llm-wiki-outside-${Date.now()}.md`);
  fs.writeFileSync(outside, "# Outside", "utf-8");

  assert.throws(() => buildSearchDocument(root, outside), /escapes wiki root/);
});

test("normalizeMarkdownForSearch keeps useful terms from common Markdown syntax", () => {
  const text = normalizeMarkdownForSearch(
    "## Heading\n\nUse `code` with **bold** and [[Target#Part|Alias]] plus ![Alt](img.png).",
  );

  assert.match(text, /Heading/);
  assert.match(text, /code/);
  assert.match(text, /bold/);
  assert.match(text, /Alias Target Part/);
  assert.match(text, /Alt img\.png/);
});

function makeWikiRoot(): string {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "llm-wiki-search-"));
  fs.mkdirSync(path.join(root, "wiki"), { recursive: true });
  fs.mkdirSync(path.join(root, "audit"), { recursive: true });
  return root;
}

function write(root: string, rel: string, content: string): void {
  const full = path.join(root, rel);
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, content, "utf-8");
}
