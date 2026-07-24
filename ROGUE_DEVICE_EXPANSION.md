Expanding CYT: Comprehensive Rogue & Surveillance Device Detection

## Executive Summary

CYT can be evolved from a **device persistence tracker** into a **comprehensive rogue/surveillance hardware detector** comparable to Biscuit Pro + specialized threat detection. By adding signatures, behavioral analysis, and frequency-based detection, CYT could identify and track:

- WiFi Pineapple (evil twin, deauth attacks)
- IMSI Catchers (stingray/fake cell towers)
- Flipper Zero (NFC/RF probe attacks)
- AirTag stalking (proximity tracking)
- Skimmers & POS theft (Bluetooth payment interception)
- Axon/Flock Police Tech (persistent device tracking)
- Meta Smart Glasses (unauthorized recording)
- Spyware Cameras (hidden video surveillance)

---

## Device-Specific Detection Strategies

### 1. WiFi Pineapple Detection
**What it is:** Rogue access point for MITM attacks, deauthentication flooding, SSL stripping

**Detection methods:**
- **Beacon frame analysis**: Monitor for suspicious beacon rate (typically >100/sec vs normal 10/sec)
- **Deauthentication floods**: Flag rapid deauth frame bursts (>50/sec on single channel)
- **SSID cloning**: Detect multiple APs broadcasting identical SSID with different MAC addresses
- **Channel hopping**: Identify rapid channel switching patterns (WiFi Pineapple cycles channels)
- **Signature patterns**: Known BSSID ranges, specific beacon frame intervals
- **DHCP behavior**: Offer DHCP addresses with unusual TTL values

**Implementation:**
```python
# In surveillance_detector.py
class WiFiPineappleDetector:
    def detect_deauth_floods(self, frames, threshold=50):
        """Detect deauthentication attack patterns"""
        deauth_rate = count_deauth_frames(frames, time_window=1.0)
        return deauth_rate > threshold
    
    def detect_ssid_cloning(self, networks):
        """Identify multiple APs with same SSID"""
        ssid_groups = group_by_ssid(networks)
        return {ssid: macs for ssid, macs in ssid_groups.items() if len(macs) > 1}
    
    def detect_beacon_anomalies(self, beacon_frames):
        """Analyze beacon frame patterns"""
        beacon_rates = calculate_beacon_interval(beacon_frames)
        return beacon_rates[beacon_rates > 100]  # Flag abnormal rates
```

**Pi resource cost:** Low (frame counting, already captured by Kismet)

---

### 2. IMSI Catcher Detection (Stingray/Fake Cell Towers)
**What it is:** Fake cellular network forcing devices to connect, enabling call/SMS interception

**Detection methods:**
- **Signal strength anomalies**: Monitor for unusually strong cell signals on uncommon bands
- **MCC/MNC inconsistencies**: Flag incorrect country/carrier codes
- **Downgrade attacks**: Detect forcing from 4G/5G down to 2G (vulnerable)
- **Persistent tower**: Device appearing on tower with unusual consistency (not moving with traffic)
- **Unusual cell IDs**: Monitor for rapidly changing cell identifiers (IMSI catcher signature)
- **LTE/GSM band mixing**: Flag impossible simultaneous cell + WiFi patterns

**Implementation:**
```python
# New module: imsi_detector.py
class IMSIDetector:
    def detect_downgrade_attacks(self, device_history):
        """Identify 5G → 4G → 2G forced downgrade"""
        tech_sequence = [d['technology'] for d in device_history]
        downgrades = detect_regression(tech_sequence)
        return downgrades
    
    def detect_persistent_tower(self, device, duration_threshold=3600):
        """Flag device locked to single tower too long"""
        tower_changes = count_unique_towers(device, time_window=1800)
        return tower_changes < 2  # Should move between towers
    
    def detect_unusual_signal_strength(self, cell_signals):
        """Identify anomalously strong/weak signals"""
        mean_rssi = np.mean(cell_signals)
        outliers = [s for s in cell_signals if abs(s - mean_rssi) > 3*sigma]
        return outliers
```

