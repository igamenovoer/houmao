# Launch Profiles

Launch profiles are reusable, operator-owned, **birth-time** launch configuration. They are distinct from reusable source definitions (specialists, recipes), and distinct from live managed-agent instances. Persisting, listing, inspecting, or removing a launch profile does not by itself create, stop, or mutate a live instance.

This page is the conceptual home for the launch-profile model. Other docs link here instead of restating the precedence chain or the easy-versus-explicit lane split inline.

## Why Launch Profiles Exist

A specialist or a recipe answers the question *what is this agent?* — its role prompt, its tool, its skills, its setup, its default credentials. But the same specialist usually needs the same recurring **launch context**: the managed-agent name, the working directory, the credential override for this lane, the mailbox binding, the gateway posture, durable env records, an optional prompt overlay.

Without a stored launch profile, an operator has to remember and re-type that launch context every time. With one, the launch context becomes a named, persisted, project-local object that both `houmao-mgr` and the system-skill-driven agent surfaces can reference by name.

## Two User-Facing Lanes Over One Shared Model

Houmao keeps the easy-versus-explicit operator split that already exists for source definitions, and surfaces launch profiles through two distinct authoring lanes:

```mermaid
flowchart LR
    subgraph EASY["Easy lane (project easy ...)"]
        S1["specialist<br/>(easy source)"]
        P1["profile<br/>(easy birth-time)"]
        I1["instance<br/>(runtime)"]
        S1 --> P1 --> I1
        S1 -.->|"direct launch"| I1
    end

    subgraph EXPLICIT["Explicit lane (project agents ...)"]
        S2["recipe<br/>(low-level source)"]
        P2["launch-profile<br/>(low-level birth-time)"]
        I2["managed agent<br/>(runtime)"]
        S2 --> P2 --> I2
        S2 -.->|"direct launch"| I2
    end

    P1 -. shared catalog<br/>launch-profile family .- P2
```

Both lanes write into one shared catalog-backed launch-profile object family, even though the user-facing nouns differ. The split is deliberate:

- **Easy lane** uses the noun `profile`, is specialist-backed, and exposes a smaller, opinionated authoring surface. It is the right place to start when you want reusable defaults without answering every low-level launch question. CLI: `houmao-mgr project easy profile ...`.
- **Explicit lane** uses the noun `launch-profile`, is recipe-backed, and exposes the fuller low-level launch contract. It is the right place to be when you need precise control over the underlying source recipe and the full launch field set. CLI: `houmao-mgr project agents launch-profiles ...`.

A specialist-backed easy profile and a recipe-backed explicit launch profile are stored as the same kind of catalog object. The difference is the source lane (`specialist` vs `recipe`) and the profile lane (`easy_profile` vs `launch_profile`) recorded on each entry. Both lanes project into the same compatibility tree under `.houmao/agents/launch-profiles/<name>.yaml`.

## Source Versus Birth-Time Taxonomy

The four operator-authored object families and the two derived runtime objects form one consistent taxonomy:

| Object | Lane | Catalog-stored | Projected to `.houmao/agents/` | Authored by | Notes |
|---|---|---|---|---|---|
| **specialist** | easy | yes | `roles/<name>/`, `presets/<recipe>.yaml`, `tools/<tool>/auth/<creds>/` | operator (easy) | The reusable easy-lane source definition: role + tool + skills + setup + default auth + durable launch posture. |
| **recipe** | explicit | yes | `presets/<name>.yaml` | operator (explicit) | The reusable low-level source definition. The CLI surface is `project agents recipes ...`; `project agents presets ...` is a compatibility alias for the same files. |
| **easy profile** | easy | yes | `launch-profiles/<name>.yaml` | operator (easy) | Specialist-backed reusable birth-time launch configuration. Targets exactly one specialist. |
| **explicit launch profile** | explicit | yes | `launch-profiles/<name>.yaml` | operator (explicit) | Recipe-backed reusable birth-time launch configuration. Targets exactly one recipe. |
| **runtime `LaunchPlan`** | derived | no | no | system | Composed at launch time from the manifest, role, backend, and working directory. Not user-authored. Not persisted as project-local source. |
| **live managed-agent instance** | runtime | no | no | system | The running tmux-backed process plus its registry record, manifest, and gateway state. |

