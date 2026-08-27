# Player Guide — Wind Turbine Challenge

> This is a starting-point orientation doc, not the full story. The
> narrative/scenario framing for this exhibit is still being written — this
> page just covers what the exhibit *is*, what "winning" means, and how to
> get your first foothold. Treat anything here as subject to change once
> the full storyline is in place.

## What is this?

Somewhere on this network is a wind turbine spinning under load. It's
being kept running by a small industrial control system: a PLC (or RTU/IED
pair, depending on which version of this exhibit you're facing) reading a
sensor, deciding whether the turbine should keep spinning, and driving a
relay that controls power to it. There's also a dashboard somewhere
showing live status.

**Your goal: stop the turbine — safely — by interacting with the control
system, not by unplugging anything or touching the hardware directly.**

This is a real industrial protocol stack running on real embedded
hardware (or a faithful simulation of one), not a web app with a "stop"
button. You'll be working with the same kinds of protocols and habits used
in real power/utility environments: Modbus, DNP3, MQTT, and a PLC talking
ladder logic. If you don't know these protocols yet, that's the point —
you'll learn enough of them here to get the turbine to stop.

## Rules of engagement

- Stay inside the exhibit network/VLAN you've been assigned. Don't scan or
  touch anything outside the ranges provided by exhibit staff.
- This is a shared exhibit — other players may be working the same targets
  at the same time. Don't intentionally break things for other players
  (e.g., don't brick a device in a way that requires an admin reset unless
  that's explicitly part of the challenge).
- If something seems physically wrong (smoke, unusual noise, a relay
  chattering rapidly) — stop and get exhibit staff, don't keep
  troubleshooting.
- Ask a staff member if you're not sure whether something is in scope.

## Getting your first foothold

1. **Get on the exhibit network.** Staff will tell you which SSID/VLAN/
   port to use and what IP range to expect.
2. **Find out what's out there.** A basic network sweep is a reasonable
   first move — you're looking for a handful of hosts, not hundreds:
   ```bash
   nmap -sV -p- <exhibit-subnet>
   ```
3. **Know what you're looking at when you find it.** Common ports/services
   you're likely to run into on this kind of exhibit:
   - **502** — Modbus TCP (talks to a PLC or RTU's coils/registers)
   - **1502** — Modbus TCP on a non-standard port (a vulnerable Modbus
     *server binary* worth pulling down and reversing, not just poking)
   - **20000** — DNP3 (talks to an RTU/IED outstation)
   - **23** — Telnet (sometimes exposed on RTU/IED nodes for diagnostics —
     don't assume it's meant to be open)
   - **1883** — MQTT (state/telemetry being published for the dashboard —
     often TLS-wrapped; a cert may not mean you're not allowed to look)
   - **3000** and **9000** (or similar) — web dashboards / PLC web UIs
4. **Find the dashboard first if you can.** It won't let you *do* anything
   to the turbine, but it'll show you live state (is it spinning? is
   there a fault flag? which "zone" is unhappy?) — use it to check whether
   whatever you just tried actually had an effect, instead of guessing.
5. **Check the shared traffic view (port 8000) if one's running on this
   exhibit.** Each challenge's network is otherwise isolated — you won't
   see one challenge's internal traffic from the outside on your own. The
   shared view shows a live, tagged feed across every challenge network at
   once, plus the ability to read (and, where it makes sense, write) the
   specific values each challenge cares about once you've worked out which
   one matters. It's a shortcut past "write your own Modbus/DNP3 client
   from scratch" once you already know *what* you want to touch — it
   won't tell you *what* to touch, or *why*, on its own.
6. **If you're on the Modbus MITM challenge specifically, look for a web
   terminal (port 7681).** That network segment isn't reachable from your
   own laptop directly — the exhibit provides a shell already sitting on
   it (in your browser, no login) so you can run Ettercap and actually
   ARP-poison and alter the traffic yourself, the way the challenge is
   meant to be played, instead of just watching it happen.
7. **Work out what "stop" means for the specific control path you're
   facing.** Depending on the exact challenge instance, that might mean:
   flipping a coil over Modbus, writing a DNP3 output point, tripping a
   fault condition the PLC's logic is already watching for, or getting a
   simulated e-stop input to register. There isn't one universal answer —
   read what the system tells you (register/point names, ladder-logic
   variable names if you can see them, dashboard zone labels) and work
   from there.
8. **If you get stuck, look for what the system is *already* designed to
   react to.** These exhibits are usually built around a real safety or
   fault-handling behavior (voltage out of range, a trip counter, an
   e-stop) — finding and triggering that legitimate behavior is often more
   productive than trying to brute-force a stop condition.

## Challenge reference

Which exhibit you're facing determines which zone lights up on the
dashboard and which protocol you're actually working with. All of them
follow the same win condition: **the turbine runs (dashboard shows
red/"Normal") during normal operation, and stops (green/"Down") as the
result of a successful attack** — that's now consistent across every
challenge, so once you understand one, the pattern carries over.

| Challenge | Zone | Protocol | How to access / interact |
|---|---|---|---|
| `bh-intellirupter` | **zone5** | Modbus TCP | PLC's Modbus port is published on the exhibit network (default `5000`). Connect with any Modbus client and look for the coils driving the ladder logic's trip/reset/turbine outputs. The OpenPLC web UI (default port `9000`) is also reachable — worth a look even if you don't touch it, to understand what's actually running. |
| `dnpchallenge` | **zone2** | DNP3 (+ Telnet) | The IED's DNP3 outstation is directly reachable (default `20000`) — connect with a DNP3 master tool and read/write the `turbine.status`/`turbine.control` points. The RTU also exposes a Telnet console (default `2323`) with a `switch`/`led`/`estop` view — useful for understanding the e-stop logic even if the DNP3 side is where you'll actually act. |
| `mitm-modbus` | **zone1** | Modbus TCP (via MITM) | `master`/`slave`'s Modbus conversation lives on a private network segment your own laptop can't reach directly. Use the in-network web terminal (no login, default port `7681`) to run Ettercap yourself and ARP-poison the link — that's the intended path here, not connecting to a published Modbus port. |
| `re-challenge` | turbine (wiring-dependent) | Modbus TCP (binary RE) | A vulnerable Modbus **server binary** (`vulnserver`) is reachable on `1502/tcp`. The attack is in the binary itself, not the traffic: pull the executable down, reverse it (it's an aarch64/Pi build), find the bug in how it handles Modbus requests, and use that to drive the turbine relay. Watching the shared traffic view / reading a coil isn't enough here — you're meant to work out the real coil/register map yourself. |
| `mqtthelper` | **zone3, zone4** | — (read-only telemetry) | Not an attack surface on its own — it mirrors two spare GPIO pins' raw state onto the dashboard. If either zone matters to a specific instance of this exhibit, staff will tell you what's physically wired to them. |

If a shared traffic view (port 8000) or an in-network terminal (port 7681)
is running on this exhibit, see steps 5–6 above for how those fit in —
they're tools for working *any* of these challenges, not challenges of
their own.

## What counts as done

You'll know you've succeeded when the dashboard (or the turbine itself, if
you're on-site with the physical hardware) shows the turbine stopped and
staying stopped — not just flickering. If you think you've done it but
it's not reflected anywhere, flag it to staff; that's useful signal for
us either way.

---
*More to come: full scenario/backstory, difficulty tiers, and
hint structure will be added here once the storyboard is finalized.*