**Pi resource cost:** Medium (requires cellular signal monitoring — may need USB cellular adapter)

---

### 3. Flipper Zero Detection
**What it is:** Handheld multi-protocol attack device (NFC, RFID, RF, Bluetooth)

**Detection methods:**
- **RF frequency sweeping**: Monitor for rapid frequency hops across 125kHz, 433MHz, 868MHz, 915MHz, 2.4GHz ISM bands
- **NFC command patterns**: Detect unusual NFC polling sequences (reading multiple card types rapidly)
- **Bluetooth pairing floods**: Flag rapid Bluetooth pairing/unpairing attempts
- **Subghz transmission bursts**: Identify suspicious RF bursts on RFID/garage door frequencies
- **Behavioral signature**: Combination of multiple protocol tests in sequence

**Implementation:**
```python
# New module: flipper_detector.py
class FlipperZeroDetector:
    def detect_rf_frequency_sweep(self, rf_events, time_window=60):
        """Identify rapid RF frequency scanning"""
        unique_freqs = set(rf_events[t:t+time_window]['frequency'])
        if len(unique_freqs) > 10:  # Rapid frequency changes
            return True
        return False
    
    def detect_nfc_polling_flood(self, nfc_events):
        """Flag aggressive NFC polling"""
        polling_rate = count_nfc_polls(nfc_events, time_window=10)
        return polling_rate > 20  # Normal: ~1-2 polls/10sec
    
    def detect_multi_protocol_attack(self, device_events):
        """Identify Flipper pattern: multi-protocol testing"""
        protocols = set(e['protocol'] for e in device_events if e['time'] < 300)
        flipper_signature = protocols >= {'RF', 'NFC', 'Bluetooth'}
        return flipper_signature
```

**Pi resource cost:** High (requires multi-protocol SDR/RF capture hardware)

---

### 4. AirTag Stalking Detection
**What it is:** Apple tracking device used for unauthorized person/property tracking

**Detection methods:**
- **Bluetooth advertisement pattern**: AirTags broadcast specific iBeacon UUIDs (00005015-0000-1000-8000-004C000000000)
- **Persistent proximity**: Same AirTag BSSID following device for extended periods
- **Rotating MAC addresses**: Apple uses rolling MAC addresses; identify by beacon UUID consistency
- **Signal strength correlation**: AirTag moving closer/farther matches user location changes
- **Multi-AirTag coordination**: Multiple AirTags from same owner coordinating (coordinated stalking)

**Implementation:**
```python
# New module: airtag_detector.py
AIRTAG_UUID = "00005015-0000-1000-8000-004C000000000"

class AirTagDetector:
    def detect_airtag_beacon(self, bt_advertisements):
        """Identify AirTag by iBeacon signature"""
        airtags = [ad for ad in bt_advertisements if ad['uuid'] == AIRTAG_UUID]
        return len(airtags) > 0
    
    def detect_stalking_pattern(self, airtag_locations, user_gps):
        """Flag AirTag following user across locations"""
        airtag_proximity = calculate_distance(airtag_locations, user_gps)
        stalking_score = 0
        
        for proximity in airtag_proximity:
            if proximity < 50:  # Within 50 meters
                stalking_score += 1
        
        return stalking_score > 0.8  # 80%+ of time within 50m = stalking
    
    def detect_coordinated_airtags(self, multiple_airtags):
        """Identify multiple AirTags from same owner (coordinated tracking)"""
        # Group by manufacturer patterns, movement correlation
        coordinated = group_by_movement_correlation(multiple_airtags)
        return len(coordinated) > 1
```

**Pi resource cost:** Low (Bluetooth monitoring already in place)

---

### 5. Payment Skimmer & POS Theft Detection
**What it is:** Bluetooth-based card readers for capturing payment data

**Detection methods:**
- **Bluetooth pairing anomalies**: Flag devices attempting rapid pairing with multiple phones
- **Payment protocol detection**: Monitor for Bluetooth profiles associated with card readers (HID, SPP)
- **MAC address spoofing**: Identify devices claiming to be legitimate POS terminals but with inconsistent behavior
- **Signal pattern matching**: Known POS skimmer MAC ranges, beacon patterns
- **Payment encryption bypass**: Detect unencrypted payment data transmission

