"""
GPS Integration for CYT
Correlates device appearances with GPS locations for surveillance detection
"""
import time
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math

logger = logging.getLogger(__name__)

@dataclass
class GPSLocation:
    """GPS coordinate with metadata"""
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    timestamp: Optional[float] = None
    accuracy: Optional[float] = None
    location_name: Optional[str] = None

@dataclass 
class LocationSession:
    """A session at a specific location"""
    location: GPSLocation
    start_time: float
    end_time: float
    devices_seen: List[str]  # MAC addresses
    session_id: str

class GPSTracker:
    """Track GPS locations and correlate with device appearances"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.locations = []
        self.location_sessions = []
        self.current_location = None
        
        # Location clustering settings
        self.location_threshold = 100  # meters - same location if within this distance
        self.session_timeout = 600     # seconds - new session if gap longer than this
        
    def add_gps_reading(self, latitude: float, longitude: float, 
                       altitude: Optional[float] = None, accuracy: Optional[float] = None,
                       location_name: Optional[str] = None) -> str:
        """Add a GPS reading and return location ID"""
        timestamp = time.time()
        
        location = GPSLocation(
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            timestamp=timestamp,
            accuracy=accuracy,
            location_name=location_name
        )
        
        self.locations.append(location)
        
        # Generate location ID (for clustering nearby locations)
        location_id = self._get_location_cluster_id(location)
        
        # Update current location and session
        self._update_current_session(location, location_id)
        
        logger.info(f"GPS reading added: {latitude:.6f}, {longitude:.6f} -> {location_id}")
        return location_id
    
    def _get_location_cluster_id(self, location: GPSLocation) -> str:
        """Get cluster ID for location (groups nearby locations)"""
        # Check if this location is close to any existing session
        for session in self.location_sessions:
            distance = self._calculate_distance(location, session.location)
            if distance <= self.location_threshold:
                return session.session_id
        
        # Create new location cluster
        if location.location_name:
            base_name = location.location_name.replace(' ', '_')
        else:
            # Generate name from coordinates
            base_name = f"loc_{location.latitude:.4f}_{location.longitude:.4f}"
        
        # Make unique
        existing_ids = [s.session_id for s in self.location_sessions]
        counter = 1
        location_id = base_name
        while location_id in existing_ids:
            location_id = f"{base_name}_{counter}"
            counter += 1
            
        return location_id
    
    def _update_current_session(self, location: GPSLocation, location_id: str) -> None:
        """Update current location session"""
        now = time.time()
        
        # Find existing session or create new one
        current_session = None
        for session in self.location_sessions:
            if session.session_id == location_id:
                # Check if this continues the existing session
                if now - session.end_time <= self.session_timeout:
                    session.end_time = now
                    current_session = session
                    break
        
        if not current_session:
            # Create new session
            current_session = LocationSession(
                location=location,
                start_time=now,
                end_time=now,
                devices_seen=[],
                session_id=location_id
            )
            self.location_sessions.append(current_session)
        
        self.current_location = current_session
        logger.debug(f"Updated session: {location_id}")
    
    def _calculate_distance(self, loc1: GPSLocation, loc2: GPSLocation) -> float:
        """Calculate distance between two GPS locations in meters"""
        # Haversine formula
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(loc1.latitude)
        lat2_rad = math.radians(loc2.latitude)
        delta_lat = math.radians(loc2.latitude - loc1.latitude)
        delta_lon = math.radians(loc2.longitude - loc1.longitude)
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon/2) * math.sin(delta_lon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    def add_device_at_current_location(self, mac: str) -> Optional[str]:
        """Record that a device was seen at current location"""
        if not self.current_location:
            logger.warning("No current location - cannot record device")
            return None
        
        if mac not in self.current_location.devices_seen:
            self.current_location.devices_seen.append(mac)
            logger.debug(f"Device {mac} seen at {self.current_location.session_id}")
        
        return self.current_location.session_id
    
    def get_current_location_id(self) -> Optional[str]:
        """Get current location ID"""
        if self.current_location:
            return self.current_location.session_id
        return None
    
    def get_location_history(self) -> List[LocationSession]:
        """Get chronological location history"""
        return sorted(self.location_sessions, key=lambda s: s.start_time)
    
    def get_devices_across_locations(self) -> Dict[str, List[str]]:
        """Get devices that appeared across multiple locations"""
        device_locations = {}
        
        for session in self.location_sessions:
            for mac in session.devices_seen:
                if mac not in device_locations:
                    device_locations[mac] = []
                if session.session_id not in device_locations[mac]:
                    device_locations[mac].append(session.session_id)
        
        # Filter to devices seen at multiple locations
        multi_location_devices = {
            mac: locations for mac, locations in device_locations.items()
            if len(locations) > 1
        }
        
        return multi_location_devices

class KMLExporter:
    """Export GPS and device data to KML format for Google Earth"""
    
    def __init__(self):
        self.kml_template = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
<Document>
    <name>🛡️ CYT Advanced Surveillance Detection Analysis</name>
    <description><![CDATA[
        <h2>🔍 Chasing Your Tail - Surveillance Detection Report</h2>
        <p><b>📊 Generated:</b> {timestamp}</p>
        <p><b>🎯 Analysis:</b> Advanced wireless device tracking and persistence analysis</p>
        <p><b>🛰️ GPS Data:</b> Real-time location correlation with device appearances</p>
        <hr>
        <p><i>This visualization shows device tracking patterns and location-based surveillance analysis.</i></p>
    ]]></description>
    
    <!-- High Persistence Device Styles -->
    <Style id="criticalPersistenceStyle">
        <IconStyle>
            <color>ff0000ff</color>
            <Icon>
                <href>http://maps.google.com/mapfiles/kml/shapes/target.png</href>
            </Icon>
            <scale>2.0</scale>
            <hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/>
        </IconStyle>
        <LabelStyle>
            <color>ff0000ff</color>
            <scale>1.2</scale>
        </LabelStyle>
        <BalloonStyle>
            <bgColor>ffccccff</bgColor>
            <textColor>ff000000</textColor>
        </BalloonStyle>
    </Style>
    
    <Style id="highPersistenceStyle">
        <IconStyle>
            <color>ff0080ff</color>
            <Icon>
                <href>http://maps.google.com/mapfiles/kml/shapes/warning.png</href>
            </Icon>
            <scale>1.7</scale>
            <hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/>
        </IconStyle>
        <LabelStyle>
            <color>ff0080ff</color>
            <scale>1.1</scale>
        </LabelStyle>
        <BalloonStyle>
            <bgColor>ffeeccff</bgColor>
            <textColor>ff000000</textColor>
        </BalloonStyle>
    </Style>
    
    <Style id="mediumPersistenceStyle">
        <IconStyle>
            <color>ff00ffff</color>
            <Icon>
                <href>http://maps.google.com/mapfiles/kml/shapes/info-i.png</href>
            </Icon>
            <scale>1.4</scale>
            <hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/>
        </IconStyle>
        <LabelStyle>
            <color>ff00ffff</color>
            <scale>1.0</scale>
        </LabelStyle>
        <BalloonStyle>
            <bgColor>ffffffcc</bgColor>
            <textColor>ff000000</textColor>
        </BalloonStyle>
    </Style>
    
    <!-- Location Monitoring Styles -->
    <Style id="primaryLocationStyle">
        <IconStyle>
            <color>ff00ff00</color>
            <Icon>
                <href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href>
            </Icon>
            <scale>1.8</scale>
            <hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/>
        </IconStyle>
        <LabelStyle>
            <color>ff00ff00</color>
            <scale>1.3</scale>
        </LabelStyle>
        <BalloonStyle>
            <bgColor>ffccffcc</bgColor>
            <textColor>ff000000</textColor>
        </BalloonStyle>
    </Style>
    
    <Style id="secondaryLocationStyle">
        <IconStyle>
            <color>ff0099ff</color>
            <Icon>
                <href>http://maps.google.com/mapfiles/kml/shapes/placemark_square.png</href>
            </Icon>
            <scale>1.5</scale>
            <hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/>
        </IconStyle>
        <LabelStyle>
            <color>ff0099ff</color>
            <scale>1.1</scale>
        </LabelStyle>
    </Style>
    
    <!-- Device Tracking Path Styles -->
    <Style id="criticalTrackingPath">
        <LineStyle>
            <color>ff0000ff</color>
            <width>6</width>
            <gx:outerColor>80ffffff</gx:outerColor>
            <gx:outerWidth>8</gx:outerWidth>
            <gx:physicalWidth>5</gx:physicalWidth>
        </LineStyle>
    </Style>
    
    <Style id="highTrackingPath">
        <LineStyle>
            <color>ff0080ff</color>
            <width>4</width>
            <gx:outerColor>80ffffff</gx:outerColor>
            <gx:outerWidth>6</gx:outerWidth>
            <gx:physicalWidth>3</gx:physicalWidth>
        </LineStyle>
    </Style>
    
    <Style id="mediumTrackingPath">
        <LineStyle>
            <color>ff00ffff</color>
            <width>3</width>
            <gx:outerColor>80ffffff</gx:outerColor>
            <gx:outerWidth>4</gx:outerWidth>
            <gx:physicalWidth>2</gx:physicalWidth>
        </LineStyle>
    </Style>
    
    <!-- Heat Map Circle Styles -->
    <Style id="highActivityZone">
        <PolyStyle>
            <color>4d0000ff</color>
            <outline>1</outline>
        </PolyStyle>
        <LineStyle>
            <color>ff0000ff</color>
            <width>2</width>
        </LineStyle>
    </Style>
    
    <Style id="mediumActivityZone">
        <PolyStyle>
            <color>4d0080ff</color>
            <outline>1</outline>
        </PolyStyle>
        <LineStyle>
            <color>ff0080ff</color>
            <width>2</width>
        </LineStyle>
    </Style>
    
    {content}
</Document>
</kml>'''
    
    def generate_kml(self, gps_tracker: GPSTracker, surveillance_devices: Optional[List] = None,
                    output_file: str = "cyt_analysis.kml") -> str:
        """Generate spectacular KML file with advanced surveillance visualization"""
        
        if not gps_tracker.location_sessions:
            logger.warning("No GPS data available for KML generation")
            return self._generate_empty_kml(output_file)
        
        content_parts = []
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Enhanced location sessions with threat level visualization  
        content_parts.append("<Folder>")
        content_parts.append("<name>📍 Monitoring Locations</name>")
        content_parts.append("<description>Geographic locations where surveillance detection occurred</description>")
        
        for session in gps_tracker.get_location_history():
            start_time = datetime.fromtimestamp(session.start_time)
            end_time = datetime.fromtimestamp(session.end_time)
            duration = (session.end_time - session.start_time) / 60  # minutes
            
            # Calculate threat level for this location
            location_persistence_score = 0.0
            suspicious_devices_here = []
            if surveillance_devices:
                for device in surveillance_devices:
                    if session.session_id in device.locations_seen:
                        location_persistence_score = max(location_persistence_score, device.persistence_score)
                        suspicious_devices_here.append(device)
            
            # Choose appropriate style based on persistence level (safer language)
            if location_persistence_score > 0.8:
                style_url = "#criticalLocationStyle"
                threat_indicator = "🚨 VERY HIGH PERSISTENCE ZONE"
                location_color = "Red"
            elif location_persistence_score > 0.6:
                style_url = "#highThreatLocationStyle" 
                threat_indicator = "⚠️ HIGH PERSISTENCE AREA"
                location_color = "Orange"
            elif location_persistence_score > 0.3:
                style_url = "#mediumThreatLocationStyle"
                threat_indicator = "🟡 MODERATE PERSISTENCE ZONE"
                location_color = "Yellow"
            else:
                style_url = "#locationStyle"
                threat_indicator = "🟢 LOW ACTIVITY LOCATION"
                location_color = "Green"
            
            placemark = f'''
    <Placemark>
        <name>[{location_color}] {session.session_id}</name>
        <description>
            <![CDATA[
            <h3>{threat_indicator}</h3>
            <table border="1" cellpadding="5">
            <tr><td><b>Location ID</b></td><td>{session.session_id}</td></tr>
            <tr><td><b>Persistence Score</b></td><td>{location_persistence_score:.3f}/1.000</td></tr>
            <tr><td><b>Monitoring Start</b></td><td>{start_time.strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
            <tr><td><b>Monitoring End</b></td><td>{end_time.strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
            <tr><td><b>Duration</b></td><td>{duration:.1f} minutes</td></tr>
            <tr><td><b>Total Devices</b></td><td>{len(session.devices_seen)}</td></tr>
            <tr><td><b>Suspicious Devices</b></td><td>{len(suspicious_devices_here)}</td></tr>
            <tr><td><b>Coordinates</b></td><td>{session.location.latitude:.6f}, {session.location.longitude:.6f}</td></tr>
            </table>
            <br/>
            <h4>📱 Device Intelligence Summary:</h4>
            {self._format_enhanced_device_list(session.devices_seen, suspicious_devices_here)}
            
            {self._format_location_persistence_analysis(suspicious_devices_here) if suspicious_devices_here else '<p><b>✅ No persistent devices detected at this location</b></p>'}
            ]]>
        </description>
        <styleUrl>{style_url}</styleUrl>
        <TimeSpan>
            <begin>{start_time.isoformat()}Z</begin>
            <end>{end_time.isoformat()}Z</end>
        </TimeSpan>
        <Point>
            <coordinates>{session.location.longitude},{session.location.latitude},0</coordinates>
        </Point>
    </Placemark>'''
            content_parts.append(placemark)
        
        content_parts.append("</Folder>")
        
        # Advanced suspicious device tracking with threat classification
        if surveillance_devices:
            # Group devices by threat level
            critical_devices = [d for d in surveillance_devices if d.persistence_score > 0.9]
            high_devices = [d for d in surveillance_devices if 0.8 <= d.persistence_score <= 0.9]
            medium_devices = [d for d in surveillance_devices if 0.6 <= d.persistence_score < 0.8]
            low_devices = [d for d in surveillance_devices if d.persistence_score < 0.6]
            
            # Very high persistence devices folder
            if critical_devices:
                content_parts.append("<Folder>")
                content_parts.append("<name>🚨 VERY HIGH PERSISTENCE DEVICES</name>")
                content_parts.append("<description>Devices with highest activity patterns</description>")
                self._add_device_tracking_folder(content_parts, critical_devices, gps_tracker, "CRITICAL")
                content_parts.append("</Folder>")
            
            # High persistence devices folder  
            if high_devices:
                content_parts.append("<Folder>")
                content_parts.append("<name>⚠️ HIGH PERSISTENCE DEVICES</name>")
                content_parts.append("<description>Devices with notable activity patterns</description>")
                self._add_device_tracking_folder(content_parts, high_devices, gps_tracker, "HIGH")
                content_parts.append("</Folder>")
            
            # Medium persistence devices folder
            if medium_devices:
                content_parts.append("<Folder>")
                content_parts.append("<name>🟡 MODERATE PERSISTENCE DEVICES</name>")
                content_parts.append("<description>Devices with some activity patterns</description>")
                self._add_device_tracking_folder(content_parts, medium_devices, gps_tracker, "MEDIUM")
                content_parts.append("</Folder>")
            
            # Surveillance pattern analysis overlay
            content_parts.append("<Folder>")
            content_parts.append("<name>🔍 BEHAVIORAL ANALYSIS</name>")
            content_parts.append("<description>Advanced surveillance pattern visualization</description>")
            
            # Add heat map style analysis
            self._add_surveillance_heatmap(content_parts, surveillance_devices, gps_tracker)
            
            # Add temporal analysis tracks
            self._add_temporal_analysis_tracks(content_parts, surveillance_devices, gps_tracker)
            
            content_parts.append("</Folder>")
        
        # Generate enhanced final KML with updated styles and timestamp
        full_content = "\n".join(content_parts)
        enhanced_kml_template = self._get_enhanced_kml_template()
        kml_output = enhanced_kml_template.format(
            content=full_content,
            timestamp=timestamp,
            total_locations=len(gps_tracker.location_sessions),
            total_devices=len(surveillance_devices) if surveillance_devices else 0
        )
        
        # Save to file
        with open(output_file, 'w') as f:
            f.write(kml_output)
        
        logger.info(f"🎯 SPECTACULAR KML visualization generated: {output_file}")
        logger.info(f"📊 Includes {len(gps_tracker.location_sessions)} locations, {len(surveillance_devices) if surveillance_devices else 0} surveillance devices")
        return kml_output
    
    def _format_device_list(self, devices: List[str]) -> str:
        """Format device list for KML description"""
        if not devices:
            return "None"
        
        # Limit to first 10 devices to avoid clutter
        displayed_devices = devices[:10]
        formatted = "<br/>".join(f"• {mac}" for mac in displayed_devices)
        
        if len(devices) > 10:
            formatted += f"<br/>... and {len(devices) - 10} more"
            
        return formatted
    
    def _format_threat_reasons(self, reasons: List[str]) -> str:
        """Format threat reasons for KML description"""
        if not reasons:
            return "No specific threats identified"
        
        return "<br/>".join(f"• {reason}" for reason in reasons)
    
    def _format_enhanced_device_list(self, all_devices: List[str], suspicious_devices: List) -> str:
        """Format enhanced device list with threat intelligence"""
        if not all_devices:
            return "<p>No devices detected</p>"
        
        html = "<ul>"
        suspicious_macs = {device.mac for device in suspicious_devices}
        
        # Show suspicious devices first
        for device in suspicious_devices:
            persistence_emoji = "🚨" if device.persistence_score > 0.8 else "⚠️" if device.persistence_score > 0.6 else "🟡"
            html += f"<li><b>{persistence_emoji} {device.mac}</b> - Persistence Score: {device.persistence_score:.2f}</li>"
        
        # Show remaining devices
        normal_devices = [mac for mac in all_devices if mac not in suspicious_macs]
        for mac in normal_devices[:10]:  # Limit to avoid clutter
            html += f"<li>✅ {mac} - Normal</li>"
        
        if len(normal_devices) > 10:
            html += f"<li><i>... and {len(normal_devices) - 10} more normal devices</i></li>"
            
        html += "</ul>"
        return html
    
    def _format_location_persistence_analysis(self, suspicious_devices: List) -> str:
        """Format location-specific persistence analysis"""
        if not suspicious_devices:
            return ""
        
        html = "<h4>📊 Persistence Analysis for This Location:</h4>"
        html += "<ul>"
        
        for device in suspicious_devices:
            html += f"<li><b>{device.mac}</b> (Score: {device.persistence_score:.2f})<ul>"
            for reason in device.reasons[:3]:  # Top 3 reasons
                html += f"<li>{reason}</li>"
            html += "</ul></li>"
        
        html += "</ul>"
        return html
    
    def _add_device_tracking_folder(self, content_parts: List[str], devices: List, 
                                  gps_tracker: GPSTracker, threat_level: str) -> None:
        """Add device tracking visualization for a specific threat level"""
        
        multi_location_devices = gps_tracker.get_devices_across_locations()
        
        # Style mapping for threat levels
        path_styles = {
            "CRITICAL": "#criticalDevicePathStyle",
            "HIGH": "#highDevicePathStyle", 
            "MEDIUM": "#mediumDevicePathStyle",
            "LOW": "#lowDevicePathStyle"
        }
        
        marker_styles = {
            "CRITICAL": "#criticalDeviceStyle",
            "HIGH": "#highDeviceStyle",
            "MEDIUM": "#mediumDeviceStyle", 
            "LOW": "#lowDeviceStyle"
        }
        
        for device in devices:
            if device.mac in multi_location_devices:
                locations = multi_location_devices[device.mac]
                
                # Create enhanced tracking path with temporal data
                path_coordinates = []
                location_times = []
                
                for session in sorted(gps_tracker.location_sessions, key=lambda s: s.start_time):
                    if session.session_id in locations:
                        path_coordinates.append(f"{session.location.longitude},{session.location.latitude},0")
                        location_times.append(datetime.fromtimestamp(session.start_time))
                
                if len(path_coordinates) > 1:
                    # Device tracking path
                    duration = device.last_seen - device.first_seen
                    device_path = f'''
    <Placemark>
        <name>[{threat_level}] Tracking Path: {device.mac}</name>
        <description>
            <![CDATA[
            <h3>🎯 DEVICE TRACKING INTELLIGENCE</h3>
            <table border="1" cellpadding="5">
            <tr><td><b>MAC Address</b></td><td>{device.mac}</td></tr>
            <tr><td><b>Persistence Classification</b></td><td>{threat_level} PERSISTENCE</td></tr>
            <tr><td><b>Persistence Score</b></td><td>{device.persistence_score:.3f}/1.000</td></tr>
            <tr><td><b>Surveillance Duration</b></td><td>{duration.total_seconds()/3600:.1f} hours</td></tr>
            <tr><td><b>Locations Tracked</b></td><td>{len(locations)}</td></tr>
            <tr><td><b>Total Appearances</b></td><td>{device.total_appearances}</td></tr>
            <tr><td><b>First Seen</b></td><td>{device.first_seen.strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
            <tr><td><b>Last Seen</b></td><td>{device.last_seen.strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
            </table>
            <br/>
            <h4>📊 Persistence Indicators:</h4>
            <ul>
            {chr(10).join(f'<li>{reason}</li>' for reason in device.reasons)}
            </ul>
            <h4>📍 Location Tracking Path:</h4>
            <ol>
            {chr(10).join(f'<li>{time.strftime("%H:%M")} - {loc}</li>' for time, loc in zip(location_times, locations))}
            </ol>
            ]]>
        </description>
        <styleUrl>{path_styles.get(threat_level, "#devicePathStyle")}</styleUrl>
        <LineString>
            <coordinates>
                {" ".join(path_coordinates)}
            </coordinates>
        </LineString>
    </Placemark>'''
                    content_parts.append(device_path)
                
                # Enhanced markers for each location
                for session in gps_tracker.location_sessions:
                    if session.session_id in locations and device.mac in session.devices_seen:
                        # Find device appearances at this location
                        appearances_here = [a for a in device.appearances if a.location_id == session.session_id]
                        
                        device_marker = f'''
    <Placemark>
        <name>[{threat_level}] {device.mac} @ {session.session_id}</name>
        <description>
            <![CDATA[
            <h3>📱 DEVICE DETECTION EVENT</h3>
            <table border="1" cellpadding="5">
            <tr><td><b>Device MAC</b></td><td>{device.mac}</td></tr>
            <tr><td><b>Location</b></td><td>{session.session_id}</td></tr>
            <tr><td><b>Persistence Level</b></td><td>{threat_level}</td></tr>
            <tr><td><b>Detection Time</b></td><td>{datetime.fromtimestamp(session.start_time).strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
            <tr><td><b>Duration at Location</b></td><td>{(session.end_time - session.start_time)/60:.1f} minutes</td></tr>
            <tr><td><b>Appearances Here</b></td><td>{len(appearances_here)}</td></tr>
            <tr><td><b>Persistence Score</b></td><td>{device.persistence_score:.3f}</td></tr>
            </table>
            {f'<h4>📡 Probe Activity:</h4><ul>{chr(10).join(f"<li>{chr(10).join(app.ssids_probed)}</li>" for app in appearances_here[:3] if app.ssids_probed)}</ul>' if any(app.ssids_probed for app in appearances_here[:3]) else '<p>No probe requests captured</p>'}
            ]]>
        </description>
        <styleUrl>{marker_styles.get(threat_level, "#suspiciousDeviceStyle")}</styleUrl>
        <Point>
            <coordinates>{session.location.longitude},{session.location.latitude},0</coordinates>
        </Point>
    </Placemark>'''
                        content_parts.append(device_marker)
    
    def _add_surveillance_heatmap(self, content_parts: List[str], surveillance_devices: List, 
                                gps_tracker: GPSTracker) -> None:
        """Add surveillance intensity heatmap visualization"""
        
        # Calculate surveillance intensity per location
        location_intensity = {}
        for device in surveillance_devices:
            for location in device.locations_seen:
                if location not in location_intensity:
                    location_intensity[location] = []
                location_intensity[location].append(device.persistence_score)
        
        for location, scores in location_intensity.items():
            avg_persistence = sum(scores) / len(scores)
            max_persistence = max(scores)
            device_count = len(scores)
            
            # Find the session for this location
            session = None
            for s in gps_tracker.location_sessions:
                if s.session_id == location:
                    session = s
                    break
            
            if session:
                # Create heatmap circle based on intensity
                radius = min(max(device_count * 50, 100), 500)  # Scale radius by device count
                
                heatmap_circle = f'''
    <Placemark>
        <name>🔥 Surveillance Intensity: {location}</name>
        <description>
            <![CDATA[
            <h3>📊 SURVEILLANCE INTENSITY ANALYSIS</h3>
            <table border="1" cellpadding="5">
            <tr><td><b>Location</b></td><td>{location}</td></tr>
            <tr><td><b>Suspicious Devices</b></td><td>{device_count}</td></tr>
            <tr><td><b>Average Persistence Score</b></td><td>{avg_persistence:.3f}</td></tr>
            <tr><td><b>Maximum Persistence Score</b></td><td>{max_persistence:.3f}</td></tr>
            <tr><td><b>Intensity Level</b></td><td>{'🔴 VERY HIGH' if max_persistence > 0.8 else '🟡 ELEVATED' if max_persistence > 0.6 else '🟢 MODERATE'}</td></tr>
            </table>
            ]]>
        </description>
        <styleUrl>#heatmapStyle</styleUrl>
        <Polygon>
            <outerBoundaryIs>
                <LinearRing>
                    <coordinates>
                        {self._generate_circle_coordinates(session.location.longitude, session.location.latitude, radius)}
                    </coordinates>
                </LinearRing>
            </outerBoundaryIs>
        </Polygon>
    </Placemark>'''
                content_parts.append(heatmap_circle)
    
    def _add_temporal_analysis_tracks(self, content_parts: List[str], surveillance_devices: List,
                                    gps_tracker: GPSTracker) -> None:
        """Add temporal surveillance pattern visualization"""  
        
        # Group devices by time patterns
        work_hour_devices = []
        off_hour_devices = []
        regular_pattern_devices = []
        
        for device in surveillance_devices:
            hours = [datetime.fromtimestamp(a.timestamp).hour for a in device.appearances]
            work_hours = [h for h in hours if 9 <= h <= 17]
            off_hours = [h for h in hours if h >= 22 or h <= 6]
            
            work_hour_ratio = len(work_hours) / len(hours) if hours else 0
            off_hour_ratio = len(off_hours) / len(hours) if hours else 0
            
            if work_hour_ratio > 0.7:
                work_hour_devices.append(device)
            elif off_hour_ratio > 0.7:
                off_hour_devices.append(device)
            
            # Check for regular intervals
            if len(device.appearances) >= 3:
                timestamps = sorted([a.timestamp for a in device.appearances])
                intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
                if len(intervals) > 1:
                    avg_interval = sum(intervals) / len(intervals)
                    variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)
                    if variance < (avg_interval * 0.1):  # Regular pattern
                        regular_pattern_devices.append(device)
        
        # Create pattern analysis placemarks
        if work_hour_devices:
            analysis = f'''
    <Placemark>
        <name>⏰ Work Hours Surveillance Pattern</name>
        <description>
            <![CDATA[
            <h3>👔 WORK HOURS SURVEILLANCE DETECTED</h3>
            <p><b>{len(work_hour_devices)} devices</b> show activity primarily during work hours (9 AM - 5 PM)</p>
            <p><b>Implications:</b> Possible workplace surveillance or professional monitoring</p>
            <h4>Affected Devices:</h4>
            <ul>
            {chr(10).join(f'<li>{device.mac} (Score: {device.persistence_score:.2f})</li>' for device in work_hour_devices)}
            </ul>
            ]]>
        </description>
        <styleUrl>#temporalPatternStyle</styleUrl>
        <Point>
            <coordinates>{gps_tracker.location_sessions[0].location.longitude},{gps_tracker.location_sessions[0].location.latitude},100</coordinates>
        </Point>
    </Placemark>'''
            content_parts.append(analysis)
        
        if off_hour_devices:
            analysis = f'''
    <Placemark>
        <name>🌙 Off-Hours Surveillance Pattern</name>
        <description>
            <![CDATA[
            <h3>🚨 OFF-HOURS SURVEILLANCE DETECTED</h3>
            <p><b>{len(off_hour_devices)} devices</b> show activity primarily during off hours (10 PM - 6 AM)</p>
            <p><b>Implications:</b> Possible stalking or personal surveillance</p>
            <h4>Affected Devices:</h4>
            <ul>
            {chr(10).join(f'<li>{device.mac} (Score: {device.persistence_score:.2f})</li>' for device in off_hour_devices)}
            </ul>
            ]]>
        </description>
        <styleUrl>#offHoursPatternStyle</styleUrl>
        <Point>
            <coordinates>{gps_tracker.location_sessions[0].location.longitude},{gps_tracker.location_sessions[0].location.latitude},150</coordinates>
        </Point>
    </Placemark>'''
            content_parts.append(analysis)
    
    def _generate_circle_coordinates(self, center_lon: float, center_lat: float, radius_meters: float) -> str:
        """Generate circle coordinates for KML polygon"""
        import math
        
        # Convert radius to degrees (approximate)
        radius_deg = radius_meters / 111000  # rough conversion
        
        coordinates = []
        for i in range(37):  # 36 points + close the circle
            angle = (i * 10) * math.pi / 180  # 10 degrees per point
            lon = center_lon + radius_deg * math.cos(angle)
            lat = center_lat + radius_deg * math.sin(angle)
            coordinates.append(f"{lon},{lat},0")
        
        return " ".join(coordinates)
    
    def _get_enhanced_kml_template(self) -> str:
        """Get spectacular KML template with advanced styling and metadata"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
