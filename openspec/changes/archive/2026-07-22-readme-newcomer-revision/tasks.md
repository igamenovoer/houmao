## 1. Prepare the Relocation Target

- [x] 1.1 Read `docs/getting-started/system-skills-overview.md` and map which README System Skills prose (pack membership resolution, actor entrypoint selection, bypass routes, ownership config, compatibility aliases, install lifecycle) is already covered there and which must be merged in.
- [x] 1.2 Merge the README-only System Skills detail into `docs/getting-started/system-skills-overview.md`, rewriting overlapping passages rather than appending duplicates; prefer the newer README wording where they conflict.

## 2. Rewrite README.md Narrative (before Quick Start)

- [x] 2.1 Rewrite the opening: keep the title/one-liner and the name-origin story as standalone brand narrative (no metaphor-to-concept mapping, no "strands"/"clones" synonyms for `specialist`/`managed agent`), then "What It Is" with every concept defined in a plain clause at first use, keeping the mandated provider ordering and Copilot qualifier.
- [x] 2.2 Expand "Why This Design" from bullets into short rationale paragraphs: real CLI processes over in-process objects, no central orchestrator (gateways + mailboxes instead), full provider capability, scaling from one helper to generated teams. Keep each sentence ≤ ~30 words.
- [x] 2.3 Rewrite "Architecture at a Glance" as a walkthrough: narrate the existing team diagram (~15 lines) and add a second conceptual mermaid diagram of one managed agent's anatomy (provider CLI in tmux, gateway sidecar, mailbox identity, memory directory), with no CLI syntax in either diagram.
- [x] 2.4 Verify the pre-Quick-Start prose stays within ~60 lines with subheadings (spec budget).

## 3. Rewrite README.md Quick Start and Later Sections

- [x] 3.1 Add a prerequisites block (Python 3.11+ with `uv`, `tmux`, Linux or macOS, `npx` for the preferred installer) at the start of Quick Start.
- [x] 3.2 Restructure Quick Start to the single golden path (install, `command -v tmux`, `npx skills add …`, start CLI agent, `$houmao-admin-welcome start-guided-tour`) with a one-line expected outcome per step; reduce pinned-tag, `houmao-mgr system-skills install` variants, explicit-home, and copy-paste installs to one-sentence doc pointers.
- [x] 3.3 Add the one-sentence explanation of `$houmao-*` skill invocation syntax at its first occurrence, and close Quick Start with the first `You:`/`AI:` exchange inline (create reviewer specialist → launch → review), framed so `$houmao-admin-welcome start-guided-tour` reads as the one invocation to remember. Source material: `imsight-design/usecases/uc-01-first-managed-agent.md` (Event 001), condensed to fit the golden-path flow. The inline first exchange shows the explicit `$houmao-admin-entrypoint` invocation (first-prompt pattern), and later natural-language prompts include the keyword `houmao` (`imsight-design/adrs/0001-entrypoint-first-prompt-houmao-keyword.md`).
- [x] 3.4 Trim the later "Agent-Driven Examples" section to the gateway-interaction example only (no duplication of the Quick Start exchange), using `imsight-design/usecases/uc-02-operator-coordinated-team.md` as source; align the Agent Loops exchange with `imsight-design/usecases/uc-03-pro-agent-loop-run.md`. Keep the Core Concepts table and Agent Loops section structure; split all prose sentences over ~30 words and replace jargon nouns (`posture`, `surface` as a noun, `credential lane`, `pack closure`, `turn evidence`) with concrete wording without dropping facts.
- [x] 3.5 Collapse the System Skills section to the six-skill table (welcome first, labeled as the starting skill) plus one short actor-model paragraph (≤ ~15 prose lines) linking to the System Skills Overview and CLI reference.
- [x] 3.6 Caption the writer-team demo video link with a sentence stating what it shows.
- [x] 3.7 Add a license line/section matching the repository's actual license (check `LICENSE`/`pyproject.toml` first).
- [x] 3.8 Update the Kimi Code role-prompt note to match maintained 0.23.x guidance (managed bootstrap / `houmao-auto-system-prompt` projection, manual invocation when not confirmed loaded).

## 4. Verify

- [x] 4.1 Diff the new README against the old and confirm no factual claim was dropped (each removed fact lives in the README or a directly linked doc).
- [x] 4.2 Verify every docs link in the revised README resolves, and grep `docs/` for inbound links to README anchors that may have changed.
- [x] 4.3 Check the revised README against every ADDED/MODIFIED scenario in `specs/readme-structure/spec.md` (narrative-before-Quick-Start budget, brand-not-vocabulary, anatomy diagram, define-before-use, golden path with outcomes, welcome primacy, prerequisites, sentence limit, `$` syntax, captioned media, license, System Skills conciseness, Kimi guidance, touring references gone).
- [x] 4.4 Run the docs build or lint step (`pixi run docs-serve` build path, or markdown lint if configured) to confirm the rewritten README renders cleanly, including both mermaid diagrams.
