from pynput import keyboard
import time
import threading
from collections import defaultdict
from .overlay import overlay

class HotkeyAgent:
    def __init__(self):
        # --- Public State Flags ---
        self._listening_active = False
        self._typing_active = False
        self._command_mode_active = False
        self._quit_requested = False
        self._emergency_stop_requested = False
        self._show_stats_requested = False

        # --- Internal Hotkey Logic ---
        self._key_press_history = defaultdict(list)
        self._multi_press_threshold = 0.4  # seconds for multi-press window

        # Map specific keys to a generic key name for easier handling
        self._key_map = {
            keyboard.Key.ctrl_l: 'ctrl_l',
            keyboard.Key.alt_l: 'alt_l',
            keyboard.Key.esc: 'esc',
            keyboard.Key.shift: 'shift',
            keyboard.Key.shift_l: 'shift',
            keyboard.Key.shift_r: 'shift'
        }

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener_thread = threading.Thread(target=self._listener.start, daemon=True)
        self._listener_thread.start()

    def _get_press_count(self, key_name):
        """Checks for multi-presses and returns the count within the threshold."""
        current_time = time.time()
        # Filter out old presses
        self._key_press_history[key_name] = [
            t for t in self._key_press_history[key_name] if current_time - t < self._multi_press_threshold
        ]
        # Add current press
        self._key_press_history[key_name].append(current_time)
        return len(self._key_press_history[key_name])

    def _on_press(self, key):
        """Handle key press events."""
        # --- Multi-press Hotkeys ---
        if key in self._key_map:
            key_name = self._key_map[key]
            press_count = self._get_press_count(key_name)

            if key_name == 'ctrl_l' and press_count == 2:
                self._listening_active = not self._listening_active
                status = "LISTENING ON" if self._listening_active else "LISTENING OFF"
                overlay.show_message(status, color="green" if self._listening_active else "red", duration=2)
                self._key_press_history[key_name].clear() # Reset after action

            elif key_name == 'alt_l' and press_count == 2:
                self._typing_active = not self._typing_active
                status = "TYPING ON" if self._typing_active else "TYPING OFF"
                overlay.show_message(status, color="green" if self._typing_active else "red", duration=2)
                self._key_press_history[key_name].clear()

            elif key_name == 'esc':
                if press_count == 2:
                    self._quit_requested = True
                    overlay.show_message("QUITTING...", color="red", duration=2)
                    self._key_press_history[key_name].clear()
                elif press_count == 3:
                    self._emergency_stop_requested = True
                    overlay.show_message("EMERGENCY STOP", color="red", duration=3)
                    self._key_press_history[key_name].clear()

            elif key_name == 'shift' and press_count == 3:
                self._show_stats_requested = True
                overlay.show_message("SHOWING STATS", color="blue", duration=2)
                # This flag should be reset by the consumer after handling
                self._key_press_history[key_name].clear()

        # --- Single-press and Hold Hotkeys ---
        elif key == keyboard.Key.ctrl_r:
            self._command_mode_active = not self._command_mode_active
            if self._command_mode_active:
                overlay.show_message("COMMAND MODE", color="orange")
            else:
                overlay.hide_message()

        elif key == keyboard.Key.alt_r: # Quick Dictation (Press and Hold)
            if not self._listening_active: # Prevent conflict if already listening
                self._listening_active = True
                self._typing_active = True
                overlay.show_message("QUICK DICTATION", color="cyan")

    def _on_release(self, key):
        """Handle key release events."""
        if key == keyboard.Key.alt_r: # End of Quick Dictation
            self._listening_active = False
            self._typing_active = False
            overlay.hide_message()

    # --- Public Interface Methods ---
    def is_listening_active(self): return self._listening_active
    def is_typing_active(self): return self._typing_active
    def is_command_mode_active(self): return self._command_mode_active
    def is_quit_requested(self): return self._quit_requested
    def is_emergency_stop_requested(self): return self._emergency_stop_requested
    def is_show_stats_requested(self): return self._show_stats_requested
    
    def reset_show_stats_request(self):
        """To be called by the consumer after stats are shown."""
        self._show_stats_requested = False

    def deactivate_command_mode(self):
        self._command_mode_active = False
        overlay.hide_message()

    def reset_typing_mode(self):
        self._typing_active = False

    def stop(self):
        """Stop the keyboard listener."""
        if self._listener.is_alive():
            self._listener.stop()
            self._listener_thread.join(timeout=1)
