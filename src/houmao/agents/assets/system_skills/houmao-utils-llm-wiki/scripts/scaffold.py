#!/usr/bin/env python3
"""
scaffold.py — Bootstrap a new LLM Wiki directory structure.

Usage:
    python3 scaffold.py <wiki-root> "<Topic Title>"

Example:
    python3 scaffold.py ~/wikis/ai-research "AI Research"

Creates:
    <wiki-root>/
    ├── README.md          (schema template)
    ├── log/
    │   └── YYYYMMDD.md    (first day's log with scaffold entry)
    ├── audit/
    │   ├── .gitkeep
    │   └── resolved/
    │       └── .gitkeep
    ├── raw/
    │   ├── articles/
    │   ├── papers/
    │   ├── notes/
    │   └── refs/
    ├── wiki/
    │   ├── index.md       (category-structured catalog)
    │   ├── concepts/
    │   ├── entities/
    │   └── summaries/
    └── outputs/
        └── queries/
"""

import os
import sys
from datetime import date, datetime


def scaffold(root: str, title: str) -> None:
    today = date.today()
    today_iso = today.isoformat()
    today_compact = today.strftime("%Y%m%d")
    now_hm = datetime.now().strftime("%H:%M")

    dirs = [
        "raw/articles",
        "raw/papers",
        "raw/notes",
        "raw/refs",
        "wiki/concepts",
        "wiki/entities",
        "wiki/summaries",
        "outputs/queries",
        "log",
        "audit",
        "audit/resolved",
    ]

    for d in dirs:
        os.makedirs(os.path.join(root, d), exist_ok=True)
    print(f"✓ Created directory tree under {root}/")

    # .gitkeep for empty audit dirs
    _write(root, "audit/.gitkeep", "")
    _write(root, "audit/resolved/.gitkeep", "")

    # README.md
    readme_md = f"""# {title} Knowledge Base

> Schema document — read at the start of every session together with `wiki/index.md`.
> Update after every major compile, ingest batch, or structural change.

## Scope

What this wiki covers:
- <describe the topic area>

What this wiki deliberately excludes:
- <describe out-of-scope areas>

## Operations

This wiki follows the llm-wiki skill's five operations: `compile`, `ingest`, `query`, `lint`, `audit`.
Every operation appends an entry to `log/YYYYMMDD.md`.

## Naming conventions

- **Concept pages** (`wiki/concepts/`): Title Case noun phrases.
- **Folder-split concepts** (`wiki/concepts/<topic>/`): used when a topic exceeds ~1200 words. Contains `index.md` + one file per aspect.
- **Entity pages** (`wiki/entities/`): Proper names.
- **Summary pages** (`wiki/summaries/`): kebab-case source slug.
- **Wikilinks**: use vault-root targets with short aliases, e.g. `[[wiki/concepts/page-slug|Page Title]]`.

All pages require YAML frontmatter: `title`, `type`, `created`, `updated`, `sources`, `tags`.

### Diagrams and formulas
- All diagrams are **mermaid**. No ASCII art.
- All formulas are **KaTeX** (inline `$...$` or block `$$...$$`).

### Raw file policy
- Small text sources → copy into `raw/<subfolder>/`.
- Large binaries → create a pointer file at `raw/refs/<slug>.md` with `kind: ref` and `external_path` fields. Do not copy the binary.
- Do not create a `## Raw references` section by default. Only if the user explicitly says they want raw material references, each touched wiki page gets a `## Raw references` section with wikilinks to the related raw materials, such as `[[raw/articles/<slug>|Raw article]]`, `[[raw/papers/<slug>|Raw paper]]`, or `[[raw/refs/<slug>|Raw reference]]`.

## Current articles

*None yet — update this list after every compile.*

### Concepts
*(none)*

### Entities
*(none)*

### Summaries
*(none)*

## Open research questions

- <What do you want to understand better?>
- <What are the key open questions in this domain?>

## Research gaps

Sources to ingest:
- [ ] <URL or paper title> — why it's relevant

## Audit backlog

*(none — run `python3 scripts/audit_review.py <wiki-root> --open` to refresh)*

## Notes for the LLM

- Language: <en | zh | bilingual>
- Tone: <neutral, academic, conversational, ...>
- Depth: <survey-level | deep technical>
- Handling contradictions: state both, cite each, add to Open Research Questions.
"""
    _write(root, "README.md", readme_md)
    print("✓ Created README.md")

    # log/<today>.md
    log_md = f"""# {today_iso}

## [{now_hm}] scaffold | Initialized {title} knowledge base
- Created directory tree (raw/, wiki/, log/, audit/, outputs/)
- Created README.md schema template
- Created wiki/index.md category skeleton
"""
    _write(root, f"log/{today_compact}.md", log_md)
    print(f"✓ Created log/{today_compact}.md")

    # wiki/index.md
    index_md = f"""# Index — {title}

> One-sentence scope of the wiki.

## 🔖 Navigation
- [[#Concepts]] · [[#Entities]] · [[#Summaries]] · [[#Open Questions]]

## Concepts

*(none yet)*

## Entities

*(none yet)*

## Summaries (chronological)

*(none yet)*

## Open Questions

- <First research question>
"""
    _write(root, "wiki/index.md", index_md)
    print("✓ Created wiki/index.md")

    print(f"""
✅ Wiki scaffolded at: {root}/

Next steps:
  1. Fill in README.md — define scope and naming conventions
  2. Add sources to raw/ (use Obsidian Web Clipper for web articles)
  3. Run ingest: tell your LLM agent "ingest raw/<file>.md"
  4. Ask questions: "what does the wiki say about X?"
  5. Run lint periodically:  python3 scripts/lint_wiki.py {root}
  6. Process feedback:       python3 scripts/audit_review.py {root} --open
""")


def _write(root: str, path: str, content: str) -> None:
    full = os.path.join(root, path)
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    scaffold(sys.argv[1], sys.argv[2])
