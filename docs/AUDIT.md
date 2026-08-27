# Repo Audit — ICS Village Wind Turbine Challenge

Scope: assess what's on the `main` branch today (this checkout), what each
directory is supposed to do, whether it can actually do it, and what's
missing for real Raspberry Pi + GPIO + relay deployment. Everything below
was verified by reading the code, not by running it against hardware — see
[Part 2](#part-2--raspberry-pi--gpio-deployment-assessment) for what can
only be confirmed on the Pi.

**Headline finding (updated):** the repo's `main` branch started as a
snapshot of several independent, WIP challenge modules, several of which
could not run at all as originally committed. As of this revision, **all
five challenge modules** (`bh-intellirupter`, `dnpchallenge`,
`mitm-modbus`, `mqtthelper`, `viz`) have been fixed and, apart from the
pieces that genuinely require real Pi hardware to exercise (GPIO,
wiringPi's architecture-specific build step), verified end-to-end —
including a live ARP-poisoning + Modbus-filter-substitution run for
`mitm-modbus` and a confirmed connection to the real dashboard for
`mqtthelper`. The `sri-fixed/` empty directory has been removed (see
below). All three turbine-relay outputs
(`bh-intellirupter`/`dnpchallenge`/`mitm-modbus`) now agree on GPIO
polarity (HIGH = running normally) after a real bug was found and fixed
in `dnpchallenge`'s logic — see `docs/PINOUT_MAP.md` §3. There are still
several dead remote branches (`VIZ`, `jg-dnp3-doc`,
`mines_students_challenge`, `mitm-modbus`, `nrahjg-dnp`)
that were never reconciled — now lower-priority since the modules they'd
have fixed are already fixed a different way, but still worth a look for
anything else useful (e.g. `jg-dnp3-doc`'s presumed DNP3 documentation).

---

## Part 1 — Directory-by-directory audit

### `bh-intellirupter/` — OpenPLC-based turbine PLC + RTU
**Intent:** An OpenPLC "PLC" container runs ladder logic (`fixedfinal.st`)
that trips a turbine output based on a voltage sensor input and a fault
counter. A separate `rtu` container (`rtu-speaker.py`) polls the PLC over
Modbus TCP, injects simulated sensor noise, forwards a synthetic "voltage"
reading to an `hmi.py` visualizer over a raw TCP socket, and writes a fault
coil back to the PLC if the value goes out of bounds.

**Status: fixed on `main` — should now build and address itself
correctly.** Originally this module was broken in three independent ways;
all three have been addressed directly:

- `docker-compose.yml` builds `plc` from `./OpenPLC_v3/`, which was empty
  in this checkout. **Fixed:** `bh-intellirupter/OpenPLC_v3/` is now a
  full **vendored** (not submoduled — deliberately no live link back to
  upstream) copy of upstream OpenPLC_v3 at commit `b5d4135`. See
  `OpenPLC_v3/VENDORED.md` for exactly what was copied and changed. Its
  `Dockerfile` was also modified to install wiringPi and default the build
  to the `rpi` hardware layer (`change_hardware_layer.sh rpi`) instead of
  upstream's default `blank_linux`, so GPIO works without a manual
  post-deploy step in the OpenPLC web UI. **Important architecture
  constraint this introduces:** wiringPi ships arch-specific packages
  (armhf/arm64), so `docker compose build` for this service **must run on
  the Raspberry Pi itself** — it will fail on an x86 simulation/dev host at
  the wiringPi install step (everything before that step — dependency
  install, compiling matiec/OpenDNP3/libmodbus/snap7 from source — is
  architecture-neutral and was confirmed to build cleanly on x86 during
  this pass; only the final wiringPi + hardware-layer-switch layer is
  Pi-only). This is a real, unavoidable limitation of using wiringPi at
  all — see Part 2 for the discussion of what remains untestable in
  simulation as a result.
- `startup.sh` referenced two containers by hardcoded auto-generated Docker
  names (`distracted_merkle`, `eloquent_heisenberg`) instead of the
  `docker-compose.yml` service/container names. **Fixed:** it now uses
  `docker compose up -d plc` / `docker compose up -d rtu`.
- `hmi.py` hardcoded `server_ip = '192.168.1.10'`, and `rtu/rtu-speaker.py`
  hardcoded a third, unrelated address (`192.168.2.100`) for both the PLC
  connection and the HMI sockets — none of these addresses agreed with each
  other or with any real network. **Fixed:**
  - `hmi.py` now binds `0.0.0.0` (override via `HMI_BIND_HOST`) so it's
    reachable from the exhibit network regardless of the host's actual IP —
    it's the one piece of this challenge meant to stay directly on the host
    (per `startup.sh`), not inside Docker, precisely so players/dashboards
    can reach it.
  - `rtu-speaker.py` now reaches the PLC via the compose service name
    (`PLC_HOST=plc`) on the container-internal Modbus port (`PLC_PORT=502`)
    instead of the host-published port (5000, which is only for
    external/admin access) — and reaches `hmi.py` via
    `HMI_HOST=host.docker.internal` (wired up with an `extra_hosts:
    host-gateway` entry in `docker-compose.yml`) instead of a hardcoded LAN
    IP. All four values are environment-variable overridable.
  - `docker-compose.yml`'s `rtu` service also had a dead port mapping
    (`8888:8888`, `8889:8889`) publishing ports that nothing in that
    container actually listens on (it's a *client* of `hmi.py`'s sockets,
    not a server) — removed.
- The ladder logic itself (`fixedfinal.st`) was already self-consistent and
  plausible and did not need changes: `Trip` latches from a fault counter
  (`CTU0`, preset 3), `Turbine` runs only while `VoltageChk` is true and
  `Trip` is false, and a 15s `TOF` drives a fault light / auto-reset.

**Remaining work:** none of the above has been build-verified end-to-end on
real Pi hardware yet (see Part 2) — the x86 validation build only proves
the pre-wiringPi portion of the OpenPLC build succeeds. `sri-fixed/` was
unrelated to this fix and has since been deleted (see its own section
below).

### `dnpchallenge/` — DNP3 RTU/IED pair on ot-sim
**Intent:** Two `ot-sim` containers (`rtu`, `ied`) speak DNP3 to each other;
the `rtu` reads a physical switch/e-stop and drives a status LED via real
Pi GPIO, and the `ied` maps DNP3 points to a GPIO output pin driving the
turbine relay. A `vizhelper.py` script polls both nodes' HTTP APIs and
republishes state to MQTT for the dashboard.

*(Correction from an earlier revision of this document: the switch/LED and
turbine-relay pins were originally attributed to the wrong node — it's
`rtu` that owns the switch/LED, per `rtuconfig.xml`'s `mode="client"` DNP3
block and its own `<telnet>`/API-on-9101 config, and `ied` that owns the
turbine relay, per `iedconfig.xml`'s `mode="server"` outstation and
API-on-9102. Verified directly against both XML files.)*

**Status: fixed on `main`.** This was already the most concrete and
Pi-realistic of the five challenges (`rtuconfig.xml`/`iedconfig.xml` are
well-formed ot-sim configs directly using `ot-sim-rpi-gpio-module` — genuine
GPIO integration, not a stub — and `docker-compose.yml` correctly runs both
nodes `privileged: true` with `/dev/gpiomem` mounted). Its remaining gaps
were all in `vizhelper.py` and have been addressed:
- **Fixed:** `check_response()` (renamed `turbine_is_stopped()`) was
  missing a `return` statement, so its actual comparison logic
  (`ieddata["value"]==1 and rtudata["value"]==0`) never executed and the
  script always published `zone2 = 1` regardless of real turbine state.
- **Fixed:** `ieddata = response.json` was missing the `()` call, which
  would have raised `TypeError` the moment the line above was actually
  reached.
- **Fixed — tied into the real viz dashboard:** the script previously
  called `requests.get("http://127.0.0.1:9101/...")` /
  `.../9102/...`, which only works if `vizhelper.py` shares the host's
  network namespace — it didn't, since the `vizhelper` service was never
  actually built or run at all (see next point). It now targets `rtu`/`ied`
  by Docker Compose service name, and both hosts and ports are
  environment-variable overridable. It also previously tried to connect to
  an MQTT broker addressed as literally `"mqtt"` with **its own local
  self-signed CA** (`mqtt-certs/ca-cert.pem`, byte-identical to
  `mqtthelper/mqtt-certs/` and `mitm-modbus/slave/mqtt-certs/`'s bundles) —
  none of which matches the CA that actually signed `viz/`'s Mosquitto
  server certificate. Even with the two code bugs above fixed, this would
  have failed every TLS handshake with an unknown-CA error. It now connects
  to `viz`'s real broker via `host.docker.internal` (viz is a separate
  compose project) using a copy of **viz's actual CA cert** — see
  `dnpchallenge/mqtt-certs/CERTS.md` for why only a CA cert is needed here
  (viz's Mosquitto doesn't require client certificates).
- **Fixed:** the polling loop had no `sleep` and no error handling — it
  would busy-loop the RTU/IED HTTP APIs as fast as possible, and would
  crash outright on any transient connection failure (e.g. if it starts
  before `rtu`/`ied` finish booting). It now polls once a second with
  `requests.RequestException` handling that logs and retries.
- **Fixed:** the `vizhelper` service in `docker-compose.yml` previously
  didn't build or run the script at all (just `image: python:3.13-rc`, no
  command, no files copied in) — it now has a `Dockerfile` +
  `requirements.txt` and builds/runs for real, with `depends_on: [rtu,
  ied]` and `restart: on-failure` so it comes back up if it starts before
  its dependencies are ready.
- **Build-verified:** `docker compose config` resolves cleanly and `docker
  compose build vizhelper` succeeds end-to-end (confirmed in this pass).
  Also caught and fixed a `paho-mqtt` 2.x deprecation warning
  (`mqtt.Client()` now wants an explicit `callback_api_version`) while
  validating the build — pinned to `CallbackAPIVersion.VERSION2` since this
  script registers no callbacks that version affects.

**Not yet verified:** end-to-end behavior against the real `rtu`/`ied`
containers requires `/dev/gpiomem`, which doesn't exist on a non-Pi host —
this was confirmed absent on the x86 host used for this validation pass, so
the full stack (`rtu`+`ied`+`vizhelper`+real GPIO) still needs a run on
actual Pi hardware. See `docs/ADMIN.md`'s dnpchallenge section for the test
plan once that's possible.

**Still open:** `README.md` was a one-line placeholder (`# dnp challenge
[TODO]`) with only a thanks-note to PatriaSecurity/OT-Sim — no setup or
objective text. Real admin/player documentation for this challenge now
lives in `docs/ADMIN.md` and `docs/PLAYER.md` instead of a per-module
README; see those.

**Verdict:** now the closest to production-ready of the GPIO-touching
challenges — code-complete pending an actual Pi hardware validation pass.

### `mitm-modbus/` — Ettercap Modbus MITM exercise
**Intent:** A `master` (client) and `slave` (server) speak Modbus TCP to
each other over a dedicated bridge network; the intent is for a player to
run Ettercap with the provided filter files (`etter.filter.modbus`) to
intercept/alter traffic between them. The slave also toggles a GPIO pin and
publishes state to MQTT.

**Status: fixed and verified end-to-end (`docker compose up` brought all
three services up and stayed up, with `master` actively writing coil 1 and
`slave` processing the writes, confirmed via live logs).** Originally this
module had the most bugs of any challenge in the repo; all of the
following were found and fixed in this pass:

- **Fixed:** `slave.py`'s unconditional `import RPi.GPIO as GPIO` raised
  `RuntimeError` at import time on any non-Pi kernel (confirmed directly —
  it's `RuntimeError`, not `ImportError`, which matters for how you catch
  it), making the container impossible to run in simulation. It's now
  wrapped in `try/except (ImportError, RuntimeError)` with a no-op mock
  GPIO fallback, and `RPi.GPIO` was added to `requirements.txt` (confirmed
  it builds fine on x86_64 given a C compiler — `gcc`/`python3-dev` added
  to the Dockerfile — it only fails at *import*, not at *build*, off a Pi).
- **Fixed:** the `GPIO.setup(17, ...)` vs. `GPIO.output(12, ...)` pin
  mismatch — both now use a single `RELAY_PIN` constant (default BCM12 /
  physical pin 32, matching `docs/PINOUT_MAP.md` CH3, overridable via env
  var).
- **Fixed:** `shutdown_coil()`'s `"Reading shutdown " + shutdown` (`str` +
  `int`) `TypeError`, and a separate bug in the same function not caught
  previously — it used `time.sleep(5)` inside an `async def`, which blocks
  the *entire* asyncio event loop (including the Modbus server running
  alongside it) for 5 seconds on every iteration. Changed to
  `asyncio.sleep(5)`.
- **Fixed — three compounding bugs, found by testing the actual
  attack/recovery cycle live, not just by reading the code:**
  `shutdown_coil()` (the coroutine that's supposed to detect the MITM'd
  coil write and flip the physical relay/dashboard) could never run at
  all, for three independent reasons:
  1. It was called without `await` in `async_helper()` — creates a
     coroutine object that's never scheduled to run.
  2. Fixing #1 alone isn't enough: it was called as
     `await run_async_server(run_args); await shutdown_coil(run_args)` —
     sequential, not concurrent. `run_async_server()` never returns while
     the Modbus server is alive (confirmed directly by reading pymodbus's
     `StartAsyncTcpServer` source — it awaits the server's serve-forever
     loop internally), so the line before `shutdown_coil()` never
     finishes. Confirmed live: even after fixing #1, `shutdown_coil()`'s
     own print statements never appeared, minutes after startup, despite
     the Modbus server itself working fine. Fixed with
     `asyncio.gather(run_async_server(run_args), shutdown_coil(run_args))`
     to run both concurrently.
  3. Even running, it was reading the wrong Modbus datastore:
     `getValues(2, 1, count=1)` uses function code 2 (discrete inputs) —
     a datastore nothing in this codebase ever writes to (it sits at its
     initial placeholder value, `17`, forever). `master.py`'s
     `write_coil(1, True)` — and what Ettercap's filter actually tampers
     with — lands in the **coils** datastore, function code 1. Changed to
     `getValues(1, 1, count=1)`.

  With all three fixed, also corrected a design-level bug: the function
  only ever called `changeON(0)` (turn off), never `changeON(1)` (turn
  back on) — so a coil read of `False` before `master`'s first write
  lands (a real race at boot, confirmed to happen in testing) would
  permanently "stick" the relay off with no way to recover even once the
  coil read `True` again. Now mirrors the coil's value both ways every
  cycle, which is self-correcting.

  **Confirmed working end-to-end, live, in this pass:** before any
  attack, the coil reads `True` continuously (one transient `False` read
  right at boot, self-corrects within one 5s cycle once `master`'s first
  write lands) and the relay/dashboard reflect "running." Running the
  actual Ettercap ARP-poisoning + filter attack (`attacker/` box) flips
  the coil to `False` for the *entire* duration of the attack, and it
  self-corrects back to `True` within one cycle of the attack stopping.
  This is the whole challenge's win condition working exactly as
  intended — previously it could not have worked at all, for any of the
  three reasons above.
- **Fixed — tied into the real viz dashboard**, same class of issue found
  and fixed in `dnpchallenge`: `changeON()` connected to an MQTT broker
  literally addressed as `"0.0.0.0"` (not a valid connect target) using
  **its own local self-signed CA** (byte-identical to `mqtthelper`'s and
  `dnpchallenge`'s pre-fix bundles) — not the CA that actually signed
  `viz`'s Mosquitto server certificate. Now connects to
  `host.docker.internal:1883` using a copy of viz's real CA (see
  `slave/mqtt-certs/CERTS.md`), and a `paho-mqtt` 2.x
  `callback_api_version` deprecation warning was fixed the same way as in
  `dnpchallenge`.
- **Fixed — found during end-to-end testing, not in the original code
  review:** `changeON()`'s MQTT connect failure (e.g. `viz` not started
  yet) was unhandled and crashed the *entire* slave process before its
  Modbus server ever started, since `changeON(1)` runs first thing in
  `async_helper()`. Now wrapped in `try/except OSError` — a dashboard
  outage no longer takes the whole challenge down with it.
