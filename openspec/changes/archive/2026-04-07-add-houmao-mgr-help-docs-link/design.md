## Context

`houmao-mgr` is the main operator-facing CLI, and its root help output is often the first surface a reader sees after installation. Today that help output lists the top-level command families and root flags, but it does not provide any direct path to the published documentation site.

The repository already has a canonical docs destination on GitHub Pages at `https://igamenovoer.github.io/houmao/`, and repo-owned docs already treat that site as the long-form reference surface. The requested change is narrow: make the root help output point readers there without changing command behavior or introducing another command just for documentation discovery.

## Goals / Non-Goals

**Goals:**
- Make `houmao-mgr --help` and bare `houmao-mgr` invocation point readers to the published detailed documentation.
- Keep the change limited to the root help surface so it is visible immediately.
- Preserve the existing command tree, options, and help structure apart from the added docs link text.

**Non-Goals:**
- Redesign the overall help layout for all subcommands.
- Add new network-dependent behavior, dynamic docs resolution, or update checks.
- Replace the existing repo docs structure or CLI reference pages.

## Decisions

### Add the docs link directly to the root Click help surface
The root `houmao-mgr` command should render one short docs-discovery line as part of the built-in help output.

Rationale:
- It keeps the link on the exact surface the user asked about.
- It works for both `houmao-mgr --help` and bare `houmao-mgr`, since bare invocation already delegates to `ctx.get_help()`.
- It avoids adding a new subcommand or requiring readers to already know where CLI reference docs live.

Alternative considered:
- Only update repo docs or README. Rejected because it does not help users who start from the local CLI.

### Use the published GitHub Pages docs URL as the canonical target
The link text should point to `https://igamenovoer.github.io/houmao/` rather than the repository root.

Rationale:
- The user explicitly asked for the GitHub Pages-style docs destination so readers can find more detailed docs.
- The docs site is the long-form operator and developer reference, while the repository homepage is broader and less focused for CLI help follow-up.

Alternative considered:
- Link to the GitHub repository homepage. Rejected because it is less direct for readers who want immediate documentation.

### Keep the added help text short and stable
The added wording should be a brief sentence or epilog-style note, not a large prose block.

Rationale:
- Root help needs to remain scannable in terminals.
- A short stable link is less fragile across different terminal widths and Click help formatting.

Alternative considered:
- Add multiple links or a longer getting-started paragraph. Rejected because it adds noise to a surface operators use for quick command discovery.

## Risks / Trade-offs

- [Help output becomes noisier] → Mitigation: keep the wording to one short line and one URL.
- [The published docs URL changes later] → Mitigation: treat the URL as one explicit maintained CLI constant or literal and update it alongside docs-site changes.
- [Readers may expect subcommand-specific links too] → Mitigation: scope this change to the top-level discovery path only; deeper help refinements can be proposed separately if needed.
