# Build the Windows Executable with PyInstaller

Run these commands from the repository root, which is this `app` folder after you copy it to GitHub.

## 1. Create the build environment

Use Python 3.10 or newer on Windows 10/11 x64.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Optional: bundle FFmpeg

To avoid requiring users to install FFmpeg separately, download a Windows FFmpeg build and place the executable here:

```text
vendor/ffmpeg/bin/ffmpeg.exe
```

The app also works without bundling FFmpeg if `ffmpeg.exe` is available in the user's `PATH`.

## 3. Optional: bundle Whisper model files

To avoid a first-run model download, place a compatible faster-whisper model directory under `models/<model-name>/`, for example:

```text
models/small/
```

If the folder is missing, faster-whisper downloads the selected model on first use.

## 4. Build

```powershell
pyinstaller --noconfirm .\video2text.spec
```

The executable package is created here:

```text
dist/Video2Text/Video2Text.exe
```

This is a one-folder build. Use this output as the input for Inno Setup.

## 5. Smoke test

```powershell
.\dist\Video2Text\Video2Text.exe
```

Verify that:

- The app window opens.
- The logo is visible.
- You can select an input media file.
- You can select an output folder.
- CPU, language, and model dropdowns work.
- A short audio or video file produces a `.txt` transcript.

## Notes

- The executable includes Python and Python packages, so end users do not install Python manually.
- CUDA mode requires a compatible NVIDIA GPU, driver, CUDA runtime libraries, and cuDNN on the target machine.
- If the app fails on a clean Windows PC with missing Microsoft runtime DLLs, include `vendor/redist/vc_redist.x64.exe` before building the installer.
