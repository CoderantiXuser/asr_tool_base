from pynput import keyboard
import time
import threading
from collections import defaultdict
from .overlay import overlay

class HotkeyAgent:
    def __init__(self, app):
        self.app = app
        # --- Public State Flags ---
        self._listening_active = False
        self._typing_active = False
        self._command_mode_active = False

        # --- Internal Hotkey Logic ---
        self._key_press_history = defaultdict(list)
        self._multi_press_threshold = 0.4

        self._key_map = {
            keyboard.Key.ctrl_l: 'ctrl_l',
            keyboard.Key.alt_l: 'alt_l',
            keyboard.Key.esc: 'esc',
            keyboard.Key.shift: 'shift',
            keyboard.Key.shift_l: 'shift',
            keyboard.Key.shift_r: 'shift'
        }

        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener_thread = threading.Thread(target=self._listener.start, daemon=True)
        self._listener_thread.start()

    def _get_press_count(self, key_name):
        current_time = time.time()
        self._key_press_history[key_name] = [t for t in self._key_press_history[key_name] if current_time - t < self._multi_press_threshold]
        self._key_press_history[key_name].append(current_time)
        return len(self._key_press_history[key_name])

    def _on_press(self, key):
        if key in self._key_map:
            key_name = self._key_map[key]
            press_count = self._get_press_count(key_name)

            if key_name == 'ctrl_l' and press_count == 2:
                self._listening_active = not self._listening_active
                overlay.show_message("LISTENING ON" if self._listening_active else "LISTENING OFF", color="green" if self._listening_active else "red", duration=2)
                self.app.update_status()
                self._key_press_history[key_name].clear()

            elif key_name == 'alt_l' and press_count == 2:
                self._typing_active = not self._typing_active
                overlay.show_message("TYPING ON" if self._typing_active else "TYPING OFF", color="green" if self._typing_active else "red", duration=2)
                self.app.update_status()
                self._key_press_history[key_name].clear()

            elif key_name == 'esc':
                if press_count == 2:
                    overlay.show_message("QUITTING...", color="red", duration=2)
                    self.app.request_quit()
                    self._key_press_history[key_name].clear()
                elif press_count == 3:
                    overlay.show_message("EMERGENCY STOP", color="red", duration=3)
                    self.app.request_emergency_quit()
                    self._key_press_history[key_name].clear()

            elif key_name == 'shift' and press_count == 3:
                self.app.show_session_stats()
                self._key_press_history[key_name].clear()

        elif key == keyboard.Key.ctrl_r:
            self._command_mode_active = not self._command_mode_active
            overlay.show_message("COMMAND MODE" if self._command_mode_active else "DICTATION MODE", color="orange" if self._command_mode_active else "cyan", duration=2)
            self.app.update_status()

        elif key == keyboard.Key.alt_r:
            if not self._listening_active:
                self._listening_active = True
                self._typing_active = True
                overlay.show_message("QUICK DICTATION", color="cyan")
                self.app.update_status()

    def _on_release(self, key):
        if key == keyboard.Key.alt_r:
            self._listening_active = False
            self._typing_active = False
            overlay.hide_message()
            self.app.update_status()

    # --- Public Interface Methods ---
    def is_listening_active(self): return self._listening_active
    def is_typing_active(self): return self._typing_active
    def is_command_mode_active(self): return self._command_mode_active
    
    def deactivate_command_mode(self):
        if self._command_mode_active:
            self._command_mode_active = False
            self.app.update_status()

    def reset_typing_mode(self):
        if self._typing_active:
            self._typing_active = False
            self.app.update_status()

    def stop(self):
        if self._listener.is_alive():
            self._listener.stop()
            self._listener_thread.join(timeout=1)
