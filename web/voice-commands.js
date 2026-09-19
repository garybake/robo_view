const KEYWORDS = {
  grid: ["grid", "great"],
  target: ["target"],
  follow: ["follow"],
  stress: ["stress", "voice stress"],
  playback: ["playback", "play back"],
  reset: ["reset", "stand down"],
};

export function commandFromText(text) {
  const normalized = text.toLowerCase().trim();
  return Object.entries(KEYWORDS).find(([, words]) => words.some((word) => normalized.includes(word)))?.[0] ?? null;
}

export class VoiceCommandListener {
  constructor(onCommand, onTranscript) {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.supported = Boolean(Recognition);
    this.running = false;
    this.onCommand = onCommand;
    this.onTranscript = onTranscript;
    this.lastFired = new Map();
    if (!Recognition) return;

    this.recognition = new Recognition();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = "en-US";

    this.recognition.onresult = (event) => {
      const result = event.results[event.results.length - 1];
      const text = result[0]?.transcript?.trim() ?? "";
      if (!text) return;
      this.onTranscript(text);
      const command = commandFromText(text);
      const now = performance.now();
      if (command && now - (this.lastFired.get(command) ?? 0) > 1500) {
        this.lastFired.set(command, now);
        this.onCommand(command);
      }
    };
    this.recognition.onend = () => {
      if (this.running) window.setTimeout(() => this.#tryStart(), 250);
    };
    this.recognition.onerror = (event) => {
      if (["not-allowed", "service-not-allowed"].includes(event.error)) this.running = false;
    };
  }

  start() {
    if (!this.supported) return;
    this.running = true;
    this.#tryStart();
  }

  stop() {
    this.running = false;
    if (this.recognition) this.recognition.stop();
  }

  #tryStart() {
    try { this.recognition.start(); } catch { /* Already active. */ }
  }
}
