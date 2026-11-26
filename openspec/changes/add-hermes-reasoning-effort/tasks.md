# Tasks

## 1. Managed Launch Projection

- [x] 1.1 Add the validated native Hermes effort type and its ordered ladder to tool parameters and shared model mapping. Extend `test_model_mapping_policy.py` to verify every index, level-zero behavior, saturation, negative-level rejection, and the nested YAML projection target.
- [x] 1.2 Resolve the winning effort before home preparation and pass it to the atomic Hermes config writer. Record the effective effort and source in launch provenance. Extend `test_hermes_configuration.py` to inspect built homes for omission, exact `xhigh`, numeric `5` and `0`, precedence, and rejection of invalid native input before the home is touched.
- [x] 1.3 Update the Hermes run-mode reference with the launch preset ladder, native tool parameter, and precedence. Check the examples against the build tests.

## 2. Fixture and Model-Pool Inputs

- [x] 2.1 Validate exact labels, manager fixture levels, and Hermes-incompatible reasoning options during fixture resolution. Verify in fixture tests that `check` and `prepare` reject invalid inputs before allocation and that a raw numeric selection directs the user to an exact label.
- [x] 2.2 Forward the native effort to raw home preparation and to the generated manager setup. Carry a manager level through the generated profile. Extend `test_agent_fixture_tools.py` and `test_model_pool_fixture.py` to compare direct and pooled inputs, inspect raw YAML and the manager setup and profile, and verify that an explicit numeric CLI level overrides a pooled level.
- [x] 2.3 Update fixture help and README with the exact-effort flag, a reusable Hermes pool entry, and the manager `--reasoning-level 5` example. Verify that the CLI help and examples match the tested selection rules.

## 3. End-to-End Reasoning Evidence

- [x] 3.1 Extend the synthetic Chat Completions peer to capture the top-level effort. Run stock Hermes against that peer on the normal raw and manager fixture paths with synthetic credentials and isolated fixture resources. Verify `xhigh` and `none` on the first matching main-model requests and inspect the managed home recorded by the launch.
- [x] 3.2 Run the focused model-mapping, Hermes configuration, fixture, and model-pool tests together. Run repository lint and type checks to verify the new validation and projection paths integrate with existing callers.