- **Fixed — same class of bug, in `master.py`:** `assert client.connected`
  right after the first `connect()` attempt crashed the whole container
  immediately if `slave` wasn't up yet (there's no `depends_on` health
  check between them). Now retries every 5s instead of asserting once.
- **Fixed:** `slave/Dockerfile`'s comment header said `# master/Dockerfile`
  (copy-paste artifact), and — a bug beyond what was previously
  documented — its `COPY mqtt-certs .` line copied that directory's
  *contents* directly into `/app` instead of into `/app/mqtt-certs/`,
  which would have broken `slave.py`'s cert path regardless of any other
  fix. Both fixed.
- **Fixed:** `master/Dockerfile` had a pointless `RUN sleep 5` (does
  nothing useful at build time, just slows every build) and used
  `python:3` with default (buffered) stdout — `master.py`'s `print()`
  calls never appeared in `docker logs` at all in testing, even though the
  process was working correctly (confirmed via `slave`'s side of the
  conversation) — until `PYTHONUNBUFFERED=1` was added. The same buffering
  fix was applied to `slave/Dockerfile` for the same reason.
- **Fixed:** `master.py`'s `run_async_slave()` function was actually the
  **client** (the docstring even says so — "CLIENT = MASTER" — but the
  function name said `_slave`); renamed to `run_async_master`. Its
  `except ModbusException` handler duplicated the retry loop and left
  dead, unreachable `rr.isError()`/`ExceptionResponse` checks after *two*
  copies of an infinite loop (which could also reference `rr` before its
  first assignment). Collapsed into one loop with one retry path. Also
  replaced the hardcoded `172.20.0.3` target with the `slave` service name
  (env-var overridable), consistent with every other hardcoded-IP fix
  elsewhere in this repo.
