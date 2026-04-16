# README.md Schema Guide

`README.md` is the **schema document** for a wiki topic. It tells the LLM agent the scope, conventions, current state, and open questions — every session should start by reading it together with `wiki/index.md`.

## Why it matters

Without a schema, the LLM creates inconsistent page names, overlapping articles, and drifts from the wiki's intended scope. With a well-maintained schema, the LLM becomes a disciplined, consistent wiki maintainer.

**Co-evolve it with the wiki** — update after every major compile, ingest batch, or structural change.

## Full template

```markdown
# <Topic Title> Knowledge Base

> Schema document — read at the start of every session together with wiki/index.md.

## Scope

What this wiki covers:
- <bullet list of included areas>

What this wiki deliberately excludes:
- <bullet list of out-of-scope areas>

## Operations

This wiki follows the llm-wiki skill's five operations: `compile`, `ingest`, `query`, `lint`, `audit`.
Every operation appends an entry to `log/YYYYMMDD.md`.

## Naming conventions

### Pages
- **Concept pages** (`wiki/concepts/`): Title Case noun phrases. E.g., "Market Making Strategy", not "market making" or "MarketMakingStrategy".
- **Folder-split concepts** (`wiki/concepts/<topic>/`): used when a topic would exceed ~1200 words as a single page. Contains `index.md` + one file per aspect.
- **Entity pages** (`wiki/entities/`): Proper names. E.g., "Obsidian", "Avellaneda-Stoikov Model", or a person relevant to the wiki topic.
- **Summary pages** (`wiki/summaries/`): kebab-case source slug. E.g., "karpathy-llm-wiki-gist".

### Wikilinks
- Always use vault-root targets with short aliases: `[[wiki/concepts/page-slug|Page Title]]`.
- For folder-split pages, link to the index: `[[wiki/concepts/foo/index|Foo]]`.
- Link sibling vault directories directly, such as `[[raw/refs/source-pointer|source pointer]]`, `[[log/20260415#0012-ingest|ingest log]]`, and `[[outputs/queries/query-slug|query output]]`.
- Link the first mention of every entity or concept. Do not link the same page more than twice per article.

### Frontmatter
Every wiki page has YAML frontmatter:
```yaml
---
title: <Page Title>
type: concept | entity | summary
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [list of raw/ slugs this page draws from]
tags: [relevant tags]
---
```

### Diagrams and formulas
- All diagrams are **mermaid**. No ASCII art.
- All formulas are **KaTeX** (inline `$...$` or block `$$...$$`).

### Raw file policy
- Small text sources → copy into `raw/<subfolder>/`.
- Large binaries → create a pointer file at `raw/refs/<slug>.md` with `kind: ref` frontmatter and an `external_path` field. Do not copy the binary.

## Current articles

### Concepts
- [[wiki/concepts/<concept-slug>|<Concept Title>]] — one-line summary
- [[wiki/concepts/<topic>/index|<Topic>]] — (folder-split) one-line summary
    - [[wiki/concepts/<topic>/<aspect-1>|<Aspect 1>]] — ...

### Entities
- [[wiki/entities/<entity-slug>|<Entity Name>]] — one-line summary

### Summaries
- [[wiki/summaries/<slug>|<Source Title>]] — source title (date)

## Open research questions

- <Questions that should drive future ingest/query work>
- <Things the wiki currently doesn't cover well>
- <Contradictions or gaps noticed between articles>

## Research gaps

Sources to ingest:
- [ ] <URL or paper title> — why it's relevant

## Audit backlog

Count of open audits per target (filled in after running `audit_review.py --open`):
- <file> — N open
- ...

## Notes for the LLM

<Any special instructions: tone, depth level, language (zh/en), how to handle contradictions, etc.>
```

## What makes a good schema

**Good scope definition** prevents sprawl. A wiki about "LLM memory techniques" should exclude "LLM training" even though they're related.

**Explicit naming conventions** keep wikilinks from breaking. If you decide concept pages use Title Case, enforce it — a broken wikilink is an orphan.

**Maintained article list** lets the LLM know what already exists before creating a new page. The most common error is creating duplicate articles with slightly different names.

**Open research questions** give the LLM direction. Without them, the LLM defaults to ingesting the most obvious sources and missing your actual questions.

**Audit backlog** surfaces what the human has flagged as wrong. The AI should glance at it at the start of every session to decide whether to run an `audit` op before ingesting new material.

## Update cadence

- After every new concept page: add to "Current articles".
- After every ingest batch: update "Sources to ingest" checklist.
- After every lint pass: update "Research gaps".
- After every audit pass: refresh the "Audit backlog" counts.
- Monthly: review scope, prune stale research questions.
