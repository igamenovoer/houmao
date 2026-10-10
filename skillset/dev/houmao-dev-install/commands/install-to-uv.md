# Install Houmao to User-Space uv

## Workflow

1. **Resolve and inspect the checkout**. Confirm the static project name is `Houmao`, both maintained scripts exist, Git `HEAD` is readable, and `uv` is available. Capture the original project version, `git status --porcelain=v1`, `uv --version`, `uv tool list`, and existing executable paths.
2. **Derive the local build version** from the exact public PEP 440 version and lowercase seven-character Git commit. Use `<public-version>+local.<commit>` for a clean preflight checkout or `<public-version>+local.<commit>.dirty` when the captured preflight status is nonempty.
3. **Temporarily stamp only `[project].version`**. Validate the derived value with `packaging.version.Version` through `pixi run python`, then make one targeted edit that preserves every other byte and pre-existing change.
4. **Install the editable user tool** by running `uv tool install --force --editable .` from the checkout root. Use uv's default user tool and executable directories.
5. **Restore the exact original version immediately** after the install attempt, including failure or interruption after stamping. Confirm the original version is back before verification.
6. **Verify the installation** using the checks in **Verification Contract**.
7. **Compare the final worktree state** with the captured preflight state. Report the result using **Output Contract**.

If the checkout metadata or uv layout differs from this procedure, use the native planning tool for a bounded diagnostic pass. Preserve the version-restoration guarantee and report the unsupported condition instead of applying a broad repair.

## Local Version Contract

Preserve the original version's public form, including release-candidate, development, or post-release segments. Do not derive from `Version.base_version`, because it can drop those segments. Remove an existing local segment before adding the development stamp.

Determine `.dirty` from the preflight Git status. The temporary version edit itself must never change that decision.

Example:

```text
release version: 2.1.0
commit:          4b3837f
clean build:     2.1.0+local.4b3837f
dirty build:     2.1.0+local.4b3837f.dirty
```

## Verification Contract

Require all of the following evidence:

1. `uv tool list` reports the derived local version and both `houmao-mgr` and `houmao-passive-server`.
2. `command -v houmao-mgr` and `command -v houmao-passive-server` resolve executable paths from uv's user executable directory.
3. `houmao-mgr --version` reports the derived local version, and both maintained commands pass a `--help` smoke check.
4. `<uv-tool-dir>/houmao/uv-receipt.toml` records `editable = "<absolute-checkout-path>"`.
5. The installed `houmao-*.dist-info/direct_url.json` records the checkout file URL with `"editable": true`.
6. The editable `.pth` file points at `<checkout>/src`.
7. The final `pyproject.toml` contains the exact original version and the final Git status matches the preflight status.

Use `uv tool dir` to resolve `<uv-tool-dir>` rather than assuming a user data path.

## Failure Handling

- If installation fails after the temporary edit, restore the original version before reporting the uv error.
- If uv reports the local version but editable evidence is missing, report verification failure with the receipt, direct-URL, and `.pth` paths examined.
- If final Git status differs, identify and repair only the temporary version change. Preserve every preflight difference.
- If another executable shadows uv's entrypoint, report both paths and do not rewrite the user's shell configuration.

## Output Contract

Lead with success or failure. State the local version, editable checkout, executable paths, uv tool directory, receipt and direct-URL evidence, smoke-check result, and worktree-preservation result.

## Guardrails

- DO NOT use `sudo`, `uv pip install --system`, `pip install --user`, or a non-editable install.
- DO NOT commit the temporary local version.
- DO NOT derive dirty posture after editing project metadata.
- DO NOT use `git reset`, `git checkout`, or whole-file replacement to restore `pyproject.toml`.
- DO NOT claim editable installation from a directory requirement alone.
