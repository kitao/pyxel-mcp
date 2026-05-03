"""render_audio tool (spec §8.3).

Renders a Pyxel sound or music slot to WAV. Delegates synthesis to Pyxel's
built-in .save() method, then reads the WAV back to compute metadata.
"""
from __future__ import annotations
import struct
import wave
from pathlib import Path
from typing import Any

from pyxel_mcp.observe._harnesses._common.error_capture import make_validation_error
from pyxel_mcp.observe._harnesses._common.preloop import PreloopFailed, run_to_preloop

# Note name lookup table (C0 = MIDI 0 in Pyxel)
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Tone int → single-char string
_TONE_NAMES = {0: "t", 1: "s", 2: "p", 3: "n"}

# Effect int → single-char string
_EFFECT_NAMES = {0: "n", 1: "s", 2: "v", 3: "f"}


def _empty(error: dict) -> dict:
    return {
        "ok": False,
        "path": None,
        "duration_seconds": 0.0,
        "sample_rate": 0,
        "channels": 0,
        "peak_amplitude": 0.0,
        "notes": [],
        "warnings": [],
        "errors": [error],
    }


def _midi_to_name(n: int) -> str:
    """Convert Pyxel MIDI note number to note name string (e.g. 36 → 'C3')."""
    if n < 0:
        return "rest"
    octave = n // 12
    return f"{_NOTE_NAMES[n % 12]}{octave}"


def _tone_to_str(t: int | str) -> str:
    """Convert tone value (int or char) to spec string."""
    if isinstance(t, str):
        return t
    return _TONE_NAMES.get(t, str(t))


def _effect_to_str(e: int | str) -> str:
    """Convert effect value (int or char) to spec string."""
    if isinstance(e, str):
        return e
    return _EFFECT_NAMES.get(e, str(e))


def _read_wav_metadata(path: str) -> tuple[int, int, float, float]:
    """Return (sample_rate, channels, duration_seconds, peak_amplitude) from WAV."""
    with wave.open(path, "rb") as wf:
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        n_frames = wf.getnframes()
        duration = n_frames / sample_rate if sample_rate > 0 else 0.0
        raw = wf.readframes(n_frames)

    if raw:
        count = n_frames * n_channels
        samples = struct.unpack(f"<{count}h", raw)
        peak = max(abs(s) for s in samples) / 32768.0 if samples else 0.0
    else:
        peak = 0.0

    return sample_rate, n_channels, duration, peak


def _build_notes(sound) -> list[dict]:
    """Build notes list from a Pyxel Sound object."""
    notes_list = list(sound.notes)
    tones_list = list(sound.tones)
    effects_list = list(sound.effects)
    volumes_list = list(sound.volumes)

    result = []
    for frame, note_num in enumerate(notes_list):
        # Resolve per-frame tone/volume/effect (Pyxel repeats last value if shorter)
        tone_val = tones_list[frame] if frame < len(tones_list) else (tones_list[-1] if tones_list else 0)
        vol_val = volumes_list[frame] if frame < len(volumes_list) else (volumes_list[-1] if volumes_list else 0)
        eff_val = effects_list[frame] if frame < len(effects_list) else (effects_list[-1] if effects_list else 0)

        result.append({
            "frame": frame,
            "note": _midi_to_name(note_num),
            "tone": _tone_to_str(tone_val),
            "volume": vol_val,
            "effect": _effect_to_str(eff_val),
        })

    return result