**Implementation:**
```python
class SkimmerDetector:
    KNOWN_SKIMMER_MACS = ['00:1A:6B:*', '00:13:EF:*']  # Known skimmer prefixes
    
    def detect_rogue_pos_terminal(self, bt_device):
        """Identify suspicious Bluetooth payment device"""
        # Check against known skimmer MACs
        if matches_pattern(bt_device['mac'], self.KNOWN_SKIMMER_MACS):
            return True
        
        # Check Bluetooth profile
        if bt_device['profile'] in ['HID', 'SPP'] and bt_device['name'].lower() in ['pos', 'terminal', 'reader']:
            return True
        
        return False
    
    def detect_pairing_flood(self, bt_events):
        """Flag device attempting rapid pairing"""
        pairing_rate = count_pairing_attempts(bt_events, time_window=60)
        return pairing_rate > 10
```

**Pi resource cost:** Low (Bluetooth monitoring)

---

### 6. Axon/Flock Police Tech Detection
**What it is:** Law enforcement persistent surveillance cameras/sensors for automated license plate recognition, facial recognition

**Detection methods:**
- **Fixed camera signatures**: Identify permanent or semi-permanent camera placements via GPS/signal patterns
- **Known Axon MAC ranges**: Axon devices have specific OUI (Organizationally Unique Identifier) ranges
- **WiFi/4G connectivity patterns**: Police equipment shows consistent connectivity to city infrastructure
- **Power grid analysis**: Cameras typically AC-powered (unusual 24/7 power draw in certain locations)
- **Signal strength consistency**: Fixed cameras maintain consistent signal strength

**Implementation:**
```python
class AxonFlockDetector:
    AXON_OUI_RANGES = ['00:14:E4:*', '00:1E:2A:*']  # Axon device ranges
    
    def detect_fixed_surveillance_camera(self, device, gps_history):
        """Identify stationary surveillance equipment"""
        # Check against known Axon OUIs
        if matches_pattern(device['mac'], self.AXON_OUI_RANGES):
            return True
        
        # Check for fixed location (GPS doesn't move)
        location_variance = calculate_location_variance(gps_history)
        if location_variance < 20:  # Less than 20m variance over hours
            return True, "Fixed location pattern"
        
        return False
    
    def detect_persistent_monitoring(self, device_detections, duration=86400):
        """Flag device present for entire day (characteristic of surveillance)"""
        detection_gaps = find_gaps(device_detections)
        uptime_percentage = (duration - sum(detection_gaps)) / duration
        return uptime_percentage > 0.95
```

**Pi resource cost:** Low (GPS + device tracking)

---

### 7. Meta Smart Glasses Detection
**What it is:** Covert video recording device worn as normal eyewear

**Detection methods:**
- **WiFi patterns**: Meta glasses connect to specific WiFi networks for cloud sync
- **Bluetooth beaconing**: Distinctive Bluetooth advertisement patterns
- **MAC address ranges**: Meta device ranges are identifiable
- **Camera indication**: Certain WiFi probe patterns indicate local video processing
- **Battery drain signature**: Consistent power draw pattern unique to recording devices

**Implementation:**
```python
class MetaGlassesDetector:
    META_OUI_RANGES = ['00:23:AB:*', 'BC:F4:D4:*']
    
    def detect_meta_glasses(self, bt_device):
        """Identify Meta smart glasses by device signature"""
        if matches_pattern(bt_device['mac'], self.META_OUI_RANGES):
            return True
        
        if 'meta' in bt_device['name'].lower() or 'ray' in bt_device['name'].lower():
            return True
        
        return False
    
    def detect_video_processing_pattern(self, wifi_probe_patterns):
        """Identify video encoding/upload traffic patterns"""
        # Meta glasses upload to Meta Cloud continuously
        upload_pattern = detect_continuous_data_transfer(wifi_probe_patterns)
        return upload_pattern
```

