#!/usr/bin/env sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DATA_DIR="${SCRIPT_DIR}/.data"
SEED_CONFIG="${SCRIPT_DIR}/config/config.json"
BCRYPT_JS="${SCRIPT_DIR}/../../../extern/orphan/filestash/public/assets/lib/vendor/bcrypt.js"

set -a
. "${SCRIPT_DIR}/.env"
set +a

if ! command -v node >/dev/null 2>&1; then
    printf 'node is required to render the Filestash admin password from %s/.env\n' "${SCRIPT_DIR}" >&2
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    printf 'jq is required to render the Filestash runtime config\n' >&2
    exit 1
fi

: "${FILESTASH_DEFAULT_PASSWORD:?FILESTASH_DEFAULT_PASSWORD must be set in ${SCRIPT_DIR}/.env}"

mkdir -p "${DATA_DIR}" "${DATA_DIR}/config" "${DATA_DIR}/db" "${DATA_DIR}/log"
chmod 0777 "${DATA_DIR}" "${DATA_DIR}/config" "${DATA_DIR}/db" "${DATA_DIR}/log"

FILESTASH_ADMIN_BCRYPT=$(
    node --input-type=module - "${FILESTASH_DEFAULT_PASSWORD}" "${BCRYPT_JS}" <<'JS'
import { randomBytes } from "node:crypto";

const [, , password, bcryptPath] = process.argv;
const { default: bcrypt } = await import(`file://${bcryptPath}`);

bcrypt.setRandomFallback((len) => Array.from(randomBytes(len)));
process.stdout.write(`${bcrypt.hashSync(password)}\n`);
JS
)

TMP_CONFIG=$(mktemp "${DATA_DIR}/config/config.json.tmp.XXXXXX")
jq \
    --arg admin_hash "${FILESTASH_ADMIN_BCRYPT}" \
    --arg label "${FILESTASH_CONNECTION_LABEL}" \
    --arg repo_path "${FILESTASH_REPO_MOUNT_PATH}" \
    '
    .auth.admin = $admin_hash
    | .middleware.attribute_mapping.related_backend = $label
    | .middleware.attribute_mapping.params = ({($label): {type: "local", password: "{{ .password }}", path: $repo_path}} | tojson)
    | .connections = [{type: "local", label: $label}]
    ' \
    "${SEED_CONFIG}" > "${TMP_CONFIG}"
chmod 0666 "${TMP_CONFIG}"
mv "${TMP_CONFIG}" "${DATA_DIR}/config/config.json"

docker compose --env-file "${SCRIPT_DIR}/.env" -f "${SCRIPT_DIR}/compose.yaml" up -d --pull never

i=0
while [ "${i}" -lt 30 ]; do
    if curl --fail --silent "http://127.0.0.1:${FILESTASH_HTTP_PORT}/healthz" | jq -e '.status == "pass"' >/dev/null 2>&1; then
        break
    fi
    i=$((i + 1))
    sleep 1
done

if ! curl --fail --silent "http://127.0.0.1:${FILESTASH_HTTP_PORT}/healthz" | jq -e '.status == "pass"' >/dev/null 2>&1; then
    printf 'Filestash helper did not become healthy on http://127.0.0.1:%s/healthz\n' "${FILESTASH_HTTP_PORT}" >&2
    exit 1
fi

printf 'Filestash repo browser: http://127.0.0.1:%s/login\n' "${FILESTASH_HTTP_PORT}"
printf 'Connection label: %s\n' "${FILESTASH_CONNECTION_LABEL}"
printf 'Default password: %s\n' "${FILESTASH_DEFAULT_PASSWORD}"
printf 'Mounted repo path: %s\n' "${FILESTASH_REPO_MOUNT_PATH}"
