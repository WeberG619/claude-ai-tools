# Drop Zone Monitor for Revit Development
import os
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
import subprocess

class RevitDropZoneMonitor:
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.zones = self.config['drop_zones']
        self.settings = self.config['global_settings']
        
    def start_monitoring(self):
        """Start monitoring all drop zones"""
        print("🚀 Revit Drop Zone Monitor Started")
        print("=" * 50)
        
        # Display active zones
        print("\nActive Drop Zones:")
        for zone_name, zone_config in self.zones.items():
            print(f"  📁 {zone_name}: {zone_config['description']}")
        
        print(f"\nWatching every {self.settings['watch_interval']} seconds...")
        print("Press Ctrl+C to stop\n")
        
        # Main monitoring loop
        try:
            while True:
                for zone_name, zone_config in self.zones.items():
                    self.check_zone(zone_name, zone_config)
                
                time.sleep(self.settings['watch_interval'])
                
        except KeyboardInterrupt:
            print("\n\n✋ Monitoring stopped")
    
    def check_zone(self, zone_name, zone_config):
        """Check a single drop zone for new files"""
        zone_path = Path(zone_config['path'])
        
        if not zone_path.exists():
            zone_path.mkdir(parents=True, exist_ok=True)
            return
        
        # Look for files with watched extensions
        for ext in zone_config['watch_extensions']:
            for file_path in zone_path.glob(f"*{ext}"):
                if file_path.is_file():
                    self.process_file(zone_name, zone_config, file_path)
    
    def process_file(self, zone_name, zone_config, file_path):
        """Process a dropped file"""
        print(f"\n📄 Processing: {file_path.name} in {zone_name}")
        
        # Create processed directory
        processed_dir = file_path.parent / self.settings['processed_folder']
        processed_dir.mkdir(exist_ok=True)
        
        # Call the appropriate handler
        handler_name = zone_config['processor']
        output_dir = processed_dir
        
        try:
            # Here you would call the actual handler
            # For now, we'll simulate it
            print(f"  🔧 Running {handler_name}...")
            
            # Move original file to processed
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            processed_path = processed_dir / new_name
            shutil.move(str(file_path), str(processed_path))
            
            print(f"  ✅ Processed successfully!")
            print(f"  📁 Output in: {processed_dir}")
            
            # Log activity
            self.log_activity(zone_name, file_path.name, "success")
            
            # Notification
            if zone_config.get('notification', False):
                print("  🔔 Notification sent!")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            self.log_activity(zone_name, file_path.name, "error", str(e))
    
    def log_activity(self, zone, filename, status, error=None):
        """Log drop zone activity"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'zone': zone,
            'file': filename,
            'status': status,
            'error': error
        }
        
        log_file = Path(self.settings.get('log_file', 'dropzone.log'))
        
        # Append to log file
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

if __name__ == "__main__":
    config_path = "D:\\claude-code-revit\\config\\dropzone_config.json"
    
    if not Path(config_path).exists():
        print("❌ Configuration file not found!")
        print(f"Expected at: {config_path}")
        exit(1)
    
    monitor = RevitDropZoneMonitor(config_path)
    monitor.start_monitoring()
