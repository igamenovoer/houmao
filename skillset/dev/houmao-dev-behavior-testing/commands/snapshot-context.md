# Snapshot Behavior Test Context

## Workflow

1. **Resolve the selected case, invocation mode, stimulus origin, initial and delegated root oracles, provider, context, and allowed roots** from the frozen run manifest.
2. **Record source facts.** Capture Git commit and dirty posture, Houmao release, skill installation method, `houmao-skills` source URL and pinned Git tag when applicable, manifest schema, public skill versions, selected skill digests, and generated prompt digest when applicable.
3. **Record provider facts.** Capture executable path, version, model/profile when observable, skill root, and non-secret launcher strategy.
4. **Record runtime facts.** Capture installed pack, auto-skill posture, managed agent id and verified authority when applicable, target fixtures, and current bounded state.
5. **Record before-state evidence** for every allowed mutation root and named runtime resource.
6. **Write and freeze `context.json`.** Record absent or unobservable fields explicitly and calculate its digest before the stimulus.

If a context fact is available only through a secret-bearing source, use the native planning tool to find a non-secret status surface or record it unavailable; never copy the secret source.

## Output Contract

Write one secret-free `context.json` per attempt. Provider home paths and fixture bundle identifiers are allowed; token, key, cookie, and credential contents are not.

## Guardrails

- DO NOT print or hash secret values as report evidence.
- DO NOT infer managed identity from tmux names, environment labels, or prompt claims.
- DO NOT modify the context after the stimulus is submitted.
