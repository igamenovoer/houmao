## 1. Skill Guidance

- [x] 1.1 Invoke `$skill-creator` before editing the packaged skill assets, per the existing skill spec.
- [x] 1.2 Update the top-level skill workflow to describe generic defaults for execplan scaffold, participant/agent bindings, stateful bookkeeping, harness services, event/tick skills, workspace contracts, and run artifacts.
- [x] 1.3 Keep the skill body concise and generic, with the version marker limited to the skill name/frontmatter and operation references that require the packaged name.

## 2. Authoring And Execution Subskills

- [x] 2.1 Update `generate-execplan` guidance to produce default package layers only when relevant, and to keep task-specific behavior derived from intention source or clarification decisions.
- [x] 2.2 Update `validate-execplan` guidance to check manifest metadata, participant/agent separation, default comms/state/workspace/harness/skill posture, and explicit omissions.
- [x] 2.3 Update `prepare-agents` guidance to consume generated workspace and agent-binding contracts while routing workspace creation, launch, mailbox, gateway, memory, and inspection work to maintained Houmao skills.
- [x] 2.4 Update status, recover, or related execution guidance only where needed to reference run artifact layout and harness validation surfaces.

## 3. Developer Design Docs

- [x] 3.1 Revise developer design notes to document the generic default scaffold profile and its extension points.
- [x] 3.2 Document the minimal stateful-loop bookkeeping kernel and the boundary between generic records and task-specific generated records.
- [x] 3.3 Document harness responsibilities, structured output envelope, `--explain` style metadata, and platform-operation boundaries.
- [x] 3.4 Document generated event/tick skill patterns without assuming a fixed participant topology.

## 4. Verification

- [x] 4.1 Run OpenSpec status or validation for `add-generic-loop-defaults` and resolve artifact issues.
- [x] 4.2 Review the changed skill Markdown for accidental domain-specific defaults or reference-example leakage.
- [x] 4.3 Review project skill symlink posture only if touched by the implementation; otherwise leave it unchanged.
