# Optional Local Whisper Models

By default, `faster-whisper` downloads the selected model on first use and stores it in the user's cache.

For a more self-contained installer, place a compatible local faster-whisper model folder here:

```text
models/small/
models/medium/
models/large-v3/
```

When a folder matching the selected model exists and contains model files, the app loads it instead of downloading from the network.

Useful references:

- faster-whisper project: <https://github.com/SYSTRAN/faster-whisper>
- CTranslate2 model conversion: <https://opennmt.net/CTranslate2/guides/transformers.html>
