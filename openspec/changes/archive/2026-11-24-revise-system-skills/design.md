# Design

## Context

The package publishes six complete standalone roots. Both actor entrypoints route ordinary work through the `houmao-shared-routines` sibling, which owns the canonical child trees under `subskills/`. The existing `access` and `files` manager commands provide the required runtime capabilities. The system-skills catalog comes from `manifest.toml`, while separate Markdown route tables and help guide the agent. [Skill manifest](../../../src/houmao/agents/assets/system_skills/manifest.toml) · [Authorization Policy](../../../docs/reference/gateway/operations/authorization-policy.md) · [File Edits](../../../docs/reference/gateway/operations/versioned-file-edits.md)

## Goals / Non-Goals

Give the two new routines their own resource boundaries and update the existing routines that hand off to them. Limit executable changes to the packaging, manifest, version validation, and catalog paths needed to ship and diagnose the revised collection. Apply the unit-test policy to the current packaged system skills. Development skills, retired migration assets, project-authored skills, and generated skill templates have separate lifecycles.

## Decisions

### Give Access and File Edits Separate Owners

Use direct `houmao-agent-access` and `houmao-agent-files` children with `SKILL-MAIN.md`, a concise numbered workflow, read-only help, a planning fallback, and operation-specific command pages. Give the parents one distinguishing route sentence per child. This keeps authorization resources usable for gateway operations other than file edits and gives the file workflow room for its lease, revision, and receipt references. A single gateway command group would require lifecycle callers to traverse policy and draft procedures they rarely need.

Use `provision()`, `policy()`, `admin-roster()`, `peer-identity()`, and `request()` as peer routines for `agent-access`. Teach how to verify an execution owner for retained policy changes and source-signer configuration. Reserve live roster changes for the supported signer and proof path. A verified managed peer can export public identity and call a separately selected target with its configured signer. Access context names the workflow lane, while the executable checks decide permission. [Authorization owner and peer workflows](../../../docs/reference/gateway/operations/authorization-policy.md#owner-and-effect-boundaries)

Use procedural `discover()`, `inspect()`, `edit-draft()`, `publish()`, and `reconcile()` pages for `agent-files`, with shared signer and lease facts in references. Discovery identifies the exact mount, resource, available actions, and base. Editing yields a saved candidate and releases the lease. Publishing uses that candidate and base, then returns an operation receipt for inspection. Keep CLI groups such as `lease open` inside the command examples. A skill invocation therefore needs one terminal parenthesized command, and implementation can use the existing one-level route resolution. [File workflow](../../../docs/reference/gateway/operations/versioned-file-edits.md#edit-and-save-a-draft)

### Keep Operational Guidance With the Existing Owners

- `agent-gateway` owns sidecar attachment, private deployment configuration, and `web-entry()`. Hand authorization setup or signed gateway requests to `agent-access`, and route mount reads and writes to `agent-files`. Treat a one-time browser link as a bearer secret. [Gateway CLI](../../../docs/reference/cli/agents-gateway.md#attach)
- `agent-instance` owns one-shot launch choices and a `native-resources()` command for native home, read-only freshness checks, and supported refresh. Explain current, pending, unknown, native settlement and next-use boundaries. Keep owner/native updates distinct from gateway-managed logical mounts. [Native refresh](../../../docs/reference/run-phase/native-refresh.md#workflow)
- `agent-definition` owns saved tmux choices for specialist-backed project profiles and recipe-backed project launch profiles. Use dedicated routes for the profile families and the separate native dossier workflow. `project-mgr` can hand profile requests to that owner. A one-shot explicit selector takes precedence over a saved choice. Use the launch fallback when neither supplies a choice, and use stored execution records to locate existing sessions. [Launch profiles](../../../docs/getting-started/launch-profiles.md#choosing-a-tmux-server)
- `agent-inspect` and `agent-messaging` use managed identity, records, and capabilities before tmux. `--agent-id` or `--agent-name` selects the peer, while port flags select a transport endpoint on supported commands. Inspect tracked TUI state through managed or gateway evidence and use the recorded owner socket plus exact target for explicit or necessary local pane access. Ordinary mail addressing and the maintained direct-prompt lane retain their gateway-independent paths. [Screen workflow](../../../src/houmao/agents/assets/system_skills/public/houmao-shared-routines/subskills/houmao-agent-inspect/commands/screen.md#workflow) · [Mail send workflow](../../../src/houmao/agents/assets/system_skills/public/houmao-shared-routines/subskills/houmao-agent-email-comms/commands/send.md)

### Align the Catalog and Metadata With the Static Trees

Use the manifest’s child records as the inventory for validation, CLI listing, and doctor comparisons. Exact checks can compare direct child names and their entrypoint paths against the records. Keep the six public roots and the two pack memberships explicit. Use `mail` as the messaging command and retain `mail-handoff` as an alias. Add the already authored definition and instance commands to the machine-readable catalog. Remove the stale `project-mgr launch-profiles` operation from the executable inventory and teach the handoff to the owning definition route. Review Markdown route and help wording against the manifest. Package validation checks technical invariants such as filenames, links, metadata, and declared route structure. [Current command declarations](../../../src/houmao/agents/assets/system_skills/manifest.toml)

Put `metadata.skill_invocation_notation` in every current entrypoint and active instruction page using object designators. Use `metadata.houmao_version` only on the six standalone roots, with a quoted release value. Change the package and version readers alongside the assets, including doctor and source, wheel, sdist, and release checks. Retain separate machine-readable release values in CLI and lifecycle records. Parsing nested YAML gives one canonical location for each key and supports the standard Agent Skills metadata envelope. [Notation validation](../../../src/houmao/agents/system_skill_manifest.py#L965) · [Release-version checks](../../../src/houmao/agents/system_skill_version.py#L201)

### Test Asset Existence and Executable Behavior

Use a small structural test for expected roots, manifest-declared child entrypoints, and declared bundled paths. In build, join, and mailbox projection tests, assert the installed paths and keep their independent runtime assertions. Remove authored Markdown assertions for quoted commands, headings, help, routing, and guardrails. Remove the pre-compaction file inventory and semantic fixture once they have no consumers. Use review for the changed workflows, notation, guards, examples, and operation parity. [Current preservation test](../../../tests/unit/agents/test_system_skills.py#L306)

Keep inexpensive coverage of the manifest API, projection and ownership transactions, CLI output, doctor diagnostics, and generated prompt behavior. Byte identity and digest tests verify the installed bytes as a product property. Parser tests can synthesize frontmatter to exercise metadata outcomes. These checks compare data and observable behavior, so they are independent of the wording of any shipped instruction.

## Risks / Trade-offs

- Router, manifest, and help edits can leave a new workflow reachable in one posture only. Review the two actor route tables and `system-skills list` together. Include explicit peer targeting and the execution-owner boundary in example requests.
- A missing reply after a push can tempt a caller to retry. Give `reconcile()` a concrete example that uses the original operation ID, including a response with incomplete native activation evidence.
- Removing prose assertions shifts the responsibility for clear instructions to review. Review command shapes against source `--help` or the existing runtime docs and use the standard skill validator when verifying the changed distribution.

## Migration Plan

Update the metadata readers, assets, and release checks in the same build. Use the normal `system-skills doctor` and explicit upgrade flow for manager-owned installations. Replace complete roots through the original installation tool for externally installed packs. A root carrying only the previous top-level version can report missing canonical metadata until upgraded. Retain the existing content integrity, user ownership, and conflict rules for pack replacement.
