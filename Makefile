# Orchestrates the Wind Challenge exhibit. Each folder is its own Compose
# project; these targets run them in the right order:
#     helpers (viz, mqtthelper)  ->  challenges  ->  audit-sidecar
# The full-exhibit up/down delegate to up.sh / down.sh; the per-challenge
# targets below bring individual/multiple challenges up or down and manage
# the shared helpers + sidecar automatically. See docs/AUDIT.md Part 3 for
# why audit-sidecar must come up last / go down first, and
# audit-sidecar/sidecar.py for how it attaches to each challenge network
# dynamically (which is what makes bringing up a subset safe).

COMPOSE ?= docker compose

# Shared helper stacks every challenge reports into. Brought up before any
# challenge and only torn down once no challenge is left running:
#   viz        - grid dashboard + Mosquitto MQTT broker
#   mqtthelper - GPIO->MQTT bridge + "all challenges complete" zone logic
HELPERS ?= viz mqtthelper

# The nameable challenges - the stacks a participant actually targets.
CHALLENGES ?= bh-intellirupter dnpchallenge mitm-modbus re-challenge

# Attaches to every challenge network at runtime via the Docker socket, so it
# works with ANY subset of challenges. Must be up whenever at least one
# challenge is up; it comes up last and goes down first.
SIDECAR ?= audit-sidecar

STACKS = $(HELPERS) $(CHALLENGES) $(SIDECAR)

# Challenge name(s) for up-challenge / down-challenge, e.g.
#   make up-challenge C="dnpchallenge mitm-modbus"
C ?=
# Extra flags forwarded to the underlying compose up/down (e.g. --build, -v).
ARGS ?=

.PHONY: help up up-build down restart ps logs up-challenge down-challenge

help:
	@echo "Wind Challenge orchestration:"
	@echo "  make up                       Bring the whole exhibit up (helpers -> challenges -> $(SIDECAR))"
	@echo "  make up-build                 Same, forcing an image rebuild"
	@echo "  make down                     Tear the whole exhibit down (reverse order)"
	@echo "  make restart                  down then up"
	@echo "  make ps                       Show status of every stack"
	@echo "  make logs                     Follow $(SIDECAR) logs"
	@echo
	@echo "Per-challenge control (names: $(CHALLENGES)):"
	@echo "  make up-<name>                Bring up one challenge + its helpers + $(SIDECAR)"
	@echo "  make down-<name>              Bring down one challenge; helpers + $(SIDECAR) stay up while"
	@echo "                                any challenge remains, and stop once the last one is down"
	@echo "  make up-challenge   C=\"a b\"   Bring up several named challenges at once"
	@echo "  make down-challenge C=\"a b\"   Bring down several named challenges at once"
	@echo "  ...append ARGS=--build (up) or ARGS=-v (down) to forward flags to compose"

up:
	./up.sh

up-build:
	./up.sh --build

down:
	./down.sh

restart: down up

ps:
	@for s in $(STACKS); do echo "== $$s =="; ( cd $$s && $(COMPOSE) ps ); done

logs:
	@cd $(SIDECAR) && $(COMPOSE) logs -f

# ---- Per-challenge control ------------------------------------------------

# Bring up one or more named challenges plus the shared helpers and sidecar:
#   make up-challenge C="dnpchallenge mitm-modbus"   (or  make up-dnpchallenge)
up-challenge:
	@if [ -z "$(strip $(C))" ]; then \
		echo "usage: make $@ C=\"<name> [name...]\"  (choices: $(CHALLENGES))" >&2; exit 2; fi; \
	for c in $(C); do case " $(CHALLENGES) " in *" $$c "*) ;; \
		*) echo "error: unknown challenge '$$c' (choices: $(CHALLENGES))" >&2; exit 2 ;; esac; done
	@for h in $(HELPERS); do \
		echo ">> up helper $$h"; ( cd "$$h" && $(COMPOSE) up -d $(ARGS) ) || exit 1; done
	@for c in $(C); do \
		echo ">> up challenge $$c"; ( cd "$$c" && $(COMPOSE) up -d $(ARGS) ) || exit 1; done
	@echo ">> ensuring $(SIDECAR) is up"; ( cd "$(SIDECAR)" && $(COMPOSE) up -d $(ARGS) ) || exit 1
	@echo "up: $(C)  (+ helpers + $(SIDECAR))"

# Bring down one or more named challenges. The sidecar is detached first so
# each challenge's network can be removed cleanly, then brought back up if any
# challenge remains; once the last challenge is down, helpers stop too.
down-challenge:
	@if [ -z "$(strip $(C))" ]; then \
		echo "usage: make $@ C=\"<name> [name...]\"  (choices: $(CHALLENGES))" >&2; exit 2; fi; \
	for c in $(C); do case " $(CHALLENGES) " in *" $$c "*) ;; \
		*) echo "error: unknown challenge '$$c' (choices: $(CHALLENGES))" >&2; exit 2 ;; esac; done
	@echo ">> detaching $(SIDECAR)"; ( cd "$(SIDECAR)" && $(COMPOSE) down $(ARGS) ) || true
	@for c in $(C); do \
		echo ">> down challenge $$c"; ( cd "$$c" && $(COMPOSE) down $(ARGS) ) || \
			echo "warning: '$$c' down returned non-zero (already stopped?)" >&2; done
	@remaining=""; \
	for c in $(CHALLENGES); do \
		if [ -n "$$( cd "$$c" && $(COMPOSE) ps -q 2>/dev/null )" ]; then remaining="$$remaining $$c"; fi; \
	done; \
	if [ -n "$$remaining" ]; then \
		echo ">> challenges still up:$$remaining"; \
		echo ">> bringing $(SIDECAR) back up to keep watching them"; \
		( cd "$(SIDECAR)" && $(COMPOSE) up -d ) || exit 1; \
	else \
		echo ">> no challenges left - stopping helpers ($(HELPERS))"; \
		for h in $(HELPERS); do ( cd "$$h" && $(COMPOSE) down $(ARGS) ) || true; done; \
	fi
	@echo "down: $(C)"

# Single-name shortcuts, e.g. `make up-dnpchallenge` / `make down-mitm-modbus`.
# Explicit targets above (up-build etc.) take precedence over these patterns.
up-%:
	@$(MAKE) --no-print-directory up-challenge C="$*" ARGS="$(ARGS)"

down-%:
	@$(MAKE) --no-print-directory down-challenge C="$*" ARGS="$(ARGS)"