<Document>
    <name>🛡️ CYT Advanced Surveillance Detection Analysis</name>
    <description><![CDATA[
        <h2>📡 CYT Device Analysis Report</h2>
        <p><b>Generated:</b> {timestamp}</p>
        <p><b>Analysis:</b> Wireless device tracking and persistence analysis</p>
        <p><b>GPS Locations:</b> {total_locations} monitoring locations</p>
        <p><b>Persistent Devices:</b> {total_devices} devices detected</p>
        <hr>
        <h3>Visualization Features:</h3>
        <ul>
        <li>Color-coded device classifications</li>
        <li>Location monitoring session data</li>
        <li>Device movement correlation</li>
        <li>Activity intensity mapping</li>
        <li>Time-based pattern analysis</li>
        </ul>
        <p><i>KML visualization for Google Earth analysis.</i></p>
    ]]></description>
    
    <!-- Location Styles -->
    <Style id="locationStyle">
        <IconStyle>
            <color>ff00ff00</color>
            <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>
            <scale>1.2</scale>
        </IconStyle>
    </Style>
    
    <Style id="criticalLocationStyle">
        <IconStyle>
            <color>ff0000ff</color>
            <Icon><href>http://maps.google.com/mapfiles/kml/shapes/forbidden.png</href></Icon>
            <scale>1.8</scale>
        </IconStyle>
    </Style>
    
    <Style id="highThreatLocationStyle">
        <IconStyle>
            <color>ff0080ff</color>
            <Icon><href>http://maps.google.com/mapfiles/kml/shapes/caution.png</href></Icon>
            <scale>1.5</scale>
        </IconStyle>
    </Style>
    
    <Style id="mediumThreatLocationStyle">
        <IconStyle>
            <color>ff00ffff</color>
            <Icon><href>http://maps.google.com/mapfiles/kml/shapes/triangle.png</href></Icon>
            <scale>1.3</scale>
        </IconStyle>
    </Style>
    
    <!-- Device Path Styles -->
    <Style id="criticalDevicePathStyle">
        <LineStyle>
            <color>ff0000ff</color>
            <width>5</width>
        </LineStyle>
    </Style>
    
    <Style id="highDevicePathStyle">
        <LineStyle>
            <color>ff0080ff</color>
            <width>4</width>
        </LineStyle>
    </Style>
    
    <Style id="mediumDevicePathStyle">
        <LineStyle>
            <color>ff00ffff</color>
            <width>3</width>
        </LineStyle>
    </Style>
    
    <Style id="devicePathStyle">
        <LineStyle>
            <color>7f00ffff</color>
            <width>3</width>
        </LineStyle>
    </Style>
    
    <!-- Device Marker Styles -->
    <Style id="criticalDeviceStyle">
        <IconStyle>
            <color>ff0000ff</color>
            <Icon><href>http://maps.google.com/mapfiles/kml/shapes/target.png</href></Icon>
            <scale>2.0</scale>
        </IconStyle>
    </Style>
    
    <Style id="highDeviceStyle">
        <IconStyle>
            <color>ff0080ff</color>
            <Icon><href>http://maps.google.com/mapfiles/kml/shapes/cross-hairs.png</href></Icon>
            <scale>1.7</scale>
        </IconStyle>
    </Style>
    
    <Style id="mediumDeviceStyle">
        <IconStyle>
            <color>ff00ffff</color>
            <Icon><href>http://maps.google.com/mapfiles/kml/shapes/open-diamond.png</href></Icon>
            <scale>1.4</scale>
        </IconStyle>
    </Style>
    
    <Style id="suspiciousDeviceStyle">
        <IconStyle>
            <color>ff0000ff</color>
            <Icon><href>http://maps.google.com/mapfiles/kml/shapes/target.png</href></Icon>
            <scale>1.5</scale>
        </IconStyle>
    </Style>
    
    <!-- Analysis Styles -->
    <Style id="heatmapStyle">
        <PolyStyle>
            <color>7f0000ff</color>
            <fill>1</fill>
            <outline>1</outline>
        </PolyStyle>
        <LineStyle>
            <color>ff0000ff</color>
            <width>2</width>
        </LineStyle>
    </Style>
    
    <Style id="temporalPatternStyle">
        <IconStyle>
            <color>ff00ff00</color>
            <Icon><href>http://maps.google.com/mapfiles/kml/shapes/clock.png</href></Icon>
            <scale>1.5</scale>
        </IconStyle>
    </Style>
    
    <Style id="offHoursPatternStyle">
        <IconStyle>
            <color>ff800080</color>
            <Icon><href>http://maps.google.com/mapfiles/kml/shapes/moon.png</href></Icon>
            <scale>1.5</scale>
        </IconStyle>
    </Style>
    
    {content}
