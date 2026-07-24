Copying this repository to a Raspberry Pi — exact commands

Recommended: Clone on the Pi (fastest, preserves git history)

# 1. On the Pi (SSH to it first)
ssh pi@raspberrypi.local
# Update OS and install git
sudo apt update && sudo apt upgrade -y
sudo apt install -y git
# Clone the repo and checkout prepared branch
git clone https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG.git /opt/cyt
cd /opt/cyt
git checkout intrench-prepare-repo-for-operation
# Run preparation script (installs system deps, creates venv, installs Python deps)
sudo bash prepare_rpi.sh

# 2. If you prefer to push local commits first (from your dev machine)
# On local dev: commit & push branch
git add .
git commit -m "Prepare repo for Pi export"
git push origin intrench-prepare-repo-for-operation
# Then on Pi: git clone as above

# 3. Direct file transfer options (alternative to git)
# Use rsync (preserves permissions, fast incremental)
rsync -avz --delete ./ pi@raspberrypi.local:/home/pi/cyt
ssh pi@raspberrypi.local 'cd /home/pi/cyt && sudo bash prepare_rpi.sh'

# 4. Tar + scp (simple archive transfer)
tar -czf cyt.tar.gz .
scp cyt.tar.gz pi@raspberrypi.local:~
ssh pi@raspberrypi.local 'mkdir -p /opt/cyt && sudo tar -xzf cyt.tar.gz -C /opt/cyt'

# 5. Post-transfer (on Pi)
# Set master password (recommended to export env var before migrating):
export CYT_MASTER_PASSWORD="<your-master-password>"
# Migrate credentials into secure storage
python3 migrate_credentials.py
# Verify readiness
python3 tools/check_readiness.py
# Optional: enable systemd service (edit paths first)
sudo cp cyt.service.example /etc/systemd/system/cyt.service
sudo systemctl daemon-reload
sudo systemctl enable --now cyt.service

Notes
- Replace raspberrypi.local with the Pi's IP if mDNS not available.
- Use the Pi user's home or /opt/cyt as shown; adjust ownership and permissions if needed.
- Ensure the Pi uses a 64-bit OS for best compatibility with dependencies.
