## 1. Claude Env Support

- [x] 1.1 Update `agents/brains/tool-adapters/claude.yaml` allowlist to include `ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL`, and the `ANTHROPIC_DEFAULT_*_MODEL` alias pinning vars required by the specs.
- [x] 1.2 Add a unit test that loads the Claude tool adapter and asserts the allowlist contains the model-selection env vars.

## 2. Runtime + Docs

- [x] 2.1 Update `docs/reference/brain_launch_runtime.md` with a “Model selection (Claude Code)” section describing how to use `ANTHROPIC_MODEL` (and optional vars like `ANTHROPIC_SMALL_FAST_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`, and `CLAUDE_CODE_SUBAGENT_MODEL`) for both `claude_headless` and `cao_rest`.

## 3. Hermetic Tests

- [x] 3.1 Add/extend a unit test that verifies `parse_allowlisted_env()` selects `ANTHROPIC_MODEL` (and `ANTHROPIC_SMALL_FAST_MODEL` and `CLAUDE_CODE_SUBAGENT_MODEL`) from a temporary env file when allowlisted.
- [x] 3.2 Add a unit test that verifies CAO tmux env composition preserves `ANTHROPIC_MODEL` (and `ANTHROPIC_SMALL_FAST_MODEL` and `CLAUDE_CODE_SUBAGENT_MODEL`) from the caller environment (without requiring tmux/CAO).
