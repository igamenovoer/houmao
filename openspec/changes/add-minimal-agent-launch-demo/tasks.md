## 1. Demo Surface

- [ ] 1.1 Replace `scripts/demo/README.md` with a supported demo index that lists the new minimal demo and keeps `legacy/` labeled as archived reference material.
- [ ] 1.2 Add `scripts/demo/minimal-agent-launch/inputs/agents/` with the canonical minimal tracked layout: empty `skills/`, shared `roles/minimal-launch/`, Claude and Codex presets, and secret-free tool setup assets.
- [ ] 1.3 Add tracked tutorial inputs and the tutorial markdown under `scripts/demo/minimal-agent-launch/` in the repo's program-tutorial style.

## 2. Runnable Workflow

- [ ] 2.1 Implement the demo run script that stages a generated working tree under the demo output root and preflights provider-specific prerequisites.
- [ ] 2.2 Implement provider-specific local auth aliasing so the generated working tree symlinks demo-local `default` auth to the appropriate fixture auth bundle for Claude or Codex.
- [ ] 2.3 Implement the headless launch, prompt, state inspection, and stop flow for the shared `minimal-launch` selector, with command artifacts written under the demo outputs area.
- [ ] 2.4 Make the demo fail clearly before launch when the selected provider's fixture auth bundle is missing.

## 3. Docs And Verification

- [ ] 3.1 Update the getting-started docs to point readers from the canonical agent-definition and quickstart pages to `scripts/demo/minimal-agent-launch/` as the supported runnable example.
- [ ] 3.2 Run the supported demo for both `claude_code` and `codex`, then tighten the tutorial verification and troubleshooting guidance to match the observed outputs and failure modes.
