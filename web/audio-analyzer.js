const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

/** Measures pitch stability from the local microphone. It is not a lie detector. */
export class VoiceStressAnalyzer {
  constructor(audioContext, stream) {
    this.context = audioContext;
    this.source = audioContext.createMediaStreamSource(stream);
    this.analyser = audioContext.createAnalyser();
    this.analyser.fftSize = 4096;
    this.analyser.smoothingTimeConstant = 0;
    this.source.connect(this.analyser);
    this.samples = new Float32Array(this.analyser.fftSize);
    this.activeSpeaker = 1;
    this.results = { 1: null, 2: null };
  }

  analyze() {
    this.analyser.getFloatTimeDomainData(this.samples);
    const result = analyzeVoice(this.samples, this.context.sampleRate);
    if (result) this.results[this.activeSpeaker] = result;
    return this.results;
  }

  close() {
    this.source.disconnect();
    this.analyser.disconnect();
  }
}

export function analyzeVoice(samples, sampleRate) {
  let energy = 0;
  for (const sample of samples) energy += sample * sample;
  const rms = Math.sqrt(energy / samples.length);
  if (rms < 0.008) return null;

  const minLag = Math.floor(sampleRate / 500);
  const maxLag = Math.min(Math.floor(sampleRate / 75), Math.floor(samples.length / 2));
  const correlations = [];
  for (let lag = minLag; lag <= maxLag; lag += 1) {
    let sum = 0;
    let leftEnergy = 0;
    let rightEnergy = 0;
    for (let i = 0; i < samples.length - lag; i += 2) {
      sum += samples[i] * samples[i + lag];
      leftEnergy += samples[i] * samples[i];
      rightEnergy += samples[i + lag] * samples[i + lag];
    }
    correlations.push(sum / Math.max(Math.sqrt(leftEnergy * rightEnergy), 1e-9));
  }
  let peakIndex = 1;
  for (let i = 2; i < correlations.length - 1; i += 1) {
    if (correlations[i] > correlations[peakIndex]) peakIndex = i;
  }
  const peak = correlations[peakIndex];
  if (peak < 0.2) return null;

  const lag = minLag + peakIndex;
  const f0 = sampleRate / lag;
  const periods = collectPeriods(samples, lag);
  if (periods.length < 3) return null;

  const periodMean = mean(periods.map((period) => period.length));
  const jitter = meanAdjacentDifference(periods.map((period) => period.length)) / periodMean;
  const amplitudes = periods.map((period) => period.amplitude);
  const shimmer = meanAdjacentDifference(amplitudes) / Math.max(mean(amplitudes), 1e-6);
  const stress = clamp(jitter / 0.035, 0, 1) * 42 + clamp(shimmer / 0.18, 0, 1) * 38 + clamp(rms / 0.2, 0, 1) * 20;
  return { f0, jitter, shimmer, stress };
}

function collectPeriods(samples, expectedLag) {
  const crossings = [];
  for (let i = 1; i < samples.length; i += 1) {
    if (samples[i - 1] <= 0 && samples[i] > 0) {
      if (!crossings.length || i - crossings.at(-1) > expectedLag * 0.55) crossings.push(i);
    }
  }
  const periods = [];
  for (let i = 1; i < crossings.length; i += 1) {
    const start = crossings[i - 1];
    const end = crossings[i];
    const length = end - start;
    if (length < expectedLag * 0.55 || length > expectedLag * 1.7) continue;
    let low = 1;
    let high = -1;
    for (let j = start; j < end; j += 1) {
      low = Math.min(low, samples[j]);
      high = Math.max(high, samples[j]);
    }
    periods.push({ length, amplitude: high - low });
  }
  return periods;
}

const mean = (values) => values.reduce((total, value) => total + value, 0) / Math.max(values.length, 1);

function meanAdjacentDifference(values) {
  if (values.length < 2) return 0;
  let total = 0;
  for (let i = 1; i < values.length; i += 1) total += Math.abs(values[i] - values[i - 1]);
  return total / (values.length - 1);
}
