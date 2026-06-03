## Context

`houmao-mgr` now exposes managed-agent operations through explicit scope groups: `agents global`, `agents single`, `agents self`, and `agents external`. Packaged system skills are executable guidance for agents, so stale command snippets there become direct runtime failures. The latest audit found three concrete command-shape mismatches: root-level `agents join`, root-level `agents memory`, and `mail move --box`. It also found leftover command-template prose after the command-template renderer was retired.

Two complete but still-active OpenSpec changes are relevant context. `retire-command-templates` already removed the runtime command-template surface and converted most skill guidance to direct commands. This change is a follow-up correctness pass over the surviving stale guidance and the spec contracts that would otherwise preserve old command shapes.

## Goals / Non-Goals

**Goals:**

- Make packaged system skills teach only the current `houmao-mgr` command shapes for join, memory, and mail move.
- Keep current-session and selected-agent memory operations distinct: `agents self memory ...` for the current session, `agents single --agent-name|--agent-id ... memory ...` for another local managed agent.
- Remove remaining generic command-template references from packaged skills so executable commands are represented as direct shell snippets or prose, while YAML authoring remains under `internals config-drafts`.
- Add tests that catch reintroduction of the stale command families and stale option names.

**Non-Goals:**

- No new `houmao-mgr` subcommands or compatibility aliases.
- No revival of `internals command-templates`.
- No changes to config-draft behavior.
- No behavioral changes to mailbox, memory, join, gateway, or lifecycle command implementations.

## Decisions

1. Treat skill guidance as the source being fixed, not the CLI.

   The live CLI already exposes `agents self join`, scoped `agents single|self memory`, and `mail move --destination-box`. The implementation should edit packaged skill assets and tests around those existing surfaces instead of adding shims for removed command shapes.

2. Use direct command snippets for executable flows.

   Command-template retirement intentionally split executable command spelling from YAML config authoring. The skill files should hard-code concise `bash` command blocks for concrete CLI workflows and should reserve `internals config-drafts generate` only for supported YAML draft generation.

3. Preserve scope language in memory guidance.

   The old `houmao-mgr agents memory ...` shorthand hides an important authority boundary. The corrected skill should explain that current-session memory may use environment paths or `agents self memory ...`, while another managed agent requires `agents single --agent-name|--agent-id ... memory ...`.

4. Validate drift with content tests plus CLI help checks.

   Content tests should assert that packaged skills do not include the removed `houmao-mgr agents join`, `houmao-mgr agents memory`, `mail move --box`, or command-template wording. Focused CLI checks should confirm that the replacement command paths and options exist in the current Click command graph.

## Risks / Trade-offs

- Stale active OpenSpec deltas may overlap this change while `retire-command-templates` remains unarchived. Mitigation: keep this proposal focused on the surviving drift and make the tasks validate against the current working tree and current CLI shape.
- Direct command snippets can drift again as the CLI evolves. Mitigation: add tests that scan packaged skill assets for retired command families and stale options.
- Legacy loop skills are retired but still packaged under `legacy/`. Mitigation: update their routing prose only where it names removed memory command shapes, without reopening their broader workflow design.
