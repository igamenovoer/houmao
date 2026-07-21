# Behavior Qualification Artifact Contract

## Workflow

1. **Choose a fresh run root** below `tmp/houmao-dev-behavior-testing/`.
2. **Write definitions and the frozen run manifest** before any provider launch.
3. **Create one isolated attempt directory** for each planned `(case, variant, provider, context, repetition)` cell.
4. **Freeze context before stimulus and raw evidence after observation.** Record content digests at both gates.
5. **Append derived verdicts and reports** without changing frozen inputs.
6. **Record cleanup separately** from behavioral outcome.

If a maintained harness owns an authoritative artifact outside this tree, use the native planning tool to store a secret-free reference and digest rather than copy or rewrite it.

## Logical Layout

```text
tmp/houmao-dev-behavior-testing/<run-id>/
├── definitions/
│   ├── catalog-snapshot.md
│   └── stimuli/<case-id>.md
├── run-manifest.json
├── plan.md
├── attempts/
│   └── <case-id>/<variant-id>/<provider>/<context>/attempt-<NNN>/
│       ├── context.json
│       ├── launch.json
│       ├── stimulus.md
│       ├── native-skill-events.ndjson
│       ├── transcript.cast
│       ├── transcript.txt
│       ├── commands.ndjson
│       ├── filesystem-before.json
│       ├── filesystem-after.json
│       ├── runtime-before.json
│       ├── runtime-after.json
│       ├── final-response.md
│       ├── evidence-index.json
│       ├── verdict.json
│       └── verdict.md
├── cleanup.json
├── report.json
└── report.md
```

Unavailable optional evidence is recorded in `evidence-index.json` with a reason; do not create an empty file that looks authoritative. Provider-native event and terminal filenames may differ when a maintained harness owns them, but the index must name their authority and digest.

## Freeze Gates

The run-manifest gate binds requested selectors, catalog version and digest, resolved case revisions and variants, functional-area/profile attribution, contributing selectors, explicit exclusions, providers, contexts, repetitions, planned attempts, stimuli, allowed roots, and source/skill revisions. Provider and repetition matrices remain independent from semantic coverage profiles. The context gate binds the attempt setup before stimulus. The evidence gate binds all raw observations before adjudication.

After a gate, corrections require a new run or attempt. Derived excerpts and renderings cite the frozen source digest.

## Cleanup

`cleanup.json` records each live session, provider home, managed agent, gateway, mailbox fixture, and temporary project with `removed`, `preserved`, `failed`, or `not-owned` posture. Cleanup failure does not rewrite the case verdict, but it makes the overall run incomplete until resolved or explicitly handed off.

## Guardrails

- DO NOT overwrite an existing attempt directory.
- DO NOT edit raw evidence after writing its index digest.
- DO NOT store secret material as evidence.
