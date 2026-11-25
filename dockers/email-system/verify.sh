#!/usr/bin/env sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/../.." && pwd)

set -a
. "${SCRIPT_DIR}/.env"
set +a

docker compose --env-file "${SCRIPT_DIR}/.env" -f "${SCRIPT_DIR}/compose.yaml" ps
curl --noproxy '*' --fail --silent --show-error "http://127.0.0.1:${STALWART_WEBADMIN_PORT:-10082}/login" >/dev/null
curl --noproxy '*' --fail --silent --show-error "http://127.0.0.1:${CYPHT_HTTP_PORT}/" >/dev/null

cd "${REPO_ROOT}"
pixi run python "${SCRIPT_DIR}/provision_stalwart.py" --env-file "${SCRIPT_DIR}/.env" verify-defaults
pixi run python "${SCRIPT_DIR}/smoke_mail_flow.py" --env-file "${SCRIPT_DIR}/.env"

printf 'Verified stack endpoints and default Stalwart mailboxes.\n'
