#!/usr/bin/env sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/../.." && pwd)
ENV_FILE="${SCRIPT_DIR}/.env"
STALWART_DATA_DIR="${SCRIPT_DIR}/.data/stalwart-v1"

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
cd "${REPO_ROOT}"
configured_file="${STALWART_DATA_DIR}/.houmao-configured"
settings=$(printf '%s\n' "${MAIL_DOMAIN}" "${STALWART_HOSTNAME}" "${STALWART_HTTP_PORT}" \
    "${STALWART_WEBADMIN_PORT:-10082}" "${STALWART_IMAP_PORT}" "${STALWART_SUBMISSION_PORT}")
if [ "$(cat "${configured_file}" 2>/dev/null || true)" != "${settings}" ]; then
    if [ -f "${configured_file}" ]; then
        compose stop bulwark jmap-http stalwart
    fi
    mkdir -p "${STALWART_DATA_DIR}"
    compose run --rm -T --no-deps --user 0:0 --entrypoint chown stalwart 2000:2000 /var/lib/stalwart
    bootstrap_container="${STACK_PROJECT_NAME}-stalwart-bootstrap"
    compose run --rm -d --no-deps --name "${bootstrap_container}" \
        --publish "127.0.0.1:${STALWART_HTTP_PORT}:8080" \
        -e STALWART_RECOVERY_MODE=1 -e STALWART_PUBLIC_URL= stalwart >/dev/null
    trap 'docker stop "${bootstrap_container}" >/dev/null 2>&1 || true' EXIT
    trap 'exit 1' HUP INT TERM
    pixi run python "${SCRIPT_DIR}/provision_stalwart.py" --env-file "${ENV_FILE}" configure-server
    printf '%s\n' "${settings}" | docker exec -i "${bootstrap_container}" sh -c '
        cat > /var/lib/stalwart/.houmao-configured.tmp &&
        mv /var/lib/stalwart/.houmao-configured.tmp /var/lib/stalwart/.houmao-configured
    '
    docker stop "${bootstrap_container}" >/dev/null
    trap - EXIT HUP INT TERM
fi

compose up -d --pull never --wait --wait-timeout 90
pixi run python "${SCRIPT_DIR}/provision_stalwart.py" --env-file "${ENV_FILE}" ensure-defaults --wait

printf 'Stalwart webadmin: https://127.0.0.1:%s/admin/\n' "${STALWART_WEBADMIN_PORT:-10082}"
printf 'Bulwark webmail: http://127.0.0.1:%s/\n' "${BULWARK_HTTP_PORT:-10081}"
printf 'Seeded mailbox login: %s\n' "${SEED_MAILBOX_NAME}"
printf 'Seeded mailbox address: %s\n' "${SEED_MAILBOX_EMAIL}"
