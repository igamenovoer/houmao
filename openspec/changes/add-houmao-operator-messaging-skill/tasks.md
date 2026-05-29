## 1. Skill Asset

- [x] 1.1 Create `src/houmao/agents/assets/system_skills/houmao-operator-messaging/` with a concise `SKILL.md` that declares manual-only activation and the `help`, `clarify`, and `dispatch` subcommands.
- [x] 1.2 Add routed guidance pages for `clarify` and `dispatch` so the entrypoint stays concise while the subcommands cover clarification records, packet planning, route selection, and blocking behavior.
- [x] 1.3 Ensure the new skill delegates direct prompts to `houmao-agent-messaging`, mailbox dispatch to `houmao-agent-email-comms`, and durable orchestration requests to the loop skills without depending on agent-loop internals.

## 2. Catalog Integration

- [x] 2.1 Add `houmao-operator-messaging` to the packaged system-skill catalog with `asset_subpath = "houmao-operator-messaging"`.
- [x] 2.2 Add `houmao-operator-messaging` to the existing `core` and `all` sets without adding a new named set.
- [x] 2.3 Update catalog and command test fixtures that assert catalog order, core/all membership, default resolved skills, and installed skill projections.

## 3. Contract Coverage

- [x] 3.1 Add unit coverage that the new skill asset is packaged and installed by default for managed launch/join and CLI-default selection.
- [x] 3.2 Add unit coverage for the operator messaging `SKILL.md` contract: manual-only activation, read-only help, no single/multi subcommands, `clarify`, `dispatch`, and lower-level skill boundaries.
- [x] 3.3 Add unit coverage for subcommand guidance: `clarify` must not dispatch and must require an explicit Markdown path for external records; `dispatch` must plan packets, delegate delivery, apply mailbox identity rules, and block instead of inventing missing runtime facts.
- [x] 3.4 Update concise docs or overview references only where current system-skill documentation lists packaged Houmao skills.

## 4. Verification

- [x] 4.1 Run focused tests for system-skill catalog, installation, and new operator messaging skill asset coverage.
- [x] 4.2 Run `pixi run lint` or the smallest equivalent lint target needed for changed Python and Markdown-facing tests.
- [x] 4.3 Run `openspec status --change add-houmao-operator-messaging-skill` and confirm the change is apply-ready.