**Pi resource cost:** Low (Bluetooth + WiFi monitoring)

---

### 8. Spyware Camera Detection
**What it is:** Hidden video surveillance devices (wearable pins, USB devices, clocks, etc.)

**Detection methods:**
- **WiFi/Bluetooth connectivity**: Spy cameras often connect to WiFi for remote viewing
- **Data exfiltration patterns**: Identify devices uploading video data to cloud
- **Power consumption**: USB-powered cameras show continuous 5V supply draw
- **Known camera MAC ranges**: Identify by device fingerprinting
- **Thermal imaging**: Detect heat signature (camera sensor generates heat)
- **RF emission**: Some cameras broadcast wireless feeds on 2.4GHz ISM band

**Implementation:**
```python
class SpyCameraDetector:
    CAMERA_OUI_RANGES = [
        '00:0A:95:*',  # Hikvision
        '00:17:F2:*',  # Netgear cameras
        '00:06:5B:*',  # Linksys cameras
    ]
    
    def detect_spy_camera(self, device):
        """Identify hidden camera by device fingerprint"""
        if matches_pattern(device['mac'], self.CAMERA_OUI_RANGES):
            return True
        
        if 'camera' in device['name'].lower() or 'cam' in device['name'].lower():
            return True
        
        return False
    
    def detect_video_upload_pattern(self, network_traffic):
        """Flag continuous video streaming (characteristic of spy cam)"""
        data_rate = calculate_data_rate(network_traffic)
        if data_rate > 500_000:  # > 500 KB/sec = video stream
            return True
        return False
    
    def detect_thermal_signature(self, ir_readings, device_location):
        """Use thermal imaging to detect hidden camera sensors"""
        if ir_readings[device_location] > 40:  # Camera sensor typically 40-50°C
            return True
        return False
```

**Pi resource cost:** High (requires thermal imaging hardware: FLIR Lepton or similar)

---

## Integrated Multi-Device Framework

### Detection Coordination Engine
```python
# New module: rogue_device_orchestrator.py
class RogueDeviceOrchestrator:
    def __init__(self):
        self.detectors = {
            'wifi_pineapple': WiFiPineappleDetector(),
            'imsi_catcher': IMSIDetector(),
            'flipper': FlipperZeroDetector(),
            'airtag': AirTagDetector(),
            'skimmer': SkimmerDetector(),
            'axon_flock': AxonFlockDetector(),
            'meta_glasses': MetaGlassesDetector(),
            'spy_camera': SpyCameraDetector(),
        }
    
    def comprehensive_threat_analysis(self, network_data, gps_data, rf_data):
        """Run all detectors and correlate findings"""
        threats = {}
        
        for detector_name, detector in self.detectors.items():
            try:
                result = detector.analyze(network_data, gps_data, rf_data)
                threats[detector_name] = result
            except Exception as e:
                self.logger.error(f"{detector_name} analysis failed: {e}")
        
        # Correlate findings (e.g., WiFi Pineapple + AirTag = coordinated attack)
        correlated_threats = self.correlate_threats(threats)
        
        return {
            'individual_threats': threats,
            'correlated_threats': correlated_threats,
            'threat_score': self.calculate_threat_score(correlated_threats),
            'recommended_action': self.recommend_action(correlated_threats)
        }
    
    def correlate_threats(self, threats):
        """Identify multi-device attack patterns"""
        patterns = []
        
        if threats['wifi_pineapple'] and threats['airtag']:
            patterns.append("Coordinated stalking: WiFi Pineapple + AirTag")
        
        if threats['imsi_catcher'] and threats['spy_camera']:
            patterns.append("Sophisticated surveillance: IMSI + Video recording")
        
        if threats['flipper'] and threats['skimmer']:
            patterns.append("Payment fraud: Flipper + Skimmer coordination")
        
        return patterns
```

---

## Hardware Requirements for Full Detection

