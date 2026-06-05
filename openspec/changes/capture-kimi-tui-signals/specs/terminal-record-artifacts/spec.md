## ADDED Requirements

### Requirement: Recorder artifacts support style-preserving Kimi high-rate capture
The terminal recorder SHALL support Kimi tool identity for capture runs and SHALL preserve ANSI/style-bearing pane text for Kimi replay analysis.

For Kimi signal investigation, the recorder SHALL be able to write capture runs under a caller-selected repo-local run root such as `tmp/kimi-tui-tracking/<run-id>/`.

The recorder SHALL support sampling intervals suitable for about 10 fps capture. Recorder metadata SHALL record the configured sample interval and enough target metadata to replay or inspect the captured pane later.

#### Scenario: Kimi capture accepts Kimi tool identity
- **WHEN** a maintainer starts a terminal recorder run with `--tool kimi`
- **THEN** the recorder persists `tool = kimi` in the manifest
- **AND THEN** later analysis can select Kimi parser and tracker behavior from that manifest

#### Scenario: Kimi high-rate capture preserves ANSI style data
- **WHEN** the recorder samples a Kimi TUI pane at about 10 fps
- **THEN** each replay-grade pane snapshot preserves ANSI escape data from the captured pane
- **AND THEN** Kimi detector development can inspect style facts such as dim, bold, color, focused border, or selected row rendering

### Requirement: Recorder artifacts support derived low-rate snapshot streams
The recorder or companion tooling SHALL support deriving a low-rate snapshot stream from an existing high-rate pane snapshot stream.

The derived stream SHALL preserve timing metadata, stable sample identifiers, and traceability to the source high-rate sample selected for each derived frame.

The derived stream SHALL live beside the source stream in the same run root or in a clearly linked derived run root.

#### Scenario: Derived 2 fps stream records source sample mapping
- **WHEN** a maintainer derives an about 2 fps stream from one about 10 fps Kimi capture
- **THEN** each derived sample records the high-rate source sample id it came from
- **AND THEN** replay validation can explain failures against either sample cadence

#### Scenario: Derived stream does not require another live Kimi run
- **WHEN** a high-rate Kimi capture already exists
- **THEN** the low-rate stream is produced from persisted snapshots
- **AND THEN** the maintainer does not need to repeat the live Kimi scenario to obtain low-rate evidence

### Requirement: Recorder sampling SHALL remain replay-grade even when visual cast recording degrades
For signal-corpus capture, the machine-readable pane snapshot stream SHALL remain the authoritative artifact even if the human-facing terminal cast recorder exits early or becomes unavailable.

When the visual cast recorder fails or exits before the requested capture is complete, the recorder SHALL either continue snapshot sampling when safe or mark the run with explicit taint metadata that distinguishes cast degradation from pane-snapshot loss.

#### Scenario: Cast recorder exit does not silently invalidate snapshots
- **WHEN** the visual cast recorder exits during a Kimi capture but pane snapshot sampling continues
- **THEN** the run metadata records the visual recording degradation
- **AND THEN** the persisted pane snapshots remain usable as replay-grade evidence

