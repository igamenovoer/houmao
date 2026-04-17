# Tooling Tips

Practical setup and usage notes for the LLM Wiki stack.

## Obsidian setup

### Essential settings

1. **Attachment folder**: Settings → Files and links → "Attachment folder path" → `raw/assets/`.
2. **New file location**: Settings → Files and links → "Default location for new notes" → `wiki/concepts/`.
3. **New link format**: Settings → Files and links → "New link format" → absolute path in vault. `llm-wiki` canonical links use vault-root targets such as `[[wiki/concepts/foo|Foo]]`.
4. **Download attachments hotkey**: Settings → Hotkeys → search "Download attachments" → bind to `Ctrl+Shift+D`. After clipping an article, hit the hotkey to download all images locally.

### Plugins to install

- **`plugins/obsidian-audit/`** (this repo) — select text → add feedback → writes to `audit/`. See "Audit plugin" section below.
- **Obsidian Web Clipper** (browser extension) — converts any webpage to Markdown and saves to your vault. Configure to save to `raw/articles/`.
- **Dataview** (optional) — query frontmatter fields; build dynamic tables of articles by tag, date, source count.
- **Marp** (optional) — render wiki content as slide decks directly from Obsidian.

### Graph view

Graph view (`Ctrl+G`) is the best way to see your wiki's shape:
- Dense hub = a well-connected concept page.
- Isolated node = orphan page (needs inbound links or removal). `lint_wiki.py` flags these.
- Cluster = a sub-topic worth a dedicated folder-split under `wiki/concepts/`.

## Audit plugin — `plugins/obsidian-audit/`

Installs into a local Obsidian vault. Workflow:

1. Build the plugin once:
   ```bash
   cd plugins/obsidian-audit
   npm install
   npm run build
   ```
2. Symlink (or copy) the plugin folder into your vault:
   ```bash
   npm run link -- "/path/to/your/vault"
   ```
3. In Obsidian, enable Community Plugins, then enable "LLM Wiki Audit".
4. In the plugin settings, set:
   - **Wiki root** — path relative to the vault root (usually `.`).
   - **Audit directory** — path relative to the wiki root (default `audit`).
   - **Author** — your name.

Commands (bind to hotkeys if you like):
- **`Audit: Add feedback on selection`** — opens a modal with severity + comment → writes an audit file.
- **`Audit: List open feedback for current file`** — shows a notice summarising open audits targeting the current file.
- **`Audit: Open audit folder`** — reveals `audit/` in the file explorer.

The plugin uses the shared `audit-shared` library, so files it writes are byte-identical in shape to files the web viewer writes.

## Web viewer — bundled deploy helper

Local Node.js server that renders the wiki with mermaid, KaTeX, and wikilinks, and lets you file feedback from your browser. Deploy it from the Houmao LLM Wiki utility skill root:

```bash
python3 scripts/deploy_viewer.py \
  --install-dir "/path/to/viewer-install" \
  --wiki "/path/to/wiki-root" \
  --port 4175
```

Then open `http://127.0.0.1:4175`. Features:
- Left sidebar: navigation tree built from `wiki/index.md`.
- Main pane: rendered markdown, mermaid diagrams rendered client-side, formulas rendered server-side.
- Right sidebar: list of open audits for the current page.
- Select any text → "💬 Add feedback" popover appears → submit → writes an audit file to `<wiki-root>/audit/`.

The server binds to `127.0.0.1` only. No auth; intended for personal use on your own machine.

## Obsidian Web Clipper usage

1. Install from [obsidian.md/clipper](https://obsidian.md/clipper).
2. Configure template to save to `raw/articles/`.
3. Clip an article → hit the download-images hotkey → file is ready for `ingest`.

For complex pages (paywalled, dynamic): copy-paste the main text manually, save as `raw/articles/<slug>.md`.

## qmd (optional, for large wikis)

[qmd](https://github.com/tobi/qmd) is a local semantic search engine for Markdown files with BM25 + vector hybrid search. Useful when the wiki grows beyond ~100 pages and `wiki/index.md` scanning becomes slow.

```bash
pip install qmd
qmd collection add wiki/ --name my-wiki
qmd embed
qmd query "what are the tradeoffs of RAG vs wiki" --collection my-wiki
```

qmd also has an MCP server so LLMs can use it as a native tool.

## Marp — generating slide decks from wiki content

```markdown
---
marp: true
theme: default
---

# Slide title

Content here

---

# Next slide
```

Install the Marp plugin in Obsidian to preview/export directly.

## Generating charts

For quantitative analyses, ask the LLM to generate a matplotlib script and save to `outputs/charts/`:

```python
# outputs/charts/my-analysis.py
import matplotlib.pyplot as plt
# ... chart code ...
plt.savefig('outputs/charts/my-analysis.png')
```

Embed in a wiki article: `![[outputs/charts/my-analysis.png]]`.

## Git workflow

The wiki is a git repo. Benefits:
- Version history for every article.
- Branching for experimental research directions.
- Audit files are tracked, so "who suggested this and when" is first-class.

```bash
git add .
git commit -m "ingest: 3 papers on attention mechanisms"
git push
```

Keep large files (PDFs >10 MB, raw images at full resolution, video, model weights) in `.gitignore`. Use the raw file policy: pointer files in `raw/refs/`, not copies.

## Interactive HTML outputs

For complex analyses, the LLM can generate interactive HTML with JavaScript and save to `outputs/`. These can be opened in a browser or embedded in Obsidian with the HTML plugin.
