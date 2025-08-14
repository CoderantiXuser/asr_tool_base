import vosk
import pyaudio
import json
import threading
import time
import audioop
from .logger import log_message

class ASREngine:
    def __init__(self, model_path, grammar_list, on_final_result, on_partial_result,
                 sample_rate=16000, buffer_size=4096):
        self.model_path = model_path
        self.grammar_list = grammar_list
        self.on_final_result = on_final_result
        self.on_partial_result = on_partial_result
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size

        self.silence_threshold = 500
        self.silence_duration_s = 1.2
        self.chunks_per_second = self.sample_rate / self.buffer_size
        self.silence_chunks_needed = int(self.silence_duration_s * self.chunks_per_second)

        self._lock = threading.Lock()
        self.silence_counter = 0
        self.speech_has_occurred = False

        try:
            self.base_model = vosk.Model(self.model_path)
        except Exception as e:
            log_message(f"Failed to load Vosk model: {e}", level="critical")
            raise

        self.default_recognizer = vosk.KaldiRecognizer(self.base_model, self.sample_rate)
        self.command_recognizer = vosk.KaldiRecognizer(self.base_model, self.sample_rate, json.dumps(self.grammar_list))
        self.current_recognizer = self.default_recognizer

        self.p_audio = pyaudio.PyAudio()
        self.stream = None

        self._is_listening = False
        self._is_command_mode = False

    def _audio_callback(self, in_data, frame_count, time_info, status):
        with self._lock:
            if not self._is_listening:
                return (in_data, pyaudio.paContinue)

            rms = audioop.rms(in_data, 2)
            if rms > self.silence_threshold:
                self.speech_has_occurred = True
                self.silence_counter = 0
                if self.current_recognizer.AcceptWaveform(in_data):
                    result = json.loads(self.current_recognizer.Result())
                    if result.get("text"): self.on_final_result(result)
                else:
                    partial_result = json.loads(self.current_recognizer.PartialResult())
                    if partial_result.get("partial"): self.on_partial_result(partial_result.get("partial"))
            else:
                self.silence_counter += 1

            if self.speech_has_occurred and self.silence_counter > self.silence_chunks_needed:
                final_result_str = self.current_recognizer.FinalResult()
                result = json.loads(final_result_str)
                if result.get("text"):
                    result['text'] += "."
                    self.on_final_result(result)
                self.current_recognizer.Reset()
                self.speech_has_occurred = False
                self.silence_counter = 0

        return (in_data, pyaudio.paContinue)

    def start(self):
        self.stream = self.p_audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.buffer_size,
            stream_callback=self._audio_callback
        )
        self.stream.start_stream()
        log_message("ASR Engine started in callback mode.")

    def stop(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p_audio.terminate()
        log_message("ASR Engine resources cleaned up.")

    def set_listening(self, listening):
        with self._lock:
            if self._is_listening != listening:
                self._is_listening = listening
                if not listening:
                    self.current_recognizer.Reset()

    def set_command_mode(self, command_mode):
        with self._lock:
            if self._is_command_mode != command_mode:
                self._is_command_mode = command_mode
                self.current_recognizer = self.command_recognizer if command_mode else self.default_recognizer
                self.current_recognizer.Reset()