- **Fixed:** `docker-compose.yml`'s `slave` service now has
  `privileged: true` + `/dev/gpiomem` mounted, matching `dnpchallenge`'s
  pattern.
- **Design gap addressed — see the new `attacker/` service below**, not
  a code bug: none of the above makes Ettercap's ARP-spoofing mechanic
  actually reachable by a participant, since `master`↔`slave` traffic
  never left `mitm-modbus`'s own private Docker network in the first
  place (this is the same class of issue as `docs/AUDIT.md` Part 3, but
  specific to this challenge's core mechanic rather than just traffic
  *observability*).
- **Still open:** `README.md` is still two lines (`docker-compose up`) —
  real setup/objective documentation now lives in `docs/ADMIN.md` and
  `docs/PLAYER.md` instead, following the pattern already used for
  `dnpchallenge`.

### `mitm-modbus/attacker/` — new: in-network Ettercap access box

Added to solve the design gap above: a container joining the same
`my_network` as `master`/`slave`, running Ettercap (+ tcpdump/net-tools),
exposing a real shell over a browser-based terminal (`ttyd`, port 7681,
intentionally unauthenticated — same trust model as `audit-sidecar`'s
write panel) so a participant can run genuine ARP-spoofing/Ettercap
filters against `master`↔`slave` without needing their own NIC on that
segment. Picks the correct `ttyd` binary for the host's architecture
(amd64/arm64/armhf) at build time rather than hardcoding one.

