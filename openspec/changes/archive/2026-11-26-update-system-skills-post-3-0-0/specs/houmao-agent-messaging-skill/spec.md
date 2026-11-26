# Spec Delta

## ADDED Requirements

### Requirement: Agent messaging rewrites request.md stub and covers DSH, service/web, and CCCC distinctions
`houmao-agent-messaging` SHALL rewrite the 11-line `commands/request.md` stub with numbered `## Workflow`, fallback, `## Guardrails`, neutral prose, automatic managed-session peer-signer default, and full flags (required `--text`, `--url`, `--passive-url`, `--source-agent-id`, `--unsigned`, `--context-id`, `--generation`, `--presence`, `--ca-bundle`), update `prompt.md` for `dsh`, `service`/`web`, and `agent-operator`, and distinguish `houmao-cccc` chat from prompt/mail.

#### Scenario: Request subcommand provides full conforming workflow and CCCC boundaries stay clear
- **WHEN** an agent or operator invokes `houmao-agent-messaging->request()` or `prompt()`
- **THEN** `commands/request.md` follows `imsight-agent-skill-handling` with numbered `## Workflow`, fallback, `## Guardrails`, neutral caller/target prose, required `--text`, and automatic current managed-session peer signing when `--source-agent-id` and `--unsigned` are omitted
- **AND THEN** `commands/prompt.md` covers `dsh`, `service`/`web` outcomes, and `agent-operator` authority while distinguishing `houmao-cccc` chat from Houmao prompt/mail

### Requirement: Agent messaging strips cross-skill boilerplate from SKILL-MAIN.md
`houmao-agent-messaging/SKILL-MAIN.md` SHALL remove duplicated launcher, Missing-Input, `houmao-cli`, and redundant Supported/Out-of-Scope/Routing lists into a lean ~90-line entrypoint per `imsight-agent-skill-handling`.

#### Scenario: Messaging entrypoint keeps only skill-specific workflow, routing, and guardrails
- **WHEN** a reviewer inspects `houmao-agent-messaging/SKILL-MAIN.md`
- **THEN** duplicated cross-skill boilerplate is absent and `## Subcommands` cleanly links all eight command pages including `request`

### Requirement: Agent messaging preserves peer posture, channel separation, and admission policies
`houmao-agent-messaging` SHALL preserve `## Actor Frame Gate`, peer-directed messaging in `actor_kind=agent`, strict channel separation (`request` vs `prompt` vs `gateway-queue` vs `send-keys` vs `mail` vs `reset-context`), `--admission-policy` (`ready-only`, `if-no-pending`, `always`), and no silent cross-channel retries.

#### Scenario: Denied or failed work request does not fall back to direct prompt or mail
- **WHEN** `agents single ... request` fails admission or is refused by target policy
- **THEN** `houmao-agent-messaging` reports the exact refusal without retrying via `prompt`, `send-keys`, `--unsigned`, or `mail`
