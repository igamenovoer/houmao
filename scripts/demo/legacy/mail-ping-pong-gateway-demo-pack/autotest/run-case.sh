#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CASE_NAME=""
FORWARD_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --case)
            if [[ $# -lt 2 ]]; then
                echo "missing value for --case" >&2
                exit 2
            fi
            CASE_NAME="$2"
            shift 2
            ;;
        *)
            FORWARD_ARGS+=("$1")
            shift
            ;;
    esac
done

if [[ -z "$CASE_NAME" ]]; then
    echo "usage: run-case.sh --case unattended-full-run [--demo-output-dir <path>]" >&2
    exit 2
fi

case "$CASE_NAME" in
    unattended-full-run|01)
        exec "$SCRIPT_DIR/case-unattended-full-run.sh" "${FORWARD_ARGS[@]}"
        ;;
    *)
        echo "unknown case: $CASE_NAME" >&2
        echo "known cases: unattended-full-run" >&2
        exit 2
        ;;
esac
