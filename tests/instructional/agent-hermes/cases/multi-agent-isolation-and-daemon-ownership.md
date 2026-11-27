# Multi-Agent Isolation and Shared Gateway Ownership

Launch two Hermes workers from separate projects under one prepared test owner. Check shared native gateway and dependency identity, independent profiles and workspaces, and exact continuation after one worker stops. Follow the [suite setup](../README.md#launch) to select the prepared root and model pool.

## Launch Two Projects

```bash
CASE_EVIDENCE="$EVIDENCE/multi-agent-isolation-and-daemon-ownership"
mkdir -p "$CASE_EVIDENCE"
for slot in a b; do
  mode=service
  if [ "$slot" = b ]; then mode=tui; fi
  pixi run python "$FIXTURE" prepare \
    --pool-slot "$slot" --surface manager --mode "$mode" \
    --hermes-owner-root "$HOUMAO_TEST_HERMES_OWNER_ROOT" \
    --tmux-server new --prompt-mode unattended --reasoning-level 5 \
    --system-prompt-file "$BUNDLE_ROOT/helpers/roles/hermes-worker.md" \
    --run-root "$RUN_TMP/runtime/isolation-$slot" > "$CASE_EVIDENCE/$slot-prepare.json"
done
RUN_ISO_A="$(jq -er '.run_dir' "$CASE_EVIDENCE/a-prepare.json")"
RUN_ISO_B="$(jq -er '.run_dir' "$CASE_EVIDENCE/b-prepare.json")"
pixi run python "$FIXTURE" launch --run-dir "$RUN_ISO_A" > "$CASE_EVIDENCE/a-launch.json"
pixi run python "$FIXTURE" launch --run-dir "$RUN_ISO_B" > "$CASE_EVIDENCE/b-launch.json"
pixi run python "$FIXTURE" check --run-dir "$RUN_ISO_A" --live > "$CASE_EVIDENCE/a-native.json"
pixi run python "$FIXTURE" check --run-dir "$RUN_ISO_B" --live > "$CASE_EVIDENCE/b-native.json"
jq -e -s '
  .[0] as $a | .[1] as $b |
  $a.native_state as $x | $b.native_state as $y |
  $x.availability == "available" and $y.availability == "available" and
  $x.prepared_root == $y.prepared_root and $x.context_id == $y.context_id and
  $x.host == $y.host and $x.build == $y.build and
  $x.dependency_environment == $y.dependency_environment and
  $x.dependency_stamp == $y.dependency_stamp and
  $x.profile_id != $y.profile_id and $x.project_home_link != $y.project_home_link and
  $x.workspace != $y.workspace and $x.session_id != $y.session_id and
  $x.generation_id != $y.generation_id and $a.tmux_socket_path != $b.tmux_socket_path
' "$CASE_EVIDENCE/a-native.json" "$CASE_EVIDENCE/b-native.json" > "$CASE_EVIDENCE/shared-owner-check.json"
```

For each worker, compare the native evidence against the launch report and the actual project link. The live check independently redeems a profile-scoped native ticket, verifies the exact session and workspace, and checks the prepared dependency selection.

```bash
for slot in a b; do
  link="$(jq -er '.native_state.project_home_link' "$CASE_EVIDENCE/$slot-native.json")"
  profile="$(jq -er '.native_state.profile_id' "$CASE_EVIDENCE/$slot-native.json")"
  test -L "$link" && test "$(readlink -f "$link")" = "$profile"
  jq -e -s '.[0].identity.generation_id == .[1].native_state.generation_id' \
    "$CASE_EVIDENCE/$slot-launch.json" "$CASE_EVIDENCE/$slot-native.json" >/dev/null
done

pixi run python "$FIXTURE" prompt --run-dir "$RUN_ISO_A" \
  --prompt "Write alpha-anchor to whoami.txt in your workspace." > "$CASE_EVIDENCE/a-prompt.json"
pixi run python "$FIXTURE" prompt --run-dir "$RUN_ISO_B" \
  --prompt "Write beta-anchor to whoami.txt in your workspace." > "$CASE_EVIDENCE/b-prompt.json"
test "$(cat "$RUN_ISO_A/workdir/whoami.txt")" = "alpha-anchor"
test "$(cat "$RUN_ISO_B/workdir/whoami.txt")" = "beta-anchor"
```

## Stop and Resume One Profile

```bash
SID_A="$(jq -er '.native_state.session_id' "$CASE_EVIDENCE/a-native.json")"
pixi run python "$FIXTURE" stop --run-dir "$RUN_ISO_A" > "$CASE_EVIDENCE/a-stop.json"
pixi run python "$LAB" inspect-home --run-dir "$RUN_ISO_A" > "$CASE_EVIDENCE/a-parked.json"
jq -e '.profile_parked' "$CASE_EVIDENCE/a-parked.json" >/dev/null
pixi run python "$FIXTURE" check --run-dir "$RUN_ISO_B" --live > "$CASE_EVIDENCE/b-after-a-stop.json"
jq -e -s '.[0].native_state == .[1].native_state' \
  "$CASE_EVIDENCE/b-native.json" "$CASE_EVIDENCE/b-after-a-stop.json" >/dev/null

pixi run python "$LAB" manager --run-dir "$RUN_ISO_A" -- \
  relaunch --chat-session-mode exact --chat-session-id "$SID_A" > "$CASE_EVIDENCE/a-relaunch.json"
pixi run python "$FIXTURE" check --run-dir "$RUN_ISO_A" --live > "$CASE_EVIDENCE/a-native-resumed.json"
jq -e -s '
  .[0].native_state as $a | .[1].native_state as $b |
  $a.session_id == $b.session_id and $a.profile_id == $b.profile_id and
  $a.host == $b.host and $a.dependency_stamp == $b.dependency_stamp and
  $a.generation_id != $b.generation_id and $a.authority_epoch != $b.authority_epoch
' "$CASE_EVIDENCE/a-native.json" "$CASE_EVIDENCE/a-native-resumed.json" >/dev/null
```

## Remove the Profiles and Retire the Host

Stop each recorded worker, remove its retained session, and preview the build cleanup before applying it. Use only this case's dedicated owner runtime. Retire the host after every named profile in that installation has been removed.

```bash
OWNER_RUNTIME="$HOUMAO_TEST_HERMES_OWNER_ROOT/fixture-owner/runtime"
OWNER_REGISTRY="$HOUMAO_TEST_HERMES_OWNER_ROOT/fixture-owner/registry"
for slot in a b; do
  run_dir="$(jq -er '.run_dir' "$CASE_EVIDENCE/$slot-prepare.json")"
  pixi run python "$FIXTURE" stop --run-dir "$run_dir" > "$CASE_EVIDENCE/$slot-final-stop.json"
  pixi run python "$LAB" manager --run-dir "$run_dir" -- cleanup session \
    > "$CASE_EVIDENCE/$slot-session-cleanup.json"
  HOUMAO_GLOBAL_REGISTRY_DIR="$OWNER_REGISTRY" HOUMAO_HERMES_INSTALLATION_ROOT="$HOUMAO_TEST_HERMES_OWNER_ROOT" \
    "$HOUMAO_MGR" --print-json admin cleanup runtime builds --runtime-root "$OWNER_RUNTIME" --dry-run \
    > "$CASE_EVIDENCE/$slot-build-preview.json"
  HOUMAO_GLOBAL_REGISTRY_DIR="$OWNER_REGISTRY" HOUMAO_HERMES_INSTALLATION_ROOT="$HOUMAO_TEST_HERMES_OWNER_ROOT" \
    "$HOUMAO_MGR" --print-json admin cleanup runtime builds --runtime-root "$OWNER_RUNTIME" \
    > "$CASE_EVIDENCE/$slot-build-cleanup.json"
  link="$(jq -er '.native_state.project_home_link' "$CASE_EVIDENCE/$slot-native.json")"
  profile="$(jq -er '.native_state.profile_id' "$CASE_EVIDENCE/$slot-native.json")"
  test ! -e "$profile" && test ! -L "$link"
  if [ "$slot" = a ]; then
    pixi run python "$FIXTURE" check --run-dir "$RUN_ISO_B" --live \
      > "$CASE_EVIDENCE/b-after-a-cleanup.json"
  fi
done
pixi run python "$FIXTURE" retire-hermes-owner \
  --hermes-owner-root "$HOUMAO_TEST_HERMES_OWNER_ROOT" > "$CASE_EVIDENCE/host-retired.json"
jq -e '.host_exited' "$CASE_EVIDENCE/host-retired.json" >/dev/null
```

Keep the evidence and prepared installation. The retirement command verifies the saved native PID, process birth, and gateway incarnation before signaling through a pinned process descriptor. It refuses while any named profile remains in the selected root.
