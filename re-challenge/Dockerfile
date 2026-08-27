# The challenge binary is an aarch64 (Raspberry Pi 4) ELF, so this image is
# arm64-only. It runs natively on the Pi; on an x86 dev host it requires
# qemu-user emulation (see README - `docker run --privileged tonistiigi/binfmt`).
FROM arm64v8/debian:bookworm-slim

WORKDIR /challenge

# The vulnserver only needs glibc (from the base image) plus its own bundled
# libmodbus.so.5 / libpwm.so, loaded via LD_LIBRARY_PATH=. at runtime - no
# extra packages are required. bash is already present in the base image for
# the helper scripts.

# Bundle the Pi4 payload (shared libs, helper scripts, and a fallback copy of
# the vulnserver binary). docker-compose.yml bind-mounts ./Pi4/vulnserver over
# the copied one so participants can patch/replace the binary externally
# without rebuilding the image - the fallback here just keeps the image
# runnable on its own.
COPY Pi4/ ./
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh ./setup_pins.sh ./runme_pi4.sh ./vulnserver

EXPOSE 1502
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
