"""Offline keyword spotting over the live mic feed using Vosk.

Rather than locking Vosk to a rigid grammar, we let it recognize free
speech and just substring-match the running transcript against our small
command vocabulary. That's more forgiving of "okay, give me a grid" style
phrasing than a closed grammar would be.
"""

import json
import queue
import time

import vosk

from . import config as cfg

vosk.SetLogLevel(-1)  # quiet, we don't want Kaldi's log spam on stdout


class VoiceCommandListener:
    def __init__(self, audio_hub, model_path=cfg.MODEL_DIR):
        if not model_path.exists():
            raise FileNotFoundError(
                f"Vosk model not found at {model_path}. Run scripts/download_model.py first."
            )
        self._model = vosk.Model(str(model_path))
        grammar = json.dumps([" ".join(cfg.VOICE_GRAMMAR_WORDS), "[unk]"])
        self._rec = vosk.KaldiRecognizer(self._model, cfg.SAMPLE_RATE, grammar)
        self._rec.SetWords(False)

        self.commands = queue.Queue()
        self._last_fired = {}
        self._last_partial_text = ""

        audio_hub.subscribe(self._on_audio_block)

    def _on_audio_block(self, block):
        data = block.tobytes()
        if self._rec.AcceptWaveform(data):
            text = json.loads(self._rec.Result()).get("text", "")
            self._check(text, final=True)
        else:
            partial = json.loads(self._rec.PartialResult()).get("partial", "")
            if partial != self._last_partial_text:
                self._last_partial_text = partial
                self._check(partial, final=False)

    def _check(self, text, final):
        if not text:
            return
        now = time.monotonic()
        for command, keywords in cfg.VOICE_COMMANDS.items():
            if any(kw in text for kw in keywords):
                last = self._last_fired.get(command, 0)
                if now - last >= cfg.COMMAND_COOLDOWN_SECONDS:
                    self._last_fired[command] = now
                    self.commands.put((command, text))

    def poll(self):
        """Non-blocking: returns (command, heard_text) or None."""
        try:
            return self.commands.get_nowait()
        except queue.Empty:
            return None
