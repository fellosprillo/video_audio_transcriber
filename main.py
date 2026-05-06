from __future__ import annotations

import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

import flet as ft

from transcription import (
    DEVICE_OPTIONS,
    LANGUAGE_OPTIONS,
    MEDIA_EXTENSIONS,
    MODEL_OPTIONS,
    TranscriptionConfig,
    TranscriptionError,
    find_ffmpeg,
    resource_path,
    transcribe,
)


APP_NAME = "Video2Text"
APP_VERSION = "1.0.0"
ASSETS_DIR = resource_path()


def _icon(name: str) -> str:
    icon_module = getattr(ft, "Icons", None) or getattr(ft, "icons", None)
    if icon_module:
        return getattr(icon_module, name, name.lower())
    return name.lower()


def _dropdown_option(value: str, label: str):
    dropdown_module = getattr(ft, "dropdown", None)
    option_cls = getattr(dropdown_module, "Option", None) or getattr(ft, "DropdownOption", None)
    if option_cls is None:
        return value

    for kwargs in ({"key": value, "text": label}, {"value": value, "text": label}):
        try:
            return option_cls(**kwargs)
        except TypeError:
            pass

    try:
        option = option_cls(value)
        if hasattr(option, "text"):
            option.text = label
        return option
    except TypeError:
        return option_cls(label)


def _default_output_dir() -> Path:
    documents = Path.home() / "Documents"
    return documents if documents.exists() else Path.home()