| Detection Type | Required Hardware | Cost | Pi-Compatible |
|---|---|---|---|
| WiFi Pineapple | WiFi adapter (monitor mode) | $20-100 | ✅ Yes |
| IMSI Catcher | USB cellular modem | $50-200 | ✅ Yes |
| Flipper | Software-defined radio (HackRF) | $100-300 | ⚠️ USB |
| AirTag | Bluetooth LE adapter | $10-50 | ✅ Yes (Pi has BT) |
| Skimmer | Bluetooth scanner | $20-100 | ✅ Yes |
| Axon/Flock | GPS + WiFi SSID database | $0 (built-in) | ✅ Yes |
| Meta Glasses | Bluetooth + WiFi monitoring | $0 (built-in) | ✅ Yes |
| Spy Camera | Thermal imaging (optional) | $200-500 | ⚠️ USB |

---

## Recommended Implementation Phases

### Phase 1: Quick Wins (2 weeks)
- ✅ WiFi Pineapple detection (beacon anomalies, SSID cloning)
- ✅ AirTag stalking detection
- ✅ Meta Glasses detection (BT signature)
- ✅ Spy Camera detection (network patterns)

**New code:** ~800 lines, mostly signature matching and pattern recognition

### Phase 2: Intermediate (4 weeks)
- ✅ IMSI Catcher detection (requires cellular modem)
- ✅ Skimmer detection (enhanced Bluetooth analysis)
- ✅ Axon/Flock detection (fixed location tracking)
- ✅ Correlation engine

**New code:** ~1200 lines, ML-based pattern matching

### Phase 3: Advanced (6+ weeks)
- ✅ Flipper Zero detection (requires SDR hardware)
- ✅ Thermal imaging integration
- ✅ Real-time threat dashboard
- ✅ SIEM/API integrations

**New code:** ~2000 lines, hardware drivers, visualization

---

## Comparison with Biscuit Pro

| Feature | Biscuit Pro | CYT (Expanded) | Winner |
|---|---|---|---|
| WiFi mapping | ✅ Native | ✅ Via Kismet | Tie |
| Bluetooth mapping | ✅ Dual-band | ✅ Built-in | Tie |
| Threat detection | ❌ Limited | ✅ Comprehensive | CYT |
| Persistence tracking | ❌ No | ✅ Yes | CYT |
| GPS correlation | ⚠️ Optional | ✅ Yes | CYT |
| Rogue device detection | ⚠️ Basic | ✅ Advanced | CYT |
| Cost | ~$400 | ~$150-400 | CYT |
| Extensibility | ❌ Closed | ✅ Open source | CYT |
| Automation | ⚠️ Limited | ✅ Full | CYT |

---

## Threat Intelligence Integration

```python
# Enhanced threat reporting with external feeds
class ThreatIntelligence:
    def check_threat_databases(self, device):
        """Cross-reference against public threat feeds"""
        threats = []
        
        # abuse.ch — known malicious devices
        if self.abuse_ch_lookup(device['mac']):
            threats.append("Known malicious device (abuse.ch)")
        
        # MalwareBazaar — known skimmer/camera MACs
        if self.malware_bazaar_lookup(device['mac']):
            threats.append("Known surveillance device (MalwareBazaar)")
        
        # Custom CYT database — community-contributed sightings
        if self.cyt_community_db.is_suspicious(device['mac']):
            threats.append(f"Reported by {count} CYT users")
        
        return threats
```

---

## Conclusion

**CYT can absolutely be expanded** into a comprehensive rogue/surveillance device detector. The modular architecture already supports adding new detection engines. With strategic hardware investments and phased development, CYT could exceed Biscuit Pro's capabilities while remaining **open-source, affordable, and deployable on Raspberry Pi**.

**Recommended entry point:** Start with Phase 1 (WiFi Pineapple + AirTag + Meta Glasses detection) to build community adoption, then progressively add threat intelligence and advanced detectors.

**Unique advantages over commercial tools:**
- Open source (community contributions, auditable code)
- Raspberry Pi-first design (persistent, low-power monitoring)
- Extensible architecture (add new threats as they emerge)
- Privacy-focused (runs locally, no cloud dependency)
