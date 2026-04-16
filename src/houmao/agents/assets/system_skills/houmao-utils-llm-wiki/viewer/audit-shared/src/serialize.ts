import * as yaml from "js-yaml";
import { AuditEntrySchema, type AuditEntry } from "./schema.js";

const FRONTMATTER_RE = /^---\n([\s\S]*?)\n---\n?([\s\S]*)$/;

/**
 * Render an AuditEntry as the full markdown file contents
 * (YAML frontmatter + body). The body typically contains the
 * `# Comment` and optional `# Resolution` sections.
 */
export function toMarkdown(entry: AuditEntry): string {
  const { body, ...front } = entry;
  const yml = yaml.dump(front, {
    lineWidth: 0,
    noRefs: true,
    sortKeys: false,
    quotingType: '"',
    forceQuotes: false,
  });
  const bodyText = body && body.trim().length > 0 ? body : defaultBody();
  return `---\n${yml}---\n\n${bodyText.trimEnd()}\n`;
}

/**
 * Parse the full markdown contents of an audit file back into an AuditEntry.
 * Throws if the frontmatter is missing or fails schema validation.
 */
export function fromMarkdown(text: string): AuditEntry {
  const m = FRONTMATTER_RE.exec(text);
  if (!m) {
    throw new Error("audit file is missing YAML frontmatter (no leading --- block)");
  }
  const frontRaw = yaml.load(m[1]!) as Record<string, unknown>;
  const body = (m[2] ?? "").replace(/^\n/, "");
  const parsed = AuditEntrySchema.parse({ ...frontRaw, body });
  return parsed;
}

function defaultBody(): string {
  return `# Comment\n\n<!-- describe the feedback here -->\n\n# Resolution\n\n<!-- filled in when the audit is processed -->\n`;
}
