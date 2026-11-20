# Reorient in an Existing Project

Use this when returning to a repository or taking over an operation with incomplete context. Start with `houmao-mgr project --project-dir "$repo" status`. If `requires_project_init` is true, use `houmao-mgr manual start first-agent` for setup. If status reports a migration, review the reported plan before editing project definitions.

```sh
houmao-mgr project --project-dir "$repo" specialist list
houmao-mgr project --project-dir "$repo" profile list
houmao-mgr project --project-dir "$repo" agents list
```

Once the overlay is ready, compare the saved roles and launch defaults to the request, then check whether a suitable worker already exists.

Use that worker's ID with `agents single` and confirm its state. A saved specialist or profile supplies a launch starting point. A listed instance supplies a target for inspection. Report which project, definition, and worker you found before continuing.

For syntax, run `houmao-mgr project --help`. [Manager CLI Reference](https://igamenovoer.github.io/houmao/reference/cli/houmao-mgr/#project-repo-local-houmao-project-overlays)
