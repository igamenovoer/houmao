import MiniSearch from "minisearch";

interface SearchDocument {
  path: string;
  title: string;
  headings: string;
  text: string;
  preview: string;
}

interface SearchIndexResponse {
  documents: SearchDocument[];
}

interface StoredSearchFields {
  path: string;
  title: string;
  preview: string;
}

interface InstallSearchOptions {
  onSelect: (path: string) => void;
  getCurrentPath: () => string;
}

type SearchResult = StoredSearchFields & { id: string; score: number };

const SEARCH_SHORTCUT = "/";

export function installSearchUI(options: InstallSearchOptions): void {
  const root = document.getElementById("search-box")!;
  const button = document.getElementById("btn-search") as HTMLButtonElement;
  const input = document.getElementById("search-input") as HTMLInputElement;
  const resultsEl = document.getElementById("search-results")!;
  const statusEl = document.getElementById("search-status")!;

  let miniSearch: MiniSearch<SearchDocument> | null = null;
  let loadPromise: Promise<MiniSearch<SearchDocument>> | null = null;
  let results: SearchResult[] = [];
  let activeIndex = -1;

  const ensureIndex = async (): Promise<MiniSearch<SearchDocument>> => {
    if (miniSearch) return miniSearch;
    if (loadPromise) return loadPromise;

    statusEl.textContent = "Loading search index";
    loadPromise = fetch("/api/search-index")
      .then(async (res) => {
        if (!res.ok) throw new Error(`search index failed: ${res.status}`);
        return (await res.json()) as SearchIndexResponse;
      })
      .then((data) => {
        const index = new MiniSearch<SearchDocument>({
          idField: "path",
          fields: ["title", "headings", "text", "path"],
          storeFields: ["path", "title", "preview"],
          searchOptions: {
            boost: { title: 4, headings: 2, path: 1.5 },
            fuzzy: 0.2,
            prefix: true,
          },
        });
        index.addAll(data.documents);
        miniSearch = index;
        statusEl.textContent = "";
        return index;
      })
      .catch((err: unknown) => {
        console.error(err);
        loadPromise = null;
        statusEl.textContent = "Search index failed to load";
        throw err;
      });

    return loadPromise;
  };

  const openSearch = async (): Promise<void> => {
    root.classList.add("open");
    button.setAttribute("aria-expanded", "true");
    input.focus();
    input.select();
    try {
      await ensureIndex();
      renderResults();
    } catch {
      renderMessage("Search is unavailable.");
    }
  };

  const closeSearch = (): void => {
    root.classList.remove("open");
    button.setAttribute("aria-expanded", "false");
    input.value = "";
    results = [];
    activeIndex = -1;
    statusEl.textContent = "";
    resultsEl.innerHTML = "";
  };

  const runSearch = async (): Promise<void> => {
    const query = input.value.trim();
    if (!query) {
      results = [];
      activeIndex = -1;
      statusEl.textContent = "";
      resultsEl.innerHTML = "";
      return;
    }

    try {
      const index = await ensureIndex();
      results = index.search(query).slice(0, 8).map((result) => {
        const stored = result as unknown as Partial<StoredSearchFields> & {
          id: string;
          score: number;
        };
        const path = stored.path ?? stored.id;
        return {
          id: stored.id,
          score: stored.score,
          path,
          title: stored.title ?? path,
          preview: stored.preview ?? "",
        };
      });
      activeIndex = results.length ? 0 : -1;
      renderResults();
    } catch {
      renderMessage("Search is unavailable.");
    }
  };

  const renderResults = (): void => {
    if (!input.value.trim()) {
      resultsEl.innerHTML = "";
      return;
    }
    if (results.length === 0) {
      renderMessage("No matches.");
      return;
    }

    statusEl.textContent = `${results.length} match${results.length === 1 ? "" : "es"}`;
    resultsEl.innerHTML = results
      .map((result, index) =>
        renderResult(result, index === activeIndex, result.path === options.getCurrentPath()),
      )
      .join("");

    resultsEl.querySelectorAll<HTMLButtonElement>("button[data-path]").forEach((el) => {
      el.addEventListener("click", () => {
        openResult(el.getAttribute("data-path")!);
      });
    });
  };

  const renderMessage = (message: string): void => {
    statusEl.textContent = message;
    resultsEl.innerHTML = "";
  };

  const moveActive = (delta: number): void => {
    if (!results.length) return;
    activeIndex = (activeIndex + delta + results.length) % results.length;
    renderResults();
    resultsEl
      .querySelector<HTMLButtonElement>(".search-result.active")
      ?.scrollIntoView({ block: "nearest" });
  };

  const openActive = (): void => {
    if (activeIndex < 0 || activeIndex >= results.length) return;
    openResult(results[activeIndex]!.path);
  };

  const openResult = (path: string): void => {
    options.onSelect(path);
    closeSearch();
  };

  button.addEventListener("click", () => {
    if (root.classList.contains("open")) closeSearch();
    else void openSearch();
  });
  input.addEventListener("input", () => {
    void runSearch();
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      moveActive(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      moveActive(-1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      openActive();
    } else if (e.key === "Escape") {
      e.preventDefault();
      closeSearch();
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.defaultPrevented || isEditableFocused()) return;
    const isCtrlK = e.key.toLowerCase() === "k" && (e.ctrlKey || e.metaKey);
    const isSlash = e.key === SEARCH_SHORTCUT && !e.ctrlKey && !e.metaKey && !e.altKey;
    if (!isCtrlK && !isSlash) return;
    e.preventDefault();
    void openSearch();
  });
  document.addEventListener("click", (e) => {
    if (!root.classList.contains("open")) return;
    if (root.contains(e.target as Node)) return;
    closeSearch();
  });
}

function renderResult(result: SearchResult, active: boolean, current: boolean): string {
  const classes = ["search-result"];
  if (active) classes.push("active");
  if (current) classes.push("current");
  return `
    <button type="button" class="${classes.join(" ")}" data-path="${escapeHtml(result.path)}">
      <span class="search-result-title">${escapeHtml(result.title || result.path)}</span>
      <span class="search-result-path">${escapeHtml(result.path)}${current ? " · current" : ""}</span>
      <span class="search-result-preview">${escapeHtml(result.preview || "")}</span>
    </button>`;
}

function isEditableFocused(): boolean {
  const el = document.activeElement;
  if (!el) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || (el as HTMLElement).isContentEditable;
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>\"']/g, (ch) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch] ?? ch),
  );
}
