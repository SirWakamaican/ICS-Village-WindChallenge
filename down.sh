#!/usr/bin/env bash
# Tear the Wind Challenge exhibit down in reverse order:
#   1. audit-sidecar   - detach it from the challenge networks first, so they
#                        can be removed cleanly
#   2. every challenge
#   3. viz
#
# Any extra arguments are forwarded to every `down` (e.g. `./down.sh -v` to
# also drop named volumes). See up.sh and docs/AUDIT.md Part 3.
set -euo pipefail

cd "$(dirname "$0")"

VIZ="viz"
CHALLENGES="${CHALLENGES:-bh-intellirupter dnpchallenge mitm-modbus mqtthelper re-challenge}"
SIDECAR="audit-sidecar"

if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
else
    echo "error: need either 'docker compose' (v2 plugin) or 'docker-compose'." >&2
    exit 1
fi

DOWN_ARGS=("$@")

compose_down() {
    local dir="$1"
    echo ">> tearing down ${dir}"
    # Don't abort the whole teardown if one stack is already gone.
    ( cd "${dir}" && "${COMPOSE[@]}" down "${DOWN_ARGS[@]+"${DOWN_ARGS[@]}"}" ) || \
        echo "warning: '${dir}' down returned non-zero (already stopped?)" >&2
}

compose_down "${SIDECAR}"

for c in ${CHALLENGES}; do
    compose_down "${c}"
done

compose_down "${VIZ}"

echo
echo "All stacks are down."
