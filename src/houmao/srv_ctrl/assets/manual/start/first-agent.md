# Launch a First Agent

Use this when an operator asks for a worker in a repository, such as a reviewer for the current patch.

1. Run `houmao-mgr project --project-dir "$repo" status`. If it reports `requires_project_init` and the request calls for setup, run `houmao-mgr project --project-dir "$repo" init`. Use `houmao-mgr manual start existing-project` to reuse an existing overlay.
2. Select a named credential and reuse a specialist whose role and tool fit the task. Create one with `project specialist create` when needed. Save recurring launch choices with `project profile create`.
3. For a preparation request, report the specialist or profile and the launch handoff. For a run request, launch from that specialist or profile. A one-off specialist launch looks like this:

```sh
houmao-mgr --print-json project --project-dir "$repo" agents launch \
  --specialist "$specialist" --name "$name" --workdir "$workdir"
```

Save the returned ID as `agent_id` and inspect it with `houmao-mgr --print-json agents single --agent-id "$agent_id" state`. If launch reports a gateway attachment error alongside an ID, inspect the existing worker before retrying. Use the verified ID to dispatch work when requested.

For syntax, run `houmao-mgr project agents launch --help`. [Quickstart](https://igamenovoer.github.io/houmao/getting-started/quickstart/)
