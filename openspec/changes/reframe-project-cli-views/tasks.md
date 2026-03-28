## 1. Reshape The Project CLI Foundation

- [ ] 1.1 Replace the top-level `houmao-mgr project` subtree wiring so the supported public surface exposes `agents`, `easy`, and `mailbox` instead of `agent-tools`.
- [ ] 1.2 Keep `project init` and `project status` working while ensuring `project init` does not create `.houmao/mailbox/` or `.houmao/easy/` by default.
- [ ] 1.3 Add shared project helpers for resolving the discovered project overlay, the canonical `.houmao/agents/` root, and the project mailbox root at `.houmao/mailbox/`.

## 2. Implement `project agents` Low-Level Source Management

- [ ] 2.1 Move the existing project tool auth flow under `houmao-mgr project agents tools <tool> auth ...` without changing the underlying auth bundle storage contract.
- [ ] 2.2 Add `houmao-mgr project agents tools <tool> get` plus `setups list|get|add|remove` for project-local tool inspection and setup bundle cloning.
- [ ] 2.3 Implement `houmao-mgr project agents roles list|get|init|scaffold|remove`, including role enumeration that sees prompt-only roles.
- [ ] 2.4 Implement `houmao-mgr project agents roles presets list|get|add|remove`, writing canonical preset files under `roles/<role>/presets/<tool>/<setup>.yaml`.

## 3. Implement `project easy` Specialist And Instance UX

- [ ] 3.1 Add project-local `easy` metadata storage under `.houmao/easy/specialists/` plus typed specialist metadata loaders/renderers.
- [ ] 3.2 Implement `project easy specialist create`, compiling prompts, auth bundles, copied skills, and default presets into the canonical `.houmao/agents/` tree.
- [ ] 3.3 Implement `project easy specialist list|get|remove`, preserving shared auth bundles and shared skills when one specialist is removed.
- [ ] 3.4 Implement `project easy specialist launch` with derived provider mapping and `project easy instance list|get` as a view over existing managed-agent runtime state.

## 4. Extend Mailbox Operations And Add `project mailbox`

- [ ] 4.1 Extend the generic `houmao-mgr mailbox` CLI with `accounts list|get` over mailbox registrations.
- [ ] 4.2 Extend the generic `houmao-mgr mailbox` CLI with `messages list|get` for direct read-only mailbox inspection by selected mailbox address.
- [ ] 4.3 Add `houmao-mgr project mailbox ...` as a project-root wrapper over the generic mailbox operations, automatically targeting `<project>/.houmao/mailbox`.
- [ ] 4.4 Keep `houmao-mgr agents mailbox ...` separate as the managed-session mailbox-binding surface and verify the new project mailbox wrapper does not change that boundary.

## 5. Add Focused Tests

- [ ] 5.1 Update project CLI help and project-init tests to cover the new `project agents`, `project easy`, and `project mailbox` surfaces.
- [ ] 5.2 Add low-level project role/tool tests for `project agents roles ...` and `project agents tools ...`, including setup cloning and auth CRUD under the renamed namespace.
- [ ] 5.3 Add `project easy` tests covering specialist compilation, copied skills, derived provider launch mapping, and instance view behavior.
- [ ] 5.4 Add mailbox tests covering `mailbox accounts ...`, `mailbox messages ...`, and parity between `mailbox ... --mailbox-root <path>` and `project mailbox ...` against `.houmao/mailbox`.

## 6. Update Documentation And Planning Artifacts

- [ ] 6.1 Update getting-started docs to teach `project easy specialist create ...` as the primary project-local authoring path and `project agents ...` as the low-level maintenance surface.
- [ ] 6.2 Update CLI reference docs to describe the revised `houmao-mgr project` tree, the nested `project agents`, `project easy`, and `project mailbox` families, and the expanded generic mailbox CLI.
- [ ] 6.3 Mark the older `add-project-role-and-tool-management-cli` direction as superseded in planning and implementation notes so future work follows this change instead of the old namespace model.
