#!/usr/bin/env sh

set -eu

TEMPLATE_PATH=/etc/cypht/nginx.conf.template
TARGET_PATH=/etc/nginx/nginx.conf

if [ -z "${CYPHT_HTTP_PORT:-}" ]; then
    echo "CYPHT_HTTP_PORT is required" >&2
    exit 1
fi

sed "s/__CYPHT_HTTP_PORT__/${CYPHT_HTTP_PORT}/g" "${TEMPLATE_PATH}" > "${TARGET_PATH}"

exec /usr/local/bin/docker-entrypoint.sh
