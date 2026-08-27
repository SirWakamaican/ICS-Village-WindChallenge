# audit-sidecar

One shared service, attached to every challenge's own Docker network at
once, so there's a single place participants can go to:

1. **Watch live traffic** across all six challenge networks (best-effort
   protocol decode: Modbus function codes, cleartext telnet, raw hex for
   everything else including DNP3, which isn't decoded in depth here).
2. **Read and, where applicable, write** the specific protocol points that
   matter for finishing each challenge (Modbus coils/registers via
   `pymodbus`, `dnpchallenge`'s ot-sim tags via its own HTTP API), instead
   of needing to hand-roll a Modbus/DNP3 client just to poke at a value
   they've already identified from the traffic view. For Modbus challenges
   each point row also exposes editable **address** and **device id (unit)**
   fields (pre-filled with the known-good defaults) so you can read/write an
   arbitrary coil/register or target a different unit id without editing
   `challenges.py` — useful for the reverse-engineering challenges where the
   real address map is what you're hunting for.

See `docs/AUDIT.md` Part 3 for *why* this exists: none of these
challenges' internal traffic reaches a physical wire on its own (private
Docker bridge networks per challenge), so without something like this,
there's no way for a participant to observe or interact with most of it at
all.

## Setup

This service can be brought up **at any time** — before, after, or between
the challenge stacks (`bh-intellirupter`, `dnpchallenge`, `mitm-modbus`,
`mqtthelper`, `viz`, `re-challenge`):

```bash
cd audit-sidecar
docker compose up --build
```

Instead of declaring the challenge networks statically (which would make
Docker refuse to start until every one of them exists), the sidecar mounts
the Docker socket and attaches itself to each challenge network **at
runtime**, as that challenge comes up, then drops off again when the
challenge is taken down. It re-scans every few seconds
(`NETWORK_POLL_INTERVAL`, default 5s), so you can start and stop challenge
stacks underneath a running sidecar and its traffic view / read-write panel
follow along automatically — a challenge that isn't running simply shows no
traffic and its reads/writes return connection errors until it's back.

The mapping of Compose-generated network name → label → preferred static IP
lives in `CHALLENGE_NETWORKS` in `sidecar.py`. If the Docker socket isn't
available, the sidecar degrades gracefully: it still serves the UI and
sniffs whatever interfaces it's already attached to, but can't attach to new
challenge networks on its own.

Open `http://<host>:8000`.

## How interface-to-challenge labeling works

Each challenge's `docker-compose.yml` was given an explicit subnet
(172.30.0.0/24 for `bh-intellirupter`, 172.31.0.0/24 for `dnpchallenge`,
172.20.0.0/16 for `mitm-modbus` (pre-existing), 172.32.0.0/24 for
`mqtthelper`, 172.33.0.0/24 for `viz`, 172.34.0.0/24 for `re-challenge`)
specifically so this container could be given a deterministic static IP on
each one. Those preferred static IPs live in `CHALLENGE_NETWORKS` in
`sidecar.py` (used when it attaches to each network at runtime), and
`sidecar.py`'s `NETWORK_LABELS` matches its own IP prefix on each interface
against that table to know which challenge a given interface's traffic
belongs to. If you change any challenge's subnet, update both
`CHALLENGE_NETWORKS` and `NETWORK_LABELS` in `sidecar.py` to match, or
interface labeling will silently show `unknown (<ip>)` instead of the
challenge name. (If the preferred IP is ever unavailable, the sidecar still
attaches with a Docker-assigned address in the same subnet, so labeling
keeps working.)

## What this does *not* do

- **It does not make `mitm-modbus`'s Ettercap/ARP-spoofing mechanic work
  as originally designed.** That challenge's premise is a participant
  actively poisoning ARP on the wire between `master` and `slave`; a
  passive observer sitting on the same Docker network doesn't reproduce
  that (there's nothing stopping the real conversation, and a participant
  still has no way to run Ettercap against it without a NIC on that
  network segment, which they still don't have). This sidecar gives
  visibility into that traffic and a way to read/write the coil it
  controls directly — it doesn't restore the "intercept and alter live
  traffic yourself" experience. That challenge's design intent may need a
  conscious update to match what's actually deliverable here (e.g.
  "observe and manipulate the point directly" rather than "MITM it").
- **DNP3 traffic is not deeply decoded** — the live traffic view shows raw
  frame bytes for `dnpchallenge`'s DNP3 traffic (port 20000), not decoded
  function codes/points. Reading and writing `dnpchallenge`'s actual tags
  works fine (via ot-sim's own HTTP API, not by decoding DNP3 on the
  wire), so the challenge is still fully usable through this tool — it's
  specifically the *raw DNP3 packet view* that's shallow right now.
- **`bh-intellirupter`'s Modbus addresses in `challenges.py` are
  best-effort**, read directly off `fixedfinal.st`'s `%QX`/`%IX`
  declarations, not verified against OpenPLC's actual compiled Modbus
  address list. Cross-check against Settings → Modbus Server in the
  OpenPLC web UI before relying on them for anything beyond exploration.
- **`re-challenge`'s exposed points are deliberately best-effort.** That
  challenge is a reverse-engineering exercise against the `vulnserver`
  binary (Modbus/TCP on port 1502) — discovering its real coil/register
  map is the whole point, so the coil/register addresses listed for it are
  just exploration starting points, not the solution. Watch
  `docker logs re-challenge-vulnserver` to see which coil writes it
  actually accepts.

## Security note

The write panel can change live challenge state (trip a coil, clear a
fault, flip an e-stop tag) from a single shared web page with no
authentication. That's intentional for an exhibit built around
participants manipulating these systems — but it also means **anyone who
can reach port 8000 can reset or interfere with another participant's
in-progress attempt**. The editable address/device-id fields widen this
further: a participant can read or write *any* coil/register on a
challenge's Modbus server, not just the curated points. If that's not
acceptable for your event, put this behind whatever access control your
exhibit network already uses, or restrict the write endpoints
(`POST /api/write/...`) separately from the read-only traffic view.

This container also mounts the host's Docker socket
(`/var/run/docker.sock`) so it can attach/detach itself to challenge
networks as they start and stop. That grants it full control of the Docker
daemon, which is effectively host root. Keep that in mind when deciding
where to run it and who can reach it — the socket mount is what makes the
"start anytime / follow challenges as they come and go" behavior possible,
so if you don't need that flexibility you can remove the socket mount and
statically attach the networks in `docker-compose.yml` instead.

