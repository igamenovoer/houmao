# Brain Launch Runtime: Open Questions Discussion

Date: 2026-02-27

This note collects the unresolved questions for the `agent-brain-launch-runtime` change and frames the decision surface (options, trade-offs, and what we need to specify). It is intended to help converge on crisp decisions that can be captured back into [design.md](../design.md) and (where relevant) [spec.md](../specs/brain-launch-runtime/spec.md).

## Scope

This discussion focuses on:

1. Non-CAO interactive session scope beyond Codex.
2. CAO runtime profile generation lifecycle (naming, stability, cleanup).
3. Session metadata (“session manifest”) requirements for audit/resume.
4. CAO REST semantics and env isolation strategy details needed for implementation.
5. Cross-change coordination to avoid duplicating the CAO REST client (notably with `agent-team-orchestration-runtime`).

## Open Questions (Explicit in design.md)

### 1) Minimum viable scope for non-Codex interactive sessions (PTY vs MCP stdio)?

Why this matters:

- This choice affects the shape of the core `InteractiveSession` abstraction (what operations are supported, what guarantees exist about replies, and how “structured” interactions are).
- It also determines what we can reasonably test hermetically.

Decision options:

1. **Stdio persistent-process backend(s)**: long-lived subprocess controlled over stdio (e.g., JSON-RPC over stdio like `codex app-server`, or other stdio protocols).
2. **Headless CLI backend(s)**: repeated one-off CLI calls with structured output (JSON/JSONL), using tool-supported resume/continue mechanisms to maintain conversational state across invocations when available.
3. **REST/HTTP backend(s)**: sessions controlled via a typed Python REST client (e.g., CAO REST), where “statefulness” is maintained server-side.

> DECISION: For non-Codex interactive sessions, do not consider PTY/terminal-scraping backends for now. Only consider stdio patterns (both long-lived subprocess protocols and repeated headless CLI calls) and REST/HTTP calls from Python. Design the runtime so that each backend is implemented as its own class (or class family) behind core interfaces, to keep extensibility clean.

> DECISION: `InteractiveSession` must support streaming output so callers can observe progress and decide to terminate a backend task early. The core interface should include an explicit interrupt/terminate capability (e.g., send an interruption keystroke like ESC/Ctrl-C when applicable, or kill the underlying subprocess) rather than requiring the caller to wait for a full request/response completion.

> DECISION: This change explicitly includes three non-CAO backends: (1) Codex app-server (long-lived process), (2) Claude headless (`claude -p` + `--resume <session_id>`), and (3) Gemini headless (`gemini -p` + `--resume <session_id>`). Session continuity is logical: headless backends may spawn a fresh process per turn while preserving context via persisted `session_id`.

What to clarify:

1. Do we model “tool-native system prompt injection” generically, or keep it adapter-specific?

> DECISION: Role/system prompt injection is backend-specific. Each backend uses its own native mechanism when available; otherwise fall back to sending the role text as the first user message (clearly delimited) before the first real user prompt.

### 2) Should generated CAO profiles be stable per role or unique per session?

Why this matters:

- CAO REST has no “create profile” endpoint; we’re writing Markdown profiles into CAO’s local agent store path.
- Profile naming and update strategy impacts reproducibility, concurrency safety, and store hygiene.

Decision options:

1. **Stable per role**: One file per role name (overwritten).
   - Pros: predictable, minimal clutter.
   - Cons: weaker auditability; concurrent launches can race; “role changed” can silently alter active behavior.
2. **Unique per session**: One file per launched session (append-only).
   - Pros: strong auditability; avoids overwrites/races.
   - Cons: store growth; requires cleanup strategy and mapping from session to profile.
3. **Stable per role + content hash**: Deterministic name derived from `{role_name, hash(role_prompt)}`.
   - Pros: reproducible; avoids overwriting across content; reduces duplicates.
   - Cons: still accumulates if role evolves frequently; still needs cleanup policy eventually.

> DECISION: Generated CAO profiles should be unique per session (append-only). Treat git-tracked role prompts as templates: session-specific context may be represented by prepending/appending additional text to the standard role text and/or by altering parameterizable strings inside the role prompt per session. This implies profile identity must be bound to the session (not just role name).

> DECISION: Profile naming schema is `<role_name>_<timestamp>_<uuid4hex>`. Cleanup is manual (no automatic GC).

What to specify:

1. Naming scheme (allowed characters, max length, collision policy).
2. Cleanup policy (explicit `cleanup` command, time-based GC, or “never cleanup” acceptable for dev use).

### 3) Do we need an explicit “session manifest” alongside the existing brain manifest for audit/resume?

Why this matters:

- The brain manifest describes “what was built” (home, tool, config), but not “what is running” (backend, PID, CAO terminal IDs, where the transcript is, how to reconnect).
- The runtime proposal includes “start session / send prompt / stop session”; without persisted session identity, those commands either require the caller to keep state in-memory or re-discover state in ad hoc ways.

Decision options:

1. **Yes (recommended)**: Write a small session handle file (JSON/YAML) with enough fields to resume/stop/audit.
2. **No**: Keep everything ephemeral; the CLI requires explicit IDs/paths passed around by the user.

> DECISION: Yes. Persist a session manifest JSON (session handle) alongside the brain manifest to support audit/resume/stop without requiring in-memory state.

