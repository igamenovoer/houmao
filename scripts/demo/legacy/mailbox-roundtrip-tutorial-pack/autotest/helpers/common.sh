#!/usr/bin/env bash

autotest_helper() {
  pixi run python "$AUTOTEST_HELPER_SCRIPT" "$@"
}

autotest_phase_stdout_path() {
  local label="$1"
  printf '%s/%s.stdout.txt\n' "$AUTOTEST_LOG_DIR" "$label"
}

autotest_phase_stderr_path() {
  local label="$1"
  printf '%s/%s.stderr.txt\n' "$AUTOTEST_LOG_DIR" "$label"
}

autotest_phase_argv_path() {
  local label="$1"
  printf '%s/%s.argv.txt\n' "$AUTOTEST_LOG_DIR" "$label"
}

autotest_write_command_log() {
  local output_path="$1"
  shift
  : >"$output_path"
  local arg
  for arg in "$@"; do
    printf '%q ' "$arg" >>"$output_path"
  done
  printf '\n' >>"$output_path"
}

autotest_run_logged_phase() {
  local label="$1"
  local timeout_seconds="$2"
  shift 2

  local stdout_path
  local stderr_path
  local argv_path
  stdout_path="$(autotest_phase_stdout_path "$label")"
  stderr_path="$(autotest_phase_stderr_path "$label")"
  argv_path="$(autotest_phase_argv_path "$label")"
  mkdir -p "$AUTOTEST_LOG_DIR"
  autotest_write_command_log "$argv_path" "$@"

  AUTOTEST_LAST_LABEL="$label"
  AUTOTEST_LAST_STDOUT_PATH="$stdout_path"
  AUTOTEST_LAST_STDERR_PATH="$stderr_path"
  AUTOTEST_LAST_ARGV_PATH="$argv_path"

  local exit_code
  set +e
  autotest_helper \
    run-with-timeout \
    --cwd "$AUTOTEST_REPO_ROOT" \
    --stdout-path "$stdout_path" \
    --stderr-path "$stderr_path" \
    --timeout-seconds "$timeout_seconds" \
    -- \
    "$@"
  exit_code=$?
  set -e
  if [[ "$exit_code" -eq 0 ]] && grep -q '^SKIP:' "$stdout_path" "$stderr_path"; then
    printf 'SKIP surfaced during phase %s\n' "$label" >>"$stderr_path"
    exit_code=65
  fi

  AUTOTEST_LAST_EXIT_CODE="$exit_code"
  return "$exit_code"
}

autotest_last_error_message() {
  if [[ "${AUTOTEST_LAST_EXIT_CODE:-1}" -eq 124 ]]; then
    printf 'phase `%s` exceeded %ss\n' "$AUTOTEST_LAST_LABEL" "$AUTOTEST_PHASE_TIMEOUT_SECONDS"
    return 0
  fi

  local detail=""
  if [[ -f "${AUTOTEST_LAST_STDERR_PATH:-}" ]]; then
    detail="$(grep -v '^[[:space:]]*$' "$AUTOTEST_LAST_STDERR_PATH" | tail -n 1 || true)"
  fi
  if [[ -z "$detail" ]] && [[ -f "${AUTOTEST_LAST_STDOUT_PATH:-}" ]]; then
    detail="$(grep -v '^[[:space:]]*$' "$AUTOTEST_LAST_STDOUT_PATH" | tail -n 1 || true)"
  fi
  if [[ -z "$detail" ]]; then
    detail="phase \`${AUTOTEST_LAST_LABEL}\` failed with exit code ${AUTOTEST_LAST_EXIT_CODE}"
  fi
  printf '%s\n' "$detail"
}

autotest_run_demo_phase() {
  local label="$1"
  local command_name="$2"
  shift 2

  local argv=(
    "$AUTOTEST_RUN_DEMO"
    "$command_name"
    "--demo-output-dir"
    "$AUTOTEST_DEMO_OUTPUT_DIR"
  )

  case "$command_name" in
    start)
      argv+=(
        "--jobs-dir"
        "$AUTOTEST_JOBS_DIR"
        "--parameters"
        "$AUTOTEST_PARAMETERS_PATH"
        "--cao-parsing-mode"
        "shadow_only"
      )
      ;;
    roundtrip|stop)
      argv+=("--cao-parsing-mode" "shadow_only")
      ;;
    verify)
      argv+=("--expected-report" "$AUTOTEST_EXPECTED_REPORT_PATH")
      ;;
  esac

  argv+=("$@")
  autotest_run_logged_phase "$label" "$AUTOTEST_PHASE_TIMEOUT_SECONDS" "${argv[@]}"
}

autotest_print_inspect_commands() {
  printf 'inspect commands:\n'
  printf '  %s inspect --demo-output-dir %q --agent sender\n' \
    "$AUTOTEST_RUN_DEMO" \
    "$AUTOTEST_DEMO_OUTPUT_DIR"
  printf '  %s inspect --demo-output-dir %q --agent receiver --json --with-output-text 400\n' \
    "$AUTOTEST_RUN_DEMO" \
    "$AUTOTEST_DEMO_OUTPUT_DIR"
}

