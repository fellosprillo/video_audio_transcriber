from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from transcription import ProgressUpdate, TranscriptionConfig, TranscriptionError, transcribe


def emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def main() -> int:
    if len(sys.argv) < 2:
        emit({"type": "error", "message": "Missing config payload."})
        return 2

    try:
        data = json.loads(sys.argv[1])
        config = TranscriptionConfig(
            input_file=Path(data["input_file"]),
            output_dir=Path(data["output_dir"]),
            language=data.get("language") or "en",
            model_size=data.get("model_size") or "small",
            device=data.get("device") or "cpu",
        )
    except Exception as exc:
        emit({"type": "error", "message": f"Invalid config payload: {exc}"})
        return 2

    def on_progress(update: ProgressUpdate) -> None:
        emit({"type": "progress", "message": update.message, "fraction": update.fraction})

    try:
        result = transcribe(config, progress=on_progress)
        payload = asdict(result)
        payload["type"] = "success"
        emit(payload)
        return 0
    except TranscriptionError as exc:
        emit({"type": "error", "message": str(exc)})
        return 1
    except Exception as exc:
        emit({"type": "error", "message": f"Unexpected worker error: {exc}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
