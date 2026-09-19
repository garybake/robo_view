/** Bounded JPEG snapshot buffer: far smaller than retaining raw canvas frames. */
export class ReplayBuffer {
  constructor({ seconds = 8, fps = 10 } = {}) {
    this.maxFrames = seconds * fps;
    this.interval = 1000 / fps;
    this.frames = [];
    this.lastCapture = 0;
    this.capturePending = false;
  }

  capture(canvas, now) {
    if (this.capturePending || now - this.lastCapture < this.interval) return;
    this.lastCapture = now;
    this.capturePending = true;
    canvas.toBlob((blob) => {
      this.capturePending = false;
      if (!blob) return;
      this.frames.push(blob);
      while (this.frames.length > this.maxFrames) this.frames.shift();
    }, "image/jpeg", 0.76);
  }

  snapshot() { return [...this.frames]; }
}

export class PlaybackController {
  constructor(fps = 10) {
    this.interval = 1000 / fps;
    this.frames = [];
    this.current = null;
    this.index = 0;
    this.lastAdvance = 0;
    this.loading = false;
    this.generation = 0;
  }

  start(frames) {
    this.stop();
    this.frames = frames;
  }

  stop() {
    this.generation += 1;
    if (this.current) this.current.close();
    this.current = null;
    this.frames = [];
    this.index = 0;
    this.lastAdvance = 0;
    this.loading = false;
  }

  update(now) {
    if (!this.frames.length || this.loading || now - this.lastAdvance < this.interval) return;
    this.lastAdvance = now;
    this.loading = true;
    const generation = this.generation;
    const blob = this.frames[this.index];
    this.index = (this.index + 1) % this.frames.length;
    createImageBitmap(blob).then((bitmap) => {
      if (generation !== this.generation) {
        bitmap.close();
        return;
      }
      if (this.current) this.current.close();
      this.current = bitmap;
    }).catch(() => {
      // A corrupt snapshot should not stop subsequent playback frames.
    }).finally(() => {
      if (generation === this.generation) this.loading = false;
    });
  }

  get progress() { return this.frames.length ? this.index / this.frames.length : 0; }
}
