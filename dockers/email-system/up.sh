#!/usr/bin/env sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/../.." && pwd)

set -a
. "${SCRIPT_DIR}/.env"
set +a

docker compose --env-file "${SCRIPT_DIR}/.env" -f "${SCRIPT_DIR}/compose.yaml" up -d --pull never

cd "${REPO_ROOT}"
pixi run python "${SCRIPT_DIR}/provision_stalwart.py" --env-file "${SCRIPT_DIR}/.env" ensure-defaults --wait

printf 'Stalwart webadmin: http://127.0.0.1:%s\n' "${STALWART_HTTP_PORT}"
printf 'Cypht webmail: http://127.0.0.1:%s\n' "${CYPHT_HTTP_PORT}"
printf 'Seeded mailbox login: %s / %s\n' "${SEED_MAILBOX_NAME}" "${SEED_MAILBOX_PASSWORD}"
printf 'Seeded mailbox address: %s\n' "${SEED_MAILBOX_EMAIL}"
