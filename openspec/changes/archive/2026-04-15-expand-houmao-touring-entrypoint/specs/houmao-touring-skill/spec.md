## ADDED Requirements

### Requirement: `houmao-touring` presents a state-adaptive welcome message

The packaged `houmao-touring` skill SHALL present a welcome message that adapts to the inspected current Houmao state at the start of the guided tour.

When the inspected workspace has no project overlay, no reusable specialists, and no running managed agents, the touring skill SHALL present the full welcome text that introduces Houmao in plain language and names the typical initial setup path.

When the inspected workspace already has any of those state components, the touring skill SHALL present a short acknowledgement in place of the full welcome, immediately followed by the current-state orientation and the offered next branches, so that the user is not pushed back to the beginning of setup.

The touring skill SHALL NOT repeat the full welcome text on every turn, and SHALL NOT present the full welcome when the recent conversation has already covered it.

#### Scenario: Blank-slate tour shows the full welcome

- **WHEN** a user starts the `houmao-touring` guided tour in a workspace with no project overlay, no reusable specialists, and no running managed agents
- **THEN** the touring skill presents the full welcome text, including the plain-language description of Houmao and the typical initial setup path
- **AND THEN** it continues with current-state orientation and the offered next branches

#### Scenario: Workspace with existing state shows short acknowledgement instead of the full welcome

- **WHEN** a user starts the `houmao-touring` guided tour in a workspace that already has a project overlay, reusable specialists, or running managed agents
- **THEN** the touring skill presents a short acknowledgement instead of the full welcome text
- **AND THEN** it presents the current-state orientation and the offered next branches first
- **AND THEN** it does not push the user back to the initial setup sequence

#### Scenario: Welcome is not repeated when the recent conversation already covered it

- **WHEN** the recent conversation already included the welcome text for `houmao-touring`
- **THEN** the touring skill does not re-emit the full welcome text on the next turn
- **AND THEN** it proceeds with current-state orientation and branch selection

### Requirement: `houmao-touring` orient branch uses an explicit posture-to-branch routing matrix

The packaged `houmao-touring` skill orient branch SHALL include an explicit routing table that maps inspected workspace posture to the set of next-likely branches.

That routing table SHALL at minimum cover the postures "no overlay and no specialists and no running agents", "overlay exists without specialists", "specialists exist without running agents", "one or more running managed agents", and "multi-agent workspace".

The orient branch SHALL use that table as the source of truth for offering next branches rather than re-deriving routing in free prose on each turn.

The offered next branches SHALL remain offers rather than mandates; the orient branch SHALL NOT force the user into exactly one branch when more than one is reasonable for the inspected posture.

#### Scenario: Empty workspace posture offers quickstart and setup branches

- **WHEN** the orient branch inspects a workspace with no project overlay, no reusable specialists, and no running managed agents
- **THEN** it uses the routing table to offer the quickstart branch and the project-and-mailbox setup branch
- **AND THEN** it explains that the quickstart branch is a minimum-viable-launch path and the setup branch is the explicit project-overlay path

#### Scenario: Post-launch posture offers live-operations and lifecycle branches

- **WHEN** the orient branch inspects a workspace with one or more running managed agents
- **THEN** it uses the routing table to offer the live-operations branch and the lifecycle follow-up branch
- **AND THEN** it does not treat setup branches as the primary next step

#### Scenario: Multi-agent workspace posture offers advanced-usage and live-operations branches

- **WHEN** the orient branch inspects a workspace with more than one running managed agent
- **THEN** it uses the routing table to offer the advanced-usage branch and the live-operations branch
- **AND THEN** it does not require the user to choose advanced-usage; the advanced-usage branch remains one of several offered options

### Requirement: `houmao-touring` offers a quickstart branch that detects available host CLI tools

The packaged `houmao-touring` skill SHALL include a quickstart branch that helps a user reach one running managed agent with the minimum number of decisions.

The quickstart branch SHALL detect which supported tool CLIs are available on the host by running a presence check such as `command -v <tool>` for each tool adapter supported by the packaged Houmao distribution.

The quickstart branch SHALL list the detected tools to the user without priority, without ordering that implies recommendation, and without marking any detected tool as the default or preferred tool.

When no supported tool CLI is detected on the host, the quickstart branch SHALL explain which tool CLIs Houmao supports and SHALL NOT attempt to launch a managed agent.

The quickstart branch SHALL route the actual specialist authoring, credential attachment, and easy-instance launch work through the maintained downstream skills (`houmao-specialist-mgr` and related) rather than restating their command shapes.

#### Scenario: Host has one supported tool CLI

- **WHEN** the quickstart branch detects exactly one supported tool CLI on the host
- **THEN** it lists that tool and explains the user can launch a minimum-viable specialist with it
- **AND THEN** it routes specialist authoring and launch through `houmao-specialist-mgr`

#### Scenario: Host has multiple supported tool CLIs

- **WHEN** the quickstart branch detects more than one supported tool CLI on the host
- **THEN** it lists the detected tools without priority, without ordering that implies recommendation, and without naming any of them as the default
- **AND THEN** it asks the user to pick one before proceeding

#### Scenario: Host has no supported tool CLI

- **WHEN** the quickstart branch detects no supported tool CLI on the host
- **THEN** it explains which tool CLIs Houmao supports
- **AND THEN** it does not attempt to launch a managed agent in that turn

### Requirement: `houmao-touring` advanced-usage branch enumerates the broader advanced feature surface

The packaged `houmao-touring` advanced-usage branch SHALL enumerate the broader advanced Houmao feature surface as a flat list of brief entries, with one entry per advanced Houmao-owned skill or advanced feature area.

