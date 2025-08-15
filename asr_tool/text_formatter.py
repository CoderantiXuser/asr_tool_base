import re
import json
import os
from .logger import log_message
from word2number import w2n

class TextFormatter:
    def __init__(self, config_dir=None):
        if config_dir is None:
            config_dir = os.path.dirname(__file__)

        self.corrections = self._load_json_config(os.path.join(config_dir, "corrections.json"))
        self.abbreviations = self._load_json_config(os.path.join(config_dir, "abbreviations.json"))

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

    def _apply_replacements(self, text: str, replacements: dict) -> str:
        """Applies a dictionary of replacements to the text."""
        for key in sorted(replacements, key=len, reverse=True):
            pattern = r'\b' + re.escape(key) + r'\b'
            text = re.sub(pattern, replacements[key], text, flags=re.IGNORECASE)
        return text

    def _convert_numbers(self, text: str) -> str:
        """Converts number words in a sentence to digits."""
        words = text.split()
        new_words = []
        for word in words:
            try:
                num = w2n.word_to_num(word)
                new_words.append(str(num))
            except ValueError:
                new_words.append(word)
        return " ".join(new_words)

    def _format_special_patterns(self, text: str) -> str:
        """Formats special spoken patterns like emails and URLs."""
        # Email: "user at domain dot com" -> "user@domain.com"
        text = re.sub(r'(\w+)\s+at\s+([\w\d\-_]+)\s+dot\s+([\w\d\-_.]+)', r'\1@\2.\3', text, flags=re.IGNORECASE)
        # URL: "domain dot com" -> "domain.com"
        text = re.sub(r'\b([\w\d\-_]+)\s+dot\s+([\w\d\-_.]+)\b', r'\1.\2', text, flags=re.IGNORECASE)
        return text

    def _capitalize_text(self, text: str) -> str:
        """Applies intelligent capitalization."""
        text = re.sub(r'\bi\b', 'I', text)
        if text and text[0].isalpha():
            text = text[0].upper() + text[1:]
        text = re.sub(r'([.?!])\s*([a-z])', lambda m: m.group(1) + ' ' + m.group(2).upper(), text)
        return text

    def _cleanup_spacing(self, text: str) -> str:
        """Cleans up spacing around punctuation."""
        text = re.sub(r'\s+([,.?!])', r'\1', text)
        text = re.sub(r'([,.?!])([a-zA-Z0-9])', r'\1 \2', text)
        return text

    def format(self, text: str) -> str:
        """
        Applies a series of formatting rules to the input text.
        """
        if not text:
            return ""

        text = text.lower()
        text = re.sub(r'\bblah blah blah\b', '', text, flags=re.IGNORECASE).strip()

        text = self._apply_replacements(text, self.corrections)
        text = self._apply_replacements(text, self.abbreviations)
        text = self._format_special_patterns(text)
        text = self._convert_numbers(text)

        text = self._capitalize_text(text)

        text = self._cleanup_spacing(text)
        text = re.sub(r'\s+', ' ', text).strip()

        return text
