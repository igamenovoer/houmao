# Local Auth Bundles Fixture Root

This fixture lane owns host-local credential bundles for maintained demos, smoke flows, and manual helpers. It is **not** a canonical agent-definition source tree.

Maintained workflows should source credentials from `tests/fixtures/auth-bundles/<tool>/<bundle>/` and then materialize the required alias or copied auth path into a run-local tree such as one demo's `inputs/agents/` copy, one overlay-local credential import, or one temporary direct-dir root derived from `tests/fixtures/plain-agent-def/`.

## Maintained Bundle Names

### Claude

- `kimi-coding`
- `official-login`
- `personal-a-default`

### Codex

- `personal-a-default`
- `yunwu-openai`

### Gemini

- `api-key-a-default`
- `personal-a-default`

Each maintained bundle directory contains a `.gitignore` so local plaintext credentials stay ignored on this host.

## Encrypted Archive Workflow

The checked-in [tools.tar.gz.enc](/data1/huangzhe/code/houmao/tests/fixtures/auth-bundles/tools.tar.gz.enc) archive is the encrypted snapshot of the local auth-bundle tree.

To verify and restore it:

1. Load `AGENT_CREDENTIAL_COMPRESS_PASSWORD` from the repo-local `.env`.
2. Verify the archive checksum:
   - `sha256sum -c tests/fixtures/auth-bundles/tools.tar.gz.enc.sha256`
3. Decrypt and unpack:

```bash
set -a
. ./.env
set +a

openssl enc -d -aes-256-cbc -pbkdf2 -salt \
  -pass env:AGENT_CREDENTIAL_COMPRESS_PASSWORD \
  -in tests/fixtures/auth-bundles/tools.tar.gz.enc \
| tar -C tests/fixtures/auth-bundles -xzf -
```

Keep the extracted bundle contents local-only and do not commit them in plaintext.

## Claude `official-login`

Reserve `tests/fixtures/auth-bundles/claude/official-login/` for the maintained local Claude vendor-login smoke bundle.

Supported files:

- `files/.credentials.json`
- `files/.claude.json`
- `env/vars.env`

Rules:

- copy vendor `.credentials.json` unchanged into `files/.credentials.json`
- keep `files/.claude.json` present; `{}` is acceptable for the smoke lane
- keep `env/vars.env` empty unless you intentionally need a local override
- do not add `claude_state.template.json` for this lane

The maintained smoke flow now copies `tests/fixtures/plain-agent-def/` into a temp direct-dir root, materializes `official-login` there from this auth-bundle lane, sets `HOUMAO_AGENT_DEF_DIR` to that temp root, and launches `server-api-smoke` with `--provider claude_code --auth official-login --headless` while the tracked preset keeps `launch.prompt_mode: unattended`.