**Fully validated end-to-end, live, in this pass** — not just "builds and
starts": `NET_ADMIN`/`NET_RAW` alone turned out to be insufficient
(Ettercap writes to `/proc/sys/net/ipv6/conf/all/forwarding` as part of
its own startup safety routine, and `/proc/sys` stays read-only under
Docker's default profile regardless of added capabilities — confirmed
directly via the exact "Read-only file system" error), so the service
runs `privileged: true` instead, which is an acceptable tradeoff given
this container's entire purpose is running this class of tooling. With
that fixed, a real `ettercap -M arp:remote` run from inside this container
against `master` (172.20.0.2) and `slave` (172.20.0.3) successfully:
resolved both hosts' real MAC addresses, established ARP-poisoning
between them, and — with `etter.filter.modbuscomp` loaded — printed
`Correctly substituted and logged`, confirming the filter actually
intercepted and altered a live Modbus write-coil packet in transit between
the two. This is the whole MITM mechanic working exactly as originally
designed, just from inside this box instead of a participant's own NIC.

**Verdict:** all previously-documented bugs plus several more found during
this pass are fixed, the stack runs end-to-end, and the live-MITM
experience is fully restored and confirmed working through the new
`attacker/` box.

### `re-challenge/` — new: vulnserver binary reverse-engineering target

**Intent:** Unlike every other module here, the vulnerability is in a
**binary**, not in protocol traffic or PLC/ladder logic. `re-challenge/Pi4/`
ships an aarch64 (Raspberry Pi 4) executable, `vulnserver` — a modified
libmodbus `unit-test-server` that serves Modbus/TCP and drives the turbine
relay over GPIO18/PWM (`libpwm.so`) — plus its bundled `libmodbus.so.5`,
the original bare-metal launch scripts (`runme_pi4.sh`, `setup_pins.sh`),
and nothing else. As committed it had **no Dockerfile, compose file, or
docs** — it was just the raw Pi payload, not a deployable challenge.

**Status: added in this pass.** A container was built around the existing
payload rather than modifying the binary (reversing it unmodified is the
point):
- `Dockerfile` — `arm64v8/debian:bookworm-slim`; the binary only needs
  glibc plus its bundled `libmodbus.so.5`/`libpwm.so` via `LD_LIBRARY_PATH`
  (confirmed via `readelf -d`: `NEEDED` is just those two plus `libc.so.6`/
  the aarch64 loader), so no extra packages are installed. Bakes in a
  pristine fallback copy of the whole `Pi4/` payload.
- `docker-compose.yml` — builds/runs it `platform: linux/arm64`,
  `privileged: true` with `/dev/gpiomem` mounted (same GPIO pattern as
  `dnpchallenge`/`mitm-modbus`), publishes `1502:1502`, and gives it an
  explicit `172.34.0.0/24` subnet so `audit-sidecar/` can attach with a
  static IP (see Part 3).
- **The `vulnserver` binary is bind-mounted** (`./Pi4/vulnserver:/challenge/vulnserver`)
  rather than only baked in, so participants can patch or replace it from
  outside the container without rebuilding — the point of an RE exercise.
- `entrypoint.sh` reproduces `runme_pi4.sh` (`LD_LIBRARY_PATH=. ./vulnserver`,
  defaulting to TCP mode on `0.0.0.0:1502`) but **guards** the Pi-only
  `setup_pins.sh`/`raspi-gpio` step behind a `command -v` check so it still
  starts in x86 simulation.
- `README.md` — new: layout, the swappable-binary rationale, arm64-only run
  instructions (native on the Pi; `tonistiigi/binfmt` for x86), and the
  objective.

**Architecture constraint (same class as `bh-intellirupter`'s wiringPi
note):** the binary is ARM64, so this stack is arm64-only — it runs
natively on the Pi and requires qemu-user emulation
(`docker run --privileged tonistiigi/binfmt --install arm64`) on an x86
dev host. Not build/run-verified end-to-end on real Pi hardware yet; the
GPIO/PWM turbine-relay effect in particular can only be confirmed there.

**Deliberately not documented:** the binary's real coil/register map and
the memory-safety bug are the challenge, so no verified address list is
published (the `audit-sidecar/` points for it are flagged best-effort).

### `mqtthelper/` — GPIO-to-MQTT bridge
**Intent:** Poll physical GPIO pin state and republish per-zone status to
MQTT for the dashboard, independent of any specific challenge's own
protocol-level publishing.

**Status: fixed and verified end-to-end** (confirmed live: connected to
`viz`'s real Mosquitto broker over valid TLS and successfully published to
`zone3`/`zone4`, subscribed to directly during this pass). This was
previously the most broken module in the repo — every layer had a bug:

- **Fixed:** `Dockerfile`'s `CMD` was `["node","MQTTHelper.py"]` — running
  a Python file with the Node interpreter, which also wasn't installed.
  Now `["python3", "MQTTHelper.py"]`.
