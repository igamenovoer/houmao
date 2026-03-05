# Claude Variant Inventory

Fixture matrix for Claude shadow parser presets:

- `exact_preset_match.txt`: exact version/preset match (`v2.1.62`)
- `floor_preset_unknown_version.txt`: unknown newer banner version (`v9.9.9`) using floor preset + anomaly
- `drifted_unknown.txt`: unsupported/drifted format expected to fail with `unsupported_output_format`
