Implementing CYT on Raspberry Pi 5 — Operations Guide

Overview
This guide covers running Chasing Your Tail (CYT) on a Raspberry Pi 5 (64-bit) after initial setup. See RPI_EXPORT.md and prepare_rpi.sh for setup steps.

System Architecture on Pi 5
```
Raspberry Pi 5 (64-bit OS)
├── Kismet (packet capture, SQLite database)
├── CYT Core Monitoring (chasing_your_tail.py)
├── GUI (cyt_gui.py, optional, requires display)
├── Analysis Tools (probe_analyzer.py, surveillance_analyzer.py)
└── Systemd Service (auto-start via cyt.service)
```

Prerequisites (post-setup)
- prepare_rpi.sh has run and succeeded
- Python venv created at /opt/cyt/venv
- CYT_MASTER_PASSWORD set in environment or .env file
- migrate_credentials.py has run to secure API tokens
- tools/check_readiness.py passes
- Kismet installed and configured
- Wi-Fi adapter supporting monitor mode connected and recognized

Running CYT Components

1. Core Monitoring (Background Mode)
```bash
source /opt/cyt/venv/bin/activate
cd /opt/cyt
python3 chasing_your_tail.py
```
Monitors Kismet database every 60 seconds, logs device persistence to ./logs/cyt_log_*.
Output files: `./logs/cyt_log_MMDDYY_HHMMSS`

2. GUI Interface (With Display)
```bash
# Requires X11 or Wayland desktop
source /opt/cyt/venv/bin/activate
cd /opt/cyt
python3 cyt_gui.py
```
Features:
- Real-time device monitoring
- Surveillance analysis button (GPS-correlated persistence detection)
- Log analysis button
- File generation notifications

3. Probe Data Analysis
```bash
# Analyze past 14 days (local only, no WiGLE API calls)
python3 probe_analyzer.py

# Analyze past 7 days
python3 probe_analyzer.py --days 7

# Analyze ALL logs
python3 probe_analyzer.py --all-logs

# Include WiGLE geolocation (uses API credits!)
python3 probe_analyzer.py --wigle
```
Output: `./reports/probe_analysis_report_YYYYMMDD_HHMMSS.txt`

4. Surveillance Detection & Advanced Analysis
```bash
# Run advanced surveillance detection with GPS correlation
python3 surveillance_analyzer.py

# Demo mode (Phoenix, Arizona test data)
python3 surveillance_analyzer.py --demo

# Analyze specific Kismet database
python3 surveillance_analyzer.py --kismet-db /path/to/kismet.db

# Focus on stalking patterns with high persistence threshold
python3 surveillance_analyzer.py --stalking-only --min-persistence 0.8

# Export results to JSON
python3 surveillance_analyzer.py --output-json results.json

# Use external GPS data file
python3 surveillance_analyzer.py --gps-file gps_coordinates.json
```
Output: 
- Markdown reports: `./surveillance_reports/surveillance_report_YYYYMMDD_HHMMSS.md`
- HTML reports: `./surveillance_reports/surveillance_report_YYYYMMDD_HHMMSS.html`
- KML visualizations: `./kml_files/surveillance_analysis_YYYYMMDD_HHMMSS.kml`

5. Systemd Service (Automatic Startup)
```bash
# Copy example service to systemd
sudo cp /opt/cyt/cyt.service.example /etc/systemd/system/cyt.service

# Edit service file to set correct paths/user
sudo nano /etc/systemd/system/cyt.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable cyt.service
sudo systemctl start cyt.service

# Check status
sudo systemctl status cyt.service

# View logs
sudo journalctl -u cyt.service -f
```

Kismet Integration

Starting Kismet (if not already running)
```bash
# Use the provided startup script
./start_kismet_clean.sh

# Or manually (requires monitor mode adapter)
kismet -c wlan1

# Verify running
ps aux | grep kismet
```

Monitor Mode Setup (if needed)
```bash
# List available interfaces
iwconfig

# Enable monitor mode on adapter (e.g., wlan1)
sudo iwconfig wlan1 mode Monitor

# Verify
iwconfig wlan1

# May need to restart Kismet after mode change
sudo killall kismet
./start_kismet_clean.sh
```

Configuration

Key Settings (config.json)
```json
{
  "paths": {
    "kismet_logs": "/home/matt/kismet_logs/*.kismet",
    "log_dir": "logs"
  },
  "timing": {
    "check_interval": 60,
    "time_windows": {
      "recent": 5,
      "medium": 10,
      "old": 15,
      "oldest": 20
    }
  }
}
```

Update kismet_logs path to where your Pi stores Kismet databases (typically `/home/pi/kismet_logs/` or similar).

Ignore Lists
- MAC filter: `./ignore_lists/mac_list.json`
- SSID filter: `./ignore_lists/ssid_list.json`

Format (JSON):
```json
{
  "ignore_macs": ["AA:BB:CC:DD:EE:FF", "..."],
  "ignore_ssids": ["MyHomeWiFi", "..."]
}
```

