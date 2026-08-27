"""audit-sidecar: a single service attached to every challenge's own Docker
network, so participants have one place to watch traffic across all of them
and to read/write the protocol points that matter for each challenge -
without needing raw NIC access to networks that never reach a physical
wire (see docs/AUDIT.md Part 3 for why that matters here).

Each challenge network stays independent from the others; this container
is simply a member of all of them at once, the same way a shared span/tap
point would be on real hardware.
"""
import html
import os
import socket
import struct
import threading
import time
from collections import deque

import requests
from flask import Flask, jsonify, render_template_string, request
from pymodbus.client import ModbusTcpClient
from scapy.all import IP, TCP, Raw, sniff

from challenges import CHALLENGES, find_challenge, find_element

app = Flask(__name__)

EVENTS = deque(maxlen=int(os.environ.get("EVENTS_MAXLEN", "500")))
EVENTS_LOCK = threading.Lock()

# Prefix-matched against this container's own IP on each interface to label
# which challenge network a given interface belongs to. Must match the
# subnets assigned in each challenge's docker-compose.yml network block.
NETWORK_LABELS = {
    "172.18.0.": "audit-sidecar",
    "172.30.0.": "bh-intellirupter",
    "172.31.0.": "dnpchallenge",
    "172.20.": "mitm-modbus",
    "172.32.0.": "mqtthelper",
    "172.33.0.": "viz",
    "172.34.0.": "re-challenge"    
}

# Docker networks this container tries to join at runtime, keyed by the exact
# Compose-generated network name, with the label and the static IP we prefer
# on each. Joining happens dynamically (see network_monitor) via the mounted
# Docker socket, so the sidecar can start before any challenge is up and
# attach/detach as challenge stacks come and go. Keep the subnets in each
# `ip` here in sync with NETWORK_LABELS and each challenge's compose file.
CHALLENGE_NETWORKS = {
    "proxiable":              {"label": "bh-intellirupter", "ip": "172.30.0.9"},
    "dnpchallenge_default":   {"label": "dnpchallenge",     "ip": "172.31.0.9"},
    "mitm-modbus_my_network": {"label": "mitm-modbus",      "ip": "172.20.0.9"},
    "mqtthelper_default":     {"label": "mqtthelper",       "ip": "172.32.0.9"},
    "viz_default":            {"label": "viz",              "ip": "172.33.0.9"},
    "re-challenge_default":   {"label": "re-challenge",     "ip": "172.34.0.9"},
}

# How often (seconds) to re-scan Docker for challenge networks to join and
# re-scan local interfaces for new sniffers to start.
POLL_INTERVAL = int(os.environ.get("NETWORK_POLL_INTERVAL", "5"))


def label_for_ip(ip):
    for prefix, label in NETWORK_LABELS.items():
        if ip.startswith(prefix):
            return label
    return f"unknown ({ip})"


def local_interfaces():
    """Yield (iface, ip) for every non-loopback IPv4-addressed interface."""
    import psutil

    for iface, addrs in psutil.net_if_addrs().items():
        if iface == "lo":
            continue
        for addr in addrs:
            if addr.family == socket.AF_INET:
                yield iface, addr.address


def iface_exists(iface):
    import psutil

    return iface in psutil.net_if_addrs()


def decode_modbus(payload):
    if len(payload) < 8:
        return None
    try:
        _txid, _protoid, length, unit_id, func_code = struct.unpack(">HHHBB", payload[:8])
    except struct.error:
        return None
    is_exception = bool(func_code & 0x80)
    return f"Modbus unit={unit_id} func={'EXC:' if is_exception else ''}0x{func_code & 0x7F:02x} len={length}"


def decode_payload(payload, sport, dport):
    # 1502 is re-challenge's vulnserver, a Modbus/TCP server on a non-standard
    # port; decode it the same way as the standard 502.
    if 502 in (sport, dport) or 1502 in (sport, dport):
        decoded = decode_modbus(payload)
        if decoded:
            return decoded
    if 23 in (sport, dport):
        try:
            text = payload.decode("utf-8", errors="replace").strip()
            if text:
                return "telnet: " + text
        except Exception:
            pass
    if 20000 in (sport, dport):
        return f"dnp3 (raw, {len(payload)}B): {payload[:24].hex()}"
    return f"raw ({len(payload)}B): {payload[:24].hex()}"


