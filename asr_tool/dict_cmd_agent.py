import json
import os
from .logger import log_message

class DictationCommandAgent:
    def __init__(self, config_dir=None):
        if config_dir is None:
            config_dir = os.path.dirname(__file__)

        config_path = os.path.join(config_dir, "dict_cmds_config.json")
        config = self._load_json_config(config_path)
        self.commands = config.get("dictation_commands", {})

    def _load_json_config(self, file_path):
        """Loads a JSON configuration file."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            log_message(f"Configuration file not found: {file_path}", level="WARNING")
            return {}
        except json.JSONDecodeError:
            log_message(f"Invalid JSON in configuration file: {file_path}", level="ERROR")
            return {}

    def process(self, text: str):
        """
        Checks if the text ends with a dictation command.

        Returns:
            A tuple (remaining_text, action).
            'remaining_text' is the text with the command stripped.
            'action' is the action dictionary to be executed, or None.
        """
        text_lower = text.lower().strip()

        # Sort commands by length to match "scratch that" before "that"
        for phrase in sorted(self.commands.keys(), key=len, reverse=True):
            if text_lower.endswith(phrase):
                command_config = self.commands[phrase]
                action = command_config.get("action")

                # Strip the command phrase from the end of the original text
                # Using slicing based on length is safer than replace for end-of-string
                remaining_text = text[:-len(phrase)].strip()

                log_message(f"Dictation command recognized: '{phrase}'", level="INFO")
                return (remaining_text, action)

        return (text, None)
