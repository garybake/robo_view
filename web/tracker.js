const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

/** Lightweight local template tracker for an arbitrary click-selected region. */
export class TemplateTracker {
  constructor({ boxSize = 90, sampleSize = 24, searchRadius = 32 } = {}) {
    this.boxSize = boxSize;
    this.sampleSize = sampleSize;
    this.searchRadius = searchRadius;
    this.reset();
  }

  get active() { return this.template !== null; }

  reset() {
    this.template = null;
    this.bbox = null;
    this.confidence = 0;
  }

  acquire(imageData, point) {
    const size = Math.min(this.boxSize, imageData.width, imageData.height);
    const x = clamp(Math.round(point.x - size / 2), 0, imageData.width - size);
    const y = clamp(Math.round(point.y - size / 2), 0, imageData.height - size);
    this.bbox = { x, y, width: size, height: size };
    this.template = this.#sample(imageData, this.bbox);
    this.confidence = 1;
    return this.bbox;
  }

  update(imageData) {
    if (!this.active) return { ok: false, bbox: null, center: null, confidence: 0 };

    const step = 4;
    const origin = this.bbox;
    let bestScore = Number.POSITIVE_INFINITY;
    let bestBox = origin;

    for (let dy = -this.searchRadius; dy <= this.searchRadius; dy += step) {
      for (let dx = -this.searchRadius; dx <= this.searchRadius; dx += step) {
        const candidate = {
          x: clamp(origin.x + dx, 0, imageData.width - origin.width),
          y: clamp(origin.y + dy, 0, imageData.height - origin.height),
          width: origin.width,
          height: origin.height,
        };
        const score = this.#differenceFromImage(this.template, imageData, candidate);
        if (score < bestScore) {
          bestScore = score;
          bestBox = candidate;
        }
      }
    }

    this.confidence = clamp(1 - bestScore / 90, 0, 1);
    if (this.confidence < 0.2) {
      return { ok: false, bbox: this.bbox, center: null, confidence: this.confidence };
    }

    this.bbox = bestBox;
    const observed = this.#sample(imageData, bestBox);
    if (this.confidence > 0.58) {
      for (let i = 0; i < this.template.length; i += 1) {
        this.template[i] = this.template[i] * 0.96 + observed[i] * 0.04;
      }
    }
    return {
      ok: true,
      bbox: bestBox,
      center: { x: bestBox.x + bestBox.width / 2, y: bestBox.y + bestBox.height / 2 },
      confidence: this.confidence,
    };
  }

  #sample(imageData, box) {
    const result = new Float32Array(this.sampleSize * this.sampleSize);
    const pixels = imageData.data;
    let outputIndex = 0;
    for (let sy = 0; sy < this.sampleSize; sy += 1) {
      const y = clamp(Math.floor(box.y + (sy + 0.5) * box.height / this.sampleSize), 0, imageData.height - 1);
      for (let sx = 0; sx < this.sampleSize; sx += 1) {
        const x = clamp(Math.floor(box.x + (sx + 0.5) * box.width / this.sampleSize), 0, imageData.width - 1);
        const index = (y * imageData.width + x) * 4;
        result[outputIndex] = pixels[index] * 0.299 + pixels[index + 1] * 0.587 + pixels[index + 2] * 0.114;
        outputIndex += 1;
      }
    }
    return result;
  }

  #differenceFromImage(template, imageData, box) {
    let total = 0;
    let templateIndex = 0;
    const pixels = imageData.data;
    for (let sy = 0; sy < this.sampleSize; sy += 1) {
      const y = clamp(Math.floor(box.y + (sy + 0.5) * box.height / this.sampleSize), 0, imageData.height - 1);
      for (let sx = 0; sx < this.sampleSize; sx += 1) {
        const x = clamp(Math.floor(box.x + (sx + 0.5) * box.width / this.sampleSize), 0, imageData.width - 1);
        const index = (y * imageData.width + x) * 4;
        const luminance = pixels[index] * 0.299 + pixels[index + 1] * 0.587 + pixels[index + 2] * 0.114;
        total += Math.abs(template[templateIndex] - luminance);
        templateIndex += 1;
      }
    }
    return total / template.length;
  }
}
