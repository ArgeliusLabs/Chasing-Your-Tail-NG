#!/usr/bin/env python3

import pathlib
import glob
import re
from datetime import datetime
import requests
import argparse

# Load config with secure credentials
from secure_credentials import secure_config_loader
config, credential_manager = secure_config_loader('config.json')

class ProbeAnalyzer:
    def __init__(self, log_dir=None, local_only=True, days_back=14):
        self.log_dir = log_dir or pathlib.Path(config['paths']['log_dir'])
        self.days_back = days_back
        # Get WiGLE API key from secure storage
        self.wigle_api_key = credential_manager.get_wigle_token()
        if not self.wigle_api_key and not local_only:
            print("⚠️  No WiGLE API token found in secure storage. Use --local for offline analysis.")
        self.probes = {}  # Dictionary to store probe requests {ssid: [timestamps]}
        self.local_only = local_only  # New flag for local search only
        
    def parse_log_file(self, log_file):
        """Parse a single CYT log file for probe requests"""
        probe_pattern = re.compile(r'Found a probe!: (.*?)\n')
        # Update timestamp pattern to match log format
        timestamp_pattern = re.compile(r'Current Time: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
        
        with open(log_file, 'r') as f:
            content = f.read()
            
        # Debug: Print all probes found in this file
        probes_found = probe_pattern.findall(content)
        print(f"\nFound {len(probes_found)} probes in {log_file}:")
        for probe in probes_found:
            print(f"- {probe}")
        
        for probe in probe_pattern.finditer(content):
            ssid = probe.group(1).strip()
            # Find nearest timestamp before this probe
            content_before = content[:probe.start()]
            timestamp_match = timestamp_pattern.findall(content_before)
            if timestamp_match:
                timestamp = timestamp_match[-1]  # Get last timestamp before probe
                if ssid not in self.probes:
                    self.probes[ssid] = []
                self.probes[ssid].append(timestamp)
            else:
                # If no timestamp found, use file creation time from filename
                # Format: cyt_log_MMDDYY_HHMMSS
                filename = str(log_file)
                date_str = filename.split('_')[2:4]  # ['MMDDYY', 'HHMMSS']
                if len(date_str) == 2:
                    timestamp = f"{date_str[0][:2]}-{date_str[0][2:4]}-{date_str[0][4:]} {date_str[1][:2]}:{date_str[1][2:4]}:{date_str[1][4:]}"
                    if ssid not in self.probes:
                        self.probes[ssid] = []
                    self.probes[ssid].append(timestamp)
    
    def parse_all_logs(self):
        """Parse log files in the log directory (filtered by days_back)"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=self.days_back)
        all_log_files = list(self.log_dir.glob('cyt_log_*'))
        filtered_files = []
        
        print(f"\nFiltering logs to past {self.days_back} days (since {cutoff_date.strftime('%Y-%m-%d')})")
        
        for log_file in all_log_files:
            try:
                # Extract date from filename: cyt_log_MMDDYY_HHMMSS
                filename_parts = log_file.name.split('_')
                if len(filename_parts) >= 3:
                    date_str = filename_parts[2]  # MMDDYY
                    if len(date_str) == 6:
                        # Convert MMDDYY to proper date
                        month = int(date_str[:2])
                        day = int(date_str[2:4])
                        year = 2000 + int(date_str[4:6])  # Convert YY to 20YY
                        
                        file_date = datetime(year, month, day)
                        if file_date >= cutoff_date:
                            filtered_files.append(log_file)
                        else:
                            print(f"- Skipping old file: {log_file.name} ({file_date.strftime('%Y-%m-%d')})")
            except (ValueError, IndexError):
                # If we can't parse the date, include the file to be safe
                print(f"- Including file with unparseable date: {log_file.name}")
                filtered_files.append(log_file)
        
        print(f"\nScanning {len(filtered_files)} recent log files (skipped {len(all_log_files) - len(filtered_files)} old files):")
        
        log_count = 0
        for log_file in filtered_files:
            print(f"- Reading {log_file.name}")
            self.parse_log_file(log_file)
            log_count += 1
        
        print(f"\nProcessed {log_count} log files from past {self.days_back} days")
            
    def query_wigle(self, ssid):
        """Query WiGLE for information about an SSID"""
        if not self.wigle_api_key:
            return {"error": "WiGLE API key not configured"}
            
        print(f"\nQuerying WiGLE for SSID: {ssid}")
        headers = {
            'Authorization': f'Basic {self.wigle_api_key}'
        }
        
        # Only include bounding box if local_only is True and coordinates are set
        params = {'ssid': ssid}
        if self.local_only:
            search_config = config.get('search', {})
            if all(search_config.get(k) is not None for k in ['lat_min', 'lat_max', 'lon_min', 'lon_max']):
                params.update({
                    'latrange1': search_config['lat_min'],
                    'latrange2': search_config['lat_max'],
                    'longrange1': search_config['lon_min'],
                    'longrange2': search_config['lon_max'],
                })
                print("Using local search area")
        
        try:
            response = requests.get(
                'https://api.wigle.net/api/v2/network/search',
                headers=headers,
                params=params
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
            
    def analyze_probes(self):
        """Analyze collected probe requests"""
        results = []
        total_ssids = len(self.probes)
        print(f"\nQuerying WiGLE for {total_ssids} unique SSIDs...")
        for i, (ssid, timestamps) in enumerate(self.probes.items(), 1):
            print(f"\nProgress: {i}/{total_ssids}")
            result = {
                "ssid": ssid,
                "count": len(timestamps),
                "first_seen": min(timestamps),
                "last_seen": max(timestamps),
                "wigle_data": self.query_wigle(ssid) if (self.wigle_api_key and not self.local_only) else None
            }
            results.append(result)
        return results

def main():
    """
    Probe Request Analyzer for Chasing Your Tail
    
    This tool analyzes probe requests from CYT log files and can query WiGLE for SSID locations.
    
    Before running:
    1. Make sure you have CYT log files in your logs directory
    2. To use WiGLE lookups:
       - Get a WiGLE API key from wigle.net
       - Add it to config.json under api_keys->wigle
       - Set your search area in config.json under search
    """
    
    if len(glob.glob(str(pathlib.Path(config['paths']['log_dir']) / 'cyt_log_*'))) == 0:
        print("\nError: No log files found!")
        print(f"Please check the logs directory: {config['paths']['log_dir']}")
        print("Run Chasing Your Tail first to generate some logs.")
        return

    # Check WiGLE configuration
    if not config.get('api_keys', {}).get('wigle'):
        print("\nNote: WiGLE API key not configured.")
        print("To enable WiGLE lookups:")
        print("1. Get an API key from wigle.net")
        print("2. Add it to config.json under api_keys->wigle")
    
    parser = argparse.ArgumentParser(description='Analyze probe requests and query WiGLE')
    parser.add_argument('--wigle', action='store_true', 
                      help='Enable WiGLE API queries (disabled by default to protect API keys)')
    parser.add_argument('--local', action='store_true', 
                      help='[DEPRECATED] Use --wigle to enable API calls')
    parser.add_argument('--days', type=int, default=14,
                      help='Number of days back to analyze (default: 14, use 0 for all logs)')
    parser.add_argument('--all-logs', action='store_true',
                      help='Analyze all log files (equivalent to --days 0)')
    args = parser.parse_args()

    # Handle days filtering
    days_back = 0 if args.all_logs else args.days

    print(f"\nAnalyzing probe requests from CYT logs...")
    if days_back > 0:
        print(f"📅 Filtering to logs from past {days_back} days")
    else:
        print("📁 Analyzing ALL log files")
        
    # Default to local_only=True unless --wigle is specified
    use_wigle = args.wigle or args.local  # Keep --local for backwards compatibility
    analyzer = ProbeAnalyzer(local_only=not use_wigle, days_back=days_back)
    
    if use_wigle:
        print("🌐 WiGLE API queries ENABLED - this will consume API credits!")
    else:
        print("🔒 Local analysis only (use --wigle to enable API queries)")
    analyzer.parse_all_logs()
    results = analyzer.analyze_probes()
    
    if not results:
        print("\nNo probe requests found in logs!")
        print("Make sure Chasing Your Tail is running and detecting probes.")
        return
    
    # Print analysis results
    print(f"\nFound {len(results)} unique SSIDs in probe requests:")
    print("-" * 50)
    
    # Sort results by count (most frequent first)
    results.sort(key=lambda x: x['count'], reverse=True)
    
    for result in results:
        print(f"\nSSID: {result['ssid']}")
        print(f"Times seen: {result['count']}")
        print(f"First seen: {result['first_seen']}")
        print(f"Last seen: {result['last_seen']}")
        
        # Calculate time span
        first = datetime.strptime(result['first_seen'], '%m-%d-%y %H:%M:%S')
        last = datetime.strptime(result['last_seen'], '%m-%d-%y %H:%M:%S')
        duration = last - first
        if duration.total_seconds() > 0:
            print(f"Time span: {duration}")
            print(f"Average frequency: {result['count'] / duration.total_seconds():.2f} probes/second")
        
        if result.get('wigle_data'):
            if 'error' in result['wigle_data']:
                if result['wigle_data']['error'] != "WiGLE API key not configured":
                    print(f"WiGLE Error: {result['wigle_data']['error']}")
            else:
                print("\nWiGLE Data:")
                locations = result['wigle_data'].get('results', [])
                print(f"Known locations: {len(locations)}")
                if locations:
                    print("Recent sightings:")
                    for loc in locations[:3]:  # Show top 3 most recent
                        print(f"- Lat: {loc.get('trilat')}, Lon: {loc.get('trilong')}")
                        print(f"  Last seen: {loc.get('lastupdt')}")

if __name__ == "__main__":
    main() 