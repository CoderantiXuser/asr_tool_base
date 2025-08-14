import vosk
import pyaudio
import json
import os
import time
import subprocess
import argparse
from pynput.keyboard import Key
from hk_agent import HotkeyAgent
from logger import log_message, display_partial, clear_partial, overlay
from exec_agent import ExecutionAgent

# Configuration Constants
MODEL_BASE_PATH = "/usr/share/piper-tts-vosk-asr-models/vosk-models/"
DEFAULT_MODEL = "vosk-model-small-en-us-0.15"
SAMPLERATE = 16000
BUFFER_SIZE = 8192

def load_commands(file_path):
    """Load commands from cmd.json file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        log_message(f"Error: cmd.json not found at {file_path}", level="ERROR")
        return {}
    except json.JSONDecodeError:
        log_message(f"Error: Invalid JSON in {file_path}", level="ERROR")
        return {}



def process_command(text, commands, exec_agent):
    """Process recognized text for commands."""
    for phrase, actions in commands.items():
        if phrase.lower() in text.lower():
            log_message(f"Executing command: {phrase}")
            for action in actions:
                if isinstance(action, dict) and "type" in action and "value" in action:
                    exec_agent.execute_command_action(action["type"], action["value"])
                else:
                    log_message(f"Invalid command action format: {action}", level="ERROR")
            return True
    return False

def select_model():
    """Handle model selection via command line argument."""
    parser = argparse.ArgumentParser(description="Real-time voice transcriber with Vosk ASR.")
    parser.add_argument("-M", "--models-list", action="store_true", 
                       help="List available Vosk models and choose one.")
    args = parser.parse_args()
    
    model_path = os.path.join(MODEL_BASE_PATH, DEFAULT_MODEL)
    
    if args.models_list:
        available_models = [d for d in os.listdir(MODEL_BASE_PATH) 
                          if os.path.isdir(os.path.join(MODEL_BASE_PATH, d))]
        if not available_models:
            log_message(f"No Vosk models found in {MODEL_BASE_PATH}", level="ERROR")
            exit(1)

        log_message("Available Vosk models:")
        for i, model_name in enumerate(available_models):
            log_message(f"{i+1}. {model_name}")

        while True:
            try:
                choice = input("Enter the number of the model to load (or press Enter for default): ")
                if not choice:
                    log_message(f"Loading default model: {DEFAULT_MODEL}")
                    break
                choice_index = int(choice) - 1
                if 0 <= choice_index < len(available_models):
                    model_path = os.path.join(MODEL_BASE_PATH, available_models[choice_index])
                    log_message(f"Loading selected model: {available_models[choice_index]}")
                    break
                else:
                    log_message("Invalid choice. Please enter a valid number.", level="ERROR")
            except ValueError:
                log_message("Invalid input. Please enter a number.", level="ERROR")
    
    return model_path

def main():
    # Initialize components
    exec_agent = ExecutionAgent()
    
    # Load commands
    cmd_path = os.path.join(os.path.dirname(__file__), "cmd.json")
    commands = load_commands(cmd_path)
    
    # Select model
    model_path = select_model()
    
    # Ensure model path exists
    if not os.path.exists(model_path):
        log_message(f"Error: Vosk model not found at {model_path}", level="ERROR")
        log_message("Please download a Vosk model and extract it to the specified path.", level="ERROR")
        log_message("For example: https://alphacephei.com/vosk/models", level="ERROR")
        exit(1)

    # Load Vosk model and create recognizers
    base_model = vosk.Model(model_path)
    
    # Generate grammar from commands
    grammar_list = list(commands.keys())
    log_message(f"Generated command grammar: {grammar_list}")
    
    # Create recognizer instances
    default_recognizer = vosk.KaldiRecognizer(base_model, SAMPLERATE)
    command_recognizer = vosk.KaldiRecognizer(base_model, SAMPLERATE, json.dumps(grammar_list))
    current_recognizer = default_recognizer
    
    # PyAudio setup
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=SAMPLERATE,
                    input=True,
                    frames_per_buffer=BUFFER_SIZE)
    
    # Initialize Hotkey Agent and overlay
    hk_agent = HotkeyAgent()
    overlay.start()
    
    log_message("Vosk ASR initialized. Waiting for hotkey to start listening...")
    
    try:
        last_command_mode = False
        
        while not hk_agent.is_quit_requested():
            # Handle recognizer switching based on command mode
            command_mode_active = hk_agent.is_command_mode_active()
            listening_active = hk_agent.is_listening_active()
            typing_active = hk_agent.is_typing_active()
            
            if command_mode_active != last_command_mode:
                if command_mode_active:
                    current_recognizer = command_recognizer
                    log_message("Switched to Command Mode Recognizer", typing_active=typing_active, listening_active=listening_active)
                else:
                    current_recognizer = default_recognizer
                    log_message("Switched to Default Recognizer", typing_active=typing_active, listening_active=listening_active)
                current_recognizer.Reset()
                last_command_mode = command_mode_active
            
            # Read audio data
            data = stream.read(BUFFER_SIZE, exception_on_overflow=False)
            if len(data) == 0:
                time.sleep(0.01)
                continue
            
            if listening_active:
                if current_recognizer.AcceptWaveform(data):
                    # Final recognition result
                    result = json.loads(current_recognizer.Result())
                    text = result.get("text", "")
                    
                    if text:
                        clear_partial()
                        log_message(f"Recognized: {text}", typing_active=typing_active, listening_active=listening_active)
                        
                        # Handle typing mode
                        if typing_active and not command_mode_active:
                            exec_agent.keyboard_controller.type(text + " ")
                            log_message(f"[TYPING] {text}", typing_active=typing_active, listening_active=listening_active)
                        
                        # Handle command mode
                        if command_mode_active:
                            command_executed = process_command(text, commands, exec_agent)
                            if command_executed:
                                overlay.show_message(f"EXECUTED: {text}", color="green", duration=1.5)
                            else:
                                overlay.show_message(f"FAILED: {text}", color="red", duration=1.5)
                            
                            hk_agent.deactivate_command_mode()
                            hk_agent.reset_typing_mode()
                            current_recognizer.Reset()
                            time.sleep(0.1)
                else:
                    # Partial recognition result
                    partial_result = json.loads(current_recognizer.PartialResult())
                    partial_text = partial_result.get("partial", "")
                    
                    if partial_text:
                        if command_mode_active:
                            overlay.show_message(f"Command: {partial_text}", color="orange")
                        else:
                            display_partial(partial_text, typing_active=typing_active, listening_active=listening_active)
            else:
                # Not listening - clear display and reset
                clear_partial()
                current_recognizer.Reset()
                time.sleep(0.1)
    
    except KeyboardInterrupt:
        log_message("Exiting via KeyboardInterrupt...", typing_active=typing_active, listening_active=listening_active)
    finally:
        log_message("Cleaning up resources...", typing_active=typing_active, listening_active=listening_active)
        stream.stop_stream()
        stream.close()
        p.terminate()
        hk_agent.stop()
        overlay.stop()
        log_message("Application terminated.", typing_active=typing_active, listening_active=listening_active)

if __name__ == "__main__":
    main()
