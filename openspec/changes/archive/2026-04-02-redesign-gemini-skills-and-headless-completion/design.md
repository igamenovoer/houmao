## Context

Houmao currently treats Gemini mailbox skills as installed under `.agents/skills/mailbox/...`, but runtime prompts and demos still leak file-path guidance into the model-facing contract. That creates two different concepts that are easy to confuse:

- the runtime-owned install destination in the Gemini home
- the prompt-visible skill usage contract for ordinary mailbox work

The recent Gemini wake-up investigation showed that path-based prompting makes the system brittle. The runtime can install mailbox skills correctly and still fail because prompts tell Gemini to open the wrong path or depend on a project-local mirror instead of the native Gemini skill surface.

Headless turn completion has a similar split. The runtime already persists durable per-turn artifacts such as `stdout.jsonl`, `stderr.log`, `process.json`, and `exitcode`, but detail/reporting flows can still prefer stale live posture over those terminal artifacts. In one-off tmux-backed headless turns, the real terminal boundary is the managed child process exiting, not the later moment when the idle shell redraws or when a higher-level status snapshot catches up.

This change is cross-cutting because it touches mailbox skill projection, Gemini prompt construction, headless runtime completion semantics, managed-agent detail reconciliation, and the maintained gateway-wakeup demo.

## Goals / Non-Goals

**Goals:**
- Make Gemini mailbox skills first-class native installed skills under `.agents/skills/` with top-level Houmao-owned names.
- Make ordinary Gemini runtime prompts invoke installed Houmao mailbox skills by name instead of instructing the model to open raw `SKILL.md` paths.
- Define tmux-backed native headless turn completion in terms of managed child-process exit and durable exit artifacts.
- Make managed-agent detail and demo verification trust durable terminal turn evidence over stale transient live posture.
- Update the supported Gemini gateway wake-up demo so it exercises the maintained runtime contract rather than a demo-only workaround.

**Non-Goals:**
- Redesign Codex or Claude mailbox skill contracts beyond any mechanical consistency updates that fall out of shared code changes.
- Remove the lower-level mailbox skill documents themselves; they remain the authored source of the installed skills.
- Redefine business-level task success as mere process exit; task success still requires the expected mailbox and file side effects.
- Preserve backward compatibility for the old Gemini mailbox namespace contract if that blocks the cleaner maintained design.

## Decisions

### 1. Gemini mailbox skills move to top-level Houmao-owned names under `.agents/skills/`

Gemini will stop using the extra `mailbox/` subtree for Houmao-owned mailbox skills. The maintained Gemini projection contract becomes:

- `.agents/skills/houmao-process-emails-via-gateway/`
- `.agents/skills/houmao-email-via-agent-gateway/`
- `.agents/skills/houmao-email-via-filesystem/`
- `.agents/skills/houmao-email-via-stalwart/`

Rationale:
- It matches the desired native Gemini skill posture more closely.
- It removes the mismatch between “install destination” and “prompt-visible usage path”.
- It keeps the Houmao-owned `houmao-...` namespace as the collision boundary instead of the extra `mailbox/` segment.

Alternatives considered:
- Keep `.agents/skills/mailbox/...` and just improve prompt wording.
  Rejected because it preserves the same split-brain design and keeps path-based prompting as the ordinary workflow.
- Keep both top-level and `mailbox/` mirrors indefinitely.
  Rejected as the maintained contract because it keeps ambiguity alive and increases test/documentation burden.

### 2. Ordinary Gemini mailbox prompts become name-based, not path-based

For maintained Gemini mailbox and notifier prompts, Houmao will instruct Gemini to use the installed Houmao mailbox skill by name, with the `houmao` prefix explicitly present in the prompt. Ordinary runtime prompts will not require opening `.agents/skills/.../SKILL.md` paths when the installed skill is already expected to exist.

Rationale:
- Native installed skills should be used through the tool’s native discovery model.
- Name-based prompting decouples prompts from local filesystem layout details.
- It prevents demos from depending on project-local skill mirrors to succeed.

