import subprocess
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
from .logger import log_message
from .overlay import overlay

class ExecutionAgent:
    def __init__(self):
        self.keyboard_controller = KeyboardController()
        self.mouse_controller = MouseController()

    def execute_command_action(self, action_type, value):
        """Execute a single command action."""
        log_message(f"Executing action: {action_type} - {value}", level="DEBUG")
        try:
            if action_type == "key_press":
                self._press_key(value)
            elif action_type == "key_combo":
                self._press_key_combo(value)
            elif action_type == "launch_application":
                self._launch_app(value)
            elif action_type == "execute_shell":
                self._execute_shell(value)
            elif action_type == "mouse_click":
                self._click_mouse(value)
            elif action_type == "mouse_scroll":
                self._scroll_mouse(value)
            elif action_type == "media_key":
                self._press_media_key(value)
            elif action_type == "overlay_control":
                self._control_overlay(value)
            else:
                log_message(f"Unknown action type: {action_type}", level="WARNING")
        except Exception as e:
            log_message(f"Failed to execute action {action_type} with value {value}: {e}", level="ERROR")

    def _get_key(self, key_name):
        """Get a pynput Key object from a string, or return the string."""
        return getattr(Key, key_name.lower(), key_name)

    def _press_key(self, key_name):
        """Presses and releases a single key."""
        key = self._get_key(key_name)
        self.keyboard_controller.press(key)
        self.keyboard_controller.release(key)

    def _press_key_combo(self, combo_str):
        """Presses and releases a key combination like 'ctrl+s'."""
        keys = [self._get_key(k.strip()) for k in combo_str.split('+')]
        with self.keyboard_controller.pressed(*keys[:-1]):
            self.keyboard_controller.press(keys[-1])
            self.keyboard_controller.release(keys[-1])

    def _launch_app(self, app_name):
        """Launches an application in a detached process."""
        subprocess.Popen(app_name, shell=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)

    def _execute_shell(self, command):
        """Executes a shell command."""
        subprocess.Popen(command, shell=True)

    def _click_mouse(self, click_type):
        """Performs a mouse click."""
        if click_type == 'left':
            self.mouse_controller.click(Button.left, 1)
        elif click_type == 'right':
            self.mouse_controller.click(Button.right, 1)
        elif click_type == 'double':
            self.mouse_controller.click(Button.left, 2)
        else:
            log_message(f"Unknown click type: {click_type}", level="WARNING")

    def _scroll_mouse(self, direction, steps=5):
        """Scrolls the mouse wheel."""
        dx = 0
        dy = steps if direction == 'down' else -steps if direction == 'up' else 0
        self.mouse_controller.scroll(dx, dy)

    def _press_media_key(self, key_name):
        """Presses a special media key."""
        media_keys = {
            "volume_up": Key.media_volume_up,
            "volume_down": Key.media_volume_down,
            "volume_mute": Key.media_volume_mute,
            "play_pause": Key.media_play_pause,
            "next_track": Key.media_next,
            "prev_track": Key.media_previous,
        }
        key = media_keys.get(key_name.lower())
        if key:
            self._press_key(key)
        else:
            log_message(f"Unknown media key: {key_name}", level="WARNING")

    def _control_overlay(self, value):
        """Controls the notification overlay."""
        command = value.get("command")
        arg = value.get("arg")
        if command == "set_theme":
            overlay.set_theme(arg)
        elif command == "set_position":
            overlay.set_position(arg)
        else:
            log_message(f"Unknown overlay command: {command}", level="WARNING")
