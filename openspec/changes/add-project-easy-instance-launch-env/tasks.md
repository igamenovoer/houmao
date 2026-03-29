## 1. Specialist Env Records

- [x] 1.1 Add repeatable `--env-set NAME=value` to `houmao-mgr project easy specialist create` and surface persisted env records in specialist inspection output.
- [x] 1.2 Extend project-catalog persistence, compatibility preset rendering, and preset parsing for dedicated persistent `launch.env_records`.
- [x] 1.3 Validate specialist `--env-set` names against auth-env allowlists and Houmao-owned reserved env names.

## 2. Runtime Env Composition

- [x] 2.1 Extend brain construction and launch-plan composition so persistent specialist env records are stored separately from credential env and applied with the documented precedence.
- [x] 2.2 Add one-off `--env-set` to `houmao-mgr project easy instance launch` and resolve inherited bindings from the invoking process environment at launch time.
- [x] 2.3 Apply one-off instance-launch env to the current live session only without persisting it in specialist config, built manifests, or relaunch authority.

## 3. Verification And Docs

- [x] 3.1 Add tests for specialist `--env-set` persistence, credential-name collision rejection, one-off instance `--env-set` behavior, and relaunch dropping one-off env while preserving specialist env records.
- [x] 3.2 Update docs for `project easy specialist create|get` and `project easy instance launch`, including the two-channel env model and the separation from credential env.