Credentials & Security

Environment Variables
```bash
# Set master password (required for secure credentials)
export CYT_MASTER_PASSWORD="<your-master-password>"

# Optional: enable test mode (not for production)
export CYT_TEST_MODE=false

# Optional: Kismet database path override
export KISMET_DB_PATH="/path/to/kismet/*.kismet"
```

Persistent Environment Setup (.env file)
```bash
# Copy example
cp .env.example .env

# Edit and set values
nano .env

# Source in scripts
source .env
python3 chasing_your_tail.py
```

Troubleshooting

Module Import Errors
```
ModuleNotFoundError: No module named 'requests' or 'cryptography'
→ pip install -r requirements.txt (with venv activated)
```

Kismet Database Not Found
```
→ Check kismet_logs path in config.json
→ Ensure Kismet has write permissions to that directory
→ Verify Kismet is running: ps aux | grep kismet
```

Monitor Mode Not Available
```
→ Check adapter with: iwconfig
→ Enable: sudo iwconfig wlan1 mode Monitor
→ May need to install drivers for your adapter
```

Credentials Prompt Loop
```
→ Set CYT_MASTER_PASSWORD: export CYT_MASTER_PASSWORD="<password>"
→ Or run migrate_credentials.py in interactive mode
```

GUI Won't Display
```
→ Check DISPLAY variable: echo $DISPLAY
→ If using SSH, enable X11 forwarding: ssh -X pi@<ip>
→ Ensure Xvfb or X server is available
```

Storage & Logging

Log Directories
- Core monitoring logs: `./logs/cyt_log_MMDDYY_HHMMSS`
- Analysis logs: `./analysis_logs/surveillance_analysis.log`
- Security audit: `./cyt_security.log`

Disk Usage Monitoring
```bash
# Check storage
df -h /

# Size of Kismet databases
du -sh /home/pi/kismet_logs/

# Archive old logs (optional)
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
rm -rf logs/*
```

Recommendation: Use an external SSD for Kismet database storage if running 24/7.

Performance Tuning

CPU & Memory Usage
```bash
# Monitor in real-time
watch -n 1 'ps aux | grep python3'

# Check system load
top -u pi

# Reduce CPU: increase check_interval in config.json (default 60s)
```

Database Optimization
```bash
# Periodically vacuum SQLite databases (Kismet)
sqlite3 /path/to/kismet.db VACUUM
```

Backup Strategy
```bash
# Backup CYT config and logs
tar -czf cyt_backup_$(date +%Y%m%d).tar.gz \
  config.json ignore_lists/ logs/ analysis_logs/

# Backup Kismet databases
rsync -av /home/pi/kismet_logs/ /media/usb/kismet_backup/
```

Network Considerations

WiFi Scanning
- Pi's built-in Wi-Fi may conflict with monitor mode
- Recommend: external USB Wi-Fi adapter (Atheros AR9271 or similar)
- Disable Pi's built-in Wi-Fi if monitor mode not available:
  ```bash
  sudo rfkill block wlan0  # disable internal
  # Use wlan1 (external adapter) for Kismet
  ```

Remote Access
```bash
# SSH into Pi
ssh pi@raspberrypi.local

# Copy files via SCP
scp -r reports/ pi@raspberrypi.local:/home/pi/reports_backup/

# Rsync for continuous sync
rsync -avz pi@raspberrypi.local:/opt/cyt/logs /local/backup/
```

Monitoring Pi Health
```bash
# Temperature
vcgencmd measure_temp

# Throttling status
vcgencmd get_throttled

# Uptime
uptime
```

Advanced: Running Multiple Analysis Passes

Parallel Analysis (background)
```bash
# Run surveillance detection in background
nohup python3 surveillance_analyzer.py > analysis.log 2>&1 &

# Run probe analysis concurrently
nohup python3 probe_analyzer.py --days 7 > probe_analysis.log 2>&1 &

# Monitor progress
tail -f analysis.log
tail -f probe_analysis.log
```

Scheduled Analysis via Cron
```bash
# Edit crontab
crontab -e

# Example: run surveillance analysis daily at 2 AM
0 2 * * * cd /opt/cyt && source venv/bin/activate && python3 surveillance_analyzer.py >> /tmp/cyt_cron.log 2>&1

# Example: daily probe analysis
0 3 * * * cd /opt/cyt && source venv/bin/activate && python3 probe_analyzer.py --days 7 >> /tmp/probe_cron.log 2>&1
```

Summary

After setup, the typical workflow is:
1. Kismet captures packets → SQLite database
2. CYT monitors in background or via systemd service
3. Run analysis tools (probe_analyzer, surveillance_analyzer) periodically or on-demand
4. Review reports and KML visualizations in Google Earth

For 24/7 operation, use systemd service; for ad-hoc analysis, run tools manually.

See OPERATION.md for quick reference and RPI_EXPORT.md for hardware requirements.
