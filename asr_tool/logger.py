import sys
import tkinter as tk
import threading
import time
from datetime import datetime

# ANSI color codes
COLOR_RESET = "\033[0m"
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_MAGENTA = "\033[95m"
COLOR_CYAN = "\033[96m"
COLOR_WHITE = "\033[97m"

def log_message(message, level="INFO", typing_active=None, listening_active=None):
    """Log a general message to the console with colors and state indication."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    state_info = ""
    if typing_active is not None:
        t_status = f"T: {'ON' if typing_active else 'OFF'}"
        t_color = COLOR_GREEN if typing_active else COLOR_RED
        state_info += f"[{t_color}{t_status}{COLOR_RESET}] "
    
    if listening_active is not None:
        l_status = f"L: {'ON' if listening_active else 'OFF'}"
        l_color = COLOR_GREEN if listening_active else COLOR_RED
        state_info += f"[{l_color}{l_status}{COLOR_RESET}] "

    level_color = COLOR_WHITE
    if level == "INFO":
        level_color = COLOR_CYAN
    elif level == "WARNING":
        level_color = COLOR_YELLOW
    elif level == "ERROR":
        level_color = COLOR_RED

    print(f"[{timestamp}] {state_info}[{level_color}{level}{COLOR_RESET}] {message}")

def display_partial(text, typing_active=None, listening_active=None):
    """Display partial recognition results on the same line, overwriting previous content."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    state_info = ""
    if typing_active is not None:
        t_status = f"T: {'ON' if typing_active else 'OFF'}"
        t_color = COLOR_GREEN if typing_active else COLOR_RED
        state_info += f"[{t_color}{t_status}{COLOR_RESET}] "
    
    if listening_active is not None:
        l_status = f"L: {'ON' if listening_active else 'OFF'}"
        l_color = COLOR_GREEN if listening_active else COLOR_RED
        state_info += f"[{l_color}{l_status}{COLOR_RESET}] "

    sys.stdout.write(f"\r[{timestamp}] {state_info}Partial: {text.ljust(80)}")
    sys.stdout.flush()

def clear_partial():
    """Clear the partial display line."""
    sys.stdout.write(f"\r{' ' * 80}\r")
    sys.stdout.flush()

class NotificationOverlay:
    def __init__(self):
        self.root = None
        self.label = None
        self.thread = None
        self.message_queue = []
        self.queue_lock = threading.Lock()
        self.running = False
        self.current_message = ""
    
    def _run_tk(self):
        """Run the tkinter main loop in a separate thread."""
        self.root = tk.Tk()
        self.root.withdraw()  # Hide initially
        self.root.overrideredirect(True)  # Remove decorations
        self.root.attributes('-topmost', True)  # Always on top
        self.root.attributes('-alpha', 0.9)  # Semi-transparent
        
        # Create label with better styling
        self.label = tk.Label(
            self.root, 
            text="", 
            font=("Arial", 20, "bold"), 
            fg="white", 
            bg="black",
            padx=20,
            pady=10
        )
        self.label.pack()
        
        self._position_window()
        self.root.deiconify()  # Show window
        self.running = True
        
        # Start processing message queue
        self._process_queue()
        self.root.mainloop()
    
    def _position_window(self):
        """Position window at top center of screen."""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = 50  # 50 pixels from top
        self.root.geometry(f"+{x}+{y}")
    
    def _process_queue(self):
        """Process queued messages."""
        if not self.running:
            return
            
        with self.queue_lock:
            if self.message_queue:
                message, color, duration = self.message_queue.pop(0)
                self._update_label(message, color)
                
                if duration > 0:
                    # Schedule message clearing after duration
                    self.root.after(int(duration * 1000), self._clear_after_delay)
        
        # Continue processing queue
        self.root.after(100, self._process_queue)
    
    def _update_label(self, message, color):
        """Update the label text and color."""
        if self.label and self.running:
            self.current_message = message
            self.label.config(text=message, fg=color)
            
            # Reposition window if text size changed
            self._position_window()
    
    def _clear_after_delay(self):
        """Clear label text after delay (only if message hasn't changed)."""
        if self.label and self.running:
            # Only clear if no new message has been set
            with self.queue_lock:
                if not self.message_queue:
                    self.label.config(text="")
                    self.current_message = ""
    
    def start(self):
        """Start the overlay in a separate thread."""
        if not self.thread or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._run_tk, daemon=True)
            self.thread.start()
            # Give time for tkinter to initialize
            time.sleep(0.1)
    
    def stop(self):
        """Stop the overlay and cleanup."""
        self.running = False
        if self.root:
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass  # Ignore cleanup errors
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
    
    def show_message(self, message, color="white", duration=0):
        """Queue a message to be displayed."""
        if not self.running:
            return
            
        with self.queue_lock:
            # Clear queue if this is a persistent message (duration=0)
            if duration == 0:
                self.message_queue.clear()
            self.message_queue.append((message, color, duration))
    
    def hide_message(self):
        """Hide the current message immediately."""
        self.show_message("", duration=0)

# Global instance for convenience
overlay = NotificationOverlay()
