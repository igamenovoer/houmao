#!/usr/bin/env sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/../.." && pwd)
ENV_FILE="${SCRIPT_DIR}/.env"

usage() {
    printf 'Usage: %s [--pull-missing-images]\n' "$0"
}

if [ "$#" -gt 1 ]; then
    usage >&2
    exit 2
fi
pull_missing_images=false
case "${1:-}" in
    "") ;;
    --pull-missing-images) pull_missing_images=true ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
esac

if [ ! -e "${ENV_FILE}" ]; then
    (
        env_copy=$(mktemp "${ENV_FILE}.tmp.XXXXXX")
        trap 'rm -- "$env_copy"' EXIT
        chmod 600 "${env_copy}"
        cat "${SCRIPT_DIR}/env.example" >"${env_copy}"
        ln "${env_copy}" "${ENV_FILE}" || [ -f "${ENV_FILE}" ]
    )
fi

set -a
. "${ENV_FILE}"
set +a

compose() {
    docker compose --env-file "${ENV_FILE}" -f "${SCRIPT_DIR}/compose.yaml" "$@"
}

if [ "${pull_missing_images}" = true ]; then
    images=$(compose config --images)
    for image in ${images}; do
        if ! docker image inspect "${image}" >/dev/null 2>&1; then
            docker pull "${image}"
        fi
    done
fi
compose up -d --pull never --wait

cd "${REPO_ROOT}"
pixi run python "${SCRIPT_DIR}/provision_stalwart.py" --env-file "${ENV_FILE}" ensure-defaults --wait

printf 'Stalwart webadmin: http://127.0.0.1:%s/login\n' "${STALWART_WEBADMIN_PORT:-10082}"
printf 'Cypht webmail: http://127.0.0.1:%s\n' "${CYPHT_HTTP_PORT}"
printf 'Seeded mailbox login: %s\n' "${SEED_MAILBOX_NAME}"
printf 'Seeded mailbox address: %s\n' "${SEED_MAILBOX_EMAIL}"
