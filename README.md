# ASR Tool - Advanced Voice Control and Dictation

## Overview

This is a sophisticated, feature-rich voice control and dictation tool for your desktop. It uses the Vosk ASR engine to provide real-time speech-to-text and then processes the results through a powerful pipeline for dictation, command execution, and text formatting. The tool is highly configurable and designed to be an efficient hands-free interface for your computer.

## Features

### Core Functionality
- **Real-time Voice Recognition:** High-performance, low-latency transcription powered by Vosk.
- **Dual Modes:**
    - **Dictation Mode:** For general-purpose dictation with advanced formatting.
    - **Command Mode:** For executing a wide range of system and application commands.
- **Advanced Hotkey System:**
    - `Double Left Ctrl`: Toggle listening on/off.
    - `Double Left Alt`: Toggle typing on/off.
    - `Right Ctrl`: Toggle Command Mode.
    - `Right Alt` (Hold): "Quick Dictation" (listens and types only while held).
    - `Double Esc`: Quit the application gracefully.
    - `Triple Esc`: Emergency stop (immediate termination).
    - `Triple Shift`: Show session statistics in the console.

### Text Processing & Formatting
- **Smart Formatting Pipeline:** A sequence of rules automatically cleans up transcribed text.
- **Custom Corrections:** Define your own corrections for common misrecognitions (e.g., "jules" -> "Jules") in `corrections.json`.
- **Abbreviation Expansion:** Expand spoken abbreviations (e.g., "btw" -> "by the way") via `abbreviations.json`.
- **Number Conversion:** Converts spoken numbers to digits (e.g., "one hundred" -> "100").
- **Intelligent Capitalization:** Automatically capitalizes the pronoun "I" and the start of sentences.
- **Automatic Punctuation (Proof of Concept):** Automatically adds a period after a long pause in speech.
- **Special Pattern Formatting:** Recognizes and formats spoken emails ("name at domain dot com") and URLs.
- **Spacing Cleanup:** Automatically fixes spacing around punctuation marks.

### Command & Action Execution
- **System Commands:** Execute commands from a predefined list in `cmd.json`. This includes:
    - Launching applications.
    - Executing shell commands.
    - Simulating key presses and combinations (e.g., `Ctrl+S`).
    - **Mouse Control:** Perform left clicks, right clicks, double clicks, and scrolling.
    - **Media Control:** Control system volume and media playback (play/pause, next track).
- **Dictation Commands:** Execute commands *during* dictation without switching modes (e.g., "scratch that" to undo, "slap" to press Enter). Configured in `dict_cmds_config.json`.

### User Interface & Logging
- **Rich Console Interface:** A modern, live-updating console display (powered by `rich`) shows real-time status (listening, typing, mode), partial recognition results, and word predictions.
- **Smart Overlay System:** A semi-transparent, on-screen overlay provides instant feedback for important events like mode changes and command execution.
    - **Themable:** Change the look with "light", "dark", and "colorful" themes.
    - **Positionable:** Move the overlay to the "top", "bottom", or "center" of the screen.
    - **Animated:** Features smooth fade-in and fade-out effects.

### Intelligence & Analytics
- **Performance Tracking:** The application tracks session statistics like recognition confidence and command success rate.
- **Word Prediction:** A basic word prediction model learns from your speech and suggests likely next words in the console UI.
- **Memory Management:** The prediction model has a built-in cap to prevent it from consuming excessive memory over long sessions.

## Setup & Installation

1.  **Python:** Ensure you have Python 3 installed.

2.  **Vosk Models:** This tool requires Vosk ASR models to function.
    - Download a model from the [Vosk Model Page](https://alphacephei.com/vosk/models). The lightweight `vosk-model-small-en-us-0.15` is a good starting point.
    - Extract the model folder and place it in `/usr/share/piper-tts-vosk-asr-models/`. The final path should look like `/usr/share/piper-tts-vosk-asr-models/vosk-models/vosk-model-small-en-us-0.15`.

3.  **Python Dependencies:**
    - Install all required packages using the `requirements.txt` file:
      ```bash
      pip install -r requirements.txt
      ```
    - **Linux Note:** The UI overlay uses `tkinter`. If it's not installed on your system, you may need to install it via your package manager (e.g., `sudo apt-get install python3-tk` on Debian/Ubuntu).

## Usage

- **To run the application:**
  ```bash
  python -m asr_tool.main
  ```
- **To select a different model on startup:**
  - Use the `-M` or `--models-list` flag to see a list of your installed models and choose one interactively.
  - ```bash
    python -m asr_tool.main -M
    ```

## Configuration

All configuration is done via the `.json` files in the `asr_tool/` directory. You can edit these files to customize the tool's behavior.

- **`cmd.json`:** Defines the commands available in "Command Mode". The key is the spoken phrase, and the value is a list of actions for the `ExecutionAgent` to perform.
- **`dict_cmds_config.json`:** Defines the in-line commands available during dictation.
- **`corrections.json`:** A simple dictionary for correcting common speech-to-text errors.
- **`abbreviations.json`:** A simple dictionary for expanding spoken abbreviations.
