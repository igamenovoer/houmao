import mermaid from "mermaid";
import type { AuditEntry } from "audit-shared";
import { renderTree } from "./tree.js";
import { installFeedbackUI } from "./feedback.js";
import { installSearchUI } from "./search.js";

interface PageResponse {
  path: string;
  title: string | null;
  html: string;
  raw: string;
  frontmatter: Record<string, unknown> | null;
}

const state = {
  currentPath: "wiki/index.md" as string,
  rawMarkdown: "" as string,
  author: "me" as string,
};

// Mermaid with Catppuccin Mocha palette.
mermaid.initialize({
  startOnLoad: false,
  theme: "base",
  securityLevel: "loose",
  fontFamily: "Inter, system-ui, sans-serif",
  themeVariables: {
    background: "#11111b",
    primaryColor: "#313244",
    primaryTextColor: "#cdd6f4",
    primaryBorderColor: "#b4befe",
    secondaryColor: "#45475a",
    secondaryTextColor: "#cdd6f4",
    secondaryBorderColor: "#89b4fa",
    tertiaryColor: "#585b70",
    tertiaryTextColor: "#cdd6f4",
    tertiaryBorderColor: "#94e2d5",
    lineColor: "#7f849c",
    textColor: "#cdd6f4",
    mainBkg: "#313244",
    nodeBorder: "#b4befe",
    clusterBkg: "#181825",
    clusterBorder: "#45475a",
    titleColor: "#cdd6f4",
    edgeLabelBackground: "#181825",
    actorBkg: "#313244",
    actorBorder: "#b4befe",
    actorTextColor: "#cdd6f4",
    actorLineColor: "#7f849c",
    signalColor: "#cdd6f4",
    signalTextColor: "#cdd6f4",
    labelBoxBkgColor: "#313244",
    labelBoxBorderColor: "#b4befe",
    labelTextColor: "#cdd6f4",
    loopTextColor: "#cdd6f4",
    noteBkgColor: "#f9e2af",
    noteTextColor: "#11111b",
    noteBorderColor: "#f9e2af",
    activationBkgColor: "#45475a",
    activationBorderColor: "#b4befe",
    stateBkg: "#313244",
    stateBorder: "#b4befe",
    specialStateColor: "#f38ba8",
  },
});

async function main() {
  try {
    const cfg = await fetch("/api/config").then((r) => r.json());
    if (cfg.author) state.author = cfg.author;
  } catch {}

  installMobilePanels();

  const tree = await fetch("/api/tree").then((r) => r.json());
  renderTree(document.getElementById("tree")!, tree, (path) => {
    navigateToPage(path);
    closeMobilePanels();
  });

  installSearchUI({
    getCurrentPath: () => state.currentPath,
    onSelect: (path) => {
      navigateToPage(path);
    },
  });

  const initial = new URL(window.location.href).searchParams.get("page") ?? "wiki/index.md";
  await loadPage(initial);

  window.addEventListener("popstate", (e) => {
    const p =
      (e.state && e.state.page) ||
      new URL(window.location.href).searchParams.get("page") ||
      "wiki/index.md";
    void loadPage(p);
  });

  document.getElementById("page-content")!.addEventListener("click", (e) => {
    const target = (e.target as HTMLElement).closest("a.wikilink") as HTMLAnchorElement | null;
    if (!target) return;
    const href = target.getAttribute("href") ?? "";
    const u = new URL(href, window.location.href);
    const page = u.searchParams.get("page");
    if (page) {
      e.preventDefault();
      navigateToPage(page);
    }
  });

  document.getElementById("btn-refresh")!.addEventListener("click", () => {
    void loadAudits(state.currentPath);
  });

  installFeedbackUI({
    getState: () => ({
      currentPath: state.currentPath,
      rawMarkdown: state.rawMarkdown,
      author: state.author,
    }),
    onCreated: async () => {
      await loadAudits(state.currentPath);
    },
  });
}

function navigateToPage(path: string): void {
  if (path !== state.currentPath) {
    void loadPage(path);
    history.pushState({ page: path }, "", `/?page=${encodeURIComponent(path)}`);
    return;
  }
  history.replaceState({ page: path }, "", `/?page=${encodeURIComponent(path)}`);
}

async function loadPage(pathArg: string): Promise<void> {
  const pageEl = document.getElementById("page-content")!;
  pageEl.innerHTML = '<p class="loading">Loading</p>';

  try {
    const res = await fetch(`/api/page?path=${encodeURIComponent(pathArg)}`);
    if (!res.ok) {
      pageEl.innerHTML = `<p class="loading">Failed to load <code>${escapeHtml(pathArg)}</code>: ${res.status}</p>`;
      return;
    }
    const data: PageResponse = await res.json();
    state.currentPath = data.path;
    state.rawMarkdown = data.raw;

    pageEl.innerHTML = data.html;

    await renderMermaidBlocks(pageEl);

    document.querySelectorAll("#tree a.active").forEach((el) => el.classList.remove("active"));
    const link = document.querySelector(`#tree a[data-path="${cssEscape(data.path)}"]`);
    if (link) link.classList.add("active");

    const titleEl = document.getElementById("wiki-title")!;
    titleEl.textContent = data.title ?? data.path;

    await loadAudits(data.path);
    pageEl.scrollTop = 0;
    (document.querySelector("main") as HTMLElement | null)?.scrollTo({ top: 0 });
  } catch (err) {
    console.error(err);
    pageEl.innerHTML = "<p class=\"loading\">Error loading page.</p>";
  }
}

