#!/usr/bin/env sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

docker compose --env-file "${SCRIPT_DIR}/.env" -f "${SCRIPT_DIR}/compose.yaml" down