def handle_packet(label, iface, pkt):
    if IP not in pkt:
        return
    sport = pkt[TCP].sport if TCP in pkt else None
    dport = pkt[TCP].dport if TCP in pkt else None
    summary = decode_payload(bytes(pkt[Raw].load), sport, dport) if Raw in pkt else ""
    event = {
        "ts": time.time(),
        "network": label,
        "iface": iface,
        "src": pkt[IP].src,
        "dst": pkt[IP].dst,
        "sport": sport,
        "dport": dport,
        "summary": summary,
    }
    with EVENTS_LOCK:
        EVENTS.appendleft(event)


def sniff_iface(iface, label):
    while True:
        if not iface_exists(iface):
            # The interface went away (e.g. its challenge network was removed
            # while we were running). Stop this thread; refresh_sniffers will
            # start a fresh one if the interface ever comes back.
            print(f"[sniff:{iface}] interface gone, stopping", flush=True)
            with SNIFFER_LOCK:
                SNIFFER_THREADS.pop(iface, None)
            return
        try:
            sniff(iface=iface, prn=lambda p: handle_packet(label, iface, p), store=False)
        except Exception as exc:
            print(f"[sniff:{iface}] error, retrying in 5s: {exc}", flush=True)
            time.sleep(5)


# iface -> Thread, so refresh_sniffers can start sniffers for interfaces that
# appear after startup (challenge networks joined while running) without
# double-starting ones already covered.
SNIFFER_THREADS = {}
SNIFFER_LOCK = threading.Lock()


def refresh_sniffers():
    """Start a sniffer thread for every currently-attached interface that
    doesn't already have a live one. Safe to call repeatedly; idempotent."""
    with SNIFFER_LOCK:
        for iface, ip in local_interfaces():
            existing = SNIFFER_THREADS.get(iface)
            if existing and existing.is_alive():
                continue
            label = label_for_ip(ip)
            thread = threading.Thread(
                target=sniff_iface, args=(iface, label), daemon=True
            )
            thread.start()
            SNIFFER_THREADS[iface] = thread
            print(f"[sidecar] sniffing {iface} ({ip}) as '{label}'", flush=True)


# ---- Dynamic challenge-network membership ------------------------------

def _self_container(client):
    """Look up this container via the Docker API so we can attach ourselves
    to challenge networks. Docker sets the container hostname to its short id
    by default; fall back to a configurable container name."""
    candidates = [
        socket.gethostname(),
        os.environ.get("SIDECAR_CONTAINER_NAME", "audit-sidecar"),
    ]
    for ident in candidates:
        if not ident:
            continue
        try:
            return client.containers.get(ident)
        except Exception:
            continue
    return None


def _sync_networks(client, me):
    """Join any known challenge network that exists and we're not on yet.
    Returns the list of (network_name, label) newly joined this pass."""
    import docker

    joined = []
    for net_name, cfg in CHALLENGE_NETWORKS.items():
        try:
            net = client.networks.get(net_name)
        except docker.errors.NotFound:
            continue
        except docker.errors.APIError as exc:
            print(f"[net-monitor] lookup {net_name} failed: {exc}", flush=True)
            continue
        net.reload()
        if any(c.id == me.id for c in net.containers):
            continue
        try:
            net.connect(me, ipv4_address=cfg["ip"])
        except docker.errors.APIError:
            # Preferred static IP may be taken or outside the subnet; still
            # join (labeling works off the subnet prefix, not the exact IP).
            try:
                net.connect(me)
            except docker.errors.APIError as exc:
                print(f"[net-monitor] connect {net_name} failed: {exc}", flush=True)
                continue
        joined.append((net_name, cfg["label"]))
    return joined


def network_monitor():
    """Continuously attach to challenge networks as they appear and pick up
    sniffers for newly-attached interfaces, so challenges can be started and
    stopped underneath a running sidecar. Degrades gracefully (static
    behavior) if the Docker SDK or socket isn't available."""
    try:
        import docker

        client = docker.from_env()
        client.ping()
    except Exception as exc:
        print(
            "[net-monitor] Docker API unavailable; dynamic network attach "
            f"disabled (sniffing whatever is already attached): {exc}",
            flush=True,
        )
        return

    me = _self_container(client)
    if me is None:
        print(
            "[net-monitor] could not identify own container; dynamic network "
            "attach disabled. Set SIDECAR_CONTAINER_NAME if needed.",
            flush=True,
        )
        return

    while True:
        try:
            for net_name, label in _sync_networks(client, me):
                print(f"[net-monitor] joined {net_name} ({label})", flush=True)
            refresh_sniffers()
        except Exception as exc:
            print(f"[net-monitor] error: {exc}", flush=True)
        time.sleep(POLL_INTERVAL)


