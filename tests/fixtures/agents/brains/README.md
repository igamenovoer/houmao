# Brains Repository

`agents/brains/` is the source-of-truth for reusable components used to build a fresh CLI runtime home (a "brain").

## Layout

```text
agents/brains/
  tool-adapters/                 # Per-tool home layout and projection rules
  cli-configs/<tool>/<profile>/ # Secret-free tool config profiles
  skills/<skill-name>/SKILL.md  # Tool-agnostic skills
  brain-recipes/<tool>/*.yaml   # Declarative, secret-free brain presets
  api-creds/<tool>/<profile>/   # Local-only credential profiles (gitignored)
```

## Brain-First Workflow

1. Pick a tool adapter (`codex`, `claude`, or `gemini`).
2. Pick a skill list from `agents/brains/skills/`.
3. Pick a tool config profile from `agents/brains/cli-configs/<tool>/`.
4. Pick a local credential profile from `agents/brains/api-creds/<tool>/`.
5. Build a fresh runtime home with `scripts/agents/build_brain_home.py`.
6. Launch the tool using the generated `launch.sh`, then apply a role from `agents/roles/`.

## Credential Profile Naming + Rotation Guidance

Use profile names that encode provider + account + intent, for example:

- `personal-a-default`
- `yunwu-openai`
- `team-burst-research`
- `service-ci-readonly`

Rotation guidance:

- Recipes select credential profiles by name, and blueprints inherit that choice through their bound recipe.
- Concurrent brains may reuse the same credential profile when the provider/tool allows shared API-key or token usage.
- If the provider or CLI imposes rate or session limits for that credential, rotate by creating a new profile directory and updating the affected recipes/blueprints to point at the new profile name.
- Keep secrets only in `agents/brains/api-creds/` (local-only); never inline secrets into recipes, adapters, or blueprints.

## Fixture Credential Archive

The test-fixture tree also keeps an encrypted snapshot of the local credential directory at `tests/fixtures/agents/brains/api-creds.tar.gz.gpg`.

Password source:

- Read `AGENT_CREDENTIAL_COMPRESS_PASSWORD` from the repository `.env`.

Create or refresh the archive:

```bash
set -a && . ./.env && set +a
tar -czf - -C tests/fixtures/agents/brains api-creds \
  | gpg --batch --yes --pinentry-mode loopback \
      --passphrase "$AGENT_CREDENTIAL_COMPRESS_PASSWORD" \
      --symmetric --cipher-algo AES256 \
      -o tests/fixtures/agents/brains/api-creds.tar.gz.gpg
chmod 600 tests/fixtures/agents/brains/api-creds.tar.gz.gpg
```

Inspect or extract the archive:

```bash
set -a && . ./.env && set +a
gpg --batch --yes --pinentry-mode loopback \
  --passphrase "$AGENT_CREDENTIAL_COMPRESS_PASSWORD" \
  -d tests/fixtures/agents/brains/api-creds.tar.gz.gpg | tar -tzf -
```

```bash
set -a && . ./.env && set +a
gpg --batch --yes --pinentry-mode loopback \
  --passphrase "$AGENT_CREDENTIAL_COMPRESS_PASSWORD" \
  -d tests/fixtures/agents/brains/api-creds.tar.gz.gpg | tar -xzf - -C tests/fixtures/agents/brains
```
