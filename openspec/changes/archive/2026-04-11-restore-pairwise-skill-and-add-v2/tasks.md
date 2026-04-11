## 1. Restore the stable pairwise skill

- [x] 1.1 Replace the current `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise/` asset tree with the pre-rewrite stable pairwise skill content.
- [x] 1.2 Align the restored stable pairwise `SKILL.md`, packaged prompt metadata, and operating pages with the manual-invocation-only `start|status|stop` contract.

## 2. Create the versioned enriched pairwise skill

- [x] 2.1 Copy the current enriched pairwise asset tree to `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v2/`.
- [x] 2.2 Rename internal skill identifiers, descriptions, prompts, and asset references so the copied tree consistently exposes `houmao-agent-loop-pairwise-v2` as a manual-invocation-only skill.

## 3. Expose both skills through catalog, install, and docs surfaces

- [x] 3.1 Update the packaged system-skill catalog, `user-control` set membership, and installer-facing expectations so both pairwise skills resolve through default set expansion.
- [x] 3.2 Update README, getting-started, and CLI system-skills docs to distinguish the restored stable pairwise skill from `houmao-agent-loop-pairwise-v2`.

## 4. Refresh verification coverage

- [x] 4.1 Update catalog-driven system-skill, projected-home, and brain-builder tests to assert both pairwise skill variants and their packaged content.
- [x] 4.2 Run targeted verification for the catalog, projected install, and system-skills CLI flows after the split is implemented.
