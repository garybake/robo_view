import { VoiceStressAnalyzer } from "./audio-analyzer.js";
import * as hud from "./hud.js";
import { PlaybackController, ReplayBuffer } from "./replay-buffer.js";
import { TemplateTracker } from "./tracker.js";
import { VoiceCommandListener } from "./voice-commands.js";

const STATES = Object.freeze({
  IDLE: "IDLE", GRID: "GRID", TARGET_WAIT: "TARGET_WAIT", TARGET: "TARGET",
  FOLLOW: "FOLLOW", STRESS: "STRESS", PLAYBACK: "PLAYBACK",
});

const pad = (value) => String(value).padStart(2, "0");
const formatClock = (date) => `${pad(date.getHours())}:${pad(date.getMinutes())}.${pad(date.getSeconds())}`;

class RoboViewApp {
  constructor() {
    this.video = document.querySelector("#camera");
    this.canvas = document.querySelector("#display");
    this.ctx = this.canvas.getContext("2d", { alpha: false, willReadFrequently: true });
    this.permissionPanel = document.querySelector("#permissionPanel");
    this.startupError = document.querySelector("#startupError");
    this.modeReadout = document.querySelector("#modeReadout");
    this.voiceReadout = document.querySelector("#voiceReadout");
    this.hardwareStatus = document.querySelector("#hardwareStatus");
    this.startButton = document.querySelector("#startButton");

    this.state = STATES.IDLE;
    this.running = false;
    this.lastHeard = "";
    this.lastTrackerUpdate = 0;
    this.lastStressUpdate = 0;
    this.tracker = new TemplateTracker();
    this.replay = new ReplayBuffer();
    this.playback = new PlaybackController();
    this.trail = [];
    this.smoothedCenter = null;
    this.stress = null;
    this.stream = null;

    this.voice = new VoiceCommandListener(
      (command) => this.handleCommand(command),
      (text) => { this.lastHeard = text; this.voiceReadout.textContent = text; },
    );
    this.bindEvents();
    this.drawOffline();
  }

  bindEvents() {
    this.startButton.addEventListener("click", () => this.start());
    document.querySelectorAll("[data-command]").forEach((button) => {
      button.addEventListener("click", () => this.handleCommand(button.dataset.command));
    });
    this.canvas.addEventListener("pointerdown", (event) => this.handlePointer(event));
    window.addEventListener("keydown", (event) => this.handleKey(event));
    window.addEventListener("pagehide", () => this.stop());
  }

