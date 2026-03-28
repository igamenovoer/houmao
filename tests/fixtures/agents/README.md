# Agents Directory

This fixture tree publishes the simplified `agents/` source layout as the canonical supported shape:

```text
tests/fixtures/agents/
  skills/<skill>/SKILL.md
  roles/<role>/system-prompt.md
  roles/<role>/presets/<tool>/<setup>.yaml
  tools/<tool>/adapter.yaml
  tools/<tool>/setups/<setup>/...
  tools/<tool>/auth/<auth>/...
  compatibility-profiles/
```

Archived demos no longer use this tree as a parallel source-of-truth. New examples, docs, and tests should rely on `skills/`, `tools/`, role-scoped `presets/`, and optional `compatibility-profiles/` only.

## How To Use Each Part

### `skills/`

Reusable Agent Skills packages. Each skill directory must contain `SKILL.md`.

Use this when:

- adding or editing reusable task instructions
- defining narrow probe skills such as `skill-invocation-probe`

### `tools/<tool>/adapter.yaml`

Per-tool runtime-home projection and launch contract.

Use this when:

- adding a new CLI tool
- changing where setup files, skills, or auth files project into the runtime home
- changing the auth env allowlist or tool-specific launch metadata

### `tools/<tool>/setups/<setup>/`

Secret-free checked-in setup bundles for one tool.

Use this when:

- you want different tracked tool defaults such as `default` vs `yunwu-openai`
- you need to update non-secret tool config files

### `tools/<tool>/auth/<auth>/`

Local-only auth bundles for one tool.

Use this when:

- populating local API credentials and auth env files
- rotating accounts or rate-limit lanes by switching bundle names

Never commit secret material. In this fixture tree, `tools/<tool>/auth/**` is local-only host state and should remain ignored entirely.

### `roles/<role>/system-prompt.md`

Role prompt and behavior package, independent of tool/runtime layout.

Use this when:

- defining the agent's behavior and policy
- reusing the same role across multiple tools or setup variants

### `roles/<role>/presets/<tool>/<setup>.yaml`

Minimal declarative launch preset for one role/tool/setup combination.

Use this when:

- you want a tracked reusable launch variant
- you need to select skills, default auth, or preset-owned launch/mailbox settings

Preset identity is path-derived. The file path determines `role`, `tool`, and `setup`, so the YAML only contains `skills` plus optional `auth`, `launch`, `mailbox`, and `extra`.

## Runtime Outputs

Generated runtime state still lives outside the source tree:

- `<runtime_root>/homes/<home-id>/`
- `<runtime_root>/manifests/<home-id>.yaml`

Default runtime root is `tmp/agents-runtime/`.

## Encrypted Tools Archive

The checked-in [tools.tar.gz.enc](/data1/huangzhe/code/houmao/tests/fixtures/agents/tools.tar.gz.enc) archive is the encrypted snapshot of `tests/fixtures/agents/tools/`, including local-only auth bundles that are ignored in plaintext on this host.

To verify and decrypt it:

1. Load `AGENT_CREDENTIAL_COMPRESS_PASSWORD` from the repo-local `.env`.
2. Verify the archive checksum:
   - `sha256sum -c tests/fixtures/agents/tools.tar.gz.enc.sha256`
3. Decrypt and unpack:

```bash
set -a
. ./.env
set +a

openssl enc -d -aes-256-cbc -pbkdf2 -salt \
  -pass env:AGENT_CREDENTIAL_COMPRESS_PASSWORD \
  -in tests/fixtures/agents/tools.tar.gz.enc \
| tar -C tests/fixtures/agents -xzf -
```

This restores `tests/fixtures/agents/tools/` in place. Keep the extracted `tools/<tool>/auth/**` contents local-only and do not commit them in plaintext.

## Recommended Workflow

1. Select a role preset such as `roles/gpu-kernel-coder/presets/claude/default.yaml`.
2. Build explicitly from that preset:
   - `pixi run houmao-mgr brains build --agent-def-dir tests/fixtures/agents --preset tests/fixtures/agents/roles/gpu-kernel-coder/presets/claude/default.yaml`
3. Or launch directly from a bare role selector:
   - `pixi run houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
4. Override auth at launch time when needed:
   - `pixi run houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --auth personal-a-default`

## Source-Of-Truth Rules

- Commit: `skills/`, `roles/`, `tools/<tool>/adapter.yaml`, `tools/<tool>/setups/`, tracked preset YAML, and compatibility metadata.
- Do not commit: secret values under `tools/<tool>/auth/**`.
- Keep managed-agent identity launch-time only. Presets do not own `default_agent_name`.
- Keep adapter definitions authoritative for per-tool projection and launch behavior.
