import type MarkdownIt from "markdown-it";

/**
 * markdown-it plugin: turn [[Target]] and [[Target|Alias]] into anchor tags.
 *
 * The resolver decides the final href and whether the target exists.
 * Unresolved links get a `wikilink-dead` class so the client can style them.
 */
export interface WikilinkResolver {
  (target: string): { href: string; exists: boolean } | null;
}

export function wikilinksPlugin(md: MarkdownIt, resolve: WikilinkResolver): void {
  const WIKILINK_RE = /\[\[([^\]|#]+)(?:#([^\]|]+))?(?:\|([^\]]+))?\]\]/;

  md.inline.ruler.before("link", "wikilink", (state, silent) => {
    const src = state.src;
    if (src[state.pos] !== "[" || src[state.pos + 1] !== "[") return false;
    const tail = src.slice(state.pos);
    const m = WIKILINK_RE.exec(tail);
    if (!m || m.index !== 0) return false;

    if (!silent) {
      const target = m[1]!.trim();
      const anchor = m[2]?.trim();
      const alias = m[3]?.trim();
      const display = alias || target;

      const resolved = resolve(target);
      const href =
        resolved?.href ??
        `/?page=${encodeURIComponent(target)}${anchor ? "#" + encodeURIComponent(anchor) : ""}`;

      const open = state.push("link_open", "a", 1);
      open.attrs = [
        ["href", href + (anchor ? `#${anchor}` : "")],
        ["class", `wikilink ${resolved?.exists ? "wikilink-alive" : "wikilink-dead"}`],
        ["data-wikilink-target", target],
      ];
      const text = state.push("text", "", 0);
      text.content = display;
      state.push("link_close", "a", -1);
    }
    state.pos += m[0].length;
    return true;
  });
}
