# Windows Offline Music Stem Separation Software Plan

Date: 2026-06-13

Detailed execution plan: [step-by-step-execution-plan.md](step-by-step-execution-plan.md)

## Summary

- Build a Windows portable-folder GUI application. The user unzips the folder and runs the executable.
- The app must work offline after delivery. Python runtime, FFmpeg, model weights, and dependencies are bundled locally.
- First version target: high-quality 4-stem separation into `vocals`, `drums`, `bass`, and `other`.
- Also export `lowest` and `highest` approximate tracks.
- Local audio and video files are decoded with bundled FFmpeg.
- Online video is handled by user playback plus Windows system-audio loopback recording, not URL downloading.

## Product Decisions

- Quality target: quality-first, using bundled pretrained model weights.
- User interface: Windows GUI first.
- Delivery format: portable folder, not installer and not single executable.
- Hardware target: CPU must work; CUDA GPU acceleration is optional and auto-detected.
- Usage scenario: personal/research use, with dependency license notices retained.
- Online video policy: record system audio while the user plays the video in a browser or other player.

## Key Implementation Changes

- Use Python with PySide6 for the desktop GUI.
- Use PyTorch and Demucs-compatible model execution for source separation.
- Use SoundCard or equivalent Windows WASAPI loopback support for system-audio recording.
- Bundle FFmpeg and use it for media probing, audio extraction, and output conversion.
- Package with PyInstaller one-folder mode for reliable bundled delivery.

## Internal Interfaces

- `MediaInput(kind, path, title, duration, sample_rate)`
- `SeparationJob(input, output_dir, device="auto", model="htdemucs", output_format="wav", stems=["vocals","drums","bass","other","lowest","highest"])`
- `MediaService`: probe metadata, extract audio, and convert media through FFmpeg.
- `RecorderService`: enumerate output devices, record WASAPI loopback audio, and save recording WAV files.
- `SeparationService`: load model, select CPU/GPU, run stem separation, and report progress.
- `ExportService`: create timestamped output directories and export WAV/FLAC/MP3.

## Output Behavior

- Each job writes to a timestamped output directory.
- Default export format is WAV; FLAC and MP3 are optional UI choices.
- `lowest.wav` is derived primarily from the `bass` stem.
- `highest.wav` is an approximate high-register/high-frequency export. The UI must label it as an approximation, not as guaranteed instrument-level separation.
- Failed jobs keep logs and any recoverable intermediate metadata for debugging.

## Test Plan

- Unit tests for FFmpeg command construction, media probing, output directory naming, device selection, CPU/GPU fallback, and log writing.
- Synthetic audio tests with low-frequency and high-frequency sine waves to verify `lowest` and `highest` directionality.
- Separation smoke test on a short audio file, verifying that all expected output files exist and have valid duration/sample rate.
- Windows offline acceptance test on a machine without Python and without external FFmpeg installed.
- Manual GUI acceptance test for local audio, local video, system-audio recording, CPU separation, and optional GPU acceleration fallback.

## Known Limitations

- 4-stem separation is model-based and can have bleed, artifacts, or weak separation on dense mixes.
- `highest` is approximate. It does not identify a real instrument when multiple instruments overlap in the same frequency region.
- URL downloading is intentionally out of scope for v1 to keep the app self-contained and stable.
- GPU acceleration depends on compatible local NVIDIA drivers. The app will not install drivers.

## References

- Demucs: https://github.com/facebookresearch/demucs
- FFmpeg documentation: https://ffmpeg.org/documentation.html
- FFmpeg devices documentation: https://ffmpeg.org/ffmpeg-devices.html
- PyInstaller operating mode: https://pyinstaller.org/en/stable/operating-mode.html
- SoundCard package: https://pypi.org/project/SoundCard/
