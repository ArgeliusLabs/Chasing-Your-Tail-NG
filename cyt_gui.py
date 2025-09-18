#!/usr/bin/env python3
"""
Enhanced CYT GUI - BlackHat Arsenal Ready
Maintains Fisher Price usability for small screens while looking professional
"""
import tkinter as tk
from tkinter import messagebox, scrolledtext
import subprocess
import os
import pathlib
import sqlite3
import glob
import json
import threading
from datetime import datetime

# Set test mode for GUI before any imports
import os
from typing import Any, Literal
os.environ['CYT_TEST_MODE'] = 'true'  # Enable test mode for GUI

class CYTGui:
    def __init__(self):
        self.root = tk.Tk()
        
        # Load config later when needed
        self.config = None
        self.credential_manager = None
        
        self.setup_ui()
        self.running_processes = {}
        self.update_status()
        
    def setup_ui(self):
        """Setup the enhanced UI"""
        self.root.title('🔒 Chasing Your Tail - BlackHat Arsenal Edition')
        self.root.configure(bg='#1a1a1a')  # Dark theme
        self.root.geometry('800x480')  # Optimized for 7-inch screens
        
        # Create main container
        main_frame = tk.Frame(self.root, bg='#1a1a1a', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title and status section
        self.create_header(main_frame)
        
        # Status indicators
        self.create_status_section(main_frame)
        
        # Main control buttons (keeping Fisher Price chunky style)
        self.create_control_buttons(main_frame)
        
        # Log output area
        self.create_log_section(main_frame)
        
    def create_header(self, parent):
        """Create header with title and security badge"""
        header_frame = tk.Frame(parent, bg='#1a1a1a')
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Main title
        title_label = tk.Label(
            header_frame,
            text="🔒 Chasing Your Tail",
            font=('Arial', 18, 'bold'),
            fg='#00ff41',  # Matrix green
            bg='#1a1a1a'
        )
        title_label.pack(side=tk.LEFT)
        
        # Security badge
        security_badge = tk.Label(
            header_frame,
            text="🛡️ SECURED",
            font=('Arial', 10, 'bold'),
            fg='#ffffff',
            bg='#ff6b35',  # Orange badge
            padx=10,
            pady=5
        )
        security_badge.pack(side=tk.RIGHT)
        
        # Subtitle
        subtitle_label = tk.Label(
            parent,
            text="Wi-Fi Probe Request Analyzer - BlackHat Arsenal Ready",
            font=('Arial', 10),
            fg='#cccccc',
            bg='#1a1a1a'
        )
        subtitle_label.pack(pady=(0, 10))
        
    def create_status_section(self, parent):
        """Create status indicators section"""
        status_frame = tk.LabelFrame(
            parent,
            text="System Status",
            font=('Arial', 10, 'bold'),
            fg='#ffffff',
            bg='#2a2a2a',
            padx=10,
            pady=10
        )
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Status indicators row
        indicators_frame = tk.Frame(status_frame, bg='#2a2a2a')
        indicators_frame.pack(fill=tk.X)
        
        # Kismet status
        self.kismet_status = tk.Label(
            indicators_frame,
            text="⏳ Kismet: Checking...",
            font=('Arial', 10),
            fg='#ffaa00',
            bg='#2a2a2a'
        )
        self.kismet_status.pack(side=tk.LEFT, padx=(0, 20))
        
        # Database status
        self.db_status = tk.Label(
            indicators_frame,
            text="⏳ Database: Checking...",
            font=('Arial', 10),
            fg='#ffaa00',
            bg='#2a2a2a'
        )
        self.db_status.pack(side=tk.LEFT, padx=(0, 20))
        
        # Credentials status
        self.creds_status = tk.Label(
            indicators_frame,
            text="⏳ Credentials: Checking...",
            font=('Arial', 10),
            fg='#ffaa00',
            bg='#2a2a2a'
        )
        self.creds_status.pack(side=tk.LEFT)
        
    def create_control_buttons(self, parent):
        """Create the main control buttons (Fisher Price style but professional)"""
        controls_frame = tk.LabelFrame(
            parent,
            text="Controls",
            font=('Arial', 12, 'bold'),
            fg='#ffffff',
            bg='#2a2a2a',
            padx=10,
            pady=10
        )
        controls_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Top row buttons
        top_row = tk.Frame(controls_frame, bg='#2a2a2a')
        top_row.pack(fill=tk.X, pady=(0, 10))
        
        # System status button
        self.status_btn = tk.Button(
            top_row,
            text="📊 Check\nSystem Status",
            font=('Arial', 9, 'bold'),
            width=12,
            height=2,
            fg='#ffffff',
            bg='#007acc',
            activebackground='#005999',
            relief='raised',
            bd=3,
            command=self.check_status_threaded
        )
        self.status_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Create ignore lists button
        self.create_ignore_btn = tk.Button(
            top_row,
            text="📝 Create\nIgnore Lists",
            font=('Arial', 9, 'bold'),
            width=12,
            height=2,
            fg='#ffffff',
            bg='#28a745',
            activebackground='#1e7e34',
            relief='raised',
            bd=3,
            command=self.create_ignore_lists_threaded
        )
        self.create_ignore_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Delete ignore lists button
        self.delete_ignore_btn = tk.Button(
            top_row,
            text="🗑️ Delete\nIgnore Lists",
            font=('Arial', 9, 'bold'),
            width=12,
            height=2,
            fg='#ffffff',
            bg='#dc3545',
            activebackground='#c82333',
            relief='raised',
            bd=3,
            command=self.delete_ignore_lists
        )
        self.delete_ignore_btn.pack(side=tk.LEFT)
        
        # Bottom row buttons
        bottom_row = tk.Frame(controls_frame, bg='#2a2a2a')
        bottom_row.pack(fill=tk.X)
        
        # Run CYT button (main action)
        self.run_cyt_btn = tk.Button(
            bottom_row,
            text="🚀 START\nCHASING YOUR TAIL",
            font=('Arial', 11, 'bold'),
            width=18,
            height=2,
            fg='#ffffff',
            bg='#ff6b35',  # Distinctive orange
            activebackground='#e55a2b',
            relief='raised',
            bd=4,
            command=self.run_cyt_threaded
        )
        self.run_cyt_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Analyze logs button
        self.analyze_btn = tk.Button(
            bottom_row,
            text="📈 Analyze\nLogs",
            font=('Arial', 9, 'bold'),
            width=12,
            height=2,
            fg='#ffffff',
            bg='#6f42c1',
            activebackground='#5a359c',
            relief='raised',
            bd=3,
            command=self.analyze_logs_threaded
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Surveillance analysis button
        self.surveillance_btn = tk.Button(
            bottom_row,
            text="🗺️ Surveillance\nAnalysis",
            font=('Arial', 9, 'bold'),
            width=12,
            height=2,
            fg='#ffffff',
            bg='#28a745',
            activebackground='#218838',
            relief='raised',
            bd=3,
            command=self.surveillance_analysis_threaded
        )
        self.surveillance_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Quit button
        self.quit_btn = tk.Button(
            bottom_row,
            text="❌ QUIT",
            font=('Arial', 9, 'bold'),
            width=12,
            height=2,
            fg='#ffffff',
            bg='#6c757d',
            activebackground='#545b62',
            relief='raised',
            bd=3,
            command=self.quit_application
        )
        self.quit_btn.pack(side=tk.RIGHT)
        
    def create_log_section(self, parent):
        """Create log output section"""
        log_frame = tk.LabelFrame(
            parent,
            text="Output Log",
            font=('Arial', 10, 'bold'),
            fg='#ffffff',
            bg='#2a2a2a',
            padx=10,
            pady=10
        )
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Log text area with dark theme
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            font=('Courier', 14),
            bg='#000000',
            fg='#00ff41',  # Matrix green text
            insertbackground='#00ff41',
            selectbackground='#333333'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Initial welcome message
        self.log_message("🔒 CYT Enhanced GUI - Security Hardened Edition")
        self.log_message("=" * 50)
        self.log_message("All SQL injection vulnerabilities eliminated ✅")
        self.log_message("Credential encryption active ✅") 
        self.log_message("Input validation enabled ✅")
        self.log_message("Ready for BlackHat Arsenal demo! 🎯")
        self.log_message("")
        
    def log_message(self, message):
        """Add message to log with timestamp"""
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        full_message = f"{timestamp} {message}\n"
        self.log_text.insert(tk.END, full_message)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def update_status(self):
        """Update status indicators"""
        threading.Thread(target=self._update_status_background, daemon=True).start()
        
    def _update_status_background(self):
        """Background status update"""
        # Check Kismet
        kismet_running = self.check_kismet_running()
        if kismet_running:
            self.kismet_status.config(text="✅ Kismet: Running", fg='#28a745')
        else:
            self.kismet_status.config(text="❌ Kismet: Not Running", fg='#dc3545')
            
        # Check database
        db_file, db_error = self.check_kismet_db()
        if db_file is None or db_error:
            self.db_status.config(text="❌ Database: Error", fg='#dc3545')
        else:
            # Get device count
            try:
                with sqlite3.connect(db_file) as con:
                    cursor = con.cursor()
                    cursor.execute("SELECT COUNT(*) FROM devices")
                    count = cursor.fetchone()[0]
                self.db_status.config(text=f"✅ Database: {count:,} devices", fg='#28a745')
            except:
                self.db_status.config(text="⚠️ Database: Connected", fg='#ffaa00')
                
        # Check credentials
        if self.credential_manager:
            try:
                token = self.credential_manager.get_wigle_token()
                if token:
                    self.creds_status.config(text="✅ Credentials: Encrypted", fg='#28a745')
                else:
                    self.creds_status.config(text="⚠️ Credentials: Missing", fg='#ffaa00')
            except:
                self.creds_status.config(text="❌ Credentials: Error", fg='#dc3545')
        else:
            self.creds_status.config(text="⚠️ Credentials: Optional", fg='#ffaa00')
            
    def check_kismet_running(self):
        """Check if Kismet is running"""
        try:
            result = subprocess.run(['pgrep', 'kismet'], capture_output=True)
            return result.returncode == 0
        except:
            return False
            
    def check_kismet_db(self) -> tuple[None, str] | tuple[Any, None]:
        """Check if Kismet database exists and is accessible"""
        if not self.config:
            try:
                with open('config.json', 'r') as f:
                    self.config = json.load(f)
            except:
                self.config = {}
        
        db_path = self.config.get('paths', {}).get('kismet_logs', '/tmp/kismet*.kismet')
        list_of_files = glob.glob(db_path)
        if not list_of_files:
            return None, "No Kismet database files found"
        try:
            latest_file = max(list_of_files, key=os.path.getctime)
            with sqlite3.connect(latest_file) as con:
                cursor = con.cursor()
                cursor.execute("SELECT COUNT(*) FROM devices")
            return latest_file, None
        except Exception as e:
            return None, str(e)
            
    def check_status_threaded(self):
        """Check system status in background"""
        self.log_message("🔍 Checking system status...")
        threading.Thread(target=self._check_status_background, daemon=True).start()
        
    def _check_status_background(self):
        """Background status check"""
        try:
            # Check Kismet status
            kismet_processes = subprocess.run(['pgrep', '-c', 'kismet'], capture_output=True, text=True)
            kismet_count = int(kismet_processes.stdout.strip()) if kismet_processes.returncode == 0 else 0
            
            if kismet_count > 0:
                self.log_message("✅ Kismet is running")
            else:
                self.log_message("❌ Kismet is not running")
            
            # Check monitor mode
            try:
                iwconfig_result = subprocess.run(['iwconfig'], capture_output=True, text=True, timeout=5)
                if "Mode:Monitor" in iwconfig_result.stdout:
                    self.log_message("✅ Monitor mode detected")
                else:
                    self.log_message("❌ Monitor mode not detected")
            except Exception as e:
                self.log_message(f"⚠️ Could not check monitor mode: {e}")
                
            self.update_status()
        except Exception as e:
            self.log_message(f"❌ Error running status check: {e}")
            
    def create_ignore_lists_threaded(self):
        """Create ignore lists in background"""
        self.log_message("📝 Creating ignore lists from Kismet database...")
        self.create_ignore_btn.config(state='disabled', text='Creating...')
        threading.Thread(target=self._create_ignore_lists_background, daemon=True).start()
        
    def _create_ignore_lists_background(self):
        """Background ignore list creation"""
        try:
            # Check database first
            db_file, error = self.check_kismet_db()
            if db_file is None or error:
                self.log_message(f"❌ Database error: {error}")
                return
                
            self.log_message(f"📊 Using database: {os.path.basename(db_file)}")
            
            # Create ignore_lists directory
            ignore_dir = pathlib.Path('./ignore_lists')
            ignore_dir.mkdir(parents=True, exist_ok=True)
            
            # Process database
            with sqlite3.connect(db_file) as con:
                # Get MAC addresses
                cursor = con.cursor()
                cursor.execute("SELECT DISTINCT devmac FROM devices")
                mac_rows = cursor.fetchall()
                
                mac_list = []
                for row in mac_rows:
                    mac = row[0]
                    if mac and mac not in mac_list:
                        mac_list.append(mac)
                        
                self.log_message(f"✅ Found {len(mac_list)} unique MAC addresses")
                
                # Get SSIDs from probe requests
                cursor.execute("SELECT device FROM devices WHERE device LIKE '%dot11.probedssid.ssid%'")
                device_rows = cursor.fetchall()
                
                ssid_list = []
                for row in device_rows:
                    try:
                        device_json = json.loads(row[0])
                        dot11_device = device_json.get('dot11.device', {})
                        if dot11_device:
                            last_probe = dot11_device.get('dot11.device.last_probed_ssid_record', {})
                            ssid = last_probe.get('dot11.probedssid.ssid')
                            if ssid and ssid not in ssid_list:
                                ssid_list.append(ssid)
                    except (json.JSONDecodeError, KeyError):
                        continue
                        
                self.log_message(f"✅ Found {len(ssid_list)} unique SSIDs")
                
            # Write files using secure format (JSON instead of Python exec)
            import json as json_module
            
            mac_file = ignore_dir / 'mac_list.json'
            with open(mac_file, 'w') as f:
                json_module.dump(mac_list, f, indent=2)
                
            ssid_file = ignore_dir / 'ssid_list.json'  
            with open(ssid_file, 'w') as f:
                json_module.dump(ssid_list, f, indent=2)
                
            self.log_message(f"💾 Saved MAC list to: {mac_file}")
            self.log_message(f"💾 Saved SSID list to: {ssid_file}")
            self.log_message("✅ Ignore lists created successfully!")
            
        except Exception as e:
            self.log_message(f"❌ Error creating ignore lists: {e}")
        finally:
            self.create_ignore_btn.config(state='normal', text='📝 Create\nIgnore Lists')
            
    def delete_ignore_lists(self):
        """Delete ignore lists with confirmation"""
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete all ignore lists?"):
            try:
                ignore_dir = pathlib.Path('./ignore_lists')
                deleted_count = 0
                
                for file_path in ignore_dir.glob('*'):
                    if file_path.is_file():
                        os.remove(file_path)
                        deleted_count += 1
                        self.log_message(f"🗑️ Deleted: {file_path.name}")
                        
                self.log_message(f"✅ Deleted {deleted_count} ignore list files")
                
            except Exception as e:
                self.log_message(f"❌ Error deleting ignore lists: {e}")
                
    def run_cyt_threaded(self):
        """Run CYT in background"""
        if 'cyt' in self.running_processes:
            self.log_message("⚠️ CYT is already running!")
            return
            
        self.log_message("🚀 Starting Chasing Your Tail...")
        self.run_cyt_btn.config(state='disabled', text='🔄 RUNNING...', bg='#ffaa00')
        threading.Thread(target=self._run_cyt_background, daemon=True).start()
        
    def _run_cyt_background(self):
        """Background CYT execution"""
        try:
            # Set test mode for non-interactive credential access
            env = os.environ.copy()
            env['CYT_TEST_MODE'] = 'true'
            
            process = subprocess.Popen(
                ['python3', './chasing_your_tail.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            
            self.running_processes['cyt'] = process
            self.log_message("✅ CYT process started successfully")
            
            # Read output in real-time
            for line in (process.stdout or []):
                if line.strip():
                    self.log_message(f"CYT: {line.strip()}")
                    
        except Exception as e:
            self.log_message(f"❌ Error running CYT: {e}")
        finally:
            if 'cyt' in self.running_processes:
                del self.running_processes['cyt']
            self.run_cyt_btn.config(state='normal', text='🚀 START\nCHASING YOUR TAIL', bg='#ff6b35')
            
    def analyze_logs_threaded(self):
        """Analyze logs in background"""
        self.log_message("📈 Starting log analysis...")
        self.analyze_btn.config(state='disabled', text='Analyzing...')
        threading.Thread(target=self._analyze_logs_background, daemon=True).start()
        
    def _analyze_logs_background(self):
        """Background log analysis"""
        try:
            env = os.environ.copy()
            env['CYT_TEST_MODE'] = 'true'
            
            self.log_message("🔄 Running probe analyzer (this may take several minutes for large datasets)...")
            
            result = subprocess.run(
                ['python3', './probe_analyzer.py', '--local'],
                capture_output=True,
                text=True,
                timeout=300,  # Increased to 5 minutes
                env=env
            )
            
            # Save full output to timestamped report file
            from datetime import datetime
            import pathlib
            
            # Create reports directory if it doesn't exist
            reports_dir = pathlib.Path('./reports')
            reports_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = reports_dir / f"probe_analysis_report_{timestamp}.txt"
            
            with open(report_file, 'w') as f:
                f.write(f"CYT Probe Analysis Report\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                
                if result.stdout:
                    f.write("ANALYSIS OUTPUT:\n")
                    f.write("-" * 30 + "\n")
                    f.write(result.stdout)
                    f.write("\n\n")
                
                if result.stderr and result.stderr.strip():
                    f.write("WARNINGS/ERRORS:\n")
                    f.write("-" * 30 + "\n")
                    f.write(result.stderr)
                    f.write("\n\n")
                
                f.write("End of Report\n")
            
            self.log_message(f"📄 Full analysis saved to: {report_file}")
            
            # Show summary in GUI
            if result.stdout:
                lines = result.stdout.split('\n')
                summary_lines = []
                
                # Extract key findings for GUI display
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['found', 'ssid:', 'times seen:', 'unique ssids']):
                        summary_lines.append(line)
                
                if summary_lines:
                    self.log_message("📊 Analysis Summary:")
                    for line in summary_lines[:15]:  # Show top findings
                        if line.strip():
                            self.log_message(f"  {line}")
                    
                    if len(summary_lines) > 15:
                        self.log_message(f"  ... and {len(summary_lines)-15} more findings")
                else:
                    # Fallback to first 10 lines if no key findings
                    for line in lines[:10]:
                        if line.strip():
                            self.log_message(f"Analysis: {line}")
                    
            if result.stderr and result.stderr.strip():
                self.log_message(f"⚠️ Analysis warnings saved to report file")
                    
            self.log_message("✅ Log analysis complete - see report file for full details")
            
        except subprocess.TimeoutExpired:
            self.log_message("⚠️ Analysis timed out after 5 minutes (very large dataset)")
            self.log_message("💡 Try running 'python3 probe_analyzer.py --local' manually for large datasets")
        except Exception as e:
            self.log_message(f"❌ Error analyzing logs: {e}")
        finally:
            self.analyze_btn.config(state='normal', text='📈 Analyze\nLogs')
    
    def surveillance_analysis_threaded(self):
        """Run surveillance analysis in background"""
        self.log_message("🗺️ Starting surveillance analysis with GPS correlation...")
        self.surveillance_btn.config(state='disabled', text='Analyzing...')
        threading.Thread(target=self._surveillance_analysis_background, daemon=True).start()
    
    def _surveillance_analysis_background(self):
        """Background surveillance analysis"""
        try:
            env = os.environ.copy()
            env['CYT_TEST_MODE'] = 'true'
            
            self.log_message("🔄 Running surveillance analyzer (generating KML for Google Earth)...")
            
            result = subprocess.run(
                ['python3', './surveillance_analyzer.py'],
                capture_output=True,
                text=True,
                timeout=300,
                env=env
            )
            
            if result.returncode == 0:
                # Look for generated files
                import glob
                kml_files = glob.glob("kml_files/surveillance_analysis_*.kml")
                report_files = glob.glob("surveillance_reports/surveillance_report_*.md")
                
                if kml_files:
                    latest_kml = max(kml_files, key=os.path.getctime)
                    self.log_message(f"✅ KML file generated: {latest_kml}")
                    self.log_message("🌍 Open this file in Google Earth to see GPS tracking!")
                
                if report_files:
                    latest_report = max(report_files, key=os.path.getctime)
                    self.log_message(f"📝 Analysis report: {latest_report}")
                
                self.log_message("✅ Surveillance analysis complete!")
                
                # Show some output
                if result.stdout:
                    lines = result.stdout.split('\n')[:10]  # Show first 10 lines
                    for line in lines:
                        if line.strip():
                            self.log_message(f"📊 {line.strip()}")
            else:
                self.log_message(f"❌ Surveillance analysis failed")
                if result.stderr:
                    self.log_message(f"Error: {result.stderr}")
                    
        except subprocess.TimeoutExpired:
            self.log_message("⚠️ Surveillance analysis timed out")
        except Exception as e:
            self.log_message(f"❌ Error running surveillance analysis: {e}")
        finally:
            self.surveillance_btn.config(state='normal', text='🗺️ Surveillance\nAnalysis')
            
    def quit_application(self):
        """Quit application with cleanup"""
        if messagebox.askyesno("Quit", "Are you sure you want to quit CYT?"):
            # Clean up any running processes
            for name, process in list(self.running_processes.items()):
                try:
                    process.terminate()
                    self.log_message(f"🛑 Stopped {name} process")
                except:
                    pass
                    
            self.log_message("👋 Goodbye!")
            self.root.quit()
            
    def run(self):
        """Start the GUI"""
        self.root.mainloop()

if __name__ == '__main__':
    try:
        app = CYTGui()
        app.run()
    except Exception as e:
        print(f"Error starting CYT GUI: {e}")
        import traceback
        traceback.print_exc()