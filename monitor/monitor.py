import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Configuration ---
WATCH_DIRECTORY = "/home/reolinkftp/front/"

# Set up logging to distinguish monitor output
monitor_logger = logging.getLogger("Monitor")
monitor_logger.setLevel(logging.INFO)
if not monitor_logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(message)s', datefmt='%H:%M:%S')
    ch.setFormatter(formatter)
    monitor_logger.addHandler(ch)

# --- Core File Handler ---

class NewFileHandler(FileSystemEventHandler):
    """Handles file creation events and ensures files are complete."""
    def __init__(self, processing_callback=None, check_interval_sec=0.5):
        self.processing_callback = processing_callback
        self.check_interval_sec = check_interval_sec

    def on_created(self, event):
        if not event.is_directory:
            file_path = Path(event.src_path)
            monitor_logger.info(f"New file detected: {file_path.name}")
            
            # CRITICAL: Wait for file completion before processing
            self.wait_for_file_completion(file_path)

            if self.processing_callback:
                # Execute the light processing logic
                self.processing_callback(file_path)

    def wait_for_file_completion(self, file_path: Path, min_checks=3):
        checks_passed = 0
        last_size = -1
        
        while checks_passed < min_checks:
            try:
                current_size = file_path.stat().st_size
                
                if current_size == last_size and current_size > 0:
                    checks_passed += 1
                elif current_size != last_size:
                    checks_passed = 0 # Reset if file is still growing
                
                last_size = current_size
                time.sleep(self.check_interval_sec)
            except FileNotFoundError:
                monitor_logger.warning(f"File vanished during completion check: {file_path.name}")
                return
        monitor_logger.info(f"File {file_path.name} stabilized.")

# --- Monitor Class ---

class DirectoryMonitor:
    """Manages the watchdog Observer thread."""
    
    def __init__(self, directory: str, callback):
        self.directory = directory
        self.event_handler = NewFileHandler(processing_callback=callback)
        self.observer = Observer()
        self.is_running = False

    def start(self):
        if self.is_running:
            monitor_logger.warning("Monitor is already running.")
            return

        monitor_logger.info(f"Monitor STARTED for {self.directory}")
        self.observer.schedule(self.event_handler, self.directory, recursive=False)
        self.observer.start()
        self.is_running = True

    def stop(self):
        if not self.is_running:
            monitor_logger.warning("Monitor is not running.")
            return
            
        monitor_logger.info("Monitor STOPPED.")
        self.observer.stop()
        self.observer.join()
        self.is_running = False

# Example Processing Function (Lightweight check for arrival)
def process_ftp_file(file_path: Path):
    """Your lightweight processing logic."""
    # Since you only care if a file arrived, we can just log the event
    # and maybe update an in-memory status flag.
    monitor_logger.info(f"File arrival confirmed for processing period: {file_path.name}")
    
    # In a real app, you might update a database record here:
    # db.record_arrival(file_path.name, time.time())
    
    # After confirmation, move or delete the file to keep the directory clean
    file_path.unlink() # Delete the file
    monitor_logger.info(f"Cleaned up processed file: {file_path.name}")

