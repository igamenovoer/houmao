# Inspect Published Files, Drafts, or Candidates

## Workflow

1. Select the exact mount and preserve the intended caller from [Discover](discover.md).
2. Choose a published revision, saved candidate, or active private draft. Check the corresponding permission in [Mount Scope](../references/mount-scope.md).
3. Read only the required paths or changes. Pin published reads to a selected revision when the result must be consistent across calls.
4. Continue bounded results using the returned cursor and report the selected revision or draft with the evidence.

Use the native planning tool to plan related read-only calls when the inspection spans several pages or paths.

## Command Examples

Use the Bash `files` prefix from [Discover](discover.md) with the intended reader's authority.

```bash
"${files[@]}" --mount "$MOUNT_ID" list
"${files[@]}" --mount "$MOUNT_ID" read "$LOGICAL_PATH" --revision "$PUBLISHED_COMMIT"
"${files[@]}" --mount "$MOUNT_ID" history
"${files[@]}" --mount "$MOUNT_ID" history --candidates
"${files[@]}" --mount "$MOUNT_ID" diff "$CANDIDATE_COMMIT"
```

Without `--revision`, published list and read use the current publication. A read response has `revision`, `path`, and base64-encoded `content_base64`. Decode only when the caller needs the contents. To list a specific logical directory, pass it after `list`. For list, history, and diff, use `--after` with `next_after` until it is null. Keep the selected published revision on subsequent list pages when consistency matters.

Use `--draft "$DRAFT_ID"` before `list`, `read`, or `diff` for an active private draft. These commands require the opening actor's draft authority and `files.edit`. For an anonymous draft, include the private capability file as described in [Edit Draft](edit-draft.md).

## Guardrails

- DO NOT open a lease or publish a candidate to perform a read-only review.
- DO NOT pass a commit or revision selector to a draft read.
- DO NOT disclose protected file contents beyond the requested authorized purpose.