- **Fixed:** `docker-compose.yml`'s one service was named `mqtt`, pulled a
  public `image: jtsmart/mqtthelper` (not this repo's own Dockerfile), and
  had `links: - mqtt` — i.e. it linked to itself, a dependency cycle
  Compose actually refuses to resolve (confirmed: `dependency cycle
  detected: mqtt -> mqtt`). Renamed the service to `mqtthelper`, switched
  to `build: .`, and dropped the self-link.
- **Fixed — resolved the pin ambiguity structurally, not by picking a
  column and hoping:** `MQTTHelper.py` shelled out to WiringPi's
  `gpio readall` and pattern-matched literal pin numbers across its
  multi-column (BCM/wPi/Physical) output, which was genuinely ambiguous
  (see the old `docs/PINOUT_MAP.md` §5) — and nothing installed the
  `gpio` CLI in the Dockerfile in the first place. Rewritten to read GPIO
  directly via `RPi.GPIO` (same mock-fallback pattern as
  `mitm-modbus/slave.py`, confirmed working off-Pi in this pass) on two
  explicitly assigned, previously-unclaimed pins (physical 33/BCM13,
  physical 35/BCM19 — see `docs/PINOUT_MAP.md` §4/§6), dropping the
  WiringPi dependency (and its Pi 4/5 support question) entirely.
- **Fixed:** `client.publish('zone'+(pin_number+2), 1)`'s `str`+`int`
  `TypeError`, and a related bug not previously documented — the `Low`
  branch published to `'zone3'+(pin_number+2)`, a different (seemingly
  typo'd) topic than the `High` branch's `'zone'+(pin_number+2)`, so even
  fixing just the crash would have left High/Low states for the same pin
  reporting to two different MQTT topics. Both are now a single
  `client.publish(zone, GPIO.input(pin))` call per monitored pin,
  publishing the pin's raw electrical level rather than a hardcoded
  constant.
- **Fixed — tied into the real viz dashboard**, same class of issue found
  and fixed in `dnpchallenge` and `mitm-modbus`: `CA_CERT`/`CLIENT_CERT`
  pointed at this module's own local self-signed CA (byte-identical to
  the other two modules' pre-fix bundles), not the CA that actually signed
  `viz`'s Mosquitto server certificate, and connected to `"0.0.0.0"` (not
  a valid connect target). Now connects to `host.docker.internal:1883`
  using a copy of viz's real CA (see `mqtt-certs/CERTS.md`).
- **Fixed:** dead code — commented-out Modbus client lines with no
  corresponding logic, and an unused `pymodbus` dependency in
  `requirements.txt` — removed. Added `RPi.GPIO`, added
  `PYTHONUNBUFFERED=1` to the Dockerfile (same stdout-buffering issue
  found in `mitm-modbus`), and pinned `paho-mqtt`'s `callback_api_version`
  the same way as the other two fixed modules.
- **Fixed:** `docker-compose.yml`'s `mqtthelper` service now has
  `privileged: true` + `/dev/gpiomem` mounted, matching every other
  GPIO-touching module in the repo.
- **New behavior — `zone3`/`zone4` go offline once all three challenges
  are done.** `MQTTHelper.py` now also *subscribes* to `zone1`/`zone2`/
  `zone5` (the three actual challenges — env-var configurable via
  `CHALLENGE_ZONES`) on the same connection it already publishes with, and
  tracks each one's latest reported value. Once all three read `0`
  (Down/green — every challenge's turbine stopped), `zone3`/`zone4` are
  forced to publish `0` regardless of what's actually wired to physical
  pins 33/35; otherwise they publish the pin's real reading as before.
  Deliberately tracks "never heard from this challenge yet" as distinct
  from "reported 0," so a challenge that hasn't started publishing yet
  can't be mistaken for one that's already finished. Verified directly:
  unit-level test of the decision function across all four states (no
  data, all running, all stopped, mixed) behaved correctly, and a live
  container correctly received and survived real MQTT messages on the
  subscribed topics without crashing.

**Found during end-to-end testing, not specific to this module — a
repo-wide finding:** bringing this up against the real `viz` broker
failed with `certificate has expired`. **The certs checked into
`viz/mqtt-certs/` (and, before this pass, copied from there into
`dnpchallenge`/`mitm-modbus`) expired 2026-02-05** (`notBefore=2025-02-05`,
365-day validity from `viz/createcerts.sh`). This isn't a "rotate before
a public event" hygiene item, it's **currently non-functional** for
anyone using the checked-in certs as of this audit's date. Regenerated
via `viz/createcerts.sh` and redistributed the new CA to `dnpchallenge`,
`mitm-modbus/slave`, and `mqtthelper` as part of this pass (new
validity: 2026-08-06 through 2027-08-06) — but this will expire again in
a year, and there's no automation or reminder for that anywhere in the
repo. Worth a calendar reminder or a pre-event checklist item at minimum
(added to `docs/ADMIN.md`).

**Verdict:** fully fixed and the only module in the repo confirmed
end-to-end against the real dashboard with valid, current TLS — a good
sign given how broken it started, but also a reminder that "looks fine in
review" and "actually connects" are different bars, given the expired-cert
issue was invisible from reading the code alone.

### `viz/` — Dashboard (Node/Express/Socket.IO + Mosquitto)
**Intent:** An HTTPS Node server subscribes to MQTT zones 1–16 and forwards
state to a browser dashboard over Socket.IO; Mosquitto is the broker
everything else (`vizhelper.py`, `MQTTHelper.py`, `mitm-modbus/slave.py`)
is meant to publish into.

**Status: the most complete, self-consistent module in the repo.**
- `docker-compose.yml` correctly builds `https` locally from its own
  `Dockerfile` and runs `eclipse-mosquitto` with TLS certs and a real
  `mosquitto.conf` mounted in.
- `server.js` is coherent: Helmet CSP, static file serving, MQTT-over-TLS
  client that subscribes to `zone1`..`zone16` and re-emits to all Socket.IO
  clients, browser-side canvas rendering of turbine "zones" in
  `public/index.html`.
- `createcerts.sh` is a clean, complete self-signed CA/server/client cert
  generator — the only certificate-generation tooling in the repo (every
  other module just ships pre-baked certs in `mqtt-certs/`, which is itself
  worth flagging — see cross-cutting notes below).
- Minor: `Dockerfilehttps` (65 bytes) sits alongside `Dockerfile` and looks
  like a leftover/duplicate; worth deleting or clarifying its purpose.
- **Found in a later pass:** `viz/index.html` and `viz/index-http.html`
  at the repo root (not inside `public/`) are **dead files** — `server.js`
  only does `express.static(path.join(__dirname, 'public'))`, so neither
  is ever served. The real, live frontend is `viz/public/index.html` +
  `viz/public/main.js`, which is a materially different, more complete
  implementation (16 zones vs. 5-6, a 4×4 canvas grid instead of custom
  polygon shapes, and the actual `<img id="map">` element). An earlier
  revision of this audit and `docs/PINOUT_MAP.md` verified dashboard
  color semantics against the dead root-level `index.html` — the
  semantics turned out to be identical between the two files (`1` →
  red/"Normal", `0` → green/"Down" in both), so no conclusions drawn from
  that were actually wrong, but the citation was to the wrong file. Fixed
  in `docs/PINOUT_MAP.md`. The two dead files are candidates for deletion
  — nothing in the repo references them — but flagging rather than
  deleting, same policy as everything else in this section.
- **Fixed:** `public/index.html` hardcoded `<img id="map" src="denMap.png"
  ...>` — no environment variable or config, just a literal filename in
  the markup, with `public/map.png` (the Las Vegas venue map, confirmed
  identical 2232×1684 pixel dimensions to `denMap.png` — they were always
  meant to be interchangeable) sitting right next to it, unused. Switching
  venues meant editing and redeploying frontend source. Now: `server.js`
  reads a `MAP_IMAGE` env var and serves it via a small `/map-config.js`
  endpoint; `public/main.js` sets the `<img>`'s `src` from
  `window.MAP_IMAGE` instead of a hardcoded value. Confirmed working
  end-to-end (built the image, verified `/map-config.js` reflects the env
  var correctly with and without an override, confirmed both PNGs are
  actually served). Switching venues is now a one-line
  `docker-compose.yml` change — see `docs/ADMIN.md`.
- **Added a third venue map:** `public/ftcMap.png` (Fort Collins), built
  from an admin-provided screenshot. The source screenshot's aspect ratio
  (1339×867, 1.544) didn't match the canvas's (2232×1684, 1.325) — a naive
  stretch would have visibly distorted it relative to the other two crisp
  maps, so it was center-cropped to the target aspect ratio first, then
  scaled to the exact 2232×1684 both other maps use. `MAP_IMAGE=ftcMap.png`
  confirmed working the same way as the other two.
- **Reworked the zone system — was one of the more significant
  latent-scale-problems in the repo, not just cosmetic:** the dashboard
  previously hardcoded zones 1–16 in three separate places
  (`server.js`'s MQTT subscription loop, `public/index.html`'s 16
  hand-written side-panel blocks, and `public/main.js`'s 4×4 canvas grid
  covering the entire map edge-to-edge) — 11 of those 16 zones have never
  had anything publish to them (only zones 1–5 are in use — see Part 1's
  per-module zone assignments). Consolidated into a single `ZONES` array
  in `server.js`, served to the frontend via a new `/zone-config.js`
  endpoint (same pattern as `/map-config.js`): `main.js` now builds the
  canvas overlay, the side panel, *and* what `server.js` subscribes to
  from that one list, instead of three independently-hardcoded copies of
  "1 through 16." Also repositioned the 5 active zones into a clustered
  layout sized/placed individually (not a uniform grid, and not covering
  the whole canvas) — hand-placed to sit over the map's downtown/city-core
  area rather than tiling arbitrary rural or open-space regions. **Caveat
  stated plainly:** the three shipped maps' actual downtown areas aren't
  at identical pixel coordinates (Fort Collins' in particular sits further
  left than Vegas/Denver's), and this is one shared canvas layout across
  all three — it's a reasonable compromise placement, not a pixel-perfect
  match verified against all three maps' actual street-level density.
  Confirmed working end-to-end: built the image, verified `/zone-config.js`
  serves the 5-entry list, confirmed `index.html` no longer contains any
  hardcoded `zoneNDiv` elements.
- No functional bugs found in the Node code itself during review.

**Verdict:** ready to run as-is. This is the piece to treat as the
reference example for "what a finished module in this repo looks like" —
modulo the two dead legacy files sitting alongside the real one, which is
itself worth a caution: always confirm which file a server actually
serves before trusting what's in it.

### `bh-intellirupter/OpenPLC_v3/` — resolved

**Update:** no longer empty. This is now a vendored copy of upstream
OpenPLC_v3 (see the `bh-intellirupter/` section above and
`OpenPLC_v3/VENDORED.md`), not the `sri` branch's Aug-2024 snapshot — the
`sri` branch was ~1 year stale relative to current upstream (which now
supports Pi 5 wiringPi installs the `sri` branch predates) and, per the
admin's review, contained no local modifications worth preserving over
fresh upstream. The `sri` branch itself is still sitting unmerged/unused;
it can likely be deleted once this fix is confirmed working on hardware,
but that's a call for whoever owns branch cleanup, not made here.

### `sri-fixed/` — resolved (deleted)

Was an empty directory, touched by exactly one commit ("adding fixes",
2024-08-08) that added no files under it. Unlike `OpenPLC_v3/` above,
nothing in the repo's compose files or scripts ever referenced
`sri-fixed/`, so its intended purpose was never derivable from the code —
no branch anywhere in the repo ever populated a directory literally named
`sri-fixed/` either (checked all six remote branches directly).

**What does exist, and is likely what this was meant to point at:** the
**`sri` branch** (not `sri-fixed`, an easy mix-up) has a `plcFiles/`
directory with two OpenPLC ladder-logic programs — `Start_Stop.st` and
`start.st` — distinct from `bh-intellirupter/fixedfinal.st`. Read both
directly:

- **`Start_Stop.st` is a complete, valid, classic latching start/stop
  circuit.** `PB1`/`PB2` (`%MX0.2`/`%MX0.3` — OpenPLC "memory" addresses,
  not physical I/O) are Start/Stop pushbuttons; `LAMP` (`%QX0.0`, a real
  physical output) is `NOT(PB2) AND (LAMP OR PB1)` — turns on and latches
  when `PB1` pulses, and unlatches immediately when `PB2` goes true,
  staying off until `PB1` pulses again. Since `%MX` bits are exposed by
  OpenPLC over Modbus (as coils), a Modbus client can drive `PB1`/`PB2`
  remotely without any physical wiring — confirming the assumption that
  this would be wired to OpenPLC and manipulated over Modbus, the same
  shape as `bh-intellirupter`'s existing challenge.
- **`start.st` is a much simpler, different pattern** — a single pushbutton
  (`PB1`, `%MX0.0`) driving a rising-edge trigger (`R_TRIG`) onto `LAMP`
  (`%QX0.1`, a different output than `Start_Stop.st`'s), producing a
  one-scan-cycle pulse on button *release*, not a persistent on/off state.
  Both files declare a `CONFIGURATION Config0`/`task0`/`instance0` block
  with the same names, which OpenPLC treats as one compiled "active
  program" at a time — these are two alternates, not something that runs
  together. `start.st` reads like an earlier/simpler draft (or a separate
  small exercise testing `R_TRIG` specifically) rather than the "final"
  logic — `Start_Stop.st` is the one that actually matches a
  turbine-relay-with-persistent-on/off-state challenge design.

**Resolved: deleted.** The admin confirmed it was safe to remove — empty,
non-deterministic, and, per the investigation above, not the actual
location of anything real (the ladder logic it was presumably meant to
reference lives on the `sri` branch's `plcFiles/`, under a differently
named directory that was never actually merged as `sri-fixed/`). If
`Start_Stop.st` is picked up as a real second challenge later, it starts
clean rather than inheriting this directory's ambiguous history.

### `.travis.yml` — dead CI
Runs `docker build .` at the repo root and `doxygen doxygen.conf`. There is
no root-level `Dockerfile` and no `doxygen.conf` anywhere in the repo, so
this pipeline has never been able to pass. Recommend either deleting it or
replacing it with per-module `docker compose config` / `docker compose
build` validation as a real smoke test (see admin docs for a
manual version of that check).

### Other unmerged branches worth reconciling
Beyond `sri`, `origin` has: `VIZ`, `jg-dnp3-doc`, `mines_students_challenge`,
`mitm-modbus`, `nrahjg-dnp`. All of them diff heavily against `main` almost
entirely inside `viz/node_modules` (i.e. `main`'s `viz/` has more
committed `node_modules` churn than these branches do), which makes them
hard to read with a plain `git diff --stat`. `jg-dnp3-doc` in particular is
named as if it contains DNP3 documentation that doesn't exist anywhere in
`main` — worth a targeted look before writing the DNP3 admin docs from
scratch, in case it's already been written once.

---

## Part 2 — Raspberry Pi / GPIO deployment assessment

This section separates what's **verifiable from source today** from what
**can only be confirmed once this is actually running on a Pi** with a
relay board wired to the turbine motor's power bus, since this checkout is
simulation-only.

### Which modules actually touch GPIO
| Module | Mechanism | Pins referenced | Container has `privileged`/`/dev/gpiomem`? |
|---|---|---|---|
| `bh-intellirupter` | OpenPLC hardware layer (`raspberrypi.cpp`, wiringPi-based) — now vendored into `main`, `Dockerfile` defaults to it | Mapped via OpenPLC's web UI hardware-layer config to `%QX10`/`%QW15`; no *physical* pin numbers committed anywhere yet — still needs an admin to assign real pins in the UI | Not applicable the same way — OpenPLC isn't a Docker-GPIO-passthrough setup, it needs wiringPi built into the image (done) and to be built/run on the Pi itself |
| `dnpchallenge` | `ot-sim-rpi-gpio-module` | RTU: in 16 (switch), out 15 (LED). IED: out 18 (turbine) | Yes, both `rtu` and `ied` |
| `mitm-modbus` (`slave`) | `RPi.GPIO` direct | `setup(17)`, but `output(12,...)` (mismatched) | No |
| `mqtthelper` | shells out to WiringPi `gpio readall` CLI | reads pins 18, 8 | N/A (compose file broken; no gpiomem/privileged either) |

### Confirmed gaps (verifiable now, without a Pi)
1. ~~**No repo-wide pin/wiring map.**~~ **Done** — see
   [`docs/PINOUT_MAP.md`](PINOUT_MAP.md), which ties every GPIO pin
   referenced anywhere in the repo to a physical header position, a relay
   channel (for the 6-channel relay board), and the owning challenge, and
   proposes pin assignments for the gaps (`bh-intellirupter`'s OpenPLC I/O,
   which isn't hardcoded anywhere in source). It also documents — but does
   not yet fix — the still-open `mitm-modbus/slave.py` pin-17-vs-12
   contradiction and `mqtthelper`'s column-ambiguous pin reads.
2. **Inconsistent container privilege model.** `dnpchallenge` correctly
   grants `privileged: true` + `/dev/gpiomem` to reach real GPIO from
   inside Docker; `mitm-modbus` and `mqtthelper` do not, despite their code
   trying to touch GPIO/wiringpi. If those two are meant to run on the same
   Pi as `dnpchallenge`, their compose files need the same treatment.
3. **`bh-intellirupter` can now reach the GPIO question, but hasn't been
   verified on hardware yet.** OpenPLC_v3 is vendored in and its
   `Dockerfile` now installs wiringPi and defaults the build to the `rpi`
   hardware layer (see the `bh-intellirupter/` section above). The
   pre-wiringPi portion of that build was confirmed to compile cleanly on
   an x86 host; the wiringPi install step itself is architecture-specific
   and was **not** validated end-to-end here, since this environment is
   x86, not a Pi. This still needs a real build-and-boot pass on the actual
   Raspberry Pi before anyone should trust it's fully working.
4. **`RPi.GPIO` import will hard-fail in *any* non-Pi environment**,
   including whatever CI or simulation host this is developed on — there's
   no mock/fake GPIO layer (`fake-rpi`, `gpiozero` with a pin-factory mock,
   or a `Mock.GPIO` shim) anywhere in the repo. That means **none of the
   GPIO-touching Python code can be exercised at all in this simulation
   environment** — not even for logic testing — until either a mock is
   added or the code is refactored to abstract GPIO access behind an
   interface that can be swapped for a mock off-Pi.
5. **WiringPi's Pi-generation support is a real open question.** WiringPi
   (used by `mqtthelper` and by OpenPLC's `raspberrypi.cpp` layer per the
   `sri` branch commit log) was deprecated by its original author and
   dropped official support for Pi 4 and later; an unofficial fork
   (`WiringPi-Python`/`unofficial-WiringPi`) is generally required on newer
   boards. Which Pi model this exhibit targets isn't recorded anywhere in
   the repo — that decision gates whether WiringPi is even the right tool,
   versus standardizing everything on `RPi.GPIO`/`gpiozero` (which
   `mitm-modbus` already assumes).

### What can only be validated on the actual Pi
- That `ot-sim-rpi-gpio-module` in `dnpchallenge` actually toggles the
  named physical pin (18) and that the relay/turbine motor responds — this
  is real electrical behavior, not something a simulated container proves.
- Whether multiple privileged containers can share `/dev/gpiomem`
  concurrently without pin-export contention when several challenges run
  on the same Pi at once (Linux GPIO character-device/sysfs export
  semantics — one exporter "owning" a pin can block another process from
  claiming it).
- Real-world timing: `hmi.py`'s fault detection loop, the ladder logic's
  15s `TOF` fault-light timer, and the physical relay's actual
  switch/settle time all need to be checked together — software polling
  intervals that look fine in simulation can still be slower than a
  spinning load needs for a clean "stop."
- That the E-stop / switch input (`dnpchallenge` IED pin 16) is wired with
  correct pull-up/pull-down and debounce — bouncing on a mechanical switch
  can look like exactly the kind of rapid state flapping the ot-sim logic
  block (`counter`-based debounce for 60 cycles) is trying to compensand
  for, but that logic has never been exercised against a real switch.
- `gpio readall`'s actual text output format against whatever WiringPi
  version/Pi model ends up installed — `MQTTHelper.py`'s string parsing
  (`f"| {pin_number} "` matching) is brittle and version-specific; this can
  only be confirmed by running the real CLI on the real board.
- Whether `RPi.GPIO`'s in-container access actually behaves as expected
  under `privileged: true` + `/dev/gpiomem` (vs. needing full `/dev/mem` or
  additional `--device` flags) — this varies by Pi model/OS image and is a
  known source of "works when I `sudo` it directly, fails in Docker"
  surprises.
- Physical safety validation: that a software-detected fault actually
  de-energizes the relay fast enough, and fails *safe* (relay open) if the
  Pi, a container, or the network link between them dies mid-challenge —
  none of this is testable without the real relay and motor.

### Recommended order of operations before a live event

1. ~~Reconcile the `sri` branch into `main` (or vendor OpenPLC_v3
   properly) so `bh-intellirupter` can build at all.~~ **Done** —
   OpenPLC_v3 vendored, see above. Still needs a real build-and-boot pass
   on Pi hardware.
2. ~~Write one pin/wiring map document covering every challenge that will
   run on the same physical Pi~~ **Done** — see `docs/PINOUT_MAP.md`. Still
   need to actually fix the `mitm-modbus` pin-17/pin-12 contradiction in
   code to match it (tracked in step 4).
3. Decide GPIO library standard (RPi.GPIO/gpiozero vs. WiringPi) per Pi
   model actually being deployed, and add a mock layer so the Python side
   can be unit-tested off-Pi.
4. Fix the confirmed code bugs listed in Part 1 for `mitm-modbus` and
   `mqtthelper` (they'll block functional testing on the Pi just as much
   as they block it in simulation). `bh-intellirupter`'s known bugs
   (hardcoded IPs, stale `startup.sh`) are already fixed.
5. Only then move to on-hardware bring-up and timing/safety validation.

---

## Part 3 — Cross-cutting: no challenge's traffic is actually observable on a wire

Every fix above has been about getting each challenge's *own* internal
plumbing (addressing, TLS, dependencies) to work. This section is a
different, more fundamental gap: **none of the protocol traffic these
challenges are built around ever crosses a real network segment a
participant could plug into.**

Each challenge's `docker-compose.yml` puts its containers on a private
Docker bridge network — either a custom one (`mitm-modbus`'s
`172.20.0.0/16`, `bh-intellirupter`'s `proxiable`) or the default one
Compose creates per project (`dnpchallenge`). These are real virtual
switches, but they're internal-only: nothing on them is reachable from
outside the Docker host unless a port is explicitly published, and
container-to-container traffic *within* that virtual switch never touches
the host's actual physical/Wi-Fi interface at all. A participant with a
laptop plugged into the exhibit's physical network — or a switch SPAN/
mirror port watching that physical network — cannot see any of it.

**Per-challenge impact, from most to least severe:**

- **`mitm-modbus` is non-functional as designed, independent of the code
  bugs already listed in Part 1.** Its entire premise is a participant
  running Ettercap to ARP-spoof and alter traffic between `master` and
  `slave`. `docker-compose.yml` publishes **no ports at all** for either
  service — their Modbus conversation lives 100% on the internal
  `172.20.0.0/16` bridge. There is currently no way for a participant's NIC
  to even be on the same network segment as that traffic, let alone
  ARP-spoof it. This needs a real network-topology fix before it's a
  working challenge, not just the pin/dependency bugs already documented.
- **`bh-intellirupter`**: the real `rtu`↔`plc` Modbus conversation lives on
  the internal `proxiable` bridge. Only the explicitly published ports
  (5000, 9000) are reachable from outside — hitting those is a *separate*
  connection a participant initiates themselves, not a view into the
  `rtu`'s actual traffic. Whether this matters depends on the intended
  challenge design: if players are meant to interact with the PLC directly
  (as the published Modbus/web ports suggest), this is fine as-is; if
  they're meant to observe/intercept the RTU's traffic specifically, it
  isn't currently possible.
- **`dnpchallenge` is the one challenge already shaped correctly for
  this.** `ied`'s DNP3 outstation (port 20000) and `rtu`'s telnet console
  (port 2323) are both published, so a participant connecting to either is
  talking to the real outstation/console, not a decoy. This works because
  the intended interaction model here is "player connects directly to the
  exposed service," not "player passively sniffs someone else's traffic" —
  worth using as the reference pattern for the others if that's also the
  intended model for them.

**Resolution chosen (superseding the macvlan-vs-sidecar options originally
raised here):** each challenge keeps its own independent Docker network —
no shared network between challenges, no macvlan/physical-LAN bridging.
Instead, a single new service, **`audit-sidecar/`**, joins every
challenge's network as an additional member (the same way a shared
span/tap port would join a physical switch), and exposes one web page
(`http://<host>:8000`) where participants can:

- watch a live, decoded feed of traffic across all six challenge networks
  at once, tagged by which challenge it came from, and
- read and write the specific protocol points that matter for finishing
  each challenge (Modbus coils/registers via `pymodbus`; `dnpchallenge`'s
  ot-sim tags via its own HTTP API, which turned out to already support
  point writes — `POST /api/v1/write/{tag}/{value}` — not just the reads
  `vizhelper.py` already used) — without needing to hand-roll a
  Modbus/DNP3 client themselves once they've identified what to touch from
  the traffic view. For Modbus points the address and device id (unit) are
  editable per row, so a participant can reach an arbitrary coil/register or
  a different unit id (useful for the RE challenges) without code changes.

This keeps the "independent per-challenge networks" property intact while
still giving one centralized, low-friction place to observe and interact —
see `audit-sidecar/README.md` for setup (it mounts the Docker socket and
attaches to each challenge's network at runtime, so it can be started at any
time and follows challenges as they come up and go down, rather than having
to start *after* every challenge) and honest limitations:

- **It does not restore `mitm-modbus`'s Ettercap/ARP-spoofing mechanic.** A
  passive observer on the same Docker network doesn't reproduce "a
  participant actively poisons ARP on the wire" — this challenge's design
  intent likely needs a conscious update (e.g. "observe and manipulate the
  point directly via the sidecar" rather than "MITM it yourself"), which
  hasn't been done as part of this pass.
- DNP3 traffic in the live view is shown as raw hex, not decoded into
  function codes/points — `dnpchallenge`'s actual tags are still fully
  readable/writable through it via ot-sim's HTTP API, it's specifically
  the *packet view* that's shallow for DNP3 right now.
- `bh-intellirupter`'s exposed Modbus addresses are best-effort, read
  directly off `fixedfinal.st`'s declarations, not verified against
  OpenPLC's actual compiled address list.
- `re-challenge`'s exposed coil/register points are best-effort by design —
  that challenge is a binary RE exercise (Modbus/TCP on port 1502) whose
  whole point is discovering the real address map, so the sidecar only
  offers a couple of exploration starting points, not the solution.
- The write panel has no authentication — anyone reaching port 8000 can
  affect another participant's in-progress attempt. Acceptable for a
  hands-on exhibit built around manipulating these systems; flag if that's
  not the intended trust model for this event.

While wiring the sidecar's per-network static IPs, also found and fixed a
real, previously-undocumented bug: `bh-intellirupter/docker-compose.yml`
*defined* a `proxiable` network but never actually attached `plc` or `rtu`
to it — both services were silently landing on Compose's own auto-created
default network instead. Fixed by adding explicit `networks: [proxiable]`
to both services.