</Document>
</kml>'''
    
    def _generate_empty_kml(self, output_file: str) -> str:
        """Generate empty KML when no GPS data is available"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        empty_content = f'''
    <Placemark>
        <name>🚨 No GPS Data Available</name>
        <description>
            <![CDATA[
            <h3>No Location Data Found</h3>
            <p>Generated: {timestamp}</p>
            <p>No GPS coordinates were available for visualization.</p>
            <p>Ensure GPS tracking is enabled and locations are being recorded.</p>
            ]]>
        </description>
        <Point>
            <coordinates>-112.0740,33.4484,0</coordinates>
        </Point>
    </Placemark>'''
        
        kml_output = self._get_enhanced_kml_template().format(
            content=empty_content,
            timestamp=timestamp,
            total_locations=0,
            total_devices=0
        )
        
        with open(output_file, 'w') as f:
            f.write(kml_output)
        
        logger.warning(f"Empty KML generated: {output_file}")
        return kml_output

def simulate_gps_data() -> List[Tuple[float, float, str]]:
    """Generate simulated GPS data for testing"""
    # Simulate a route with multiple stops
    locations = [
        (33.4484, -112.0740, "Phoenix_Home"),
        (33.4734, -112.0431, "Phoenix_Office"), 
        (33.5076, -112.0726, "Phoenix_Mall"),
        (33.4942, -112.1122, "Phoenix_Restaurant"),
        (33.4484, -112.0740, "Phoenix_Home_Return")
    ]
    return locations