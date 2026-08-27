#!/usr/bin/env bash
# Bring up the whole Wind Challenge exhibit in the required order:
#   1. viz             - dashboard + MQTT broker everything else reports into
#   2. every challenge - each creates its own isolated Docker network
#   3. audit-sidecar   - joins every challenge network by name, so it MUST be last
#
# Each folder stays its own independent Compose project (that's exactly what
# lets audit-sidecar attach to their networks by their per-project names) -
# this script just runs them in the correct sequence. See docs/AUDIT.md Part 3.
#
# Any extra arguments are forwarded to every `up` (e.g. `./up.sh --build`).
set -euo pipefail

cd "$(dirname "$0")"

VIZ="viz"
# Override the challenge set with e.g.
#   CHALLENGES="dnpchallenge re-challenge" ./up.sh
# Note: audit-sidecar references every challenge network, so it will fail to
# start if you skip one - bring the full set up, or also trim audit-sidecar.
CHALLENGES="${CHALLENGES:-bh-intellirupter dnpchallenge mitm-modbus mqtthelper re-challenge}"
SIDECAR="audit-sidecar"

# Prefer the docker compose v2 plugin; fall back to the legacy binary.
if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
else
    echo "error: need either 'docker compose' (v2 plugin) or 'docker-compose'." >&2
    exit 1
fi

UP_ARGS=("$@")

compose_up() {
    local dir="$1"
    echo ">> bringing up ${dir}"
    # Run from inside the folder so the project (and thus its network names)
    # matches standalone `cd ${dir} && docker compose up` exactly.
    if ! ( cd "${dir}" && "${COMPOSE[@]}" up -d "${UP_ARGS[@]+"${UP_ARGS[@]}"}" ); then
        echo "error: '${dir}' failed to come up." >&2
        echo "  - If this is bh-intellirupter on a non-Pi host, its OpenPLC/wiringPi build is Pi-only." >&2
        echo "  - Bring up a subset with e.g." >&2
        echo "      CHALLENGES=\"dnpchallenge mitm-modbus mqtthelper re-challenge\" ./up.sh" >&2
        echo "    (audit-sidecar references every challenge network, so skip/trim it too if you skip a challenge)." >&2
        exit 1
    fi
}

# viz's Mosquitto broker needs these certs; they are NOT auto-generated here
# because regenerating the CA would break the CA copies the challenges pin.
if [[ ! -f "${VIZ}/mqtt-certs/server.pem" ]]; then
    echo "warning: ${VIZ}/mqtt-certs/server.pem is missing - run ${VIZ}/createcerts.sh first if viz fails to start." >&2
fi

compose_up "${VIZ}"

for c in ${CHALLENGES}; do
    compose_up "${c}"
done

# Last: it joins each challenge's network (external: true) by name, so those
# networks must already exist by the time it starts.
compose_up "${SIDECAR}"

echo
echo "All stacks are up."
echo "  dashboard:     https://localhost:3000"
echo "  audit-sidecar: http://localhost:8000"
