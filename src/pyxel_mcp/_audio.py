"""WAV audio analysis with numpy-accelerated frequency estimation."""

import math
import wave

import numpy as np

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

_SCALE_TEMPLATES = {
    "major": {0, 2, 4, 5, 7, 9, 11},
    "minor": {0, 2, 3, 5, 7, 8, 10},
    "penta": {0, 2, 4, 7, 9},
}


def freq_to_note(freq):
    """Convert frequency (Hz) to note name like C5, A4."""
    if freq < 20:
        return "~"
    midi = 69 + 12 * math.log2(freq / 440.0)
    idx = round(midi) % 12
    octave = (round(midi) // 12) - 1
    return f"{NOTE_NAMES[idx]}{octave}"


def freq_to_midi(freq):
    """Convert frequency to MIDI note number."""
    if freq < 20:
        return -1
    return round(69 + 12 * math.log2(freq / 440.0))


def estimate_freq(samples, sample_rate):
    """Estimate fundamental frequency using FFT-based autocorrelation.

    ~50-100x faster than pure-Python autocorrelation.
    """
    n = len(samples)
    if n < 50:
        return 0

    min_lag = max(1, sample_rate // 2000)
    max_lag = min(sample_rate // 50, n // 2)
    if max_lag <= min_lag:
        return 0

    samples = np.asarray(samples, dtype=np.float64)
    samples = samples - np.mean(samples)
    energy = np.dot(samples, samples)
    if energy == 0:
        return 0

    # FFT-based autocorrelation: R(lag) = IFFT(|FFT(x)|^2)
    fft_size = 1
    while fft_size < 2 * n:
        fft_size *= 2
    f = np.fft.rfft(samples, fft_size)
    acf = np.fft.irfft(f * np.conj(f))[:n]
    acf /= acf[0]

    corrs = acf[min_lag:max_lag]
    if len(corrs) == 0:
        return 0

    # Find where correlation first drops below threshold
    dip_idx = None
    for i in range(len(corrs)):
        if corrs[i] < 0.2:
            dip_idx = i
            break

    if dip_idx is None:
        best_i = int(np.argmax(corrs))
        return sample_rate / (min_lag + best_i) if corrs[best_i] > 0.6 else 0

    # Find first peak after the dip
    for i in range(max(1, dip_idx), len(corrs) - 1):
        if corrs[i] > 0.3 and corrs[i] >= corrs[i - 1] and corrs[i] >= corrs[i + 1]:
            return sample_rate / (min_lag + i)

    return 0


def detect_key(midi_notes):
    """Detect musical key from a list of MIDI note numbers."""
    if not midi_notes:
        return "unknown"
    pc_hist = [0] * 12
    for m in midi_notes:
        pc_hist[m % 12] += 1

    best_score = -1
    best_key = "C major"
    for root in range(12):
        for scale_name, template in _SCALE_TEMPLATES.items():
            score = sum(pc_hist[(root + pc) % 12] for pc in template)
            if score > best_score:
                best_score = score
                best_key = f"{NOTE_NAMES[root]} {scale_name}"
    return best_key


def analyze_intervals(midi_notes):
    """Classify intervals between consecutive notes."""
    if len(midi_notes) < 2:
        return {}
    counts = {"step (1-2)": 0, "skip (3-4)": 0, "leap (5-7)": 0, "jump (8+)": 0}
    for i in range(1, len(midi_notes)):
        diff = abs(midi_notes[i] - midi_notes[i - 1])
        if diff <= 2:
            counts["step (1-2)"] += 1
        elif diff <= 4:
            counts["skip (3-4)"] += 1
        elif diff <= 7:
            counts["leap (5-7)"] += 1
        else:
            counts["jump (8+)"] += 1
    return counts


def suggest_role(midi_notes, durations_ms):
    """Suggest channel role based on pitch range and rhythm."""
    if not midi_notes:
        return "silent"
    avg = sum(midi_notes) / len(midi_notes)
    unique_durs = len(set(durations_ms))

    if avg < 48:
        return "bass"
    if avg < 60:
        return "bass" if unique_durs <= 2 else "bass/accompaniment"
    if avg < 72:
        return "melody" if unique_durs >= 3 else "accompaniment"
    return "melody (high)"


def analyze_wav(wav_path):
    """Analyze WAV file, return frequency/amplitude report with musical analysis."""
    with wave.open(wav_path, "r") as wf:
        n_channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if n_frames == 0:
        return "Empty audio (0 samples)"

    samples = np.frombuffer(raw, dtype=np.int16)
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1).astype(np.int16)

    duration = n_frames / sample_rate
    peak = int(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))

    # Time-windowed analysis (100ms windows)
    window_size = sample_rate // 10
    segments = []
    for start in range(0, len(samples), window_size):
        w = samples[start:start + window_size].astype(np.float64)
        if len(w) < 50:
            break
        w_rms = float(np.sqrt(np.mean(w ** 2)))
        if w_rms < 50:
            segments.append(("~", 0, w_rms))
            continue
        freq = estimate_freq(w, sample_rate)
        note = freq_to_note(freq) if freq > 0 else "~"
        segments.append((note, freq, w_rms))

    # Group consecutive identical notes
    grouped = []
    for note, freq, w_rms in segments:
        if grouped and grouped[-1][0] == note:
            grouped[-1] = (
                note, freq,
                max(grouped[-1][2], w_rms),
                grouped[-1][3] + 100,
            )
        else:
            grouped.append((note, freq, w_rms, 100))

    lines = [
        f"Duration: {duration:.2f}s | Peak: {peak / 327.67:.0f}%"
        f" | RMS: {rms / 327.67:.0f}%",
        "",
        "Note sequence:",
    ]
    time_ms = 0
    for note, freq, w_rms, dur_ms in grouped:
        if note == "~":
            lines.append(f"  {time_ms / 1000:.1f}s [{dur_ms}ms] rest")
        else:
            lines.append(
                f"  {time_ms / 1000:.1f}s [{dur_ms}ms] {note}"
                f" (~{freq:.0f}Hz) vol={w_rms / 327.67:.0f}%"
            )
        time_ms += dur_ms

    # Musical analysis
    played = [(n, f, r, d) for n, f, r, d in grouped if n != "~"]
    if played:
        midi_notes = [freq_to_midi(f) for _, f, _, _ in played if f > 0]
        durations = [d for _, _, _, d in played]

        if midi_notes:
            lo_note = freq_to_note(min(f for _, f, _, _ in played if f > 0))
            hi_note = freq_to_note(max(f for _, f, _, _ in played if f > 0))
            semitone_range = max(midi_notes) - min(midi_notes)

            lines.append("")
            lines.append("Musical analysis:")
            lines.append(
                f"  Pitch range: {lo_note} - {hi_note}"
                f" ({semitone_range} semitones)"
            )

            note_counts = {}
            for n, _, _, _ in played:
                note_counts[n] = note_counts.get(n, 0) + 1
            top_notes = sorted(note_counts.items(), key=lambda x: -x[1])[:6]
            lines.append(
                "  Top notes: "
                + " ".join(f"{n}({c}x)" for n, c in top_notes)
            )

            key = detect_key(midi_notes)
            lines.append(f"  Key estimate: {key}")

            intervals = analyze_intervals(midi_notes)
            if intervals:
                total = sum(intervals.values())
                parts = []
                for label, count in intervals.items():
                    if count > 0:
                        pct = count * 100 // total
                        parts.append(f"{label}:{pct}%")
                lines.append(f"  Intervals: {' '.join(parts)}")

            dur_counts = {}
            for d in durations:
                dur_counts[d] = dur_counts.get(d, 0) + 1
            top_durs = sorted(dur_counts.items(), key=lambda x: -x[1])[:4]
            lines.append(
                "  Rhythm: "
                + " ".join(f"{d}ms({c}x)" for d, c in top_durs)
            )

            role = suggest_role(midi_notes, durations)
            lines.append(f"  Suggested role: {role}")

    return "\n".join(lines)
