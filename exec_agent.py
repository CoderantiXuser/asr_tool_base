import subprocess
from pynput.keyboard import Controller as KeyboardController, Key
from logger import log_message

class ExecutionAgent:
    def __init__(self):
        self.keyboard_controller = KeyboardController()

    def execute_command_action(self, action_type, value):
        """Execute a single command action."""
        if action_type == "key_press":
            try:
                key = getattr(Key, value.lower()) if hasattr(Key, value.lower()) else value
                self.keyboard_controller.press(key)
                self.keyboard_controller.release(key)
            except AttributeError:
                self.keyboard_controller.press(value)
                self.keyboard_controller.release(value)
        elif action_type == "key_combo":
            keys = [k.strip() for k in value.split('+')]
            pressed_keys = []
            # Press all keys
            for k in keys:
                try:
                    key = getattr(Key, k.lower()) if hasattr(Key, k.lower()) else k
                    self.keyboard_controller.press(key)
                    pressed_keys.append(key)
                except AttributeError:
                    self.keyboard_controller.press(k)
                    pressed_keys.append(k)
            # Release in reverse order
            for key in reversed(pressed_keys):
                self.keyboard_controller.release(key)
        elif action_type == "launch_application":
            try:
                # Launch application detached from the current console
                subprocess.Popen(
                    [value],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=True,  # Close inherited file descriptors
                    start_new_session=True  # Detach from controlling terminal (Unix-like)
                )
            except FileNotFoundError:
                log_message(f"Application not found: {value}", level="ERROR")
        elif action_type == "execute_shell":
            try:
                subprocess.Popen(value, shell=True)
            except Exception as e:
                log_message(f"Shell command error: {e}", level="ERROR")
