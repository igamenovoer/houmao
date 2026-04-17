import { z } from "zod";

export const Severity = z.enum(["info", "suggest", "warn", "error"]);
export type Severity = z.infer<typeof Severity>;

export const AuditSource = z.enum(["obsidian-plugin", "web-viewer", "manual"]);
export type AuditSource = z.infer<typeof AuditSource>;

export const AuditStatus = z.enum(["open", "resolved"]);
export type AuditStatus = z.infer<typeof AuditStatus>;

/**
 * The text-based anchor used to locate a selection in the target file.
 * Written verbatim from the source: no normalization, no trimming.
 */
export const AnchorSchema = z.object({
  target_lines: z.tuple([z.number().int().positive(), z.number().int().positive()]),
  anchor_before: z.string(),
  anchor_text: z.string().min(1),
  anchor_after: z.string(),
});
export type Anchor = z.infer<typeof AnchorSchema>;

/**
 * One feedback entry. Lives as a markdown file with YAML frontmatter.
 * Shared byte-for-byte between the Obsidian plugin and the web viewer.
 */
export const AuditEntrySchema = z.object({
  id: z.string().regex(/^\d{8}-\d{6}-[0-9a-f]{4}$/),
  target: z.string().min(1),
  target_lines: AnchorSchema.shape.target_lines,
  anchor_before: AnchorSchema.shape.anchor_before,
  anchor_text: AnchorSchema.shape.anchor_text,
  anchor_after: AnchorSchema.shape.anchor_after,
  severity: Severity,
  author: z.string().min(1),
  source: AuditSource,
  created: z.string(),
  status: AuditStatus,
  // Body is the markdown after the frontmatter. Contains the # Comment and (for resolved) # Resolution sections.
  body: z.string().default(""),
});
export type AuditEntry = z.infer<typeof AuditEntrySchema>;

export const CONTEXT_CHARS = 80;
