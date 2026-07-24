Preparing Chasing Your Tail (CYT) for Raspberry Pi 5

Overview
- Target: Raspberry Pi 5 (64-bit aarch64). Assumes a Debian-based Raspberry Pi OS (64-bit) with network access.
- Goal: Provide reproducible steps and a safe, idempotent script to prepare a Pi for running CYT.

Quick steps
1. Flash Raspberry Pi OS (64-bit) and boot the Pi.
2. Update system packages:
   sudo apt update && sudo apt upgrade -y
3. Run the provided preparation script on the Pi:
   sudo bash prepare_rpi.sh
   (The script installs required system packages, creates a Python venv, and installs Python packages.)
4. Configure secrets and credentials:
   - Export CYT_MASTER_PASSWORD in the shell or copy .env.example -> .env and edit.
   - Migrate tokens into secure storage:
     python3 migrate_credentials.py
5. Verify readiness:
   python3 tools/check_readiness.py
6. Optional: enable the included systemd unit (example) to run the main monitor on boot.

Notes & Pi-specific tips
- Cryptography: pip should be upgraded to get prebuilt wheels. If build tools are missing, the script installs them.
- Kismet: For live capture, install Kismet from upstream packages; on RPi install instructions are at https://kismetwireless.net/.
- Monitor mode: Ensure the Wi‑Fi adapter supports monitor mode; Pi 5 built‑in radio may require additional firmware/drivers.
- Storage: Use a sufficiently large SD card or external SSD for logs and Kismet DBs.

Files added
- prepare_rpi.sh — idempotent setup script
- cyt.service.example — systemd service example
- RPI_EXPORT.md — this guide

Security
- Do NOT hardcode secrets; use CYT_MASTER_PASSWORD env var and migrate_credentials.py to secure credentials.
