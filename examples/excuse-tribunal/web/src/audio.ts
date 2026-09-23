// Courtroom audio: no files, just oscillators.

let audio: AudioContext | null = null;
let enabled: () => boolean = () => true;

/** Sound follows a checkbox, read at the moment each tone would play. */
export function bindSoundSwitch(box: HTMLInputElement): void {
  enabled = () => box.checked;
}

function context(): AudioContext {
  // Created lazily: browsers only allow audio after the first user gesture.
  if (!audio) {
    const Ctor =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    audio = new Ctor();
  }
  return audio;
}

function tone(freq: number, duration: number, type: OscillatorType = "sine", gain = 0.08, slideTo?: number): void {
  if (!enabled()) return;
  const ac = context();
  const osc = ac.createOscillator();
  const vol = ac.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, ac.currentTime);
  if (slideTo) osc.frequency.exponentialRampToValueAtTime(slideTo, ac.currentTime + duration);
  vol.gain.setValueAtTime(gain, ac.currentTime);
  vol.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + duration);
  osc.connect(vol).connect(ac.destination);
  osc.start();
  osc.stop(ac.currentTime + duration);
}

export const keyClick = (): void => tone(1800 + Math.random() * 400, 0.03, "square", 0.02);

export function thud(): void {
  tone(180, 0.22, "triangle", 0.22, 40);
  tone(90, 0.3, "sine", 0.18, 30);
}

export function ding(): void {
  tone(1320, 0.5, "sine", 0.06);
  tone(1980, 0.4, "sine", 0.03);
}