# ---- Challenge element read/write ------------------------------------

def parse_overrides(challenge, source):
    """Pull optional address / device-id (Modbus unit) overrides out of a
    request (query args for reads, JSON body for writes). Only meaningful for
    Modbus challenges; ignored for ot-sim tag challenges. Returns
    (overrides_dict, error_message)."""
    overrides = {}
    if challenge["protocol"] != "modbus":
        return overrides, None
    addr = source.get("address")
    if addr not in (None, ""):
        try:
            overrides["address"] = int(addr)
        except (TypeError, ValueError):
            return None, f"invalid address {addr!r}"
    unit = source.get("unit")
    if unit not in (None, ""):
        try:
            overrides["unit"] = int(unit)
        except (TypeError, ValueError):
            return None, f"invalid device id {unit!r}"
    return overrides, None


def read_modbus_element(challenge, element, overrides):
    client = ModbusTcpClient(challenge["host"], port=challenge["port"])
    try:
        if not client.connect():
            return None, "connection failed"
        unit = overrides.get("unit", challenge.get("unit", 1))
        kind = element["kind"]
        addr = overrides.get("address", element["address"])
        if kind == "coil":
            rr = client.read_coils(address=addr, count=1, device_id=unit)
        elif kind == "discrete_input":
            rr = client.read_discrete_inputs(address=addr, count=1, device_id=unit)
        elif kind == "holding_register":
            rr = client.read_holding_registers(address=addr, count=1, device_id=unit)
        else:
            return None, f"unsupported kind {kind}"
        if rr.isError():
            return None, str(rr)
        value = rr.registers[0] if kind == "holding_register" else rr.bits[0]
        return value, None
    except Exception as exc:
        return None, str(exc)
    finally:
        client.close()


def write_modbus_element(challenge, element, value, overrides):
    client = ModbusTcpClient(challenge["host"], port=challenge["port"])
    try:
        if not client.connect():
            return "connection failed"
        unit = overrides.get("unit", challenge.get("unit", 1))
        kind = element["kind"]
        addr = overrides.get("address", element["address"])
        if kind == "coil":
            rr = client.write_coil(address=addr, value=bool(int(float(value))), device_id=unit)
        elif kind == "holding_register":
            rr = client.write_register(address=addr, value=int(float(value)), device_id=unit)
        else:
            return f"cannot write to a {kind}"
        return str(rr) if rr.isError() else None
    except Exception as exc:
        return str(exc)
    finally:
        client.close()


def read_otsim_element(challenge, element):
    url = f"http://{challenge['host']}:{challenge['port']}/api/v1/query/{element['tag']}"
    try:
        resp = requests.get(url, timeout=3)
        resp.raise_for_status()
        return resp.json().get("value"), None
    except Exception as exc:
        return None, str(exc)


def write_otsim_element(challenge, element, value):
    url = f"http://{challenge['host']}:{challenge['port']}/api/v1/write/{element['tag']}/{value}"
    try:
        resp = requests.post(url, timeout=3)
        resp.raise_for_status()
        return None
    except Exception as exc:
        return str(exc)


def read_element(challenge, element, overrides=None):
    overrides = overrides or {}
    if challenge["protocol"] == "modbus":
        return read_modbus_element(challenge, element, overrides)
    return read_otsim_element(challenge, element)


def write_element(challenge, element, value, overrides=None):
    overrides = overrides or {}
    if challenge["protocol"] == "modbus":
        return write_modbus_element(challenge, element, value, overrides)
    return write_otsim_element(challenge, element, value)


# ---- Web UI ------------------------------------------------------------

