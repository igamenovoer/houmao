## Context

Houmao currently exposes four mailbox-related top-level system skills:

- `houmao-process-emails-via-gateway`
- `houmao-email-via-agent-gateway`
- `houmao-email-via-filesystem`
- `houmao-email-via-stalwart`

Only one of those skills is actually workflow-oriented: `houmao-process-emails-via-gateway` defines how to process one notifier-driven unread-mail round. The other three all describe ordinary email communication work and repeat the same routing contract:

- use prompt-provided `gateway.base_url` when available,
- otherwise resolve current bindings through `houmao-mgr agents mail resolve-live`,
- prefer shared `/v1/mail/*` when a live gateway facade exists,
- fall back to transport-local guidance when it does not,
- treat `message_ref` and `thread_ref` as opaque,
- mark mail read only after successful work.

That split leaks into the packaged catalog, runtime mailbox-skill projection constants, notifier prompt copy, `houmao-agent-messaging` delegation, and tests. As a result, one conceptual change to ordinary email operations requires edits across multiple top-level skill packages and all of the code that advertises them.

## Goals / Non-Goals

**Goals:**

- Provide one installed Houmao-owned skill, `houmao-agent-email-comms`, as the ordinary mailbox communication entrypoint.
- Keep `houmao-process-emails-via-gateway` separate as the workflow skill for notifier-driven rounds.
- Move gateway-specific and transport-specific operational details into internal pages of `houmao-agent-email-comms` instead of separate top-level installed skills.
- Update runtime projection, mailbox prompts, installer inventory, and skill-to-skill delegation so they advertise the new two-skill mailbox surface consistently.
- Preserve the actual mailbox API and resolver contracts while simplifying skill packaging and discovery.

**Non-Goals:**

- Change the semantics of `/v1/mail/*`, `houmao-mgr agents mail ...`, or mailbox transport bindings.
- Merge round-processing workflow into the ordinary mailbox skill.
- Add backward-compatibility wrappers that keep the removed top-level skill names available.
- Redesign mailbox transports, notifier scheduling, or mailbox data models.

## Decisions

### 1. Replace the three ordinary mailbox skills with one installed skill

The system will replace `houmao-email-via-agent-gateway`, `houmao-email-via-filesystem`, and `houmao-email-via-stalwart` with one installed skill named `houmao-agent-email-comms`.

Rationale:

- The three legacy skills differ mostly in supporting detail, not in the core operator flow.
- A single entrypoint makes mailbox discovery simpler for both agents and runtime-generated prompts.
- The runtime and tests only need to advertise one ordinary mailbox skill name.

Alternatives considered:

- Keep the three legacy skills and add an umbrella index skill.
  Rejected because the duplicated routing rules and runtime references would remain.
- Keep the three skills and rename only the gateway skill.
  Rejected because transport-specific top-level skills would still fragment ordinary mailbox work.

### 2. Keep `houmao-process-emails-via-gateway` as a separate workflow skill

The round-oriented notifier workflow remains a distinct installed skill. It will delegate ordinary mailbox operations to `houmao-agent-email-comms` when the round needs exact operational guidance.

Rationale:

- The processing skill is about bounded wake-up rounds, triage, selection, and stop-after-round discipline.
- Ordinary mailbox operations are reusable outside notifier rounds.
- Combining both concerns would make the ordinary skill harder to scan and the workflow skill easier to misuse as a generic operations reference.

Alternatives considered:

- Merge the workflow into `houmao-agent-email-comms`.
  Rejected because workflow semantics and basic operations have different triggers and guardrails.

### 3. Internalize gateway and transport detail as subpages of the unified skill

`houmao-agent-email-comms` will expose ordinary mailbox behavior through internal action and reference pages instead of separate installed skill packages.

Planned internal layout:

- `actions/resolve-live.md`
- `actions/status.md`
- `actions/check.md`
- `actions/read.md`
- `actions/send.md`
- `actions/reply.md`
- `actions/mark-read.md`
- `transports/filesystem.md`
- `transports/stalwart.md`
- shared references for gateway routes, fallback surfaces, and resolver fields

Rationale:

- The internal page split preserves focused guidance without multiplying installed skill names.
- Transport-specific guidance still has a clear home.
- Existing gateway and transport reference material can be moved with minimal semantic change.

Alternatives considered:

- Flatten everything into one long `SKILL.md`.
  Rejected because the resulting document would be too dense and would bury transport-local guidance.
- Keep separate installed transport skills but nest them under a mailbox namespace.
  Rejected because the user goal is to unify ordinary email communication under one skill surface.

### 4. Project only two mailbox skills at the top level

Mailbox-enabled sessions will project these top-level Houmao-owned mailbox skills:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`

No top-level installed skill directories will remain for `houmao-email-via-agent-gateway`, `houmao-email-via-filesystem`, or `houmao-email-via-stalwart`.

Rationale:

- The visible mailbox surface becomes stable across transports.
- Runtime projections, notifier prompts, and installer inventory all become simpler.
- Transport differences move into resolver-driven branching inside the unified skill.

Alternatives considered:

- Keep transport-specific top-level skills as aliases.
  Rejected because it preserves duplicate discovery surfaces and prolongs the split contract.

### 5. Keep mailbox set names stable while simplifying their contents

The packaged mailbox set names can remain `mailbox-core` and `mailbox-full`, but both sets will resolve to the current two-skill mailbox selection.

Rationale:

- This avoids unrelated CLI churn around set names while still simplifying the installed skill inventory.
- The real user-facing change is the skill surface, not the set labels.

Alternatives considered:

- Remove `mailbox-full`.
  Rejected for now because it creates extra operator-facing breakage without adding architectural value.

### 6. Update every runtime-owned prompt and delegation path to the new skill names

The following surfaces will be updated to reference `houmao-agent-email-comms`:

- `houmao-agent-messaging` mailbox delegation
- notifier wake-up supporting-material guidance
- mailbox help or command guidance emitted by manager-backed surfaces
- runtime mailbox-skill constants and projected references
- packaged catalog inventory and tests

Rationale:

- The value of unification is lost if any system-owned prompt still points agents at removed skill names.
- Centralizing the skill names in runtime constants reduces future drift.

## Risks / Trade-offs

- [Operator or agent prompts still reference removed skill names] → Update runtime-generated guidance, tests, and demos in the same change; treat stale references as failures.
- [The unified skill becomes too large] → Keep a strict internal action/reference structure and route the reader to one page at a time.
- [Transport-specific nuance becomes less visible] → Reserve dedicated `transports/` pages and keep transport-specific references explicit from the entry document.
- [Keeping both mailbox set names may look redundant] → Accept short-term redundancy to reduce CLI churn; revisit set simplification in a later cleanup if it becomes confusing.

## Migration Plan

1. Add the new `houmao-agent-email-comms` skill package and define its internal page structure.
2. Update mailbox runtime constants, projected references, and packaged catalog entries to treat `houmao-agent-email-comms` as the ordinary mailbox skill.
3. Update `houmao-process-emails-via-gateway`, `houmao-agent-messaging`, and runtime-generated notifier/mail guidance to reference the unified skill.
4. Update system-skill installation/reporting behavior and tests to use the new mailbox inventory.
5. Remove the legacy top-level skill packages and any remaining references to their names.

Rollback strategy:

- Reintroduce the legacy catalog entries and runtime constants, then restore the old skill packages, if the unified skill proves incomplete before the change is archived.

## Open Questions

- None for the proposal phase. The change intentionally keeps mailbox set names stable and treats the top-level skill-name replacement as the primary breaking surface.
