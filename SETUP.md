# CYT Setup Guide

## Quick Start for BlackHat Demo

### 1. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 2. Security Configuration (REQUIRED FIRST TIME)
Edit `config.json` to set your Wigle API token:
```json
{
  "api_keys": {
    "wigle": {
      "encoded_token": "BASE_64_ENCODED_TOKEN_HERE"
    }
  }
}
```

### 3. Security Setup (REQUIRED)
```bash
# Migrate credentials to secure storage
python3 migrate_credentials.py

# Verify security hardening
python3 chasing_your_tail.py
# Should show: "🔒 SECURE MODE: All SQL injection vulnerabilities have been eliminated!"
```

### 4. Configuration
Edit `config.json` with your Kismet database path:
```json
{
  "kismet_db_path": "/path/to/your/kismet/*.kismet"
}
```

### 5. Run Analysis
```bash
# Start GUI interface
python3 cyt_gui.py

# Or run surveillance analysis directly
python3 surveillance_analyzer.py

# For demo with simulated GPS data
python3 surveillance_analyzer.py --demo
```

### 6. View Results
- **Reports**: Check `surveillance_reports/` for markdown and HTML files
- **Visualizations**: Open `.kml` files from `kml_files/` in Google Earth

## BlackHat Arsenal Demo Features

- ✅ **Spectacular KML Visualization** - Professional Google Earth integration
- ✅ **Multi-format Reports** - Markdown, HTML, and KML outputs  
- ✅ **Security Hardened** - SQL injection prevention, encrypted credentials
- ✅ **GPS Integration** - Automatic coordinate extraction from Kismet
- ✅ **Multi-location Tracking** - Detects devices following across locations
- ✅ **Professional GUI** - Enhanced Tkinter interface with analysis buttons

## Documentation
- **README.md** - Complete user documentation
- **CLAUDE.md** - Technical developer documentation

## Support
GitHub: https://github.com/matt0177/cyt