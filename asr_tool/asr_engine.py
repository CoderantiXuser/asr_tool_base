import vosk
import pyaudio
import json
import threading
import time
import audioop
from .logger import log_message

class ASREngine(threading.Thread):
    def __init__(self, model_path, grammar_list, on_final_result, on_partial_result,
                 sample_rate=16000, buffer_size=4096): # Smaller buffer for better responsiveness
        super().__init__(daemon=True)
        self.model_path = model_path
        self.grammar_list = grammar_list
        self.on_final_result = on_final_result
        self.on_partial_result = on_partial_result
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size

        # --- Punctuation PoC Parameters ---
        self.silence_threshold = 500  # RMS threshold for silence
        self.silence_duration_s = 1.2 # Seconds of silence to trigger punctuation
        self.chunks_per_second = self.sample_rate / self.buffer_size
        self.silence_chunks_needed = int(self.silence_duration_s * self.chunks_per_second)

        try:
            self.base_model = vosk.Model(self.model_path)
        except Exception as e:
            log_message(f"Failed to load Vosk model: {e}", level="critical")
            raise

        self.default_recognizer = vosk.KaldiRecognizer(self.base_model, self.sample_rate)
        self.command_recognizer = vosk.KaldiRecognizer(self.base_model, self.sample_rate, json.dumps(self.grammar_list))
        self.current_recognizer = self.default_recognizer

        self.p_audio = pyaudio.PyAudio()
        self.stream = self.p_audio.open(format=pyaudio.paInt16, channels=1, rate=self.sample_rate, input=True, frames_per_buffer=self.buffer_size)

        self._is_running = False
        self._is_listening = False
        self._is_command_mode = False

    def run(self):
        self._is_running = True
        self.stream.start_stream()
        log_message("ASR Engine thread started.")

        silence_counter = 0
        speech_has_occurred = False

        while self._is_running:
            data = self.stream.read(self.buffer_size, exception_on_overflow=False)
            if not self._is_running: break

            if self._is_listening:
                rms = audioop.rms(data, 2) # 2 is for paInt16

                if rms > self.silence_threshold:
                    # Speech detected
                    speech_has_occurred = True
                    silence_counter = 0
                    if self.current_recognizer.AcceptWaveform(data):
                        result = json.loads(self.current_recognizer.Result())
                        if result.get("text"): self.on_final_result(result)
                    else:
                        partial_result = json.loads(self.current_recognizer.PartialResult())
                        if partial_result.get("partial"): self.on_partial_result(partial_result.get("partial"))
                else:
                    # Silence detected
                    silence_counter += 1

                if speech_has_occurred and silence_counter > self.silence_chunks_needed:
                    # Long pause after speech, finalize with punctuation
                    final_result_str = self.current_recognizer.FinalResult()
                    result = json.loads(final_result_str)

                    if result.get("text"):
                        result['text'] += "." # Add the period
                        log_message("Auto-punctuation triggered.", level="debug")
                        self.on_final_result(result)

                    # Reset for next utterance
                    self.current_recognizer.Reset()
                    speech_has_occurred = False
                    silence_counter = 0
            else:
                time.sleep(0.1)

    def set_listening(self, listening):
        if self._is_listening != listening:
            self._is_listening = listening
            if not listening:
                self.current_recognizer.Reset() # Reset on stop listening

    def set_command_mode(self, command_mode):
        if self._is_command_mode != command_mode:
            self._is_command_mode = command_mode
            self.current_recognizer = self.command_recognizer if command_mode else self.default_recognizer
            self.current_recognizer.Reset()

    def stop(self):
        log_message("Stopping ASR Engine thread...")
        self._is_running = False
        time.sleep(0.2)
        if self.stream.is_active():
            self.stream.stop_stream()
            self.stream.close()
        self.p_audio.terminate()
        log_message("ASR Engine resources cleaned up.")