Alternatives considered:
- Continue prompting Gemini to open known `SKILL.md` files directly.
  Rejected for maintained flows because it treats installed skills as documentation files instead of installed native capabilities.

### 3. Tmux-backed headless terminality is defined by child-process exit plus durable exit artifact

For native tmux-backed headless turns, the terminal event is the managed child process exiting and the runtime persisting that turn’s terminal artifact state, especially the exit-status artifact. Idle-shell recovery and tmux redraw remain inspectability concerns, not the terminality boundary itself.

Rationale:
- The headless turn is a one-off CLI execution, not a long-lived provider process.
- Exit status is the authoritative control boundary the runtime already owns.
- This removes races where a task is finished but higher-level detail still looks active because the shell has not yet settled.

Alternatives considered:
- Keep terminality tied to live detail / idle-shell readiness.
  Rejected because it is later, noisier, and weaker than the process-exit fact.

### 4. Managed-agent detail reconciles from durable turn evidence before stale live posture

Managed-agent headless detail will treat durable terminal turn artifacts as authoritative whenever they contradict stale live posture for the same turn. `can_accept_prompt_now` derives from authoritative active-turn absence plus terminal artifact evidence, not from whether tmux has visibly redrawn an idle shell.

`completion_source` remains optional metadata. Its absence does not block `completed` or `failed` status when exit status is already known.

Rationale:
- Callers need a stable answer about whether a headless turn is still running.
- Optional metadata should not prevent terminal-state reconciliation.

Alternatives considered:
- Require both terminal artifact evidence and optional completion metadata before marking a turn complete.
  Rejected because it makes successful turns look incomplete for no operational benefit.

### 5. The demo verifies settled pipeline completion, not the earliest observable side effect

The maintained Gemini gateway-wakeup demo will treat success as a combination of:
- expected file side effect,
- mailbox read-state side effect,
- settled gateway notifier completion evidence,
- settled headless terminal turn evidence.

Verification will wait for that pipeline to settle instead of snapshotting immediately after the file appears.

Rationale:
- It aligns the demo with the system contract rather than with incidental timing.
- It keeps the demo useful as a regression harness for the real runtime semantics.

## Risks / Trade-offs

- [Breaking Gemini mailbox skill paths] → Update the builder, prompt construction, docs, and tests together in one change so there is one maintained contract.
- [Gemini native skill resolution might differ across CLI versions] → Gate the maintained contract behind covered Gemini versions and add direct runtime/integration coverage for installed-skill invocation by name.
- [Top-level Houmao skill names could collide with user-authored skill names] → Reserve the `houmao-` prefix as the ownership boundary and keep user docs explicit about that namespace.
- [Process-exit terminality may be misread as task success] → Keep higher-level verification distinct: terminal headless turn status does not replace output-file or mailbox-success checks.
- [Joined or reused Gemini homes may contain old `mailbox/` layouts] → Rebuild or re-project managed Gemini homes under the new contract and fail clearly when prompt assumptions and installed skill layout disagree.

## Migration Plan

1. Change Gemini mailbox skill projection to top-level Houmao-owned paths under `.agents/skills/`.
2. Update runtime prompt construction so maintained Gemini mailbox prompts use Houmao skill names rather than raw skill paths.
3. Update headless runtime reconciliation and managed-agent detail to finalize terminal turn state from child-process exit and durable artifacts.
4. Update the single-agent gateway wake-up demo verification flow and fixtures to rely on the new Gemini skill and headless completion contracts.
5. Update docs and tests in the same change so the maintained contract is unambiguous.

Rollback is straightforward during development: revert the contract change and return Gemini to the prior namespaced prompt/path model. Because the repository explicitly allows breaking changes during active development, the preferred rollout is one coherent switch rather than a long dual-contract period.

## Open Questions

- Should Houmao keep a short-lived compatibility reader or projection shim for preexisting Gemini homes, or require rebuild/reprojection immediately?
- Do any maintained non-demo Gemini flows still depend on path-based `SKILL.md` opening semantics that should be rewritten in the same change?
- Should `completion_source` remain part of public headless detail at all if terminality no longer depends on it, or is it still useful purely as diagnostic metadata?