def main(page: ft.Page) -> None:
    page.title = APP_NAME
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#f5f7fb"
    page.padding = 24
    page.spacing = 18
    page.scroll = ft.ScrollMode.AUTO

    try:
        page.window.min_width = 860
        page.window.min_height = 680
    except AttributeError:
        page.window_min_width = 860
        page.window_min_height = 680

    running = {"value": False}

    input_path = ft.TextField(
        label="Input video or audio file",
        hint_text="Select a media file",
        read_only=True,
        expand=True,
        dense=True,
    )
    output_path = ft.TextField(
        label="Output folder",
        value=str(_default_output_dir()),
        read_only=True,
        expand=True,
        dense=True,
    )
    language_dropdown = ft.Dropdown(
        label="Language",
        value="en",
        width=220,
        options=[_dropdown_option(value, label) for label, value in LANGUAGE_OPTIONS],
    )
    model_dropdown = ft.Dropdown(
        label="Model",
        value="small",
        width=190,
        options=[_dropdown_option(value, value) for value in MODEL_OPTIONS],
    )
    device_dropdown = ft.Dropdown(
        label="Device",
        value="cpu",
        width=160,
        options=[_dropdown_option(value, value.upper()) for value in DEVICE_OPTIONS],
    )

    log_view = ft.TextField(
        label="Activity log",
        value="",
        multiline=True,
        min_lines=9,
        max_lines=9,
        read_only=True,
        border_color="#d7dee8",
    )
    status_text = ft.Text("Ready", color="#344054", size=13)
    result_text = ft.Text("", selectable=True, color="#0f5132", size=13)
    progress_ring = ft.ProgressRing(width=20, height=20, stroke_width=3, visible=False)

    file_picker_cls = getattr(ft, "FilePicker", None)
    if file_picker_cls is None:
        raise RuntimeError(
            "This Flet version does not expose FilePicker. "
            "Upgrade Flet with: pip install --upgrade flet"
        )

    def _selected_file_path(file_obj) -> str | None:
        # Desktop returns absolute path in `path`; web/mobile may only expose
        # name/bytes. This app transcribes local files, so `path` is required.
        path = getattr(file_obj, "path", None)
        return str(path) if path else None

    def update_page() -> None:
        try:
            page.update()
        except Exception:
            pass

    def append_log(message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        current = log_view.value or ""
        lines = (current + f"[{timestamp}] {message}\n").splitlines()[-250:]
        log_view.value = "\n".join(lines) + "\n"
        status_text.value = message
        update_page()

    def show_snack(message: str, is_error: bool = False) -> None:
        snack = ft.SnackBar(
            content=ft.Text(message),
            bgcolor="#b42318" if is_error else "#067647",
        )
        try:
            page.open(snack)
        except Exception:
            page.snack_bar = snack
            snack.open = True
            update_page()

    def set_running(value: bool) -> None:
        running["value"] = value
        progress_ring.visible = value
        start_button.disabled = value
        choose_file_button.disabled = value
        choose_folder_button.disabled = value
        language_dropdown.disabled = value
        model_dropdown.disabled = value
        device_dropdown.disabled = value
        update_page()

    def validate_config() -> TranscriptionConfig | None:
        if not input_path.value:
            show_snack("Select an input media file first.", is_error=True)
            return None

        input_file = Path(input_path.value)
        if not input_file.is_file():
            show_snack("The selected input file does not exist.", is_error=True)
            return None

        if not output_path.value:
            show_snack("Select an output folder first.", is_error=True)
            return None

        language_value = language_dropdown.value
        if language_value is None:
            language_value = "en"

        return TranscriptionConfig(
            input_file=input_file,
            output_dir=Path(output_path.value),
            language=language_value,
            model_size=model_dropdown.value or "small",
            device=device_dropdown.value or "cpu",
        )

    def start_transcription(_: ft.ControlEvent) -> None:
        if running["value"]:
            return

        config = validate_config()
        if config is None:
            return

        result_text.value = ""
        append_log("Starting transcription job...")
        set_running(True)

        def worker() -> None:
            try:
                result = transcribe(config, progress=append_log)
                result_text.value = (
                    f"Completed. Transcript: {result.text_file} | "
                    f"Language: {result.language} | Segments: {result.segment_count}"
                )
                show_snack("Transcription completed.")
            except TranscriptionError as exc:
                append_log(f"Error: {exc}")
                result_text.value = "The job failed. Check the activity log for details."
                show_snack(str(exc), is_error=True)
            except Exception as exc:
                append_log(f"Unexpected error: {exc}")
                result_text.value = "Unexpected error. Check the activity log for details."
                show_snack("Unexpected error. Check the activity log for details.", is_error=True)
            finally:
                set_running(False)

        runner = getattr(page, "run_thread", None)
        if callable(runner):
            runner(worker)
        else:
            threading.Thread(target=worker, daemon=True).start()

    async def choose_file(_: ft.ControlEvent) -> None:
        file_type_enum = getattr(ft, "FilePickerFileType", None)
        custom_type = getattr(file_type_enum, "CUSTOM", None) if file_type_enum else None
        kwargs = {"allow_multiple": False}
        if custom_type is not None:
            kwargs["file_type"] = custom_type
            kwargs["allowed_extensions"] = [extension.lstrip(".") for extension in MEDIA_EXTENSIONS]
        try:
            files = await file_picker_cls().pick_files(**kwargs)
        except Exception as exc:
            show_snack(f"Could not open the file picker: {exc}", is_error=True)
            return

        if files:
            selected = _selected_file_path(files[0])
            if selected is None:
                show_snack(
                    "The selected file has no local path. Run the app as a desktop app, not in browser mode.",
                    is_error=True,
                )
                return
            input_path.value = selected
            if selected and not output_path.value:
                output_path.value = str(Path(selected).parent)
            append_log(f"Selected input file: {selected}")
        update_page()

    async def choose_folder(_: ft.ControlEvent) -> None:
        try:
            selected_dir = await file_picker_cls().get_directory_path(dialog_title="Choose output folder")
        except Exception as exc:
            show_snack(f"Could not open the folder picker: {exc}", is_error=True)
            return

        if selected_dir:
            output_path.value = str(selected_dir)
            append_log(f"Selected output folder: {selected_dir}")
        update_page()

    def open_output_folder(_: ft.ControlEvent) -> None:
        target = Path(output_path.value or "")
        if not target.exists():
            show_snack("The output folder does not exist yet.", is_error=True)
            return
        try:
            if sys.platform == "win32":
                os.startfile(target)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])
        except Exception as exc:
            show_snack(f"Could not open the output folder: {exc}", is_error=True)

    choose_file_button = ft.ElevatedButton(
        "Select file",
        icon=_icon("UPLOAD_FILE"),
        on_click=choose_file,
        tooltip="Select input media file",
    )
    choose_folder_button = ft.OutlinedButton(
        "Output folder",
        icon=_icon("FOLDER_OPEN"),
        on_click=choose_folder,
        tooltip="Select output folder",
    )
    start_button = ft.FilledButton(
        "Start transcription",
        icon=_icon("PLAY_ARROW"),
        on_click=start_transcription,
        tooltip="Start transcription",
    )
    open_folder_button = ft.IconButton(
        icon=_icon("FOLDER"),
        tooltip="Open output folder",
        on_click=open_output_folder,
    )

    ffmpeg_status = (
        "FFmpeg detected"
        if find_ffmpeg()
        else "FFmpeg not detected. Video files need FFmpeg in PATH or bundled under vendor/ffmpeg/bin."
    )

    header = ft.Container(
        bgcolor="#172033",
        border_radius=8,
        padding=20,
        content=ft.Row(
            controls=[
                ft.Image(src="images/logo.png", width=62, height=62, fit=ft.BoxFit.CONTAIN),
                ft.Column(
                    spacing=4,
                    expand=True,
                    controls=[
                        ft.Text(APP_NAME, size=28, weight=ft.FontWeight.BOLD, color="#ffffff"),
                        ft.Text(
                            "Local video and audio transcription with faster-whisper",
                            size=14,
                            color="#d8e0ee",
                        ),
                    ],
                ),
                ft.Container(
                    bgcolor="#22304a",
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    content=ft.Text(f"v{APP_VERSION}", color="#d8e0ee", size=12),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    file_section = ft.Container(
        bgcolor="#ffffff",
        border=ft.border.all(1, "#d7dee8"),
        border_radius=8,
        padding=18,
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Row(
                    controls=[input_path, choose_file_button],
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
                ft.Row(
                    controls=[output_path, choose_folder_button, open_folder_button],
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
                ft.Row(
                    spacing=12,
                    wrap=True,
                    controls=[language_dropdown, model_dropdown, device_dropdown],
                ),
                ft.Row(
                    spacing=12,
                    controls=[start_button, progress_ring, ft.Text(ffmpeg_status, size=12, color="#667085")],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
        ),
    )

    log_section = ft.Container(
        bgcolor="#ffffff",
        border=ft.border.all(1, "#d7dee8"),
        border_radius=8,
        padding=18,
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(_icon("TERMINAL"), color="#475467", size=18),
                        ft.Text("Job status", size=16, weight=ft.FontWeight.W_600, color="#172033"),
                        ft.Container(expand=True),
                        status_text,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                log_view,
                result_text,
            ],
        ),
    )

    page.add(
        ft.Column(
            expand=True,
            spacing=18,
            controls=[
                header,
                file_section,
                log_section,
            ],
        )
    )


if __name__ == "__main__":
    ft.app(target=main, assets_dir=str(ASSETS_DIR))
