# Edit and Save a Private Draft

## Workflow

1. Use the exact mount and published base from [Discover](discover.md) or its trusted receipt supplied by the target owner. Verify `files.edit` and open a lease against that base.
2. Save the draft ID and lease expiry. For an unsigned lease, protect the capability as described in **Anonymous Leases**.
3. Apply the requested logical edits within the lease and inspect the diff. Renew the lease as needed.
4. Commit to save an immutable candidate or abort to discard the draft. Return the saved candidate, recorded base, and attribution when committing.

Use the native planning tool to sequence different supported edits without widening the selected mount, paths, or authorization.

## Command Examples

This sequence assumes a signed caller and the Bash `files` prefix from discovery. Set `DRAFT_ID` from the response to the first command before continuing. The sample adds a previously absent `review` skill.

```bash
"${files[@]}" --mount "$MOUNT_ID" lease open --expected-base "$BASE_COMMIT"
```

```bash
draft=("${files[@]}" --mount "$MOUNT_ID" --draft "$DRAFT_ID")
"${draft[@]}" mkdir review
"${draft[@]}" write review/SKILL.md --from-file ./SKILL.md
"${draft[@]}" diff
"${draft[@]}" commit --message 'Add review skill'
```

This example assumes the source file is ready and has a skill frontmatter `name: review` and nonempty `description`. Logical paths are relative to the mount. Use `write --from-file -` to consume standard input, `rename PATH DESTINATION` to move entries, or `delete PATH` to stage removal. Writes have a 2 MiB decoded size limit. An active lease is exclusive to the mount. Use `lease renew` before expiry or `abort` to discard the draft. Expiry discards staged changes.

Commit releases the lease. Its receipt includes the `commit_id`, `base_commit`, `author`, committing `actor`, and target `committer`. The published tree stays at its existing revision until an authorized push publishes a candidate. Signed drafts belong to the opening actor kind and principal. An enrolled replacement key for the same principal can use its draft with current `files.edit`. An unsigned draft records anonymous authorship.

## Anonymous Leases

An unsigned lease under a verified open roster returns a secret `lease_capability`. Redirect the lease response to a new owner-private file outside the checkout. Extract the capability into a private file and use `--lease-capability-file` at the group level for subsequent operations, including renewal.

This example uses an existing verified owner-private directory `PRIVATE_PARENT` outside the checkout and a `files` prefix without a signer.

```bash
lease_dir=$(mktemp -d "${PRIVATE_PARENT:?Select the owner-private directory}/houmao-file-edit.XXXXXXXX") &&
(
  umask 077
  "${files[@]}" --mount "$MOUNT_ID" lease open --expected-base "$BASE_COMMIT" \
    > "$lease_dir/receipt.json" &&
  jq -er '.lease_capability' "$lease_dir/receipt.json" > "$lease_dir/capability"
)
```

After a successful lease open and extraction, select `DRAFT_ID` from the private receipt.

```bash
DRAFT_ID=$(jq -er '.draft_id' "${lease_dir:?Open an anonymous lease first}/receipt.json") &&
draft=("${files[@]}" --mount "$MOUNT_ID" --draft "$DRAFT_ID"
  --lease-capability-file "$lease_dir/capability")
```

The capability remains bound to its draft and open policy epoch. Renewal retains it. If the lease cannot be recovered, report the failure and use the documented expiry boundary.

## Guardrails

- DO NOT log a lease response carrying an anonymous capability or put that capability in command arguments.
- DO NOT use a private home path as a logical mount path.
- DO NOT claim that staged edits or a candidate changed the running agent.
