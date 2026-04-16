/**
 * Generate an audit id of the form: YYYYMMDD-HHMMSS-<4hex>.
 * Local time. Collision probability is negligible for single-user use.
 */
export function makeId(now: Date = new Date()): string {
  const y = now.getFullYear();
  const mo = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  const ss = String(now.getSeconds()).padStart(2, "0");
  const rand = Math.floor(Math.random() * 0x10000)
    .toString(16)
    .padStart(4, "0");
  return `${y}${mo}${d}-${hh}${mm}${ss}-${rand}`;
}

/**
 * Derive a short filesystem-safe slug from a string. Used to make audit
 * filenames a bit more human-readable:
 *   20260409-143022-a1b2-claude-code-size.md
 */
export function slugify(input: string, maxLen = 30): string {
  return input
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "") // strip diacritics
    .replace(/[^a-z0-9\s-]+/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, maxLen)
    .replace(/^-+|-+$/g, "");
}

export function filenameFor(id: string, slug?: string): string {
  if (!slug) return `${id}.md`;
  const cleaned = slugify(slug);
  return cleaned ? `${id}-${cleaned}.md` : `${id}.md`;
}
