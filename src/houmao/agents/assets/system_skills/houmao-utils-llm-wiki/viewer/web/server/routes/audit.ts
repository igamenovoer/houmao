import fs from "node:fs";
import path from "node:path";
import type { Request, Response } from "express";
import {
  computeAnchor,
  filenameFor,
  fromMarkdown,
  makeId,
  toMarkdown,
  type AuditEntry,
  type Severity,
} from "audit-shared";
import type { ServerConfig } from "../config.js";

const VALID_SEVERITIES: readonly Severity[] = ["info", "suggest", "warn", "error"];

export function handleAuditList(cfg: ServerConfig) {
  return (req: Request, res: Response) => {
    const target = req.query.target as string | undefined;
    const mode = (req.query.mode as string | undefined) ?? "open";

    const entries: AuditEntry[] = [];
    const dirs: string[] = [];
    if (mode === "open" || mode === "all") dirs.push(path.join(cfg.wikiRoot, "audit"));
    if (mode === "resolved" || mode === "all") dirs.push(path.join(cfg.wikiRoot, "audit/resolved"));

    for (const dir of dirs) {
      if (!fs.existsSync(dir)) continue;
      for (const name of fs.readdirSync(dir)) {
        if (!name.endsWith(".md")) continue;
        const full = path.join(dir, name);
        if (!fs.statSync(full).isFile()) continue;
        try {
          const text = fs.readFileSync(full, "utf-8");
          const entry = fromMarkdown(text);
          if (target && entry.target !== target) continue;
          entries.push(entry);
        } catch (err) {
          console.warn(`skipping malformed audit ${full}: ${String(err)}`);
        }
      }
    }

    entries.sort((a, b) => a.created.localeCompare(b.created));
    res.json({ entries });
  };
}

export function handleAuditCreate(cfg: ServerConfig) {
  return (req: Request, res: Response) => {
    try {
      const {
        target,
        rawMarkdown,
        selStart,
        selEnd,
        comment,
        severity,
        author,
      } = req.body as {
        target?: string;
        rawMarkdown?: string;
        selStart?: number;
        selEnd?: number;
        comment?: string;
        severity?: string;
        author?: string;
      };

      if (!target || typeof target !== "string") {
        res.status(400).json({ error: "target is required" });
        return;
      }
      if (!rawMarkdown || typeof rawMarkdown !== "string") {
        res.status(400).json({ error: "rawMarkdown is required" });
        return;
      }
      if (typeof selStart !== "number" || typeof selEnd !== "number") {
        res.status(400).json({ error: "selStart and selEnd must be numbers" });
        return;
      }
      if (!comment || !comment.trim()) {
        res.status(400).json({ error: "comment is required" });
        return;
      }
      if (!severity || !VALID_SEVERITIES.includes(severity as Severity)) {
        res.status(400).json({ error: `severity must be one of ${VALID_SEVERITIES.join(", ")}` });
        return;
      }

      // Make sure the target file exists inside the wiki root. Audit targets
      // are vault-root-relative; .md suffixes are optional for markdown pages.
      const targetFull = resolveVaultFile(cfg.wikiRoot, target);
      if (!fs.existsSync(targetFull) || !fs.statSync(targetFull).isFile()) {
        res.status(404).json({ error: "target file not found", target });
        return;
      }

      // Compute anchor from the raw markdown the client sent (client sends its
      // own copy so the offsets are unambiguous).
      const anchor = computeAnchor(rawMarkdown, selStart, selEnd);

      const id = makeId();
      const slug = comment.trim().split(/\s+/).slice(0, 5).join(" ");
      const filename = filenameFor(id, slug);
      const auditDir = path.join(cfg.wikiRoot, "audit");
      fs.mkdirSync(auditDir, { recursive: true });
      const outPath = path.join(auditDir, filename);

      const entry: AuditEntry = {
        id,
        target,
        target_lines: anchor.target_lines,
        anchor_before: anchor.anchor_before,
        anchor_text: anchor.anchor_text,
        anchor_after: anchor.anchor_after,
        severity: severity as Severity,
        author: (author && author.trim()) || cfg.author,
        source: "web-viewer",
        created: new Date().toISOString(),
        status: "open",
        body: `# Comment\n\n${comment.trim()}\n\n# Resolution\n\n<!-- filled in when the audit is processed -->\n`,
      };

      fs.writeFileSync(outPath, toMarkdown(entry), "utf-8");
      res.json({ id, filename, path: path.relative(cfg.wikiRoot, outPath).split(path.sep).join("/"), entry });
    } catch (err) {
      console.error("failed to create audit", err);
      res.status(500).json({ error: "failed to create audit", detail: String(err) });
    }
  };
}

export function handleAuditResolve(cfg: ServerConfig) {
  return (req: Request, res: Response) => {
    try {
      const id = req.params.id;
      if (!id || !/^\d{8}-\d{6}-[0-9a-f]{4}$/.test(id)) {
        res.status(400).json({ error: "invalid id" });
        return;
      }
      const { resolution } = req.body as { resolution?: string };

      const openDir = path.join(cfg.wikiRoot, "audit");
      const resolvedDir = path.join(cfg.wikiRoot, "audit/resolved");
      fs.mkdirSync(resolvedDir, { recursive: true });

      // Find the file whose name starts with the id.
      const candidate = fs.readdirSync(openDir).find((f) => f.startsWith(id));
      if (!candidate) {
        res.status(404).json({ error: "no open audit with that id" });
        return;
      }
      const openPath = path.join(openDir, candidate);
      const text = fs.readFileSync(openPath, "utf-8");
      const entry = fromMarkdown(text);

      const today = new Date().toISOString().slice(0, 10);
      const newBody = replaceResolution(
        entry.body,
        `${today} · accepted.\n${(resolution ?? "").trim() || "(no details)"}\n`,
      );
      const resolvedEntry: AuditEntry = { ...entry, status: "resolved", body: newBody };

      const resolvedPath = path.join(resolvedDir, candidate);
      fs.writeFileSync(resolvedPath, toMarkdown(resolvedEntry), "utf-8");
      fs.unlinkSync(openPath);
      res.json({ id, from: openPath, to: resolvedPath });
    } catch (err) {
      console.error("failed to resolve audit", err);
      res.status(500).json({ error: "failed to resolve audit", detail: String(err) });
    }
  };
}

function replaceResolution(body: string, newBlock: string): string {
  // Find "# Resolution" section; replace or append.
  const re = /# Resolution[\s\S]*$/;
  if (re.test(body)) {
    return body.replace(re, `# Resolution\n\n${newBlock}`);
  }
  return `${body.trimEnd()}\n\n# Resolution\n\n${newBlock}`;
}

function resolveVaultFile(wikiRoot: string, target: string): string {
  const candidates = [target];
  if (!target.endsWith(".md")) candidates.push(`${target}.md`);
  for (const rel of candidates) {
    const full = path.join(wikiRoot, rel);
    const relFromRoot = path.relative(wikiRoot, full);
    if (relFromRoot.startsWith("..") || path.isAbsolute(relFromRoot)) continue;
    if (fs.existsSync(full) && fs.statSync(full).isFile()) return full;
  }
  return path.join(wikiRoot, target);
}
