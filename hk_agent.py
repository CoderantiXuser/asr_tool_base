from pynput import keyboard
import time
import threading
from logger import overlay

class HotkeyAgent:
    def __init__(self):
        self._listening_active = False
        self._typing_active = False
        self._command_mode_active = False
        self._quit_requested = False
        
        self._last_ctrl_press = 0
        self._last_alt_press = 0
        self._last_esc_press = 0
        self._double_press_threshold = 0.3  # seconds
        
        self._setup_listener()
    
    def _setup_listener(self):
        """Initialize and start the keyboard listener."""
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener_thread = threading.Thread(target=self._listener.start, daemon=True)
        self._listener_thread.start()
    
    def _on_press(self, key):
        """Handle key press events."""
        current_time = time.time()
        
        try:
            if key == keyboard.Key.esc:
                if current_time - self._last_esc_press < self._double_press_threshold:
                    self._quit_requested = True
                    overlay.show_message("QUITTING...", color="red", duration=2)
                self._last_esc_press = current_time
            
            elif key == keyboard.Key.ctrl_l:
                # Handle double press for listening toggle
                if current_time - self._last_ctrl_press < self._double_press_threshold:
                    self._listening_active = not self._listening_active
                    status = "LISTENING ON" if self._listening_active else "LISTENING OFF"
                    color = "green" if self._listening_active else "red"
                    overlay.show_message(status, color=color, duration=2)
                
                self._last_ctrl_press = current_time
            
            elif key == keyboard.Key.ctrl_r:
                # Toggle command mode on single press
                self._command_mode_active = not self._command_mode_active
                if self._command_mode_active:
                    overlay.show_message("COMMAND MODE ACTIVE", color="orange")
                else:
                    overlay.hide_message() # Clear overlay when command mode is deactivated
            
            elif key == keyboard.Key.alt_l:
                if current_time - self._last_alt_press < self._double_press_threshold:
                    self._typing_active = not self._typing_active
                    status = "TYPING ON" if self._typing_active else "TYPING OFF"
                    color = "green" if self._typing_active else "red"
                    overlay.show_message(status, color=color, duration=2)
                
                self._last_alt_press = current_time
        
        except AttributeError:
            # Ignore keys that don't have the expected attributes
            pass
    
    def _on_release(self, key):
        """Handle key release events."""
        # No specific action on release for now, as command mode is toggled by press
        pass
    
    # Public interface methods
    def is_listening_active(self):
        return self._listening_active
    
    def is_typing_active(self):
        return self._typing_active
    
    def is_command_mode_active(self):
        return self._command_mode_active
    
    def is_quit_requested(self):
        return self._quit_requested
    
    def deactivate_command_mode(self):
        self._command_mode_active = False
        overlay.hide_message()

    def reset_typing_mode(self):
        self._typing_active = False
        # Optionally, hide typing overlay if it's still visible
        # overlay.hide_message() # This might interfere with other overlays, so be careful

    def stop(self):
        """Stop the keyboard listener and cleanup."""
        if hasattr(self, '_listener'):
            self._listener.stop()
            if hasattr(self, '_listener_thread') and self._listener_thread.is_alive():
                self._listener_thread.join(timeout=1)
