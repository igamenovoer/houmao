## 1. Remove Obsolete Test Contracts

- [x] 1.1 Delete the demo unit test whose expected command is `project easy instance launch`.
- [x] 1.2 Confirm no maintained test asserts a successful `project easy ...` command vector while retaining the negative command-tree assertion.

## 2. Rename Retained Coverage

- [x] 2.1 Rename specialist and profile unit tests from `project_easy` terminology to the supported project command terminology.
- [x] 2.2 Rename project-agent unit and integration tests from `project_easy_instance` terminology to `project_agents` terminology and update stale docstrings.
- [x] 2.3 Confirm retained tests continue invoking `project specialist`, `project profile`, and `project agents` paths.

## 3. Verification

- [x] 3.1 Run the focused project command, CLI-shape, system-skill, and demo unit tests affected by the cleanup.
- [x] 3.2 Run lint or equivalent static validation for the edited test files and validate the OpenSpec change strictly.
