# Video2Text

Video2Text is a Windows desktop app that transcribes local video and audio files using `faster-whisper`. The interface is built with Flet and is designed for non-technical users: select an input file, choose an output folder, select language/model/device, and start the transcription.

## Features

- Flet desktop GUI in English.
- Input file picker for common video and audio formats.
- Output folder picker.
- Language dropdown with English as the default.
- Model dropdown with `small` as the default.
- Device dropdown with `cpu` as the default and optional `cuda`.
- User-facing error handling without crashing the window.
- Timestamped `.txt` transcript output.
- Optional extracted `.wav` output for video files.
- PyInstaller and Inno Setup build instructions.

## Requirements

For development and build:

- Windows 10/11 x64.
- Python 3.10 to 3.12 recommended for the build environment: <https://www.python.org/downloads/windows/>
- Flet: <https://flet.dev/docs/getting-started/installation/>
- faster-whisper: <https://github.com/SYSTRAN/faster-whisper>
- PyInstaller: <https://pyinstaller.org/en/latest/usage.html>
- Inno Setup 6: <https://jrsoftware.org/isdl.php>

For runtime:

- The PyInstaller build includes Python and installed Python packages.
- FFmpeg is required for video input. Bundle `ffmpeg.exe` in the installer or install it separately from <https://www.ffmpeg.org/download.html>.
- Microsoft Visual C++ Redistributable may be required on clean Windows machines: <https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist>
- CUDA mode requires an NVIDIA GPU, current NVIDIA driver, CUDA libraries, and cuDNN:
  - CUDA Toolkit: <https://developer.nvidia.com/cuda/toolkit>
  - cuDNN: <https://developer.nvidia.com/cudnn>

## Recommended Build Sequence

1. Build the Windows executable with PyInstaller. See `BUILD_PYINSTALLER.md`.
2. Build the user-friendly Windows installer with Inno Setup. See `BUILD_WINDOWS_INSTALLER.md`.
3. Test the installer on a clean Windows machine.

## Run from Source

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python .\main.py
```

## Build the Executable

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm .\video2text.spec
```

Output:

```text
dist/Video2Text/Video2Text.exe
```

## Build the Installer

```powershell
iscc .\installer\Video2Text.iss
```

Output:

```text
installer_output/Video2TextSetup-1.0.2.exe
```

## Making the Installer More Self-Contained

The executable already bundles Python and Python dependencies. To reduce external setup for end users:

- Add FFmpeg before building: `vendor/ffmpeg/bin/ffmpeg.exe`.
- Add Microsoft runtime before compiling the installer: `vendor/redist/vc_redist.x64.exe`.
- Add local faster-whisper model files before building: `models/small/`, `models/medium/`, or another supported model folder.

If model files are not bundled, the first transcription with a model may need internet access so `faster-whisper` can download it to the user's cache.

## Output

For an input file named:

```text
meeting.mp4
```

The selected output folder receives:

```text
meeting.txt
meeting.wav
```

Audio-only inputs produce the `.txt` transcript and do not create a separate `.wav` file.

## Troubleshooting

- `ModuleNotFoundError: No module named 'flet'`: rebuild from the same virtual environment where dependencies are installed. Activate `.venv`, run `python -m pip install -r requirements.txt`, then run `python -m PyInstaller --noconfirm .\video2text.spec`. Do not use a global `pyinstaller` command from another Python installation.
- `FFmpeg was not found`: bundle `vendor/ffmpeg/bin/ffmpeg.exe` or install FFmpeg and add it to `PATH`.
- `Could not load the Whisper model`: check internet access for first-run downloads, available disk space, or bundled local model files.
- CUDA errors: use CPU mode first, then verify NVIDIA driver, CUDA, and cuDNN installation.
- Missing runtime DLLs on a clean PC: include the Microsoft Visual C++ Redistributable in `vendor/redist/` and rebuild the installer.
