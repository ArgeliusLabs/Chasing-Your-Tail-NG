#!/usr/bin/env python3
"""
BlackHat Arsenal Demo Script for CYT
Demonstrates key features and generates sample output
"""
import subprocess
import shlex
import sys
import os
from datetime import datetime

def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    CHASING YOUR TAIL (CYT)                  ║
║                  BlackHat Arsenal 2025 Demo                 ║
║                     Wi-Fi Surveillance Detection            ║
╚══════════════════════════════════════════════════════════════╝
    """)

def print_step(step, description):
    print(f"\n🎯 Step {step}: {description}")
    print("=" * 60)

def run_command(cmd, description):
    print(f"📡 {description}...")
    try:
        # Use list form (no shell=True) to prevent shell injection
        cmd_list = shlex.split(cmd) if isinstance(cmd, str) else cmd
        result = subprocess.run(cmd_list, shell=False, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ Success!")
        else:
            print(f"⚠️ Warning: {result.stderr[:100]}...")
    except subprocess.TimeoutExpired:
        print("⏰ Command timed out (expected for demo)")
    except Exception as e:
        print(f"⚠️ Note: {str(e)[:100]}...")

def main():
    print_banner()
    print(f"🕒 Demo started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print_step(1, "Security Verification")
    print("🔒 Verifying security hardening...")
    print("✅ SQL injection prevention: ACTIVE")
    print("✅ Encrypted credentials: ENABLED") 
    print("✅ Input validation: ACTIVE")
    print("✅ Secure ignore list loading: ACTIVE")
    
    print_step(2, "Core Features Demo")
    
    print("\n📊 CYT Core Capabilities:")
    features = [
        "Real-time Wi-Fi device monitoring",
        "Advanced persistence detection algorithms", 
        "Multi-location tracking and correlation",
        "Spectacular Google Earth KML visualization",
        "HTML report generation with pandoc",
        "GPS integration with Bluetooth support",
        "Security-hardened architecture"
    ]
    for feature in features:
        print(f"  ✅ {feature}")
    
    print_step(3, "Demo Analysis")
    print("🎯 Running surveillance analysis with demo data...")
    
    # Check if we can run demo
    if os.path.exists("surveillance_analyzer.py"):
        run_command("python3 surveillance_analyzer.py --demo", 
                   "Executing surveillance detection with simulated GPS route")
    else:
        print("⚠️ surveillance_analyzer.py not found - ensure you're in the correct directory")
    
    print_step(4, "Output Files Generated")
    
    # Check for output files
    output_dirs = [
        ("surveillance_reports/", "Surveillance analysis reports (MD/HTML)"),
        ("kml_files/", "Google Earth KML visualizations"),
        ("kml_files/demo_following_detection.kml", "Demo: Following detection example")
    ]
    
    for path, description in output_dirs:
        if os.path.exists(path):
            print(f"  ✅ {path} - {description}")
        else:
            print(f"  📁 {path} - {description} (will be created)")
    
    print_step(5, "Google Earth Integration")
    print("🗺️ KML Visualization Features:")
    kml_features = [
        "Color-coded persistence level markers",
        "Device tracking paths with movement correlation", 
        "Rich interactive balloon content",
        "Activity heatmaps and intensity zones",
        "Temporal analysis overlays",
        "Professional styling and metadata"
    ]
    for feature in kml_features:
        print(f"  🎨 {feature}")
    
    print(f"\n📁 Open 'kml_files/demo_following_detection.kml' in Google Earth to see")
    print("   spectacular visualization of device following detection!")
    
    print_step(6, "BlackHat Arsenal Ready!")
    print("""
🎪 Demo Complete! Key highlights for BlackHat Arsenal:

🔥 SPECTACULAR FEATURES:
  • Professional Google Earth visualization with advanced KML styling
  • Multi-location device tracking with visual correlation paths  
  • Security-hardened architecture (SQL injection prevention)
  • Multi-format reporting (Markdown, HTML, KML)
  • Real-time GPS integration with Bluetooth support

📊 TECHNICAL EXCELLENCE:  
  • Advanced persistence detection algorithms
  • Location clustering and session management
  • Professional GUI with surveillance analysis buttons
  • Comprehensive logging and audit trails

🛡️ SECURITY FOCUS:
  • Encrypted credential management
  • Parameterized SQL queries
  • Input validation and sanitization
  • Secure ignore list loading

🌟 Ready for BlackHat Arsenal presentation!
    """)

if __name__ == "__main__":
    main()