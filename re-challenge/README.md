# re-challenge — vulnserver reverse-engineering target

A deliberately vulnerable **Modbus/TCP server** (`vulnserver`) that stands in
for a wind-turbine relay controller. Unlike the other challenges — where the
attack is in the *protocol traffic* or *PLC logic* — here the attack is in the
**binary itself**: participants pull the `vulnserver` executable, reverse it,
find the memory-safety bug in its Modbus request handling, and drive the
turbine relay (GPIO18/PWM) through it.

The binary is an **aarch64 / Raspberry Pi 4** build. It is a modified copy of
libmodbus's `unit-test-server`, extended to toggle a real PWM output for the
turbine relay and to log every coil write it processes.

## Layout

```
re-challenge/
├── Dockerfile             # arm64 runtime image for the vulnserver
├── docker-compose.yml     # builds + runs it, bind-mounts the binary
├── entrypoint.sh          # Pi-safe launcher (guards raspi-gpio, sets LD_LIBRARY_PATH)
└── Pi4/                   # the arm64 payload
    ├── vulnserver         # the RE target (bind-mounted so it's swappable)
    ├── libmodbus.so.5(.1.0)  # bundled libmodbus, loaded via LD_LIBRARY_PATH=.
    ├── libpwm.so          # PWM helper the binary uses for the turbine relay
    ├── runme_pi4.sh       # original bare-metal launch script (setup_pins + run)
    └── setup_pins.sh      # raspi-gpio: put GPIO18 into PWM (alt5) mode
```

## The swappable binary

`docker-compose.yml` **bind-mounts** `./Pi4/vulnserver` over the copy baked
into the image:

```yaml
volumes:
  - ./Pi4/vulnserver:/challenge/vulnserver
```

That means the binary participants analyze is the exact file on disk in
`Pi4/vulnserver`, and it can be **patched or replaced from outside the
container** (e.g. dropping in a fixed build to demonstrate a fix, or a
tampered build for a variant) without rebuilding the image — just restart the
service to pick up the change. The image still contains a pristine fallback
copy so it runs on its own if the mount is ever removed.

## Running it

This stack is **arm64-only** because the binary is an ARM64 ELF.

**On a Raspberry Pi 4 (native, intended target):**

```bash
cd re-challenge
docker compose up --build
```

The server listens on **`0.0.0.0:1502`** (Modbus/TCP), published to the host
as `1502:1502`. `privileged: true` + `/dev/gpiomem` give it the GPIO/PWM access
it needs to actually move the turbine relay.

**On an x86 dev host (simulation):** enable qemu-user emulation once, then the
same command works (the GPIO/PWM writes simply no-op with no real hardware):

```bash
docker run --rm --privileged tonistiigi/binfmt --install arm64
cd re-challenge
docker compose up --build
```

### Poking at it

The binary defaults to TCP mode (`VULNSERVER_MODE=tcp|tcppi|rtu` overrides).
It logs every coil write it accepts, so watch its output while you probe:

```bash
docker logs -f re-challenge-vulnserver
```

## Objective

Reach the server on `1502/tcp`, work out its coil/holding-register map and the
bug in how it parses Modbus requests, and use that to stop the turbine — the
same win condition as the other challenges (dashboard zone flips to
green/"Down"). Discovering the real address map and the memory-safety flaw is
the point of the exercise, so no address list is published here.

> The [`audit-sidecar`](../audit-sidecar/README.md) exposes a couple of
> best-effort coil/register points for this challenge purely as exploration
> starting points — they are intentionally *not* the answer.

## Security note

`vulnserver` is intentionally vulnerable and unauthenticated, and this service
runs `privileged: true` for GPIO access. Run it only on an isolated exhibit
network you control. See the repo [README](../README.md#security-notes).

## Acknowledgement

This challenge was developed with help from Daniel Salloum, a Reverse Engineer with [Assured Information Security (AIS)](https://www.ainfosec.com/).
