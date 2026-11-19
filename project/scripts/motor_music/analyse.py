"""
The motors' pitch at each calibration step, from the mic recording.

    python3 analyse.py <run folder>

Reads calib.wav, recording.json (when the recording started, wall clock) and
steps.json (throttle stick value, start and end, wall clock), and writes
pitch.json: for each step the strongest peaks, and an estimate of the
fundamental (harmonic product spectrum, which finds the pitch the ear hears
even when a harmonic is louder). The player interpolates between the steps'
fundamentals. Needs numpy (the dev container has it).
"""
import json
import os
import sys
import wave

import numpy as np

LOW_HZ, HIGH_HZ = 80.0, 6000.0
SETTLE_S = 0.6     # spin-up at the start of each step, not measured


def read_wav(path):
    with wave.open(path) as w:
        rate = w.getframerate()
        raw = w.readframes(w.getnframes())
        channels = w.getnchannels()
        width = w.getsampwidth()
    dtype = {2: np.int16, 4: np.int32}[width]
    x = np.frombuffer(raw, dtype=dtype).astype(np.float64)
    if channels > 1:
        x = x.reshape(-1, channels).mean(axis=1)
    return x, rate


def spectrum(x, rate):
    """Averaged magnitude spectrum of 0.5 s windows (Hann, half overlap)."""
    n = int(0.5 * rate)
    if len(x) < n:
        raise ValueError('step too short to measure')
    window = np.hanning(n)
    frames = [x[i:i + n] * window for i in range(0, len(x) - n + 1, n // 2)]
    mag = np.mean([np.abs(np.fft.rfft(f)) for f in frames], axis=0)
    return np.fft.rfftfreq(n, 1.0 / rate), mag


def peaks(freqs, mag, count=5):
    band = (freqs >= LOW_HZ) & (freqs <= HIGH_HZ)
    idx = np.where(band)[0]
    local = [i for i in idx[1:-1] if mag[i] > mag[i - 1] and mag[i] >= mag[i + 1]]
    local.sort(key=lambda i: mag[i], reverse=True)
    top = mag[local[0]] if local else 1.0
    return [{'hz': round(float(freqs[i]), 1), 'level': round(float(mag[i] / top), 3)}
            for i in local[:count]]


def fundamental(freqs, mag, harmonics=4):
    """Harmonic product spectrum: the frequency whose multiples are all loud."""
    hps = np.log(mag + 1e-9)
    for h in range(2, harmonics + 1):
        down = mag[::h]
        hps[:len(down)] += np.log(down + 1e-9)
    band = (freqs >= LOW_HZ) & (freqs <= HIGH_HZ / harmonics)
    i = np.argmax(np.where(band, hps, -np.inf))
    return round(float(freqs[i]), 1)


def main():
    run = sys.argv[1]
    x, rate = read_wav(os.path.join(run, 'calib.wav'))
    with open(os.path.join(run, 'steps.json')) as f:
        steps = json.load(f)
    with open(os.path.join(run, 'recording.json')) as f:
        rec_start = json.load(f)['start_epoch']
    out = []
    for s in steps:
        a = int((s['start_epoch'] - rec_start + SETTLE_S) * rate)
        b = int((s['end_epoch'] - rec_start) * rate)
        freqs, mag = spectrum(x[a:b], rate)
        row = {'value': s['value'], 'peaks': peaks(freqs, mag),
               'fundamental_hz': fundamental(freqs, mag)}
        out.append(row)
        print(f"{s['value']}: fundamental {row['fundamental_hz']} Hz, peaks " +
              ', '.join(f"{p['hz']} ({p['level']})" for p in row['peaks']))
    with open(os.path.join(run, 'pitch.json'), 'w') as f:
        json.dump(out, f, indent=2)
        f.write('\n')


if __name__ == '__main__':
    main()
