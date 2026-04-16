interface State {
  currentPath: string;
  rawMarkdown: string;
  author: string;
}

export interface FeedbackUIOptions {
  getState: () => State;
  onCreated: () => Promise<void> | void;
}

/**
 * Wires up the selection → popover → dialog flow for filing an audit comment.
 *
 * The trick is turning a DOM selection back into character offsets inside
 * the raw markdown. We do it in two steps:
 *
 *   1) Walk up from the selection to the nearest element with
 *      `data-source-line="<start>,<end>"` (emitted by the server renderer).
 *      That tells us which block the selection is in and what line range
 *      that block spans in the source.
 *   2) Look up the selected text as a substring inside the source for that
 *      line range. If unique, we have the offsets. If not, fall back to a
 *      whole-file search.
 *
 * This is good enough for anchor capture — the anchor algorithm itself
 * stores `anchor_before` / `anchor_text` / `anchor_after` windows so that
 * later line drift doesn't invalidate the audit.
 */
export function installFeedbackUI(opts: FeedbackUIOptions): void {
  const popover = document.getElementById("feedback-popover") as HTMLElement;
  const popoverBtn = document.getElementById("feedback-trigger") as HTMLButtonElement;
  const dialog = document.getElementById("feedback-dialog") as HTMLDialogElement;
  const preview = document.getElementById("feedback-preview") as HTMLElement;
  const textarea = document.getElementById("feedback-comment") as HTMLTextAreaElement;
  const form = document.getElementById("feedback-form") as HTMLFormElement;
  const cancelBtn = document.getElementById("feedback-cancel") as HTMLButtonElement;
  const pageEl = document.getElementById("page-content") as HTMLElement;

  let pending: { selStart: number; selEnd: number; text: string } | null = null;

  document.addEventListener("selectionchange", () => {
    const sel = document.getSelection();
    if (!sel || sel.rangeCount === 0 || sel.isCollapsed) {
      popover.classList.add("hidden");
      return;
    }
    const range = sel.getRangeAt(0);
    if (!pageEl.contains(range.commonAncestorContainer)) {
      popover.classList.add("hidden");
      return;
    }
    const text = sel.toString();
    if (!text.trim()) {
      popover.classList.add("hidden");
      return;
    }
    // Position the popover just above the selection.
    const rect = range.getBoundingClientRect();
    popover.style.left = `${window.scrollX + rect.left}px`;
    popover.style.top = `${window.scrollY + rect.top - 38}px`;
    popover.classList.remove("hidden");
  });

  popoverBtn.addEventListener("click", () => {
    const sel = document.getSelection();
    if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return;
    const text = sel.toString();
    if (!text.trim()) return;
    const range = sel.getRangeAt(0);
    const { rawMarkdown } = opts.getState();
    const offsets = resolveSelectionToRawOffsets(rawMarkdown, range, text);
    if (!offsets) {
      alert(
        "Couldn't locate the selection in the source markdown. Try selecting plain text only (no rendered symbols).",
      );
      return;
    }
    pending = { ...offsets, text };
    preview.textContent = text.length > 400 ? text.slice(0, 400) + "…" : text;
    textarea.value = "";
    dialog.showModal();
    setTimeout(() => textarea.focus(), 30);
    popover.classList.add("hidden");
  });

  cancelBtn.addEventListener("click", (e) => {
    e.preventDefault();
    dialog.close();
    pending = null;
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!pending) return;
    const severity =
      (form.querySelector('input[name="severity"]:checked') as HTMLInputElement | null)?.value ??
      "warn";
    const comment = textarea.value.trim();
    if (!comment) {
      alert("Comment is empty");
      return;
    }
    const { currentPath, rawMarkdown, author } = opts.getState();
    try {
      const res = await fetch("/api/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target: currentPath,
          rawMarkdown,
          selStart: pending.selStart,
          selEnd: pending.selEnd,
          comment,
          severity,
          author,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(`Failed to save feedback: ${err.error ?? res.statusText}`);
        return;
      }
      dialog.close();
      pending = null;
      await opts.onCreated();
    } catch (err) {
      alert(`Error: ${String(err)}`);
    }
  });
}

/**
 * Turn a DOM Range into char offsets in the raw markdown.
 * Strategy:
 *   1) Find the nearest ancestor element with data-source-line to scope the search.
 *   2) Search for the selection text inside that line range. If unique, use it.
 *   3) Otherwise search the whole source. If still ambiguous, return null.
 */
function resolveSelectionToRawOffsets(
  raw: string,
  range: Range,
  selText: string,
): { selStart: number; selEnd: number } | null {
  if (!selText) return null;

  const scope = findSourceLineAncestor(range.commonAncestorContainer);
  const lines = raw.split("\n");

  if (scope) {
    const [ls, le] = scope;
    const startOffset = lineStartOffset(lines, ls - 1);
    const endOffset =
      le >= lines.length ? raw.length : lineStartOffset(lines, le);
    const slice = raw.slice(startOffset, endOffset);
    const idx = slice.indexOf(selText);
    if (idx >= 0) {
      const next = slice.indexOf(selText, idx + 1);
      if (next < 0) {
        return {
          selStart: startOffset + idx,
          selEnd: startOffset + idx + selText.length,
        };
      }
    }
  }

  // Fall back to whole-file search.
  const idx = raw.indexOf(selText);
  if (idx < 0) return null;
  if (raw.indexOf(selText, idx + 1) >= 0) {
    // Ambiguous. Give up — user should select something more unique.
    return null;
  }
  return { selStart: idx, selEnd: idx + selText.length };
}

function findSourceLineAncestor(node: Node): [number, number] | null {
  let el: Node | null = node;
  while (el && el.nodeType !== Node.ELEMENT_NODE) el = el.parentNode;
  while (el && el instanceof HTMLElement) {
    const attr = el.getAttribute("data-source-line");
    if (attr) {
      const parts = attr.split(",").map((x) => parseInt(x.trim(), 10));
      if (parts.length === 2 && Number.isFinite(parts[0]) && Number.isFinite(parts[1])) {
        return [parts[0]!, parts[1]!];
      }
    }
    el = el.parentElement;
  }
  return null;
}

function lineStartOffset(lines: string[], lineIndex: number): number {
  let offset = 0;
  for (let i = 0; i < lineIndex && i < lines.length; i++) {
    offset += lines[i]!.length + 1;
  }
  return offset;
}
