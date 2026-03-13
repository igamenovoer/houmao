## 1. Canonical package root and build surfaces

- [x] 1.1 Rename the active Python package tree from `src/gig_agents` to `src/houmao` and update build/package metadata such as wheel/sdist package lists and entrypoint targets.
- [x] 1.2 Rewrite internal imports, packaged-resource lookup strings, subprocess module-launch strings, lazy import/export tables, and generated helper snippets so the active codebase uses `houmao...` consistently.
- [x] 1.3 Update new runtime-owned identity strings that encode module ownership (for example launcher ownership metadata) to the canonical `houmao...` namespace while documenting that previously generated runtime homes may need rebuild.
- [x] 1.4 Rename the remaining user-facing launcher binary from `gig-cao-server` to `houmao-cao-server` and update entrypoint wiring accordingly.

## 2. User-facing strings, guidance, scripts, and tests

- [x] 2.1 Update `pyproject.toml` project URLs, active assistant/contributor guidance, shipped docstrings, CLI help/output references, and repo-owned docs to use the canonical GitHub URL and current `Houmao` / `houmao...` / `houmao-cao-server` surfaces.
- [x] 2.2 Update repo-owned scripts, demos, helpers, and automated tests to use `houmao...` imports, `houmao-cao-server`, module-invocation examples, and source-path references instead of `gig_agents...` or `gig-cao-server`.
- [x] 2.3 Expand the shipped-doc sweep beyond branding cleanup so `README.md`, pages under `docs/`, and demo READMEs use canonical Houmao names and module paths wherever they teach the current runnable contract.

## 3. Portable instructional paths

- [x] 3.1 Review active instructional docs that currently include checkout-local absolute paths and classify each occurrence as active guidance versus historical or diagnostic context.
- [x] 3.2 Replace active instructional absolute paths with repo-relative paths or `<repo-root>` placeholders wherever readers are expected to run commands, inspect files, or navigate the repository directly.
- [x] 3.3 Update affected tutorial or operator docs so rerunnable examples follow the repo-relative or placeholder path policy while preserving clearly labeled historical or observed-path references only in non-user-facing record material where needed.

## 4. Verification and exception handling

- [x] 4.1 Re-scan user-facing surfaces for old GitHub slug, old project-name, old `gig_agents` module paths, old `gig-*` CLI names, and checkout-local path patterns and confirm that touched user-facing surfaces now use the canonical Houmao identity.
- [x] 4.2 Verify the canonical module-entrypoint surfaces, renamed user-facing CLI binaries, and quality gates, including `pixi run python -m houmao.agents.realm_controller --help`, `pixi run python -m houmao.cao.tools.cao_server_launcher --help`, `pixi run houmao-cli --help`, `pixi run houmao-cao-server --help`, and the relevant lint/type/test/build commands.
- [x] 4.3 Review remaining matches after the sweep and keep only references that are intentionally historical, provenance-preserving, archived, internal-review, or machine-required local-path exceptions outside user-facing source/docs/CLI surfaces.