PAGE = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>audit-sidecar</title>
<style>
  body { font-family: -apple-system, Segoe UI, sans-serif; margin: 0; padding: 1rem;
         background: #111; color: #ddd; }
  h1 { font-size: 1.1rem; margin: 0 0 0.75rem; }
  h2 { font-size: 0.95rem; margin: 1.5rem 0 0.5rem; }
  .tabs { display: flex; gap: 0.5rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
  .tab { padding: 0.25rem 0.6rem; border: 1px solid #444; border-radius: 4px;
         cursor: pointer; font-size: 0.85rem; }
  .tab.active { background: #2d6cdf; border-color: #2d6cdf; color: white; }
  table { border-collapse: collapse; width: 100%; font-size: 0.82rem; }
  th, td { border-bottom: 1px solid #333; padding: 0.3rem 0.5rem; text-align: left;
           font-family: ui-monospace, monospace; }
  th { color: #999; font-weight: normal; }
  .net-badge { padding: 0.05rem 0.4rem; border-radius: 3px; background: #333;
               font-size: 0.75rem; }
  .challenge { border: 1px solid #333; border-radius: 6px; padding: 0.75rem;
               margin-bottom: 0.75rem; }
  .challenge .note { color: #999; font-size: 0.78rem; margin: 0.25rem 0 0.6rem; }
  .elem-row { display: flex; align-items: center; gap: 0.5rem; margin: 0.3rem 0;
              font-size: 0.85rem; }
  .elem-name { flex: 1; }
  .elem-value { min-width: 3.5rem; font-family: ui-monospace, monospace; }
  button { background: #2d6cdf; border: none; color: white; padding: 0.2rem 0.5rem;
           border-radius: 4px; cursor: pointer; font-size: 0.78rem; }
  button.secondary { background: #444; }
  input[type=text] { width: 4rem; background: #222; border: 1px solid #444;
                      color: #ddd; padding: 0.15rem 0.3rem; border-radius: 3px; }
  input.small { width: 3rem; }
  .elem-field { display: flex; align-items: center; gap: 0.2rem; color: #999;
                font-size: 0.75rem; }
  .ro-tag { color: #777; font-size: 0.72rem; }
  #traffic { max-height: 45vh; overflow-y: auto; border: 1px solid #333; border-radius: 6px; }
</style>
</head>
<body>
<h1>audit-sidecar - shared traffic + challenge state view</h1>

<h2>Live traffic (all challenge networks)</h2>
<div class="tabs" id="netTabs"><div class="tab active" id="allTab">all</div></div>
<div id="traffic">
  <table>
    <thead><tr><th>time</th><th>network</th><th>src</th><th>dst</th><th>ports</th><th>summary</th></tr></thead>
    <tbody id="trafficBody"></tbody>
  </table>
</div>

<h2>Challenge state</h2>
<div id="challenges"></div>

<script>
const CHALLENGES = {challenges_json};
const NETWORKS = {networks_json};
let currentNet = "";

function fmtTime(ts) {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString();
}

async function refreshTraffic() {
  const url = currentNet ? `/api/events?network=${encodeURIComponent(currentNet)}` : "/api/events";
  const resp = await fetch(url);
  const events = await resp.json();
  const body = document.getElementById("trafficBody");
  body.innerHTML = events.map(e => `
    <tr>
      <td>${fmtTime(e.ts)}</td>
      <td><span class="net-badge">${e.network}</span></td>
      <td>${e.src}</td>
      <td>${e.dst}</td>
      <td>${e.sport ?? ""}&rarr;${e.dport ?? ""}</td>
      <td>${e.summary}</td>
    </tr>`).join("");
}

function buildTabs() {
  const tabsEl = document.getElementById("netTabs");
  for (const net of NETWORKS) {
    const tab = document.createElement("div");
    tab.className = "tab";
    tab.textContent = net;
    tab.onclick = () => selectTab(net, tab);
    tabsEl.appendChild(tab);
  }
}

function selectTab(net, el) {
  currentNet = net;
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  el.classList.add("active");
  refreshTraffic();
}

function renderChallenges() {
  const root = document.getElementById("challenges");
  root.innerHTML = CHALLENGES.map(c => `
    <div class="challenge">
      <strong>${c.label}</strong> <span class="net-badge">${c.protocol}</span>
      ${c.note ? `<div class="note">${c.note}</div>` : ""}
      ${c.elements.map(el => `
        <div class="elem-row" data-challenge="${c.id}" data-element="${el.name}">
          <span class="elem-name">${el.name}</span>
          <span class="elem-value" id="val-${c.id}-${cssSafe(el.name)}">-</span>
          ${c.protocol === "modbus" ? `
            <span class="elem-field">addr
              <input type="text" class="small" id="addr-${c.id}-${cssSafe(el.name)}"
                     value="${el.address ?? ""}" title="Modbus address"></span>
            <span class="elem-field">id
              <input type="text" class="small" id="unit-${c.id}-${cssSafe(el.name)}"
                     value="${c.unit ?? ""}" title="Modbus device id (unit)"></span>
          ` : ""}
          <button class="secondary" onclick="doRead('${c.id}', '${escapeJs(el.name)}')">read</button>
          ${el.access === "rw" ? `
            <input type="text" id="in-${c.id}-${cssSafe(el.name)}" placeholder="value">
            <button onclick="doWrite('${c.id}', '${escapeJs(el.name)}')">write</button>
          ` : '<span class="ro-tag">read-only</span>'}
        </div>
      `).join("")}
    </div>
  `).join("");
}

function cssSafe(s) { return s.replace(/[^a-zA-Z0-9]/g, "_"); }
function escapeJs(s) { return s.replace(/'/g, "\\\\'"); }

function elemOverrides(challengeId, elementName) {
  const key = cssSafe(elementName);
  const overrides = {};
  const addrEl = document.getElementById(`addr-${challengeId}-${key}`);
  const unitEl = document.getElementById(`unit-${challengeId}-${key}`);
  if (addrEl && addrEl.value !== "") overrides.address = addrEl.value;
  if (unitEl && unitEl.value !== "") overrides.unit = unitEl.value;
  return overrides;
}

async function doRead(challengeId, elementName) {
  const valEl = document.getElementById(`val-${challengeId}-${cssSafe(elementName)}`);
  valEl.textContent = "...";
  const params = new URLSearchParams(elemOverrides(challengeId, elementName));
  const qs = params.toString() ? `?${params.toString()}` : "";
  const resp = await fetch(`/api/read/${encodeURIComponent(challengeId)}/${encodeURIComponent(elementName)}${qs}`);
  const data = await resp.json();
  valEl.textContent = resp.ok ? data.value : `err: ${data.error}`;
}

async function doWrite(challengeId, elementName) {
  const inputEl = document.getElementById(`in-${challengeId}-${cssSafe(elementName)}`);
  const value = inputEl.value;
  const body = Object.assign({value}, elemOverrides(challengeId, elementName));
  const resp = await fetch(`/api/write/${encodeURIComponent(challengeId)}/${encodeURIComponent(elementName)}`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
  const data = await resp.json();
  if (!resp.ok) {
    alert(`write failed: ${data.error}`);
  } else {
    doRead(challengeId, elementName);
  }
}

document.getElementById("allTab").onclick = (e) => selectTab("", e.target);
buildTabs();
renderChallenges();
refreshTraffic();
setInterval(refreshTraffic, 2000);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    import json

    challenges_for_js = [
        {
            "id": c["id"],
            "label": html.escape(c["label"]),
            "protocol": c["protocol"],
            "unit": c.get("unit"),
            "note": html.escape(c.get("note", "")) if c.get("note") else "",
            "elements": [
                {
                    "name": e["name"],
                    "access": e["access"],
                    "kind": e.get("kind"),
                    "address": e.get("address"),
                }
                for e in c["elements"]
            ],
        }
        for c in CHALLENGES
    ]
    page = PAGE.replace("{challenges_json}", json.dumps(challenges_for_js))
    page = page.replace(
        "{networks_json}", json.dumps(sorted(set(NETWORK_LABELS.values())))
    )
    return render_template_string(page)


@app.route("/api/events")
def api_events():
    network = request.args.get("network")
    with EVENTS_LOCK:
        events = list(EVENTS)
    if network:
        events = [e for e in events if e["network"] == network]
    return jsonify(events[:200])


@app.route("/api/read/<challenge_id>/<element_name>")
def api_read(challenge_id, element_name):
    challenge = find_challenge(challenge_id)
    if not challenge:
        return jsonify({"error": "unknown challenge"}), 404
    element = find_element(challenge, element_name)
    if not element:
        return jsonify({"error": "unknown element"}), 404
    overrides, err = parse_overrides(challenge, request.args)
    if err:
        return jsonify({"error": err}), 400
    value, err = read_element(challenge, element, overrides)
    if err:
        return jsonify({"error": err}), 502
    return jsonify({"value": value})


@app.route("/api/write/<challenge_id>/<element_name>", methods=["POST"])
def api_write(challenge_id, element_name):
    challenge = find_challenge(challenge_id)
    if not challenge:
        return jsonify({"error": "unknown challenge"}), 404
    element = find_element(challenge, element_name)
    if not element:
        return jsonify({"error": "unknown element"}), 404
    if element.get("access") != "rw":
        return jsonify({"error": "read-only element"}), 403
    payload = request.get_json(silent=True) or {}
    value = payload.get("value")
    if value is None or value == "":
        return jsonify({"error": "missing value"}), 400
    overrides, err = parse_overrides(challenge, payload)
    if err:
        return jsonify({"error": err}), 400
    err = write_element(challenge, element, value, overrides)
    if err:
        return jsonify({"error": err}), 502
    return jsonify({"ok": True})


if __name__ == "__main__":
    refresh_sniffers()
    threading.Thread(target=network_monitor, daemon=True).start()
    app.run(host="0.0.0.0", port=8000, threaded=True)
