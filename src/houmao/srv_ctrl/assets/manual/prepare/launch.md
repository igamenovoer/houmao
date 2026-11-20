# Choose Launch Settings

Use this before starting a qualified tool with `project agents launch`. Select the project that owns the definition and the workdir where the worker will act. If a trusted execution profile is needed, select it with `--executor` and confirm paths on that owner.

Choose `headless` for one native worker per prompt, `service` for a persistent protocol process, `tui` for a terminal interface, or `web` for a browser interface. Check the tool's supported modes and inspect the reported `mode`, `backend`, and `native_surface` after launch.

Set approval posture on the specialist or profile. `unattended` fills omitted permission settings with the tool's most permissive supported defaults. Supported explicit values take precedence, and Houmao rejects values for reserved inputs such as native session identity. `as_is` uses the provider baseline for omitted settings.

Launch arguments override stored profile defaults for one launch. Use `project profile set` for recurring changes. Relaunch uses the instance's saved mode. For syntax, run `houmao-mgr project agents launch --help`. [Session Lifecycle](https://igamenovoer.github.io/houmao/reference/run-phase/session-lifecycle/) · [Launch Policy](https://igamenovoer.github.io/houmao/reference/build-phase/launch-policy/)
