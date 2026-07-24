#!/usr/bin/env bash
# prepare_rpi.sh — Idempotent preparation script for Raspberry Pi (Debian-based)
# Run as root or with sudo on the Raspberry Pi 5 (64-bit).
set -euo pipefail

echo "[CYT] Starting Raspberry Pi preparation"
ARCH=$(uname -m)
echo "[CYT] Host architecture: $ARCH"
if [[ "$ARCH" != "aarch64" && "$ARCH" != "armv7l" ]]; then
  echo "[WARN] Expected Pi architecture (aarch64 or armv7l). Proceeding but confirm compatibility."
fi

# Update and install system packages needed to build Python packages and for Kismet
apt-get update -y
apt-get install -y --no-install-recommends \
  build-essential python3-venv python3-dev python3-pip \
  libpcap-dev libssl-dev libffi-dev pkg-config \
  wireless-tools iw ethtool git ca-certificates \
  # Optional: kismet (may require upstream repo or manual install)
  
# Create a dedicated venv
VENV_DIR="/opt/cyt/venv"
if [[ ! -d "$VENV_DIR" ]]; then
  echo "[CYT] Creating /opt/cyt and virtualenv"
  mkdir -p /opt/cyt
  python3 -m venv "$VENV_DIR"
fi

# Activate venv and install Python deps
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel
if [[ -f "requirements.txt" ]]; then
  pip install -r requirements.txt
else
  echo "[WARN] requirements.txt not found in current directory. Please run this script from the project root or copy requirements.txt to the Pi." >&2
fi

# Create logs dir
mkdir -p /opt/cyt/logs
chown -R $SUDO_USER:${SUDO_USER:-root} /opt/cyt || true

# Copy example env if none exists
if [[ ! -f ".env" && -f ".env.example" ]]; then
  cp .env.example .env
  echo "[CYT] .env.example copied to .env — edit it and set CYT_MASTER_PASSWORD before running migrate_credentials.py"
fi

cat <<'EOF'

[CYT] Preparation complete.
Next steps (on the Pi):
  1. Edit .env and set CYT_MASTER_PASSWORD or export it in the shell:
       export CYT_MASTER_PASSWORD="<your-password>"
  2. Migrate credentials safely:
       python3 migrate_credentials.py
  3. Run readiness checks:
       python3 tools/check_readiness.py
  4. Optionally enable the systemd service example (edit paths first):
       sudo cp cyt.service.example /etc/systemd/system/cyt.service
       sudo systemctl daemon-reload
       sudo systemctl enable --now cyt.service

EOF

exit 0
