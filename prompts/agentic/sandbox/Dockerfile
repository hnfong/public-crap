# PCP standardized guest image (see PLAN.md §2.4).
# Build with: sandbox/build.sh <tag>
#
# Pins (bump deliberately, never as a side effect):
#   - base image: debian:trixie-slim, pinned by manifest digest
#   - NODE_VERSION / RUST_TOOLCHAIN / RUSTUP_VERSION / PI_VERSION: exact
#   - clang, python3, openjdk-21: stable distro toolchains from apt (trixie)
FROM debian@sha256:8aa5a7bf5a1955bddbe7d74fcdd0b91ab30e74362a8b73af672b0481b35b44a0

ARG DEBIAN_FRONTEND=noninteractive
ARG NODE_VERSION=22.23.5
ARG RUST_TOOLCHAIN=1.100.0
ARG RUSTUP_VERSION=1.28.2
ARG PI_VERSION=1.6.1

ENV LANG=C.UTF-8

# --- stable toolchains from apt ---
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl wget git jq ripgrep unzip zip xz-utils bzip2 file less \
      procps psmisc \
      build-essential clang lld cmake ninja-build \
      python3 python3-venv python3-pip \
      openjdk-21-jdk-headless \
      openssh-server openssh-client \
 && rm -rf /var/lib/apt/lists/*

# --- Node.js: official nodejs.org tarball, SHA-256 verified ---
RUN set -eu; \
    cd /tmp; \
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-arm64.tar.xz" -O; \
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/SHASUMS256.txt" -O; \
    grep "  node-v${NODE_VERSION}-linux-arm64.tar.xz\$" SHASUMS256.txt | sha256sum -c -; \
    tar -xJf "node-v${NODE_VERSION}-linux-arm64.tar.xz" -C /usr/local --strip-components=1 --no-same-owner; \
    rm -f "node-v${NODE_VERSION}-linux-arm64.tar.xz" SHASUMS256.txt

# --- non-root agent user (owner decision: agent never runs as root) ---
RUN useradd -m -s /bin/bash -u 1000 agent

# --- Rust: official rustup, minimal profile, pinned toolchain ---
# Toolchain lives read-only in /usr/local/rustup; cargo home is writable by agent.
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/home/agent/.cargo \
    PATH=/home/agent/.cargo/bin:${PATH}
RUN set -eu; \
    curl -fsSL "https://static.rust-lang.org/rustup/archive/${RUSTUP_VERSION}/aarch64-unknown-linux-gnu/rustup-init" -o /tmp/rustup-init; \
    curl -fsSL "https://static.rust-lang.org/rustup/archive/${RUSTUP_VERSION}/aarch64-unknown-linux-gnu/rustup-init.sha256" -o /tmp/rustup-init.sha256; \
    cd /tmp && sha256sum -c rustup-init.sha256; \
    chmod +x rustup-init; \
    ./rustup-init -y --profile minimal --default-toolchain "${RUST_TOOLCHAIN}" --no-modify-path; \
    rm -f /tmp/rustup-init /tmp/rustup-init.sha256; \
    chown -R agent:agent /home/agent/.cargo

# --- pi coding agent (pinned) ---
RUN npm install -g "@earendil-works/pi-coding-agent@${PI_VERSION}" \
 && npm cache clean --force || true

# --- pi config template (sanitized copy of host config; NO auth/trust tokens) ---
COPY pi-config/settings.json /etc/skel/.pi/agent/settings.json

# --- sshd: used by the harness for a per-run reverse tunnel (host loopback
#     services, e.g. the model server, reach the guest at 127.0.0.1:<port>) ---
RUN mkdir -p /run/sshd \
 && printf 'PasswordAuthentication no\nPubkeyAuthentication yes\nX11Forwarding no\nPrintMotd no\n' \
      > /etc/ssh/sshd_config.d/pcp.conf

# --- entrypoint: start sshd, drop to agent, exec the test command ---
COPY pcp-entrypoint.sh /usr/local/bin/pcp-entrypoint
RUN chmod 755 /usr/local/bin/pcp-entrypoint \
 && mkdir -p /work \
 && chown agent:agent /work

WORKDIR /work
ENTRYPOINT ["/usr/local/bin/pcp-entrypoint"]
