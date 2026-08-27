#!/bin/bash
# hmi.py must come up first and stay on the host (see docker-compose.yml
# comments) so the rtu container has something at host.docker.internal to
# connect to as soon as it starts.
cd "$(dirname "$0")"
source venv/bin/activate
python3 hmi.py &

# Bring the PLC up first and give OpenPLC time to finish booting its
# webserver/Modbus listener before starting the rtu, which depends on it.
docker compose up -d plc
sleep 10
docker compose up -d rtu

