#!/usr/bin/env python3
"""
Integrated Surveillance Analysis Tool for CYT
Combines GPS tracking, device detection, and KML export for stalking/surveillance detection
"""
import argparse
import glob
import json
import logging
import os
import time
from datetime import datetime
from typing import List, Optional

from surveillance_detector import SurveillanceDetector, SuspiciousDevice, load_appearances_from_kismet
from gps_tracker import GPSTracker, KMLExporter, simulate_gps_data
from secure_credentials import secure_config_loader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('surveillance_analysis.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class SurveillanceAnalyzer:
    """Main surveillance analysis orchestrator"""
    
    def __init__(self, config_path: str = 'config.json'):
        # Load secure configuration
        os.environ['CYT_TEST_MODE'] = 'true'  # For non-interactive mode
        self.config, self.credential_manager = secure_config_loader(config_path)
        
        # Initialize components
        self.detector = SurveillanceDetector(self.config)
        self.gps_tracker = GPSTracker(self.config)
        self.kml_exporter = KMLExporter()
        
        # Analysis settings
        self.analysis_window_hours = 24  # Analyze last 24 hours by default
        
    def analyze_kismet_data(self, kismet_db_path: Optional[str | list] = None, 
                          gps_data: Optional[list] = None)  -> dict[str, int | str | List[SuspiciousDevice] | None]:
        """Perform complete surveillance analysis on Kismet data"""
        
        print("🔍 Starting Surveillance Analysis...")
        print("=" * 50)
        
        # Find all Kismet databases from past 24 hours
        if not kismet_db_path:
            db_pattern = self.config['paths']['kismet_logs']
            all_db_files = glob.glob(db_pattern)
            if not all_db_files:
                raise FileNotFoundError(f"No Kismet database found at: {db_pattern}")
            
            # Filter to databases modified in the past 24 hours
            import sqlite3
            current_time = time.time()
            hours_24_ago = current_time - (self.analysis_window_hours * 3600)
            
            recent_db_files = [db for db in all_db_files if os.path.getmtime(db) >= hours_24_ago]
            recent_db_files = sorted(recent_db_files, key=os.path.getmtime, reverse=True)
            
            if not recent_db_files:
                print(f"⚠️ No databases found from past {self.analysis_window_hours} hours, using most recent")
                kismet_db_path = max(all_db_files, key=os.path.getmtime)
            else:
                print(f"📊 Found {len(recent_db_files)} databases from past {self.analysis_window_hours} hours:")
                total_gps_coords = 0
                for db_file in recent_db_files:
                    try:
                        conn = sqlite3.connect(db_file)
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM devices WHERE avg_lat != 0 AND avg_lon != 0")
                        gps_count = cursor.fetchone()[0]
                        conn.close()
                        print(f"   📁 {os.path.basename(db_file)}: {gps_count} GPS locations")
                        total_gps_coords += gps_count
                    except:
                        print(f"   ❌ {os.path.basename(db_file)}: Error reading")
                
                print(f"🛰️ Total GPS coordinates across all databases: {total_gps_coords}")
                # We'll process all recent databases, not just one
                kismet_db_path = recent_db_files  # Pass list instead of single file
        
        # Handle multiple database files
        db_files_to_process = kismet_db_path if isinstance(kismet_db_path, list) else [kismet_db_path]
        print(f"📊 Processing {len(db_files_to_process)} Kismet database(s)")
        
        # Load GPS data (real, simulated, or extract from Kismet)
        if gps_data:
            print(f"🛰️ Loading {len(gps_data)} GPS coordinates...")
            for lat, lon, name in gps_data:
                location_id = self.gps_tracker.add_gps_reading(lat, lon, location_name=name)
                print(f"   📍 {name}: {lat:.4f}, {lon:.4f} -> {location_id}")
        else:
            # Extract GPS coordinates from all Kismet databases
            print("🛰️ Extracting GPS coordinates from Kismet databases...")
            try:
                import sqlite3
                all_gps_coords = []
                
                for db_file in db_files_to_process:
                    try:
                        if db_file is None:
                            raise Exception("❌ Invalid database file")
                        
                        conn = sqlite3.connect(db_file)
                        cursor = conn.cursor()
                        
                        # Get GPS locations with timestamps from this database
                        cursor.execute("""
                            SELECT DISTINCT avg_lat, avg_lon, first_time
                            FROM devices 
                            WHERE avg_lat != 0 AND avg_lon != 0 
                            ORDER BY first_time
                        """)
                        
                        db_coords = cursor.fetchall()
                        conn.close()
                        
                        if db_coords:
                            print(f"   📁 {os.path.basename(db_file)}: {len(db_coords)} GPS locations")
                            all_gps_coords.extend(db_coords)
                        
                    except Exception as e:
                        print(f"   ❌ Error reading {os.path.basename(str(db_file))}: {e}")
                        continue
                
                if all_gps_coords:
                    # Sort all coordinates by timestamp and deduplicate nearby points
                    all_gps_coords.sort(key=lambda x: x[2])  # Sort by timestamp
                    
                    gps_data = []
                    prev_lat, prev_lon = None, None
                    location_counter = 1
                    
                    for lat, lon, timestamp in all_gps_coords:
                        # Skip if too close to previous point (within ~50m)
                        if prev_lat and prev_lon:
                            import math
                            distance = math.sqrt((lat - prev_lat)**2 + (lon - prev_lon)**2) * 111000  # rough meters
                            if distance < 50:
                                continue
                        
                        location_name = f"Location_{location_counter}"
                        location_id = self.gps_tracker.add_gps_reading(lat, lon, location_name=location_name)
                        print(f"   📍 {location_name}: {lat:.6f}, {lon:.6f}")
                        gps_data.append((lat, lon, location_name))
                        
                        prev_lat, prev_lon = lat, lon
                        location_counter += 1
                    
                    print(f"🛰️ Total unique GPS locations: {len(gps_data)}")
                else:
                    print("⚠️ No GPS coordinates found in any Kismet database - using single location mode")
                    location_id = "unknown_location"
                    
            except Exception as e:
                print(f"❌ Error extracting GPS from Kismet: {e}")
                print("⚠️ Using single location mode")
                location_id = "unknown_location"
        
        # Load device appearances from Kismet databases
        print("📡 Loading device appearances from Kismet databases...")
        total_count = 0
        
        if gps_data:
            # Load devices from all databases, associating them with GPS locations
            primary_location = "Location_1"  # Use the first/primary location
            for db_file in db_files_to_process:
                if db_file is None:
                    raise Exception("❌ Invalid database file")
                db_count = self._load_appearances_with_gps(db_file, primary_location)
                print(f"   📁 {os.path.basename(db_file)}: {db_count} device appearances")
                total_count += db_count
        else:
            # Load from all databases without GPS correlation
            for db_file in db_files_to_process:
                if db_file is None:
                    raise Exception("❌ Invalid database file")
                db_count = load_appearances_from_kismet(db_file, self.detector, "unknown_location")
                print(f"   📁 {os.path.basename(str(db_file))}: {db_count} device appearances")
                total_count += db_count
        
        print(f"✅ Total device appearances loaded: {total_count:,}")
        
        # Perform surveillance detection
        print("\\n🚨 Analyzing for surveillance patterns...")
        suspicious_devices = self.detector.analyze_surveillance_patterns()
        
        if suspicious_devices:
            print(f"⚠️ Found {len(suspicious_devices)} potentially suspicious devices!")
            print("\\nTop suspicious devices:")
            for i, device in enumerate(suspicious_devices[:5], 1):
                print(f"  {i}. {device.mac} (Score: {device.persistence_score:.2f})")
                print(f"     Appearances: {device.total_appearances}, Locations: {len(device.locations_seen)}")
                for reason in device.reasons[:2]:  # Show top 2 reasons
                    print(f"     • {reason}")
                print()
        else:
            print("✅ No suspicious surveillance patterns detected")
        
        # Generate reports
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate surveillance report
        report_file = f"surveillance_reports/surveillance_report_{timestamp}.md"
        html_file = f"surveillance_reports/surveillance_report_{timestamp}.html"
        print(f"\\n📝 Generating surveillance reports:")
        print(f"   📄 Markdown: {report_file}")
        print(f"   🌐 HTML: {html_file}")
        surveillance_report = self.detector.generate_surveillance_report(report_file)
        
        # Generate KML file if GPS data available
        kml_file = None
        if gps_data:
            kml_file = f"kml_files/surveillance_analysis_{timestamp}.kml"
            print(f"🗺️ Generating KML visualization: {kml_file}")
            self.kml_exporter.generate_kml(self.gps_tracker, suspicious_devices, kml_file)
            print(f"   Open in Google Earth to visualize device tracking patterns")
        
        # Analysis summary
        multi_location_devices = self.gps_tracker.get_devices_across_locations()
        location_sessions = self.gps_tracker.get_location_history()
        
        results = {
            'total_devices': total_count,
            'suspicious_devices': len(suspicious_devices),
            'high_persistence_devices': len([d for d in suspicious_devices if d.persistence_score > 0.8]),
            'multi_location_devices': len(multi_location_devices),
            'location_sessions': len(location_sessions),
            'report_file': report_file,
            'kml_file': kml_file,
            'suspicious_device_list': suspicious_devices
        }
        
        return results
    
    def generate_demo_analysis(self) -> dict:
        """Generate analysis using simulated GPS data for demo purposes"""
        print("🎯 Generating BlackHat Arsenal Demo Analysis...")
        print("Using simulated GPS route with real Kismet data")
        
        # Use simulated GPS route
        gps_route = simulate_gps_data()
        
        # Perform analysis
        results = self.analyze_kismet_data(gps_data=gps_route)
        
        print("\\n🎪 Demo Analysis Complete!")
        print("=" * 50)
        print(f"📊 Analysis Results:")
        print(f"   Total Devices: {results['total_devices']:,}")
        print(f"   Suspicious Devices: {results['suspicious_devices']}")
        print(f"   High Threat: {results['high_threat_devices']}")
        print(f"   Multi-Location Devices: {results['multi_location_devices']}")
        print(f"   Location Sessions: {results['location_sessions']}")
        print(f"\\n📁 Generated Files:")
        print(f"   📝 Report: {results['report_file']}")
        if results['kml_file']:
            print(f"   🗺️ KML: {results['kml_file']}")
        
        return results
    
    def analyze_for_stalking(self, min_persistence_score: float = 0.7) -> list:
        """Specifically analyze for stalking patterns"""
        suspicious_devices = self.detector.analyze_surveillance_patterns()
        
        # Filter for high-threat stalking indicators
        stalking_candidates = []
        for device in suspicious_devices:
            if device.persistence_score >= min_persistence_score:
                # Additional stalking-specific checks
                locations = len(device.locations_seen)
                appearances = device.total_appearances
                
                # Stalking indicators:
                # - Appears at 3+ different locations
                # - High frequency of appearances
                # - Spans multiple days
                time_span = device.last_seen - device.first_seen
                time_span_hours = time_span.total_seconds() / 3600
                
                stalking_score = 0
                stalking_reasons = []
                
                if locations >= 3:
                    stalking_score += 0.4
                    stalking_reasons.append(f"Follows across {locations} locations")
                
                if appearances >= 10:
                    stalking_score += 0.3
                    stalking_reasons.append(f"High frequency ({appearances} appearances)")
                
                if time_span_hours >= 24:
                    stalking_score += 0.3
                    stalking_reasons.append(f"Persistent over {time_span_hours/24:.1f} days")
                
                if stalking_score >= 0.6:
                    device.stalking_score = stalking_score
                    device.stalking_reasons = stalking_reasons
                    stalking_candidates.append(device)
        
        return stalking_candidates
    
    def export_results_json(self, results: dict, output_file: str) -> None:
        """Export analysis results to JSON for further processing"""
        
        # Convert device objects to serializable format
        serializable_results = results.copy()
        if 'suspicious_device_list' in results:
            device_list = []
            for device in results['suspicious_device_list']:
                device_dict = {
                    'mac': device.mac,
                    'persistence_score': device.persistence_score,
                    'total_appearances': device.total_appearances,
                    'locations_seen': device.locations_seen,
                    'reasons': device.reasons,
                    'first_seen': device.first_seen.isoformat(),
                    'last_seen': device.last_seen.isoformat()
                }
                device_list.append(device_dict)
            serializable_results['suspicious_device_list'] = device_list
        
        with open(output_file, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        print(f"📊 Results exported to JSON: {output_file}")
    
    def _load_appearances_with_gps(self, db_path: str, location_id: str) -> int:
        """Load device appearances and register them with GPS tracker"""
        import sqlite3
        import json
        
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Get all devices with timestamps
                cursor.execute("""
                    SELECT devmac, last_time, type, device 
                    FROM devices 
                    WHERE last_time > 0
                    ORDER BY last_time DESC
                """)
                
                rows = cursor.fetchall()
                count = 0
                
                # Set current location in GPS tracker for device correlation
                if hasattr(self.gps_tracker, 'location_sessions') and self.gps_tracker.location_sessions:
                    # Find the location session that matches our location_id
                    for session in self.gps_tracker.location_sessions:
                        if session.session_id == location_id:
                            self.gps_tracker.current_location = session
                            break
                
                for row in rows:
                    mac, timestamp, device_type, device_json = row
                    
                    # Extract SSIDs from device JSON
                    ssids_probed = []
                    try:
                        device_data = json.loads(device_json)
                        dot11_device = device_data.get('dot11.device', {})
                        if dot11_device:
                            probe_record = dot11_device.get('dot11.device.last_probed_ssid_record', {})
                            ssid = probe_record.get('dot11.probedssid.ssid')
                            if ssid:
                                ssids_probed = [ssid]
                    except (json.JSONDecodeError, KeyError):
                        pass
                    
                    # Add to surveillance detector
                    self.detector.add_device_appearance(
                        mac=mac,
                        timestamp=timestamp,
                        location_id=location_id,
                        ssids_probed=ssids_probed,
                        device_type=device_type
                    )
                    
                    # Also add to GPS tracker if current location is set
                    if self.gps_tracker.current_location:
                        self.gps_tracker.add_device_at_current_location(mac)
                    
                    count += 1
                
                logger.info(f"Loaded {count} device appearances from {db_path}")
                return count
                
        except Exception as e:
            logger.error(f"Error loading from Kismet database: {e}")
            return 0

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description='CYT Surveillance Analysis Tool')
    parser.add_argument('--demo', action='store_true', 
                       help='Run demo analysis with simulated GPS data')
    parser.add_argument('--kismet-db', type=str,
                       help='Path to specific Kismet database file')
    parser.add_argument('--gps-file', type=str,
                       help='JSON file with GPS coordinates')
    parser.add_argument('--stalking-only', action='store_true',
                       help='Focus analysis on stalking detection')
    parser.add_argument('--output-json', type=str,
                       help='Export results to JSON file')
    parser.add_argument('--min-threat', type=float, default=0.5,
                       help='Minimum threat score for reporting (default: 0.5)')
    
    args = parser.parse_args()
    
    try:
        analyzer = SurveillanceAnalyzer()
        
        if args.demo:
            results = analyzer.generate_demo_analysis()
        else:
            # Load GPS data if provided
            gps_data = None
            if args.gps_file:
                with open(args.gps_file, 'r') as f:
                    gps_data = json.load(f)
            
            results = analyzer.analyze_kismet_data(
                kismet_db_path=args.kismet_db,
                gps_data=gps_data
            )
        
        # Stalking-specific analysis
        if args.stalking_only:
            stalking_devices = analyzer.analyze_for_stalking(args.min_threat)
            if stalking_devices:
                print(f"\\n🚨 STALKING ALERT: {len(stalking_devices)} devices with stalking patterns!")
                for device in stalking_devices:
                    print(f"   ⚠️ {device.mac} (Stalking Score: {device.stalking_score:.2f})")
                    for reason in device.stalking_reasons:
                        print(f"      • {reason}")
            else:
                print("\\n✅ No stalking patterns detected")
        
        # Export JSON if requested
        if args.output_json:
            analyzer.export_results_json(results, args.output_json)
        
        print("\\n🔒 Analysis complete! Stay safe out there.")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())