function installMobilePanels(): void {
  const navButton = document.getElementById("btn-nav") as HTMLButtonElement | null;
  const auditsButton = document.getElementById("btn-audits") as HTMLButtonElement | null;
  const backdrop = document.getElementById("mobile-panel-backdrop");

  navButton?.addEventListener("click", () => {
    setMobilePanel(document.body.classList.contains("mobile-nav-open") ? null : "nav");
  });
  auditsButton?.addEventListener("click", () => {
    setMobilePanel(document.body.classList.contains("mobile-audits-open") ? null : "audits");
  });
  backdrop?.addEventListener("click", closeMobilePanels);
  document.querySelectorAll("[data-mobile-close]").forEach((button) => {
    button.addEventListener("click", closeMobilePanels);
  });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMobilePanels();
  });
}

function setMobilePanel(panel: "nav" | "audits" | null): void {
  const navOpen = panel === "nav";
  const auditsOpen = panel === "audits";
  document.body.classList.toggle("mobile-nav-open", navOpen);
  document.body.classList.toggle("mobile-audits-open", auditsOpen);
  document.body.classList.toggle("mobile-panel-open", navOpen || auditsOpen);
  document.getElementById("btn-nav")?.setAttribute("aria-expanded", String(navOpen));
  document.getElementById("btn-audits")?.setAttribute("aria-expanded", String(auditsOpen));
}

function closeMobilePanels(): void {
  setMobilePanel(null);
}

async function renderMermaidBlocks(pageEl: HTMLElement): Promise<void> {
  const mermaidNodes = pageEl.querySelectorAll("pre.mermaid-block code.language-mermaid");
  for (let i = 0; i < mermaidNodes.length; i++) {
    const code = mermaidNodes[i] as HTMLElement;
    const pre = code.parentElement as HTMLElement;
    const source = code.textContent ?? "";
    const id = `mermaid-${Date.now()}-${i}`;
    try {
      const { svg } = await mermaid.render(id, source);
      const container = document.createElement("div");
      container.className = "mermaid-block mermaid-rendered";
      container.innerHTML = svg;
      const srcLine = pre.getAttribute("data-source-line");
      if (srcLine) container.setAttribute("data-source-line", srcLine);
      pre.replaceWith(container);
    } catch (err) {
      const fallback = document.createElement("div");
      fallback.className = "mermaid-block mermaid-error";
      const srcLine = pre.getAttribute("data-source-line");
      if (srcLine) fallback.setAttribute("data-source-line", srcLine);
      fallback.innerHTML = `
        <p class="mermaid-error-title">Diagram failed to render.</p>
        <p class="mermaid-error-message">${escapeHtml(errorMessage(err))}</p>
        <pre><code>${escapeHtml(source)}</code></pre>
      `;
      pre.replaceWith(fallback);
      console.error("mermaid render failed", err);
    }
  }
}

async function loadAudits(targetPath: string): Promise<void> {
  const el = document.getElementById("audit-list")!;
  el.innerHTML = '<p class="loading">Loading</p>';
  try {
    const res = await fetch(`/api/audit?target=${encodeURIComponent(targetPath)}&mode=open`);
    const data: { entries: AuditEntry[] } = await res.json();
    if (data.entries.length === 0) {
      el.innerHTML =
        '<p class="muted" style="padding: 4px 6px; font-size: 12.5px;">No open audits for this page.</p>';
      return;
    }
    el.innerHTML = data.entries.map((e) => renderAuditItem(e)).join("");
    el.querySelectorAll("button[data-resolve]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-resolve")!;
        const note = window.prompt("Resolution note (optional):", "") ?? "";
        const r = await fetch(`/api/audit/${id}/resolve`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ resolution: note }),
        });
        if (r.ok) await loadAudits(targetPath);
        else alert("Failed to resolve.");
      });
    });
  } catch (err) {
    el.innerHTML = '<p class="muted" style="padding: 4px 6px;">Failed to load audits.</p>';
    console.error(err);
  }
}

function renderAuditItem(e: AuditEntry): string {
  const body = e.body
    .replace(/^#\s*Comment\s*/i, "")
    .split(/^#\s*Resolution/im)[0]!
    .replace(/<!--[\s\S]*?-->/g, "")
    .trim();
  const when = new Date(e.created).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  return `
    <div class="audit-item sev-${e.severity}" data-id="${e.id}">
      <div class="audit-head">
        <span class="sev-pill sev-${e.severity}">${e.severity}</span>
        <span class="author">${escapeHtml(e.author)}</span>
      </div>
      <div class="audit-body">${escapeHtml(body)}</div>
      <div class="audit-meta">${e.id} · ${when}</div>
      <div class="audit-actions"><button type="button" data-resolve="${e.id}">mark resolved</button></div>
    </div>`;
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>\"']/g, (ch) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch] ?? ch),
  );
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

function cssEscape(s: string): string {
  return s.replace(/[\"\\\\]/g, "\\$&");
}

void main();