The two profile rows share one underlying catalog model. The CLI surfaces are split for UX reasons, not because the storage is different.

## What Launch Profiles Capture

A launch profile may store, with no inline secrets:

- a source reference (specialist for easy, recipe for explicit),
- managed-agent identity defaults (`--agent-name`, optionally `--agent-id`),
- a default working directory,
- an auth override by name (the actual credentials still live in the auth bundle),
- an operator prompt-mode override (`unattended` or `as_is`),
- durable non-secret env records,
- declarative mailbox configuration (transport, root, address, principal id, and Stalwart-only fields when applicable),
- launch posture defaults (`headless`, gateway auto-attach, fixed loopback gateway port),
- a managed prompt-header policy (`inherit`, `enabled`, or `disabled`),
- a prompt overlay (mode plus inline text or a referenced file).

Inline prompt-overlay text is stored inline. File-referenced overlays are kept as managed file-backed content under the overlay-owned content roots, and the catalog stores only the reference. This keeps long prompt overlays out of the catalog database itself.

## Effective-Launch Precedence

When an operator launches from a source plus a launch profile plus direct CLI overrides, the effective launch inputs are composed from five layers in order:

```mermaid
flowchart TD
    A["1. Tool-adapter defaults<br/>(LaunchDefaults)"]
    B["2. Source recipe defaults<br/>(skills, setup, auth, launch.prompt_mode, ...)"]
    C["3. Launch-profile defaults<br/>(easy profile or explicit launch profile)"]
    D["4. Direct CLI overrides<br/>(--agent-name, --auth, --workdir, ...)"]
    E["5. Live runtime mutations<br/>(late mailbox registration, etc.)"]

    A --> B --> C --> D --> E
```

Rules:

- Fields omitted by a higher-priority layer survive from the next lower-priority layer.
- Direct CLI overrides win over launch-profile defaults but **never rewrite the stored launch profile**. Overrides such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir` apply to one launch and are dropped on the next launch from the same profile.
- Live runtime mutations such as late filesystem mailbox registration are runtime-owned. They affect the running session and the runtime manifest, but they never rewrite the stored launch profile.
- For easy profiles, the easy lane compiles down through the same five layers — the specialist resolves into a recipe-backed source layer before the launch-profile layer applies.

## Prompt Overlays

A launch profile may declare a prompt overlay. The supported modes are:

- `append` — the effective role prompt is the source role prompt followed by the overlay text.
- `replace` — the effective role prompt is the overlay text instead of the source role prompt.

The effective role prompt is composed once, **before** backend-specific role injection planning begins. Resumed turns do not replay the overlay as a separate second bootstrap step. From the backend's perspective, the prompt overlay is part of the role prompt that role injection plans against.

Prompt overlays are inline text or a referenced file. File-backed overlays remain managed content under the overlay-owned content roots, and the catalog stores only the reference; the catalog does not duplicate large overlay payloads inside the SQLite store itself.

## Managed Prompt Header

Managed launches prepend one short Houmao-owned prompt header by default. The header tells the agent that it is Houmao-managed, includes the resolved managed-agent name and id, points the agent toward `houmao-mgr` and other supported Houmao system interfaces for Houmao-related work, and tells it to avoid unsupported ad hoc probing when a supported Houmao interface exists. The header stays general-purpose and does not name individual packaged guidance entries.

Prompt composition order is:

1. source role prompt,
2. launch-profile prompt overlay resolution,
3. managed prompt-header prepend,
4. backend-specific prompt injection.

That means backend-specific role injection sees one already-composed effective launch prompt. The runtime does not replay the managed header later as a separate bootstrap turn.

The managed header is controlled by the same precedence model as other birth-time launch defaults:

- direct launch-time override via `--managed-header` or `--no-managed-header`,
- stored launch-profile policy (`inherit`, `enabled`, `disabled`),
- default enabled behavior when neither of the above forces a result.

`inherit` means "use the default enabled behavior." If you need a role to stay effectively promptless or you want one launch to skip the Houmao-owned prelude, use `--no-managed-header` for that launch or store `disabled` on the relevant launch profile.

## Launch-Profile Provenance In Inspection Output

When a managed agent was launched from a reusable launch profile, the build manifest and the runtime launch metadata preserve secret-free provenance sufficient for inspection and replay:

- whether the launch originated from a specialist source or a recipe source,
- whether the birth-time reusable config came from an easy profile or an explicit launch profile,
- the originating profile name when available.

Inspection commands surface that provenance:

- `houmao-mgr project easy instance list` and `houmao-mgr project easy instance get` report the originating easy-profile identity when runtime-backed state makes it resolvable, and continue to report the originating specialist when available.
- `houmao-mgr agents state` and `houmao-mgr agents list` report the same lane and profile information for explicit launch-profile-backed managed agents.
- Inspection output never includes secret credential values inline; auth is reported by bundle name only.

## Picking A Lane

Use the easy lane (`project easy specialist` plus `project easy profile`) when:

- you want one specialist with a small set of opinionated defaults,
- you want the same specialist relaunched with the same managed-agent name, workdir, mailbox, and credential lane each time,
- you do not want to hand-author the underlying recipe.

Use the explicit lane (`project agents recipes` plus `project agents launch-profiles`) when:

- you need precise control over the source recipe (skills list, setup bundle, prompt-mode default, mailbox-source declaration, etc.),
- you want birth-time defaults that are intentionally low-level and visible,
- the team checks recipes into the project so the easy lane's specialist convenience layer is not the right authoring surface.

Both lanes can coexist in the same project overlay. The shared catalog model means a future change can tighten the relationship between them without forcing a migration today.

## CLI Surfaces

Canonical authoring surfaces:

```bash
# Easy lane
houmao-mgr project easy specialist create --name <name> --tool <tool> ...
houmao-mgr project easy profile create --name <profile> --specialist <name> ...
houmao-mgr project easy instance launch --profile <profile>           # easy-profile-backed
houmao-mgr project easy instance launch --specialist <name> --name <managed-name>

# Explicit lane
houmao-mgr project agents recipes add --name <recipe> --role <role> --tool <tool> ...
houmao-mgr project agents launch-profiles add --name <profile> --recipe <recipe> ...
houmao-mgr agents launch --launch-profile <profile>                   # launch-profile-backed
houmao-mgr agents launch --agents <selector> --provider <provider>    # direct recipe selector
```

`--profile` and `--specialist` cannot be combined on `project easy instance launch`. `--launch-profile` and `--agents` cannot be combined on `agents launch`.

`project agents presets ...` remains valid as a compatibility alias for the same files that `project agents recipes ...` administers; both names map to `.houmao/agents/presets/<name>.yaml`.

For full option tables and edge cases, see the [`houmao-mgr` CLI reference](../reference/cli/houmao-mgr.md).

## See Also

- [Easy Specialists](easy-specialists.md) — operator workflow for the easy lane (specialist → optional easy profile → instance).
- [Agent Definition Directory](agent-definitions.md) — directory layout, projection paths, and the canonical recipe authoring path.
- [`houmao-mgr` CLI reference](../reference/cli/houmao-mgr.md) — authoritative option tables for `project easy profile`, `project agents launch-profiles`, and `agents launch --launch-profile`.
- [Launch Overrides](../reference/build-phase/launch-overrides.md) — how launch-profile defaults compose with adapter defaults and direct overrides during build.
- [Launch Plan](../reference/run-phase/launch-plan.md) — how launch-profile-derived inputs flow through the manifest into the run-phase `LaunchPlan`.