> DECISION: All runtime-generated structured manifest/config artifacts are schema-validated on write and on read/resume. JSON Schema files are stored under the runtime package in `src/gig_agents/.../schemas/`.

What to align with:

- `agent-team-orchestration-runtime` already sketches a `controller/session.json` “runtime-to-CAO binding” handle concept. If we choose to create a session handle here too, we should consider a compatible shape and naming scheme to avoid two competing patterns.

What to specify (minimum viable):

1. Backend type (`codex_app_server` vs `cao_rest`).
2. Connection identity (PID + working dir, or CAO base URL + session/terminal IDs).
3. Role identity (role name + role content hash, if we care about reproducibility).
4. Paths to artifacts (brain home path, transcript/snapshot paths).

Additional clarification for this change:

5. Headless reconnect identity (`session_id`) and resume invariants (for Gemini: same working directory/project context).
6. Role bootstrap status for headless sessions to avoid replaying initial role text on resumed turns.
7. Schema version + schema file mapping for each generated artifact so write/read validation is deterministic.

## Open Questions (Implicit / Underspecified)

### 4) CAO REST API semantics: “send prompt” and “fetch last reply” contract

Why this matters:

- Tasks propose “prompt send + last-reply fetch”, but the runtime needs a clear definition of “reply”:
  - Is “last output chunk” enough?
  - How do we know when the tool is idle/completed vs still generating?
  - What is the failure behavior (timeouts, retries, partial output)?

> DECISION: For CAO-managed agents, only send input when the terminal status is `idle` or `completed` (poll via `GET /terminals/{id}`); do not use CAO inbox semantics. Fetch output only after the request is fully processed (no “mid-generation” output consumption for this backend). Queueing/syncing/locking for concurrent callers is handled externally (outside CAO and outside this runtime). Default timeout is 15s. If the agent/tool returns an error, return it to the caller as an error message and let the caller decide how to proceed.

Key questions to answer:

1. Do we poll `/output?mode=last` until terminal state is `idle|completed`, or do we rely on “last output” only?
2. Do we need inbox semantics (queued delivery) here, or is direct input acceptable for single-agent sessions?
3. What are the default timeouts and error categories the caller can handle?

Coordination note:

- `agent-team-orchestration-runtime` also depends on a typed CAO REST client and discusses inbox semantics. It is likely beneficial to share a single CAO client implementation and agree on the primitives once.

### 5) CAO env isolation: which mode is the default, and what are the invariants?

Why this matters:

- The design lists two modes (“one tmux session per launched agent” vs “sequential spawn into shared session”), but supporting both still requires:
  - a default,
  - concurrency rules (can we launch two terminals concurrently without env races?),
  - documentation of constraints.

Decision options:

1. **Default to per-agent tmux session**: simplest mental model, strongest isolation; fewer race hazards.
2. **Default to shared session sequential spawn**: supports “team-like” grouping, but demands careful sequencing and makes concurrent launches tricky.

> DECISION: Use per-agent tmux sessions for CAO launches; never share a tmux session between agents.

What to specify:

1. Whether the runtime must support concurrent launches under CAO at all.
2. If yes, how we prevent env races (locking around spawn, per-agent session, or “no concurrency” documented constraint).

### 6) Credential sharing: what do we do when shared credentials imply shared local state?

Why this matters:

- The requirement says “credential profile sharing is permitted” (no locks). That’s about *policy*, but we still need to decide how to handle *practical* shared-state collisions (token caches, provider rate limits, home directory write contention).

Decision options:

1. **Silent**: do nothing; caller owns the consequences.
2. **Warn-only**: detect likely collision cases (same tool home path, same profile name) and log a warning without blocking.
3. **Documented constraints**: define “safe sharing” expectations (separate homes recommended, or “sharing credentials is fine but share-home is risky”).

> DECISION: Silent. The runtime does not attempt to detect or prevent shared-state collisions when credential profiles are reused; ensuring safe usage is the caller’s responsibility.

### 7) Shared CAO REST client across changes: how do we prevent duplication?

Why this matters:

- Both this change and `agent-team-orchestration-runtime` include “implement typed CAO REST client” tasks. Duplicating clients risks:
  - inconsistent timeouts and error handling,
  - divergent endpoint assumptions,
  - duplicated test scaffolding.

Decision options:

1. **Single shared client module** (recommended): a small `cao_rest_client` package used by both runtimes.
2. **Duplicate now, reconcile later**: faster in the short term, but likely costly.

> DECISION: Use a shared CAO REST client module used by both `agent-brain-launch-runtime` and `agent-team-orchestration-runtime`. Update the related change artifacts to reflect this so we do not implement/maintain two divergent clients.

What to specify:

1. Ownership and module location (where it lives under `src/gig_agents/`).
2. Minimal endpoint surface and types needed by both runtimes.

## Proposed “Decide Next” Checklist

If we want to unblock implementation with minimal churn, the highest-leverage decisions are:

1. Session handle/manifest: yes/no and minimum schema.
2. CAO profile lifecycle: stable vs per-session vs content-hash naming.
3. CAO env isolation default: per-agent tmux session vs shared session.
4. Shared CAO REST client: commit to one shared module or accept duplication explicitly.
