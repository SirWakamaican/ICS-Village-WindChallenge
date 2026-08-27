#!/bin/bash
# Launch the vulnserver Modbus RE target the same way runme_pi4.sh does on the
# Pi, but tolerant of running inside a container / off real hardware.
set -euo pipefail

cd /challenge

# Pi-only: force GPIO18 into its PWM (alt5) function for the turbine relay.
# raspi-gpio only exists on Raspberry Pi OS - skip it everywhere else so the
# server still starts in simulation / on an x86 host under emulation.
if command -v raspi-gpio >/dev/null 2>&1; then
    ./setup_pins.sh || echo "[entrypoint] setup_pins.sh failed (non-fatal), continuing" >&2
else
    echo "[entrypoint] raspi-gpio not present - skipping PWM pin setup (non-Pi host)" >&2
fi

# Backend defaults to TCP (listens on 0.0.0.0:1502), matching runme_pi4.sh's
# no-argument invocation. Override with VULNSERVER_MODE=tcp|tcppi|rtu.
MODE="${VULNSERVER_MODE:-}"
echo "[entrypoint] starting vulnserver ${MODE:-(default tcp)} on :1502" >&2
exec env LD_LIBRARY_PATH=. ./vulnserver ${MODE}
