# Launch Profiles

This tracked root exists so plain direct-dir helpers can exercise the filesystem-backed `launch-profiles/*.yaml` contract when needed.

The current maintained fixture lane does not ship one default launch profile here, but direct-dir credential helpers still treat this path as part of the supported contract when a copied temp root adds one.