autotest_write_result() {
  local status="$1"
  local phase="$2"
  local error_message="${3:-}"
  local timed_out="${4:-0}"
  local args=(
    write-autotest-result
    "--output"
    "$AUTOTEST_RESULT_PATH"
    "--pack-dir"
    "$AUTOTEST_PACK_DIR"
    "--demo-output-dir"
    "$AUTOTEST_DEMO_OUTPUT_DIR"
    "--case-id"
    "$AUTOTEST_CASE_ID"
    "--status"
    "$status"
    "--phase"
    "$phase"
    "--log-dir"
    "$AUTOTEST_LOG_DIR"
  )
  if [[ -n "${AUTOTEST_PREFLIGHT_RESULT_PATH:-}" ]]; then
    args+=("--preflight-result-path" "$AUTOTEST_PREFLIGHT_RESULT_PATH")
  fi
  if [[ -n "$error_message" ]]; then
    args+=("--error-message" "$error_message")
  fi
  if [[ "$timed_out" -eq 1 ]]; then
    args+=("--timed-out")
  fi
  if [[ "${AUTOTEST_ENFORCE_MAILBOX_PERSISTENCE:-0}" -eq 1 ]]; then
    args+=("--enforce-mailbox-persistence")
  fi
  autotest_helper "${args[@]}"
}

autotest_best_effort_stop() {
  if [[ ! -f "$AUTOTEST_DEMO_OUTPUT_DIR/control/demo_state.json" ]]; then
    return 0
  fi
  autotest_run_demo_phase "99-stop-after-failure" stop >/dev/null 2>&1 || true
}

autotest_run_preflight_case() {
  autotest_helper \
    real-agent-preflight \
    --output "$AUTOTEST_RESULT_PATH" \
    --repo-root "$AUTOTEST_REPO_ROOT" \
    --pack-dir "$AUTOTEST_PACK_DIR" \
    --parameters "$AUTOTEST_PARAMETERS_PATH" \
    --demo-output-dir "$AUTOTEST_DEMO_OUTPUT_DIR" \
    --jobs-dir "$AUTOTEST_JOBS_DIR" \
    --registry-dir "$AUTOTEST_REGISTRY_DIR" \
    --case-id "$AUTOTEST_CASE_ID"
}

autotest_execute_roundtrip_case() {
  local success_phase="$1"
  AUTOTEST_ENFORCE_MAILBOX_PERSISTENCE=1
  AUTOTEST_PREFLIGHT_RESULT_PATH="$AUTOTEST_TESTPLAN_DIR/${AUTOTEST_CASE_BASENAME}.preflight.json"
  local preflight_cache_path
  local original_log_dir
  local start_log_cache_dir
  preflight_cache_path="$(mktemp "${TMPDIR:-/tmp}/${AUTOTEST_CASE_BASENAME}.preflight.XXXXXX.json")"
  original_log_dir="$AUTOTEST_LOG_DIR"
  start_log_cache_dir="$(mktemp -d "${TMPDIR:-/tmp}/${AUTOTEST_CASE_BASENAME}.logs.XXXXXX")"

  if ! autotest_helper \
    real-agent-preflight \
    --output "$preflight_cache_path" \
    --repo-root "$AUTOTEST_REPO_ROOT" \
    --pack-dir "$AUTOTEST_PACK_DIR" \
    --parameters "$AUTOTEST_PARAMETERS_PATH" \
    --demo-output-dir "$AUTOTEST_DEMO_OUTPUT_DIR" \
    --jobs-dir "$AUTOTEST_JOBS_DIR" \
    --registry-dir "$AUTOTEST_REGISTRY_DIR" \
    --case-id "$AUTOTEST_CASE_ID"; then
    mkdir -p "$AUTOTEST_TESTPLAN_DIR"
    cp "$preflight_cache_path" "$AUTOTEST_PREFLIGHT_RESULT_PATH"
    autotest_write_result failure preflight "real-agent preflight failed" 0 || true
    return 1
  fi

  AUTOTEST_LOG_DIR="$start_log_cache_dir"
  if ! autotest_run_demo_phase "01-start" start; then
    AUTOTEST_LOG_DIR="$original_log_dir"
    mkdir -p "$AUTOTEST_LOG_DIR"
    cp "$start_log_cache_dir"/01-start.* "$AUTOTEST_LOG_DIR"/ 2>/dev/null || true
    local timed_out=0
    [[ "${AUTOTEST_LAST_EXIT_CODE}" -eq 124 ]] && timed_out=1
    autotest_best_effort_stop
    autotest_write_result failure start "$(autotest_last_error_message)" "$timed_out" || true
    return 1
  fi
  AUTOTEST_LOG_DIR="$original_log_dir"

  mkdir -p "$AUTOTEST_TESTPLAN_DIR"
  cp "$preflight_cache_path" "$AUTOTEST_PREFLIGHT_RESULT_PATH"
  mkdir -p "$AUTOTEST_LOG_DIR"
  cp "$start_log_cache_dir"/01-start.* "$AUTOTEST_LOG_DIR"/ 2>/dev/null || true

  autotest_print_inspect_commands

  if ! autotest_run_demo_phase "02-roundtrip" roundtrip; then
    local timed_out=0
    [[ "${AUTOTEST_LAST_EXIT_CODE}" -eq 124 ]] && timed_out=1
    autotest_best_effort_stop
    autotest_write_result failure roundtrip "$(autotest_last_error_message)" "$timed_out" || true
    return 1
  fi

  if ! autotest_run_demo_phase "03-verify" verify; then
    local timed_out=0
    [[ "${AUTOTEST_LAST_EXIT_CODE}" -eq 124 ]] && timed_out=1
    autotest_best_effort_stop
    autotest_write_result failure verify "$(autotest_last_error_message)" "$timed_out" || true
    return 1
  fi

  if ! autotest_run_demo_phase "04-stop" stop; then
    local timed_out=0
    [[ "${AUTOTEST_LAST_EXIT_CODE}" -eq 124 ]] && timed_out=1
    autotest_write_result failure stop "$(autotest_last_error_message)" "$timed_out" || true
    return 1
  fi

  autotest_write_result success "$success_phase"
}