  async start() {
    this.startButton.disabled = true;
    this.startupError.textContent = "";
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error("Camera access requires HTTPS or localhost.");
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } },
        audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false, autoGainControl: false },
      });
      this.video.srcObject = this.stream;
      await this.video.play();
      const trackSettings = this.stream.getVideoTracks()[0]?.getSettings();
      this.canvas.width = trackSettings?.width || this.video.videoWidth || 1280;
      this.canvas.height = trackSettings?.height || this.video.videoHeight || 720;

      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioContext();
      await this.audioContext.resume();
      this.stress = new VoiceStressAnalyzer(this.audioContext, this.stream);
      this.voice.start();
      this.running = true;
      this.permissionPanel.classList.add("hidden");
      this.hardwareStatus.textContent = this.voice.supported ? "CAM + MIC + VOICE ONLINE" : "CAM + MIC ONLINE // VOICE KEYS ONLY";
      this.hardwareStatus.classList.add("online");
      this.setState(STATES.IDLE);
      requestAnimationFrame((now) => this.frame(now));
    } catch (error) {
      this.stream?.getTracks().forEach((track) => track.stop());
      this.stream = null;
      this.startupError.textContent = error instanceof Error ? error.message : "Unable to initialize camera and microphone.";
      this.startButton.disabled = false;
    }
  }

  stop() {
    this.running = false;
    this.voice.stop();
    this.stress?.close();
    this.audioContext?.close();
    this.stream?.getTracks().forEach((track) => track.stop());
  }

  handleCommand(command) {
    if (!this.running) return;
    if (command !== "playback") this.playback.stop();
    if (command === "grid") this.setState(STATES.GRID);
    if (command === "target") this.setState(STATES.TARGET_WAIT);
    if (command === "follow") this.setState(this.tracker.active ? STATES.FOLLOW : STATES.TARGET_WAIT);
    if (command === "stress") this.setState(STATES.STRESS);
    if (command === "playback") {
      this.playback.start(this.replay.snapshot());
      this.setState(STATES.PLAYBACK);
    }
    if (command === "reset") {
      this.tracker.reset();
      this.playback.stop();
      this.trail = [];
      this.smoothedCenter = null;
      this.setState(STATES.IDLE);
    }
  }

  handleKey(event) {
    if (event.repeat || ["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName)) return;
    if (this.state === STATES.STRESS && ["1", "2"].includes(event.key)) {
      this.stress.activeSpeaker = Number(event.key);
      return;
    }
    const command = ({ g: "grid", t: "target", f: "follow", s: "stress", p: "playback", r: "reset" })[event.key.toLowerCase()];
    if (command) this.handleCommand(command);
  }

  handlePointer(event) {
    if (this.state !== STATES.TARGET_WAIT) return;
    const rect = this.canvas.getBoundingClientRect();
    const point = {
      x: (event.clientX - rect.left) * this.canvas.width / rect.width,
      y: (event.clientY - rect.top) * this.canvas.height / rect.height,
    };
    this.drawCamera();
    this.tracker.acquire(this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height), point);
    this.trail = [];
    this.smoothedCenter = null;
    this.setState(STATES.TARGET);
  }

  setState(state) {
    this.state = state;
    this.modeReadout.textContent = state;
    document.querySelectorAll("[data-command]").forEach((button) => {
      const mapsToState = state.startsWith(button.dataset.command.toUpperCase());
      button.classList.toggle("active", mapsToState);
    });
  }

  frame(now) {
    if (!this.running) return;
    if (this.state === STATES.PLAYBACK) this.renderPlayback(now);
    else {
      this.drawCamera();
      this.renderState(now);
      hud.drawBanner(this.ctx, this.canvas.width, this.canvas.height, `[${this.state}]  HEARD: ${this.lastHeard || "—"}`);
      this.replay.capture(this.canvas, now);
    }
    requestAnimationFrame((nextNow) => this.frame(nextNow));
  }

  drawCamera() {
    this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
  }

  renderState(now) {
    if (this.state === STATES.IDLE) hud.drawText(this.ctx, ["SYSTEM READY", "SAY ‘GRID’ TO BEGIN CALIBRATION"]);
    if (this.state === STATES.GRID) {
      hud.drawGrid(this.ctx, this.canvas.width, this.canvas.height);
      hud.drawText(this.ctx, ["TARGETING GRID // CALIBRATED"]);
    }
    if (this.state === STATES.TARGET_WAIT) hud.drawText(this.ctx, ["CLICK THE TARGET TO LOCK ON"], { color: hud.COLORS.amber });
    if ([STATES.TARGET, STATES.FOLLOW].includes(this.state)) this.renderTracking(now);
    if (this.state === STATES.STRESS) this.renderStress(now);
  }

  renderTracking(now) {
    if (now - this.lastTrackerUpdate > 66) {
      this.lastTrackerUpdate = now;
      const image = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
      this.trackingResult = this.tracker.update(image);
    }
    const result = this.trackingResult;
    if (!result?.ok) {
      hud.drawText(this.ctx, ["TARGET LOST — SAY ‘TARGET’ TO REACQUIRE"], { color: hud.COLORS.red });
      if (result) {
        this.tracker.reset();
        this.setState(STATES.TARGET_WAIT);
      }
      return;
    }
    if (this.state === STATES.FOLLOW) {
      this.smoothedCenter = this.smoothedCenter
        ? { x: this.smoothedCenter.x * 0.35 + result.center.x * 0.65, y: this.smoothedCenter.y * 0.35 + result.center.y * 0.65 }
        : result.center;
      this.trail.push({ ...this.smoothedCenter });
      if (this.trail.length > 20) this.trail.shift();
      this.ctx.save();
      this.ctx.strokeStyle = hud.COLORS.dim;
      this.ctx.beginPath();
      this.trail.forEach((point, index) => index ? this.ctx.lineTo(point.x, point.y) : this.ctx.moveTo(point.x, point.y));
      this.ctx.stroke();
      this.ctx.restore();
      hud.drawGrid(this.ctx, this.canvas.width, this.canvas.height, this.smoothedCenter);
    } else hud.drawGrid(this.ctx, this.canvas.width, this.canvas.height, result.center);
    hud.drawLockBrackets(this.ctx, result.bbox, `${this.state === STATES.FOLLOW ? "FOLLOWING" : "TARGET"} ${(result.confidence * 100).toFixed(0)}%`);
  }

  renderStress(now) {
    if (now - this.lastStressUpdate > 100) {
      this.lastStressUpdate = now;
      this.stressResults = this.stress.analyze();
    }
    hud.drawText(this.ctx, ["VOICE/STRESS", "PRESS 1 / 2 TO SELECT ACTIVE SPEAKER"]);
    const traceWidth = Math.min(340, this.canvas.width * 0.4);
    for (const [speaker, x] of [[1, 40], [2, this.canvas.width - traceWidth - 40]]) {
      const active = this.stress.activeSpeaker === speaker;
      const color = active ? hud.COLORS.green : hud.COLORS.dim;
      const result = this.stressResults?.[speaker];
      const label = `VOICE ${speaker}${active ? " (LISTENING)" : ""} — STRESS ${Math.round(result?.stress ?? 0)}%`;
      hud.drawWaveform(this.ctx, { x, y: this.canvas.height - 140, width: traceWidth, height: 100, waveform: result?.waveform, label, color });
    }
  }

  renderPlayback(now) {
    this.playback.update(now);
    this.drawCamera();
    hud.drawText(this.ctx, ["PLAYBACK — LAST 8 SECONDS"], { color: hud.COLORS.amber });

    const winWidth = Math.min(420, this.canvas.width * 0.4);
    const winHeight = winWidth * 9 / 16;
    const winX = this.canvas.width - winWidth - 30;
    const winY = 30;
    this.ctx.save();
    this.ctx.fillStyle = "#000";
    this.ctx.fillRect(winX, winY, winWidth, winHeight);
    if (this.playback.current) this.ctx.drawImage(this.playback.current, winX, winY, winWidth, winHeight);
    else hud.drawText(this.ctx, ["NOTHING BUFFERED YET"], { x: winX + 14, y: winY + winHeight / 2, size: 14, color: hud.COLORS.red });
    this.ctx.strokeStyle = hud.COLORS.green;
    this.ctx.lineWidth = 2;
    this.ctx.strokeRect(winX, winY, winWidth, winHeight);
    this.ctx.restore();

    hud.drawText(this.ctx, [formatClock(new Date())], { x: winX, y: winY + winHeight + 34, size: 26, gap: 0 });
    hud.drawBanner(this.ctx, this.canvas.width, this.canvas.height, `[PLAYBACK]  HEARD: ${this.lastHeard || "—"}`, hud.COLORS.amber);
  }

  drawOffline() {
    this.ctx.fillStyle = "#000";
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    hud.drawGrid(this.ctx, this.canvas.width, this.canvas.height);
  }
}

new RoboViewApp();
