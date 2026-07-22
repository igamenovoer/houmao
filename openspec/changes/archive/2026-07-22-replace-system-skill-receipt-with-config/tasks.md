## 1. Minimal Configuration Model

- [x] 1.1 Replace receipt constants and data models with `houmao-skill-config.v1` config models and the `houmao-skill-config.json` path.
- [x] 1.2 Implement exact minimal serialization and strict parsing for the four top-level and four per-skill fields.
- [x] 1.3 Derive manifest-ordered selected pack ids from per-skill owner sets and validate the exact installed union.
- [x] 1.4 Remove receipt schema parsing, receipt migration statuses, legacy composed-receipt models, and compatibility aliases.

## 2. Transactional Lifecycle

- [x] 2.1 Update install and sync to consume config ownership, write the config last, and return `config_path`.
- [x] 2.2 Update upgrade to refresh only new-config or clean installations without reading receipt state.
- [x] 2.3 Update partial and final uninstall to rewrite or remove the minimal config while retaining shared owners.
- [x] 2.4 Update rollback helpers and transaction state to restore only new-format config bytes.
- [x] 2.5 Preserve unowned collision protection when old roots or an ignored `receipt.json` exist without a new config.

## 3. Public and Command Surfaces

- [x] 3.1 Rename the public system-skills facade exports and call sites from receipt to config terminology.
- [x] 3.2 Rename doctor config evidence while preserving direct configless installed-root health checks.
- [x] 3.3 Rename structured CLI fields and plain renderers to `config`, `config_path`, and `Skill config:`.
- [x] 3.4 Rename managed brain-construction provenance from `receipt_path` to `config_path`.

## 4. Tests

- [x] 4.1 Add lifecycle tests for the exact minimal config payload, derived pack selection, strict validation, and the new filename.
- [x] 4.2 Add lifecycle tests for shared-owner partial uninstall, final config removal, rollback, and receipt ignorance.
- [x] 4.3 Update doctor tests for config evidence, stored Houmao version, and healthy configless static packs.
- [x] 4.4 Update CLI and managed-construction tests to require config terminology and reject current receipt fields.

## 5. Documentation and Validation

- [x] 5.1 Rewrite the system-skills reference around the minimal config, version meanings, and breaking clean-reinstall procedure.
- [x] 5.2 Remove current receipt terminology from maintained source, CLI help/output, README guidance, and current documentation outside historical OpenSpec artifacts.
- [x] 5.3 Run focused system-skill lifecycle, doctor, CLI, managed-construction, and documentation tests.
- [x] 5.4 Run formatting, lint, type checking, diff checks, and strict OpenSpec validation.
