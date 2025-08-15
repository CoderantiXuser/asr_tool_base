import json
import os
import time
import argparse
import sys
import re
import threading

from .hk_agent import HotkeyAgent
from .logger import log_message, status_display, console
from .overlay import overlay
from .exec_agent import ExecutionAgent
from .asr_engine import ASREngine
from .text_formatter import TextFormatter
from .dict_cmd_agent import DictationCommandAgent
from .stats_agent import StatisticsAgent
from rich.table import Table

def load_commands(file_path):
    # ... (no changes to this function)
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        log_message(f"Config not found: {file_path}", level="warning")
        return {}
    except json.JSONDecodeError:
        log_message(f"Invalid JSON: {file_path}", level="error")
        return {}

def select_model():
    # ... (no changes to this function)
    parser = argparse.ArgumentParser(description="Vosk ASR Tool.")
    parser.add_argument("-M", "--models-list", action="store_true", help="List and choose a Vosk model.")
    args = parser.parse_args()
    MODEL_BASE_PATH = "/usr/share/piper-tts-vosk-asr-models/vosk-models/"
    DEFAULT_MODEL = "vosk-model-small-en-us-0.15"
    model_path = os.path.join(MODEL_BASE_PATH, DEFAULT_MODEL)
    if args.models_list:
        try:
            available_models = [d for d in os.listdir(MODEL_BASE_PATH) if os.path.isdir(os.path.join(MODEL_BASE_PATH, d))]
            if not available_models:
                log_message(f"No Vosk models found in {MODEL_BASE_PATH}", level="error")
                sys.exit(1)
            console.print("\n[bold yellow]Available Vosk Models:[/bold yellow]")
            for i, model_name in enumerate(available_models):
                console.print(f"  [cyan]{i+1}[/cyan]. {model_name}")
            console.print(f"  [cyan]Enter[/cyan]. Use default ({DEFAULT_MODEL})")
            choice = input("\nEnter the number of the model to load: ")
            if choice.strip():
                choice_index = int(choice) - 1
                if 0 <= choice_index < len(available_models):
                    chosen_model = available_models[choice_index]
                    model_path = os.path.join(MODEL_BASE_PATH, chosen_model)
                    log_message(f"Loading selected model: {chosen_model}")
        except (ValueError, IndexError):
            log_message("Invalid selection. Using default model.", level="warning")
    if not os.path.exists(model_path):
        log_message(f"Model not found at {model_path}", level="critical")
        sys.exit(1)
    return model_path

class Application:
    def __init__(self):
        self._quit_event = threading.Event()
        self.exec_agent = ExecutionAgent()
        self.hk_agent = HotkeyAgent(self) # Pass app instance to agent
        self.text_formatter = TextFormatter()
        self.dict_cmd_agent = DictationCommandAgent()
        self.stats_agent = StatisticsAgent()

        cmd_path = os.path.join(os.path.dirname(__file__), "cmd.json")
        self.commands = load_commands(cmd_path)
        model_path = select_model()

        self.asr_engine = ASREngine(
            model_path=model_path,
            on_final_result=self._on_final_result, on_partial_result=self._on_partial_result
        )
        status_display.start()
        overlay.start()
        log_message("Application initialized.")
        self.update_status() # Initial status update

    def _on_partial_result(self, partial_text):
        last_word = re.findall(r'\b\w+\b', partial_text)[-1] if partial_text else ""
        predictions = self.stats_agent.get_predictions(last_word)
        status_display.update(partial_text=partial_text, predictions=predictions)

    def _calculate_confidence(self, result: dict) -> float:
        """Calculates the average confidence from a Vosk result dictionary."""
        if 'result' not in result or not result['result']:
            return 0.0

        word_confidences = [item['conf'] for item in result['result']]
        return sum(word_confidences) / len(word_confidences)

    def _on_final_result(self, result):
        text = result.get("text", "")
        if not text: return

        confidence = self._calculate_confidence(result)

        status_display.update(partial_text=f"[bold green]✓[/] {text}", predictions=[])
        log_message(f"Recognized (conf: {confidence:.2f}): {text}")
        self.stats_agent.log_recognition(confidence=confidence, text=text)

        if self.hk_agent.is_command_mode_active():
            command_executed = self._process_command(text)
            self.stats_agent.log_command_execution(success=command_executed)
            overlay.show_message(f"EXECUTED: {text}" if command_executed else f"FAILED: {text}",
                                 color="green" if command_executed else "red", duration=1.5)
            self.hk_agent.deactivate_command_mode()
            self.hk_agent.reset_typing_mode()
            # Manually update the UI to reflect the state change,
            # ensuring not to call back into the ASR engine from this thread.
            status_text = self._get_status_text()
            status_display.update(status_text=status_text)
        elif self.hk_agent.is_typing_active():
            remaining_text, action = self.dict_cmd_agent.process(text)
            if action:
                self.exec_agent.execute_command_action(action["type"], action["value"])
            formatted_text = self.text_formatter.format(remaining_text)
            if formatted_text:
                self.exec_agent.keyboard_controller.type(formatted_text + " ")
                log_message(f"Typed: {formatted_text}", level="debug")

    def _process_command(self, text):
        # Use exact matching for commands to avoid false positives
        command_text = text.lower().strip()
        if command_text in self.commands:
            actions = self.commands[command_text]
            log_message(f"Executing command: {command_text}")
            for action in actions:
                self.exec_agent.execute_command_action(action["type"], action["value"])
            return True
        return False

    def show_session_stats(self):
        stats = self.stats_agent.get_stats()
        table = Table(title="[bold blue]Session Statistics[/bold blue]")
        table.add_column("Metric", justify="right", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        for key, value in stats.items():
            table.add_row(key, str(value))
        console.print(table)

    def _get_status_text(self):
        listen_status = "[bold green]ON[/]" if self.hk_agent.is_listening_active() else "[bold red]OFF[/]"
        type_status = "[bold green]ON[/]" if self.hk_agent.is_typing_active() else "[bold red]OFF[/]"
        mode = "[bold orange]CMD[/]" if self.hk_agent.is_command_mode_active() else "[cyan]DICTATE[/]"
        return f"Listening: {listen_status}\nTyping:    {type_status}\nMode:      {mode}"

    def update_status(self):
        """Called by HotkeyAgent to update UI and ASR engine state."""
        self.asr_engine.set_listening(self.hk_agent.is_listening_active())
        # self.asr_engine.set_command_mode(self.hk_agent.is_command_mode_active()) # This was commented out to fix a bug
        status_text = self._get_status_text()
        status_display.update(status_text=status_text)

    def run(self):
        self.asr_engine.start()
        self._quit_event.wait() # Wait here until quit is requested

    def request_quit(self):
        """Signals the application to start shutting down."""
        self._quit_event.set()

    def request_emergency_quit(self):
        """Immediately terminates the application."""
        os._exit(1)

    def cleanup(self):
        log_message("Cleaning up resources...")
        status_display.stop()
        self.asr_engine.stop()
        self.hk_agent.stop()
        overlay.stop()
        log_message("Application terminated.")

def main():
    app = None
    try:
        app = Application()
        app.run()
    except KeyboardInterrupt:
        log_message("Exiting via KeyboardInterrupt...")
        app.request_quit()
    except Exception as e:
        log_message(f"An unexpected error occurred: {e}", level="critical")
    finally:
        if app:
            app.cleanup()

if __name__ == "__main__":
    main()
