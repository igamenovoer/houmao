# Design

This directory contains module, interface, and contract design notes for the Agent Loop Correctness Evaluator.

## Index

| Design Doc | Purpose | Status |
| --- | --- | --- |
| [Public Interfaces](public-interfaces.md) | Public skill commands, data models, and report formats | Not started |

## Module Map

- **Test-case design guide**: operator-facing guidance for deriving cases from execplan contracts.
- **Manifest model**: machine-readable test-case manifest schema.
- **Bounded-run harness**: isolated execution or replay driver for the loop under test.
- **Assertion engine**: compares observed behavior against expected invariants.
- **Report generator**: produces human-readable verdict reports.

## Open Questions

- Which assertion language should the manifest use?
- Should the harness be a new component or reuse an existing loop execution stage?
