## ADDED Requirements

### Requirement: CLI reference points Kimi automation at unattended prompt mode
The CLI reference SHALL document `launch.prompt_mode: unattended` and the corresponding project/profile prompt-mode flags as the supported Houmao-facing way to run Kimi Code without permission dialogs or user questions.

The CLI reference SHALL NOT present Kimi `--yolo` as a current Houmao launch option for achieving unattended behavior.

The CLI reference MAY mention Kimi provider-native `--auto` only as implementation background or low-level provider behavior, not as the recommended Houmao managed launch control.

#### Scenario: Reader finds supported Kimi no-question launch control
- **WHEN** a reader looks up how to run a Kimi managed agent automatically
- **THEN** the CLI reference points them to `launch.prompt_mode: unattended` or the matching project/profile prompt-mode CLI controls
- **AND THEN** it does not instruct them to pass `--yolo`

#### Scenario: Reader does not need raw Kimi flags for managed launch
- **WHEN** a reader looks up Kimi project specialist or project profile launch options
- **THEN** the reference describes prompt mode as the managed automation control
- **AND THEN** it does not require raw launch overrides with Kimi `--auto` for ordinary managed unattended launch
