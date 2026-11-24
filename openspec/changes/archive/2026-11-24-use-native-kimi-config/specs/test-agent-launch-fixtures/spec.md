# Spec Delta

## ADDED Requirements

### Requirement: Kimi fixtures share a native model catalog across launch surfaces

Both Kimi API fixture cases SHALL write a private native `config.toml` from their selected provider, endpoint, alias, and model metadata. Raw and managed launches SHALL use the same configuration inputs. Fixture models that offer multiple thinking levels SHALL declare ordered native labels in `support_efforts`. Config-owned values SHALL be absent from launch env.

#### Scenario: Kimi API fixtures run the same config-backed model directly and through Houmao

- **WHEN** a developer prepares the same Kimi API case with an explicitly selected endpoint, model, and metadata for raw and managed launch
- **THEN** both private homes use the same provider type, endpoint, model ID, alias, and capabilities in native config
- **AND THEN** the fixture uses the selected credential without requiring OAuth token storage or an env-model selector

#### Scenario: A private fixture config is sufficient for managed numeric reasoning

- **WHEN** an explicitly selected Kimi model exposes multiple efforts and its fixture credential config declares the ordered labels
- **AND WHEN** the managed Web launch selects that alias and a numeric reasoning level through the project profile
- **THEN** launch succeeds with the native label at the selected position and Kimi exposes its configured effort options
- **AND THEN** the setup bundle needs no duplicate catalog and neither the owning tmux session nor an ordinary pane has config-owned Kimi env bindings
