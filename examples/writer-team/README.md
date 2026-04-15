# Writer Team Example

This example is a reusable template for a three-agent writing team. `alex-story` owns the run, writes chapters, and delegates only to `alex-char` for character profiles and `alex-review` for logic, pacing, and continuity review.

The checked-in files are source material only. Running the example creates local `.houmao/` state, mailbox data, runtime files, and story output under this directory; those generated files are intentionally ignored.

## Layout

```text
examples/writer-team/
  prompts/
    story-writer.md
    character-designer.md
    story-reviewer.md
  loop-plan/
    story-chapter-loop.md
    start-charter.md
  story/
    chapters/
    characters/
    review/
```

Generated artifacts are written locally:

- `story/chapters/`: chapter drafts, revised drafts, and finalized chapters.
- `story/characters/`: character profiles and relationship notes.
- `story/review/`: review reports from `alex-review`.
- `story/run-state.md`: optional master-owned run status.

## Prerequisites

Run commands from this directory:

```bash
cd examples/writer-team
```

Install system skills for the tools used by the team:

```bash
houmao-mgr system-skills install --tool claude
houmao-mgr system-skills install --tool codex
```

Credentials are local operator setup. The commands below use credential names as placeholders; replace them with credentials already configured in your environment, or use the appropriate `houmao-mgr project easy specialist create` credential flags for your tool lane. Do not commit credential files or secrets into this example.

## Create Specialists

Initialize local Houmao project state:

```bash
houmao-mgr project init
```

Create the three specialists from the prompt files:

```bash
houmao-mgr project easy specialist create \
  --name story-writer \
  --tool claude \
  --credential story-writer-creds \
  --system-prompt-file prompts/story-writer.md

houmao-mgr project easy specialist create \
  --name character-designer \
  --tool claude \
  --credential character-designer-creds \
  --system-prompt-file prompts/character-designer.md

houmao-mgr project easy specialist create \
  --name story-reviewer \
  --tool codex \
  --credential story-reviewer-creds \
  --system-prompt-file prompts/story-reviewer.md
```

## Create Mailbox-Enabled Profiles

The profiles give each specialist a stable managed-agent name, working directory, and filesystem mailbox identity.

```bash
houmao-mgr project easy profile create \
  --name alex-story \
  --specialist story-writer \
  --agent-name alex-story \
  --workdir "$PWD" \
  --prompt-mode unattended \
  --mail-transport filesystem \
  --mail-root "$PWD/.houmao/mailbox" \
  --mail-principal-id HOUMAO-alex-story \
  --mail-address alex-story@houmao.localhost

houmao-mgr project easy profile create \
  --name alex-char \
  --specialist character-designer \
  --agent-name alex-char \
  --workdir "$PWD" \
  --prompt-mode unattended \
  --mail-transport filesystem \
  --mail-root "$PWD/.houmao/mailbox" \
  --mail-principal-id HOUMAO-alex-char \
  --mail-address alex-char@houmao.localhost

houmao-mgr project easy profile create \
  --name alex-review \
  --specialist story-reviewer \
  --agent-name alex-review \
  --workdir "$PWD" \
  --prompt-mode unattended \
  --mail-transport filesystem \
  --mail-root "$PWD/.houmao/mailbox" \
  --mail-principal-id HOUMAO-alex-review \
  --mail-address alex-review@houmao.localhost
```

## Launch The Team

```bash
houmao-mgr project easy instance launch --profile alex-story
houmao-mgr project easy instance launch --profile alex-char
houmao-mgr project easy instance launch --profile alex-review
```

The loop plan expects the master and workers to use mailbox-backed pairwise communication. When operating the run through the `houmao-agent-loop-pairwise` skill, enable gateway mail-notifier polling for live mailbox participants before sending the start charter unless your operator flow explicitly disables notifier setup.

## Start A Run

Edit `loop-plan/start-charter.md` to set the chapter count and premise. Then start through an operator agent with the `houmao-agent-loop-pairwise` skill, using:

- plan: `loop-plan/story-chapter-loop.md`
- start charter: `loop-plan/start-charter.md`
- master: `alex-story`

For a direct CLI start without the loop skill's notifier preflight, send the charter to the master:

```bash
houmao-mgr agents prompt --agent-name alex-story < loop-plan/start-charter.md
```

The direct prompt path is useful for small local trials. For the full pairwise lifecycle, use the skill vocabulary: plan, start, status, and stop.

## Artifact Policy

This example persists user-visible writing output under `story/`. Houmao-managed agent memory remains managed by the launch environment and project overlay; this example does not carry manual legacy memory configuration.

Do not commit generated chapter files, character profiles, review reports, mailbox messages, credentials, or `.houmao/` runtime state. The committed files are the reusable team definition and loop contract.