Each entry SHALL be short (roughly one to two sentences) and SHALL name the owning skill that the user can invoke or select when they want to go deeper on that entry.

The advanced-usage branch SHALL cover at minimum the following advanced entries:

- pairwise loop plan authoring and run control through `houmao-agent-loop-pairwise`,
- enriched pairwise loop plan authoring and extended run control through `houmao-agent-loop-pairwise-v2`,
- generic pairwise plus relay loop graph planning through `houmao-agent-loop-generic`,
- elemental immediate driver-worker edge protocol and related composed patterns through `houmao-adv-usage-pattern`,
- managed-agent `houmao-memo.md` and contained pages memory through `houmao-memory-mgr`,
- gateway mail-notifier and reminder surfaces through `houmao-agent-gateway`,
- project-local credential management through `houmao-credential-mgr`,
- low-level role and preset authoring through `houmao-agent-definition`.

The advanced-usage branch SHALL NOT mark any enumerated entry as the recommended, preferred, primary, or default advanced feature. It SHALL NOT order the entries to imply a priority ranking.

The advanced-usage branch SHALL NOT restate composed pairwise loop plan templates, run charters, routing packets, mailbox result protocol, reminder protocol, memory file layouts, or credential lifecycle details inline; those belong to the selected owning skill.

#### Scenario: Advanced-usage branch lists entries as a flat brief list with no priority

- **WHEN** the user reaches the advanced-usage branch
- **THEN** the touring skill presents the advanced entries as a flat list of brief entries
- **AND THEN** it does not mark any entry as recommended, preferred, primary, or default
- **AND THEN** the pairwise entries appear alongside the other advanced entries without being elevated or demoted

#### Scenario: Advanced-usage branch routes each entry to its owning skill

- **WHEN** the user picks one enumerated advanced entry
- **THEN** the touring skill tells the agent to invoke or select the owning skill named in that entry
- **AND THEN** it does not attempt to restate the detailed workflow for that entry inline

#### Scenario: Advanced-usage branch omits none of the minimum enumerated entries

- **WHEN** the advanced-usage branch is rendered
- **THEN** it includes entries for `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-generic`, `houmao-adv-usage-pattern`, `houmao-memory-mgr`, `houmao-agent-gateway`, `houmao-credential-mgr`, and `houmao-agent-definition`
- **AND THEN** it continues to honour the existing pairwise routing guidance encoded in the pairwise loop creation requirement

### Requirement: `houmao-touring` ships a self-contained concepts reference

The packaged `houmao-touring` skill SHALL ship a concepts reference file at `references/concepts.md` inside its packaged asset directory.

That concepts reference SHALL be a compact self-contained glossary of the vocabulary the tour uses, including at minimum `specialist`, `easy profile`, `launch profile`, `managed agent`, `recipe`, `tool adapter`, `project overlay`, `gateway`, `gateway sidecar`, `mailbox root`, `mailbox account`, `principal id`, `user agent`, `master`, `loop plan`, `relaunch`, and `cleanup`.

Each glossary entry SHALL be short (roughly one to three sentences) and SHALL cross-reference the owning Houmao-owned skill when such a skill exists, so that deeper detail remains on the owning skill rather than duplicated in the glossary.

The concepts reference SHALL be usable as a standalone file without reading any other file in the repository.

The touring `SKILL.md` and touring branch pages SHALL be allowed to cite `references/concepts.md` for vocabulary grounding.

#### Scenario: Concepts reference is present inside the packaged asset directory

- **WHEN** the packaged `houmao-touring` skill is installed on a user workspace
- **THEN** `references/concepts.md` is present inside the installed asset directory
- **AND THEN** it is reachable without depending on any file outside the packaged asset directory

#### Scenario: Concepts reference covers the minimum vocabulary

- **WHEN** the tour cites the concepts reference during an explanation
- **THEN** the reference defines `specialist`, `easy profile`, `launch profile`, `managed agent`, `recipe`, `tool adapter`, `project overlay`, `gateway`, `gateway sidecar`, `mailbox root`, `mailbox account`, `principal id`, `user agent`, `master`, `loop plan`, `relaunch`, and `cleanup`
- **AND THEN** each entry stays compact and cross-references the owning skill when applicable

### Requirement: `houmao-touring` content is self-contained inside its packaged asset directory

All content that the packaged `houmao-touring` skill reads, links, or instructs the agent to read SHALL live inside `src/houmao/agents/assets/system_skills/houmao-touring/`.

The touring skill SHALL NOT reference paths under the development-only parts of the repository (including but not limited to `examples/`, `docs/`, `magic-context/`, and `openspec/`) because those paths are not present in the pypi-distributed wheel.

The touring skill SHALL NOT reference files that only exist in the source repository checkout and therefore disappear after `pip install`.

This self-containment rule SHALL apply to `SKILL.md`, every file under `branches/`, every file under `references/`, and any future file added to the packaged asset directory.

#### Scenario: Touring content does not reference repo-only paths

- **WHEN** a reviewer audits the packaged `houmao-touring` skill content
- **THEN** no reference, link, or instructional sentence points at a path outside `src/houmao/agents/assets/system_skills/houmao-touring/`
- **AND THEN** the skill remains fully usable against a pypi-installed Houmao distribution

#### Scenario: Installed touring skill works without the source repository

- **WHEN** the `houmao-touring` skill is invoked on a host that only has the pypi-installed Houmao distribution and does not have a clone of the Houmao source repository
- **THEN** every branch page and reference cited by `SKILL.md` is reachable
- **AND THEN** the user-facing tour experience is identical to running the tour from a source checkout
