# Claude Code Native Skill Projection

## Question

How must a skill be projected so Claude Code can discover and invoke it natively through `/skills` and `/<skill-name>`?

## Short Answer

Claude Code discovers native skills when they live as top-level skill directories:

- personal/config-home scope: `CLAUDE_CONFIG_DIR/skills/<skill-name>/SKILL.md`
- project scope: `.claude/skills/<skill-name>/SKILL.md`

Houmao's current mailbox projection for Claude does not satisfy that because it installs mailbox skills under an extra namespace layer:

- current Houmao layout: `CLAUDE_CONFIG_DIR/skills/mailbox/<skill-name>/SKILL.md`

That namespaced layout is not discovered by Claude Code as a native skill.

## Empirical Probe

Probe workspace:

- config home: `/data1/huangzhe/code/houmao/tmp/claude-skill-projection-probe/config-home`
- project root: `/data1/huangzhe/code/houmao/tmp/claude-skill-projection-probe/project`
- Claude Code version: `2.1.89`

Probe skills created:

- top-level config-home skill:
  `/data1/huangzhe/code/houmao/tmp/claude-skill-projection-probe/config-home/skills/top-probe/SKILL.md`
- namespaced config-home skill:
  `/data1/huangzhe/code/houmao/tmp/claude-skill-projection-probe/config-home/skills/mailbox/namespaced-probe/SKILL.md`
- project-local skill:
  `/data1/huangzhe/code/houmao/tmp/claude-skill-projection-probe/project/.claude/skills/project-probe/SKILL.md`

Observed in the live Claude TUI:

- `/skills` listed `top-probe`
- `/skills` listed `project-probe`
- `/skills` did not list `namespaced-probe`
- `/namespaced-probe` returned `Unknown skill: namespaced-probe`
- `/top-probe` was recognized as a valid skill command
- `/project-probe` was recognized as a valid skill command

The recognized commands later hit Claude's separate login gate, but discovery had already succeeded. The namespaced skill failed at discovery.

## Why Houmao Misses Native Claude Invocation

Current runtime mailbox projection code keeps mailbox skills under a shared namespace:

- `MAILBOX_PRIMARY_NAMESPACE_DIR = "mailbox"` in
  `/data1/huangzhe/code/houmao/src/houmao/agents/mailbox_runtime_support.py`

Current Claude runtime-home installation therefore becomes:

```text
<CLAUDE_CONFIG_DIR>/skills/mailbox/houmao-process-emails-via-gateway/SKILL.md
```

Example from the live demo:

- `/data1/huangzhe/code/houmao/scripts/demo/single-agent-mail-wakeup/outputs/overlay/runtime/homes/claude-brain-20260401-152754Z-e8238c/skills/mailbox/houmao-process-emails-via-gateway/SKILL.md`

That path exists, but Claude Code does not treat it as a native slash-invocable skill.

## Projection Rule For Claude

If Houmao wants Claude-native invocation, Claude-facing mailbox skills should be projected as top-level skill directories under the Claude home:

```text
<CLAUDE_CONFIG_DIR>/skills/houmao-process-emails-via-gateway/SKILL.md
<CLAUDE_CONFIG_DIR>/skills/houmao-email-via-agent-gateway/SKILL.md
<CLAUDE_CONFIG_DIR>/skills/houmao-email-via-filesystem/SKILL.md
<CLAUDE_CONFIG_DIR>/skills/houmao-email-via-stalwart/SKILL.md
```

Not this:

```text
<CLAUDE_CONFIG_DIR>/skills/mailbox/<skill-name>/SKILL.md
```

## Design Implication

The important distinction is not `skills` versus `.claude/skills` alone.

- Under `CLAUDE_CONFIG_DIR`, top-level `skills/<skill-name>` works.
- Under a project worktree, `.claude/skills/<skill-name>` works.
- The extra `mailbox/` namespace layer is what breaks Claude-native discovery for Houmao mailbox skills.

## Source References

- Claude docs: `https://code.claude.com/docs/en/slash-commands`
- Houmao mailbox projection code:
  `/data1/huangzhe/code/houmao/src/houmao/agents/mailbox_runtime_support.py`
- Probe files:
  `/data1/huangzhe/code/houmao/tmp/claude-skill-projection-probe/config-home/skills/top-probe/SKILL.md`
  `/data1/huangzhe/code/houmao/tmp/claude-skill-projection-probe/config-home/skills/mailbox/namespaced-probe/SKILL.md`
  `/data1/huangzhe/code/houmao/tmp/claude-skill-projection-probe/project/.claude/skills/project-probe/SKILL.md`
