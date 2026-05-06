# Optional FFmpeg Bundle

Put a Windows `ffmpeg.exe` here if you want the PyInstaller build and the Inno Setup installer to include FFmpeg automatically:

```text
vendor/ffmpeg/bin/ffmpeg.exe
```

Recommended source:

- Official FFmpeg download page: <https://www.ffmpeg.org/download.html>
- Windows builds linked by FFmpeg: <https://www.gyan.dev/ffmpeg/builds/>

If this file is not bundled, users must install FFmpeg separately and add it to `PATH`.
