"""Known per-challenge protocol endpoints and the elements worth exposing
in the sidecar's read/write panel.

Reached by Docker service name because this container is a member of every
challenge's own network (see docker-compose.yml) - no host-published ports
are needed for any of this.

Modbus addresses for bh-intellirupter are BEST-EFFORT read off
bh-intellirupter/fixedfinal.st's %QX/%IX declarations, not verified against
OpenPLC's actual compiled Modbus address list (Settings -> Modbus Server in
the OpenPLC web UI is the source of truth). Verify there before trusting
these if you're relying on them for anything other than exploration.
"""

CHALLENGES = [
    {
        "id": "bh-intellirupter",
        "label": "bh-intellirupter (OpenPLC ladder logic)",
        "protocol": "modbus",
        "host": "plc",
        "port": 502,
        "unit": 1,
        "note": "Addresses are best-effort from fixedfinal.st - verify "
                "against OpenPLC's own Modbus address list before relying "
                "on them.",
        "elements": [
            {"name": "VoltageChk (%IX0.0)", "kind": "discrete_input", "address": 0, "access": "ro"},
            {"name": "Sensor (%IX0.1)", "kind": "discrete_input", "address": 1, "access": "ro"},
            {"name": "Trip (%QX0.0)", "kind": "coil", "address": 0, "access": "rw"},
            {"name": "Fault (%QX0.1)", "kind": "coil", "address": 1, "access": "rw"},
            {"name": "FaultLight (%QX0.4)", "kind": "coil", "address": 4, "access": "ro"},
            {"name": "Reset (%QX0.6)", "kind": "coil", "address": 6, "access": "rw"},
            {"name": "Turbine (%QX10)", "kind": "coil", "address": 10, "access": "ro"},
        ],
    },
    {
        "id": "mitm-modbus",
        "label": "mitm-modbus (master/slave)",
        "protocol": "modbus",
        "host": "slave",
        "port": 502,
        "unit": 1,
        "note": "slave.py's datastore is a flat sequential block of "
                "coils/registers initialized to the same value (see "
                "slave/slave.py) - address 1 is the coil master.py drives.",
        "elements": [
            {"name": "Coil 1 (shutdown-run)", "kind": "coil", "address": 1, "access": "rw"},
        ],
    },
    {
        "id": "re-challenge",
        "label": "re-challenge (vulnserver - Modbus RE target)",
        "protocol": "modbus",
        "host": "vulnserver",
        "port": 1502,
        "unit": 1,
        "note": "vulnserver is a reverse-engineering target - discovering its "
                "real coil/register map (and the memory-safety bug behind it) "
                "IS the challenge, so no verified address list is published. "
                "The points below are best-effort exploration starting points "
                "only; the binary logs every coil write it accepts to stdout "
                "(docker logs re-challenge-vulnserver), so watch there to see "
                "which address actually drives the turbine relay.",
        "elements": [
            {"name": "Coil 0 (turbine relay? - best-effort)", "kind": "coil", "address": 0, "access": "rw"},
            {"name": "Coil 1 (best-effort)", "kind": "coil", "address": 1, "access": "rw"},
            {"name": "Holding reg 0 (best-effort)", "kind": "holding_register", "address": 0, "access": "rw"},
        ],
    },
    {
        "id": "dnpchallenge-rtu",
        "label": "dnpchallenge - rtu (switch / LED / e-stop logic)",
        "protocol": "otsim",
        "host": "rtu",
        "port": 9101,
        "elements": [
            {"name": "switch", "tag": "switch", "access": "rw"},
            {"name": "led", "tag": "led", "access": "ro"},
            {"name": "control (DNP3 turbine.control, as seen by rtu)", "tag": "control", "access": "rw"},
        ],
    },
    {
        "id": "dnpchallenge-ied",
        "label": "dnpchallenge - ied (turbine relay outstation)",
        "protocol": "otsim",
        "host": "ied",
        "port": 9102,
        "elements": [
            {"name": "estop", "tag": "estop", "access": "rw"},
            {"name": "status", "tag": "status", "access": "ro"},
            {"name": "turbine (drives GPIO pin 18)", "tag": "turbine", "access": "ro"},
            {"name": "control (DNP3 turbine.control, as seen by ied)", "tag": "control", "access": "rw"},
        ],
    },
]


def find_challenge(challenge_id):
    return next((c for c in CHALLENGES if c["id"] == challenge_id), None)


def find_element(challenge, element_name):
    return next((e for e in challenge["elements"] if e["name"] == element_name), None)