def _validate_target(target: Any) -> tuple[str | None, int | None, dict | None]:
    """Validate target dict. Returns (kind, slot_index, error_or_None)."""
    if not isinstance(target, dict):
        return None, None, make_validation_error("`target` must be a dict with exactly one key: 'sound' or 'music'")

    valid_keys = {"sound", "music"}
    present = {k for k in target if k in valid_keys}
    extra = {k for k in target if k not in valid_keys}

    if extra:
        return None, None, make_validation_error(
            f"`target` has unexpected keys: {sorted(extra)}; only 'sound' and 'music' are allowed"
        )

    if len(present) != 1:
        return None, None, make_validation_error(
            f"`target` must have exactly one of 'sound' or 'music', got: {sorted(present)}"
        )

    kind = next(iter(present))
    slot = target[kind]

    if not isinstance(slot, int) or isinstance(slot, bool):
        return None, None, make_validation_error(
            f"`target.{kind}` must be a non-negative int, got: {slot!r}"
        )

    if slot < 0:
        return None, None, make_validation_error(
            f"`target.{kind}` must be non-negative, got: {slot}"
        )

    return kind, slot, None


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """Render a sound or music slot to WAV at the pre-loop checkpoint.

    Result includes `ok: bool` — True iff `len(errors) == 0`. Empty-slot
    warnings (e.g., "sound slot 1 is empty") do not affect `ok`.
    """
    # --- Validate basic fields (script-independent shape checks happen first) ---
    target = payload.get("target")
    kind, slot, target_error = _validate_target(target)
    if target_error is not None:
        return _empty(target_error)

    output_path = payload.get("output_path")
    if not isinstance(output_path, str):
        return _empty(make_validation_error("missing or non-str `output_path`"))

    # --- Run script to pre-loop checkpoint ---
    try:
        with run_to_preloop(payload, empty_factory=_empty):
            import pyxel

            # --- Validate slot index range ---
            if kind == "sound":
                if slot >= len(pyxel.sounds):
                    return _empty(make_validation_error(
                        f"sound slot {slot} out of range [0, {len(pyxel.sounds)})"
                    ))
                audio_obj = pyxel.sounds[slot]
            else:  # music
                if slot >= len(pyxel.musics):
                    return _empty(make_validation_error(
                        f"music slot {slot} out of range [0, {len(pyxel.musics)})"
                    ))
                audio_obj = pyxel.musics[slot]

            # --- Detect empty slot ---
            warnings: list[str] = []
            is_empty_slot = False

            if kind == "sound":
                notes_raw = list(audio_obj.notes)
                if not notes_raw or all(n < 0 for n in notes_raw):
                    is_empty_slot = True
                    warnings.append(f"sound slot {slot} is empty / not populated")
            else:
                # Music: check if all constituent channel lists are empty
                seqs = audio_obj.seqs if hasattr(audio_obj, "seqs") else getattr(audio_obj, "snds_list", [])
                has_content = any(len(list(ch)) > 0 for ch in seqs)
                if not has_content:
                    is_empty_slot = True
                    warnings.append(f"music slot {slot} is empty / not populated")

            # --- Determine duration and write WAV ---
            if kind == "sound":
                if hasattr(audio_obj, "total_sec"):
                    duration_hint = audio_obj.total_sec()
                    if duration_hint <= 0:
                        duration_hint = 1.0  # fallback for empty slot
                else:
                    # Approximate: len(notes) * speed / sample_rate
                    n_notes = max(len(list(audio_obj.notes)), 1)
                    duration_hint = n_notes * audio_obj.speed / 22050
            else:
                duration_hint = 10.0  # conservative default for music

            out_path = str(Path(output_path).resolve())
            audio_obj.save(out_path, duration_hint)

            # --- Read WAV metadata ---
            sample_rate, channels, duration_seconds, peak_amplitude = _read_wav_metadata(out_path)

            # --- Build notes list (sound only) ---
            if kind == "sound" and not is_empty_slot:
                notes = _build_notes(audio_obj)
            else:
                notes = []

            # Empty-slot override
            if is_empty_slot:
                peak_amplitude = 0.0

            return {
                "ok": True,
                "path": out_path,
                "duration_seconds": duration_seconds,
                "sample_rate": sample_rate,
                "channels": channels,
                "peak_amplitude": peak_amplitude,
                "notes": notes,
                "warnings": warnings,
                "errors": [],
            }
    except PreloopFailed as f:
        return f.result
