import vosk
import pyaudio
import json
import threading
import time
import audioop
from .logger import log_message

class ASREngine:
    def __init__(self, model_path, on_final_result, on_partial_result,
                 sample_rate=16000, buffer_size=4096):
        self.model_path = model_path
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

        self.recognizer = vosk.KaldiRecognizer(self.base_model, self.sample_rate)

        self.p_audio = pyaudio.PyAudio()
        self.stream = None
        self._is_listening = False

    def _audio_callback(self, in_data, frame_count, time_info, status):
        with self._lock:
            if not self._is_listening:
                return (in_data, pyaudio.paContinue)

            rms = audioop.rms(in_data, 2)

            if rms > self.silence_threshold:
                # Speech is detected
                self.speech_has_occurred = True
                self.silence_counter = 0

                self.recognizer.AcceptWaveform(in_data)
                partial_result = json.loads(self.recognizer.PartialResult())
                if partial_result.get("partial"):
                    self.on_partial_result(partial_result.get("partial"))
            else:
                # Silence is detected
                self.silence_counter += 1

            # If speech was happening and is now followed by a long pause, finalize.
            if self.speech_has_occurred and self.silence_counter > self.silence_chunks_needed:
                final_result_str = self.recognizer.FinalResult()
                result = json.loads(final_result_str)

                if result.get("text"):
                    # Don't add a period if the text is just a command
                    # This is a heuristic, a better way would be to check against cmd.json
                    if len(result.get("text").split()) > 2:
                         result['text'] += "."
                    self.on_final_result(result)

                # Reset for the next utterance
                self.recognizer.Reset()
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
                    self.recognizer.Reset()
