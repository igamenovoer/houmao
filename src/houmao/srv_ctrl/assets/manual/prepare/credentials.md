# Select Project Credentials

Use this when preparing a worker or diagnosing missing authentication. A project credential is a named bundle for one tool. The specialist selects a bundle by display name, and a profile or launch can override that selection.

1. Select the project and tool, then list its credential names. For Codex, run `houmao-mgr project --project-dir "$repo" credentials codex list`.
2. Reuse an approved bundle when one fits. To register a new bundle, use the selected tool's `add` command or its `login` command where offered. Use the supported import path for a provider login the user has already prepared. Keep credential material out of prompts, project source, and reports.
3. Set the intended bundle name on the specialist or choose the appropriate launch override. With a delegated executor, confirm the credential is available in the owner-side project.

Verify the saved display name and tool before launch. For available auth methods and syntax, run `houmao-mgr project credentials "$tool" --help`. [Manager CLI Reference](https://igamenovoer.github.io/houmao/reference/cli/houmao-mgr/#project-repo-local-houmao-project-overlays) · [Execution Contexts](https://igamenovoer.github.io/houmao/reference/run-phase/execution-contexts/)
