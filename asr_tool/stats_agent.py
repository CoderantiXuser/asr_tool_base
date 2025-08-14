import time
import re
from collections import defaultdict, Counter

class StatisticsAgent:
    def __init__(self):
        self.start_time = time.time()
        self.total_recognitions = 0
        self.total_commands = 0
        self.command_successes = 0
        self.confidence_scores = []

        # New: For word prediction
        self.word_pair_counts = defaultdict(Counter)

    def log_recognition(self, confidence=None, text=""):
        """Log a successful recognition and process its text for prediction model."""
        self.total_recognitions += 1
        if confidence is not None:
            self.confidence_scores.append(confidence)

        # Update word pair model
        words = re.findall(r'\b\w+\b', text.lower())
        if len(words) > 1:
            for i in range(len(words) - 1):
                current_word = words[i]
                next_word = words[i+1]
                self.word_pair_counts[current_word][next_word] += 1

    def log_command_execution(self, success: bool):
        """Log the result of a command execution."""
        self.total_commands += 1
        if success:
            self.command_successes += 1

    def get_predictions(self, word: str, limit=3):
        """Get the most likely next words based on the frequency model."""
        if not word:
            return []

        next_word_counts = self.word_pair_counts.get(word.lower())
        if not next_word_counts:
            return []

        return [word for word, count in next_word_counts.most_common(limit)]

    def get_stats(self):
        """Calculate and return a dictionary of current statistics."""
        uptime_seconds = time.time() - self.start_time
        avg_confidence = sum(self.confidence_scores) / len(self.confidence_scores) if self.confidence_scores else 0
        success_rate = (self.command_successes / self.total_commands * 100) if self.total_commands > 0 else 0

        return {
            "Session Uptime (s)": f"{uptime_seconds:.2f}",
            "Total Recognitions": self.total_recognitions,
            "Total Commands": self.total_commands,
            "Command Success %": f"{success_rate:.2f}",
            "Avg. Confidence": f"{avg_confidence:.2f}"
        }
