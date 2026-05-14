from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".webm", ".wmv"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"}
MEDIA_EXTENSIONS = sorted(VIDEO_EXTENSIONS | AUDIO_EXTENSIONS)

LANGUAGE_OPTIONS = [
    ("English", "en"),
    ("Italian", "it"),
    ("French", "fr"),
    ("German", "de"),
    ("Spanish", "es"),
    ("Portuguese", "pt"),
    ("Dutch", "nl"),
    ("Polish", "pl"),
    ("Romanian", "ro"),
    ("Auto detect", ""),
]

MODEL_OPTIONS = ["tiny", "base", "small", "medium", "large-v3"]
DEVICE_OPTIONS = ["cpu", "cuda"]

@dataclass(frozen=True)
class ProgressUpdate:
    message: str
    fraction: float | None = None


ProgressCallback = Callable[[ProgressUpdate], None]


class TranscriptionError(RuntimeError):
    """User-facing transcription error."""


@dataclass(frozen=True)
class TranscriptionConfig:
    input_file: Path
    output_dir: Path
    language: str = "en"
    model_size: str = "small"
    device: str = "cpu"


@dataclass(frozen=True)
class TranscriptionResult:
    text_file: Path
    audio_file: Path | None
    language: str
    segment_count: int


def resource_path(*parts: str) -> Path:
    """Return a path that works from source and from a PyInstaller bundle."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def find_ffmpeg() -> str | None:
    candidates: list[Path] = []

    env_path = os.environ.get("VIDEO2TEXT_FFMPEG")
    if env_path:
        candidates.append(Path(env_path))

    candidates.extend(
        [
            resource_path("vendor", "ffmpeg", "bin", "ffmpeg.exe"),
            resource_path("vendor", "ffmpeg", "ffmpeg.exe"),
            resource_path("bin", "ffmpeg.exe"),
            resource_path("ffmpeg.exe"),
        ]
    )

    path_from_env = shutil.which("ffmpeg")
    if path_from_env:
        candidates.append(Path(path_from_env))

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    return None


def resolve_model_reference(model_size: str) -> str:
    local_model_dir = resource_path("models", model_size)
    if local_model_dir.is_dir():
        model_files = [p for p in local_model_dir.iterdir() if p.name.upper() != "README.MD"]
        if model_files:
            return str(local_model_dir)
    return model_size


def _notify(progress: ProgressCallback | None, message: str, fraction: float | None = None) -> None:
    if progress:
        progress(ProgressUpdate(message=message, fraction=fraction))


def _compute_type_for(device: str) -> str:
    override = os.environ.get("VIDEO2TEXT_COMPUTE_TYPE")
    if override:
        return override
    return "float16" if device == "cuda" else "int8"


def _subprocess_flags() -> dict[str, int]:
    if sys.platform == "win32":
        create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if create_no_window:
            return {"creationflags": create_no_window}
    return {}


def extract_audio(input_file: Path, audio_file: Path, progress: ProgressCallback | None = None) -> None:
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        raise TranscriptionError(
            "FFmpeg was not found. Install FFmpeg, add it to PATH, or bundle ffmpeg.exe "
            "under vendor/ffmpeg/bin before building the app."
        )

    _notify(progress, "Extracting mono 16 kHz WAV audio with FFmpeg...", 0.05)
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(input_file),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(audio_file),
    ]

    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            **_subprocess_flags(),
        )
    except OSError as exc:
        raise TranscriptionError(f"Could not start FFmpeg: {exc}") from exc

    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout or "").strip()
        if len(details) > 1200:
            details = details[-1200:]
        raise TranscriptionError(f"FFmpeg could not extract audio. {details}")


def transcribe(config: TranscriptionConfig, progress: ProgressCallback | None = None) -> TranscriptionResult:
    input_file = config.input_file.expanduser().resolve()
    output_dir = config.output_dir.expanduser().resolve()

    if not input_file.is_file():
        raise TranscriptionError(f"Input file does not exist: {input_file}")

    if config.model_size not in MODEL_OPTIONS:
        raise TranscriptionError(f"Unsupported model: {config.model_size}")

    if config.device not in DEVICE_OPTIONS:
        raise TranscriptionError(f"Unsupported device: {config.device}")

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise TranscriptionError(f"Cannot create output folder: {exc}") from exc

    text_file = output_dir / f"{input_file.stem}.txt"
    audio_file: Path | None = None
    audio_input = input_file

    if input_file.suffix.lower() in VIDEO_EXTENSIONS:
        audio_file = output_dir / f"{input_file.stem}.wav"
        if not audio_file.exists() or input_file.stat().st_mtime > audio_file.stat().st_mtime:
            extract_audio(input_file, audio_file, progress)
        else:
            _notify(progress, f"Using existing extracted audio: {audio_file.name}", 0.1)
        audio_input = audio_file
    elif input_file.suffix.lower() not in AUDIO_EXTENSIONS:
        _notify(progress, "Unknown file extension; trying to transcribe it as media.", 0.1)

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise TranscriptionError(
            "faster-whisper is not installed. Run 'pip install -r requirements.txt' in the app folder."
        ) from exc

    model_reference = resolve_model_reference(config.model_size)
    compute_type = _compute_type_for(config.device)
    _notify(progress, f"Loading model '{config.model_size}' on {config.device} ({compute_type})...", 0.2)

    try:
        model = WhisperModel(model_reference, device=config.device, compute_type=compute_type)
    except Exception as exc:
        raise TranscriptionError(f"Could not load the Whisper model: {exc}") from exc

    language = config.language or None
    _notify(progress, "Transcribing audio...", 0.25)

    try:
        segments, info = model.transcribe(str(audio_input), language=language)
        detected_language = getattr(info, "language", language or "unknown") or "unknown"
        duration_seconds = float(getattr(info, "duration", 0.0) or 0.0)

        segment_count = 0
        last_notified_fraction = 0.0
        last_notified_at = 0.0
        with text_file.open("w", encoding="utf-8") as output:
            for segment in segments:
                output.write(f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text.strip()}\n")
                segment_count += 1
                if duration_seconds > 0:
                    transcribe_fraction = min(1.0, max(0.0, float(segment.end) / duration_seconds))
                    total_fraction = 0.25 + (0.7 * transcribe_fraction)
                    should_notify = (
                        total_fraction - last_notified_fraction >= 0.01
                        or segment_count - last_notified_at >= 25
                        or total_fraction >= 0.95
                    )
                    if should_notify:
                        last_notified_fraction = total_fraction
                        last_notified_at = float(segment_count)
                        _notify(
                            progress,
                            f"Processed {segment_count} segments ({segment.end:.1f}s / {duration_seconds:.1f}s)...",
                            total_fraction,
                        )
                else:
                    fallback_fraction = min(0.95, 0.25 + (segment_count * 0.02))
                    if segment_count == 1 or segment_count % 10 == 0:
                        _notify(progress, f"Processed {segment_count} segments...", fallback_fraction)
    except Exception as exc:
        raise TranscriptionError(f"Transcription failed: {exc}") from exc

    _notify(progress, f"Saved transcript: {text_file}", 1.0)
    return TranscriptionResult(
        text_file=text_file,
        audio_file=audio_file,
        language=detected_language,
        segment_count=segment_count,
    )
