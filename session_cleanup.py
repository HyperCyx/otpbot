import os
import threading
import time
import glob
from datetime import datetime, timedelta
from config import SESSIONS_DIR
from telegram_otp import session_manager

class SessionCleanupManager:
    """Manages automatic session file cleanup every 4 hours"""
    
    def __init__(self):
        self.cleanup_interval = 4 * 60 * 60  # 4 hours in seconds
        self.cleanup_thread = None
        self.running = False
        self.max_session_age = 24 * 60 * 60  # 24 hours max age for temp sessions
        
    def start_cleanup_scheduler(self):
        """Start the cleanup scheduler thread"""
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            print("🧹 Session cleanup scheduler already running")
            return
            
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        print("🧹 Session cleanup scheduler started (runs every 4 hours)")
    
    def stop_cleanup_scheduler(self):
        """Stop the cleanup scheduler"""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        print("🛑 Session cleanup scheduler stopped")
    
    def _cleanup_loop(self):
        """Main cleanup loop that runs every 4 hours"""
        while self.running:
            try:
                print(f"🧹 Starting scheduled session cleanup at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Perform the cleanup
                cleaned_count = self.cleanup_temporary_sessions()
                
                print(f"✅ Scheduled cleanup completed - removed {cleaned_count} temporary sessions")
                
                # Wait for 4 hours before next cleanup
                for _ in range(self.cleanup_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                print(f"❌ Error in cleanup loop: {e}")
                # Wait a bit before retrying
                time.sleep(300)  # 5 minutes
    
    def cleanup_temporary_sessions(self):
        """Clean up temporary session files"""
        cleaned_count = 0
        current_time = time.time()
        
        try:
            # Ensure sessions directory exists
            if not os.path.exists(SESSIONS_DIR):
                print(f"📁 Sessions directory {SESSIONS_DIR} doesn't exist, creating it")
                os.makedirs(SESSIONS_DIR, exist_ok=True)
                return 0
            
            print(f"🔍 Scanning for temporary sessions in {SESSIONS_DIR}")
            
            # Get all session files recursively
            session_patterns = [
                os.path.join(SESSIONS_DIR, "**", "*.session"),
                os.path.join(SESSIONS_DIR, "*.session"),
                os.path.join(SESSIONS_DIR, "**", "*.session-journal"),
                os.path.join(SESSIONS_DIR, "*.session-journal")
            ]
            
            all_session_files = []
            for pattern in session_patterns:
                all_session_files.extend(glob.glob(pattern, recursive=True))
            
            print(f"📊 Found {len(all_session_files)} session files to check")
            
            for session_file in all_session_files:
                try:
                    # Check if file is old enough to be considered temporary
                    file_modified_time = os.path.getmtime(session_file)
                    file_age = current_time - file_modified_time
                    
                    # Check if session is temporary (older than max_session_age and not in use)
                    if file_age > self.max_session_age:
                        if self._is_temporary_session(session_file):
                            os.remove(session_file)
                            cleaned_count += 1
                            print(f"🗑️ Removed temporary session: {session_file}")
                        else:
                            print(f"⏭️ Keeping active session: {os.path.basename(session_file)}")
                    
                except Exception as e:
                    print(f"⚠️ Error processing session file {session_file}: {e}")
            
            # Clean up empty directories
            self._cleanup_empty_directories()
            
        except Exception as e:
            print(f"❌ Error during session cleanup: {e}")
        
        return cleaned_count
    
    def _is_temporary_session(self, session_file):
        """Determine if a session file is temporary and should be cleaned"""
        try:
            filename = os.path.basename(session_file)
            
            # Skip journal files cleanup if main session exists
            if filename.endswith('.session-journal'):
                main_session = session_file.replace('.session-journal', '.session')
                if os.path.exists(main_session):
                    return False
            
            # Check if session is associated with active users
            if self._is_session_in_use(session_file):
                return False
            
            # Check if session file is corrupted or incomplete
            if self._is_corrupted_session(session_file):
                print(f"🔧 Found corrupted session: {filename}")
                return True
            
            # Consider sessions temporary if they're old and not recently accessed
            file_stats = os.stat(session_file)
            current_time = time.time()
            
            # If not accessed in last 24 hours, consider temporary
            last_access_time = max(file_stats.st_mtime, file_stats.st_atime)
            if (current_time - last_access_time) > self.max_session_age:
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ Error checking if session is temporary {session_file}: {e}")
            return False
    
    def _is_session_in_use(self, session_file):
        """Check if session is currently in use by the bot"""
        try:
            # Check if session is in session_manager's active states
            if hasattr(session_manager, 'user_states'):
                for user_id, state in session_manager.user_states.items():
                    if state.get('session_path') == session_file:
                        return True
            
            # Check if session is locked by another process
            try:
                # Try to open file in exclusive mode briefly
                with open(session_file, 'r+b') as f:
                    pass
                return False
            except (IOError, OSError):
                # File might be locked by active session
                return True
                
        except Exception:
            return False
    
    def _is_corrupted_session(self, session_file):
        """Check if session file is corrupted"""
        try:
            # Very basic corruption check - file size and basic structure
            file_size = os.path.getsize(session_file)
            
            # If file is too small or empty, consider corrupted
            if file_size < 100:  # SQLite sessions are usually larger
                return True
            
            # Try to read first few bytes to check if it's a valid SQLite file
            with open(session_file, 'rb') as f:
                header = f.read(16)
                # SQLite files start with "SQLite format 3"
                if not header.startswith(b'SQLite format 3'):
                    return True
            
            return False
            
        except Exception:
            # If we can't read the file, consider it corrupted
            return True
    
    def _cleanup_empty_directories(self):
        """Remove empty directories in sessions directory"""
        try:
            for root, dirs, files in os.walk(SESSIONS_DIR, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):  # Directory is empty
                            os.rmdir(dir_path)
                            print(f"🗑️ Removed empty directory: {dir_path}")
                    except OSError:
                        pass  # Directory not empty or other issue
                        
        except Exception as e:
            print(f"⚠️ Error cleaning empty directories: {e}")
    
    def manual_cleanup(self):
        """Perform manual cleanup (can be called by admin commands)"""
        print("🧹 Starting manual session cleanup...")
        cleaned_count = self.cleanup_temporary_sessions()
        print(f"✅ Manual cleanup completed - removed {cleaned_count} temporary sessions")
        return cleaned_count

# Global instance
session_cleanup_manager = SessionCleanupManager()

# Functions for external use
def start_session_cleanup():
    """Start the session cleanup scheduler"""
    session_cleanup_manager.start_cleanup_scheduler()

def stop_session_cleanup():
    """Stop the session cleanup scheduler"""
    session_cleanup_manager.stop_cleanup_scheduler()

def manual_session_cleanup():
    """Perform manual session cleanup"""
    return session_cleanup_manager.manual_cleanup()

def get_cleanup_status():
    """Get status of cleanup scheduler"""
    return {
        'running': session_cleanup_manager.running,
        'thread_alive': session_cleanup_manager.cleanup_thread and session_cleanup_manager.cleanup_thread.is_alive(),
        'cleanup_interval_hours': session_cleanup_manager.cleanup_interval / 3600,
        'max_session_age_hours': session_cleanup_manager.max_session_age / 3600
    }