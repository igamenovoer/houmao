# Tasks

## 1. Author the Packaged Manual

- [x] 1.1 Write the root and five catalog `index.md` files under `src/houmao/srv_ctrl/assets/manual/`. Verify the root maps common requests to entry pages and each catalog describes every page listed in the design.
- [x] 1.2 Write the six `start` and `prepare` pages. Walk through first launch, existing-project discovery, and deployment handoff against the maintained project CLI and confirm each page identifies the expected result.
- [x] 1.3 Write the eight `operate` and `communicate` pages. Check scoped selectors, run-mode evidence, readiness and retry guidance, mail delivery and wakeup, and the Web entry path against the current CLI and reference contracts.
- [x] 1.4 Write the three `coordinate` pages. Walk through a builder-to-reviewer handoff with an explicit artifact and workdirs, then verify the loop page points to the maintained Lite and Pro workflow and generated controls.

## 2. Expose the Manual in the CLI

- [x] 2.1 Register the `manual` group, catalogs, and leaves. Load the selected UTF-8 file from package resources and use the existing output context for plain, JSON, and fancy output. Verify root, catalog, and leaf reads and a missing-resource error.
- [x] 2.2 Add the root help pointer and a short manual section to the manager CLI reference. Update the exact root command inventory test and verify both forms of root help and the three documented navigation commands.
- [x] 2.3 Add focused CLI tests for index and command agreement, every leaf resource, normal `--help` and unknown-name errors, and output styles. Run the focused tests from an isolated directory with state discovery and mutation paths guarded against calls.

## 3. Verify the Release Path

- [x] 3.1 Build the wheel and sdist and verify all 23 Markdown resources are present in both. Invoke the wheel-installed CLI outside the repository with an isolated home and without project state, Houmao skills, or a live runtime. Read the root, a catalog, and a page in plain and JSON output.
- [x] 3.2 Run repository lint, type checking, unit tests, and the docs build. Run `openspec validate add-manager-operator-manual --strict` before marking the change ready for review.
