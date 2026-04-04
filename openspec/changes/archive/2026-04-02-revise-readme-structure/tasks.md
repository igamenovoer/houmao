## 1. Remove duplicated reference content from README

- [x] 1.1 Remove §2 "Initialize A Local Houmao Project Overlay" (lines 184–203) — content already in `docs/reference/agents/operations/project-aware-operations.md`
- [x] 1.2 Remove §3 "Prepare The Agent Definition Directory Contents" (lines 206–349) — content already in `docs/getting-started/agent-definitions.md`
- [x] 1.3 Remove §5 "Server-Backed Multi-Agent Coordination" (lines 380–392) — content already in `docs/reference/houmao_server_pair.md`
- [x] 1.4 Remove "Developer Guide / Architecture" section (lines 396–479) — mermaid diagrams already in `docs/getting-started/overview.md`
- [x] 1.5 Shrink "Appendix: Legacy CAO" to a one-sentence footnote with a link to docs

## 2. Trim Installation and Documentation sections

- [x] 2.1 Remove the optional pg-hosting block from Installation
- [x] 2.2 Remove the standalone "Documentation" section (mkdocs build/serve commands); fold `pixi run docs-serve` into the Development section

## 3. Add new Easy Specialists section

- [x] 3.1 Add "Easy Specialists" section after §1 (agents join), showing `project init` → `specialist create` → `instance launch` → prompt → stop flow with correct CLI flags verified from Click commands
- [x] 3.2 Include link to `docs/getting-started/easy-specialists.md` for full details

## 4. Slim the basic workflow section

- [x] 4.1 Replace §4 "Basic Workflow (Local tmux)" with a brief "Full Preset Launch" section: 5-line code example of `agents launch` + link to agent-definitions docs and minimal-agent-launch demo

## 5. Add Runnable Demos section

- [x] 5.1 Add "Runnable Demos" section with entry for `scripts/demo/minimal-agent-launch/` — brief description of preset-backed headless launch + run command
- [x] 5.2 Add entry for `scripts/demo/single-agent-mail-wakeup/` — brief description of easy-specialist + gateway + mailbox-notifier workflow + run command + link to demo README

## 6. Add Subsystems at a Glance section

- [x] 6.1 Add "Subsystems at a Glance" section with one-liner descriptions and links for gateway, mailbox, and TUI tracking pointing to docs pages / GitHub Pages

## 7. Add Full Documentation link and trim Development

- [x] 7.1 Add explicit "Full Documentation" section pointing to `https://igamenovoer.github.io/houmao/`
- [x] 7.2 Consolidate "Development Checks" to include format/lint/typecheck/test + docs-serve, remove standalone docs build section

## 8. Update docs index cross-reference

- [x] 8.1 Add a note to `docs/index.md` indicating the README is the recommended starting point for new users
