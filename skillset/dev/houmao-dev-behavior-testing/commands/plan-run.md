# Plan a Behavior Qualification Run

## Workflow

1. **Resolve the repository and fresh run root.** Default to `tmp/houmao-dev-behavior-testing/<UTC timestamp>-<scope>` and refuse a non-empty destination.
2. **Resolve case selection.** Read the catalog, selected family page, and [../references/case-schema.md](../references/case-schema.md); reject unknown or duplicate case ids.
3. **Resolve providers and contexts.** Apply [../references/fixture-contexts.md](../references/fixture-contexts.md) and record unsupported combinations rather than silently dropping them.
4. **Check catalog drift.** Compare the case route expectations with the current packaged manifest; never rewrite cases from manifest content.
5. **Declare repetitions, timeouts, evidence sources, allowed mutation roots, and cleanup obligations.** Use case values or their declared family defaults.
6. **Write and freeze `run-manifest.json`.** Include catalog and case revisions, Git/source posture, selections, planned attempts, and content digests.

If the requested slice cannot use one common fixture strategy, use the native planning tool to partition it into explicit context groups under the same run without weakening isolation or evidence requirements.

## Admission Contract

Planning is read-only outside the new run root. A runnable plan needs exact case revisions, providers, contexts, repetitions, fixture strategy, and evidence visibility posture. Catalog drift, unavailable credentials, unsupported providers, or unsafe targets produce planned `incomplete` entries before any launch.

## Output Contract

Write `run-manifest.json` and `plan.md` under the run root. Freeze their hashes before `execute-case`; any correction creates a new run id.

## Guardrails

- DO NOT select cases from memory when the committed catalog is available.
- DO NOT use the runtime manifest to manufacture a new oracle.
- DO NOT treat an existing non-empty directory as a fresh run root.
