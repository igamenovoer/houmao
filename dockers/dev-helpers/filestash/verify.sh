#!/usr/bin/env sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TMP_DIR=$(mktemp -d)
COOKIE_JAR="${TMP_DIR}/cookies.txt"

cleanup() {
    rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

set -a
. "${SCRIPT_DIR}/.env"
set +a

docker compose --env-file "${SCRIPT_DIR}/.env" -f "${SCRIPT_DIR}/compose.yaml" ps

HEALTH_JSON=$(curl --noproxy '*' --fail --silent "http://127.0.0.1:${FILESTASH_HTTP_PORT}/healthz")
printf '%s' "${HEALTH_JSON}" | jq -e '.status == "pass"' >/dev/null

CONFIG_JSON=$(curl --noproxy '*' --fail --silent "http://127.0.0.1:${FILESTASH_HTTP_PORT}/api/config")
printf '%s' "${CONFIG_JSON}" | jq -e '.status == "ok"' >/dev/null
printf '%s' "${CONFIG_JSON}" | jq -e --arg label "${FILESTASH_CONNECTION_LABEL}" '.result.connections | length == 1 and .[0].label == $label and .[0].type == "local"' >/dev/null
printf '%s' "${CONFIG_JSON}" | jq -e --arg label "${FILESTASH_CONNECTION_LABEL}" '.result.auth | index($label) != null' >/dev/null

curl --noproxy '*' --fail --silent -c "${COOKIE_JAR}" "http://127.0.0.1:${FILESTASH_HTTP_PORT}/api/session/auth/?action=redirect&label=${FILESTASH_CONNECTION_LABEL}" | grep -q 'type="password"'
curl --noproxy '*' --fail --silent -o /dev/null -b "${COOKIE_JAR}" -c "${COOKIE_JAR}" -X POST --data-urlencode "password=${FILESTASH_DEFAULT_PASSWORD}" "http://127.0.0.1:${FILESTASH_HTTP_PORT}/api/session/auth/?label=${FILESTASH_CONNECTION_LABEL}"

SESSION_JSON=$(curl --noproxy '*' --fail --silent -H 'X-Requested-With: XmlHttpRequest' -b "${COOKIE_JAR}" "http://127.0.0.1:${FILESTASH_HTTP_PORT}/api/session")
printf '%s' "${SESSION_JSON}" | jq -e '.status == "ok" and .result.is_authenticated == true and .result.home == "/"' >/dev/null

LS_JSON=$(curl --noproxy '*' --fail --silent -H 'X-Requested-With: XmlHttpRequest' -b "${COOKIE_JAR}" "http://127.0.0.1:${FILESTASH_HTTP_PORT}/api/files/ls?path=/")
printf '%s' "${LS_JSON}" | jq -e '.status == "ok"' >/dev/null
printf '%s' "${LS_JSON}" | jq -e '.results | any(.name == ".gitignore")' >/dev/null
printf '%s' "${LS_JSON}" | jq -e '.results | any(.name == ".git")' >/dev/null

printf 'Verified Filestash helper health, seeded auth flow, repo-root landing, and hidden-file visibility.\n'
