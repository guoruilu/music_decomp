# Dependency And Asset Manifest

Date: 2026-06-24

## Status

This Step 11 pass adds the manifest structure and direct dependency input, but
does not generate real Windows lock files or vendor assets. The executor
environment is Linux with no networked Windows build validation, so
`requirements/win-cpu.txt` and `requirements/win-cuda.txt` are explicit
placeholders. They must be replaced on the Windows build machine after tests and
smoke checks pass.

## Scope

- Make dependency inputs visible and auditable.
- Split Windows CPU and CUDA package locks because PyTorch wheel channels differ.
- Track FFmpeg and model asset provenance without committing binaries or model
  weights.
- Keep `models/` ignored. `models/README.md` is intentionally not created
  because there is no user approval to track files under the ignored directory.

## Dependency Version Strategy

- `requirements/base.in` lists direct dependencies only.
- `requirements/win-cpu.txt` will be the tested Windows CPU lock once generated and validated.
- `requirements/win-cuda.txt` will be the tested Windows CUDA lock once generated and validated.
- Windows locks must be generated from a clean Windows x64 Python 3.11
  environment, then tested before commit.
- Do not update a lock from Linux, from an untested virtual environment, or from
  a machine that depends on globally installed FFmpeg, Demucs, PyTorch, or model
  files.
- A lock update is valid only when the exact Python version, PyTorch channel,
  test command, and any GPU smoke result are recorded in this document.

## Direct Dependencies

| Package | Purpose | Version policy |
| --- | --- | --- |
| `PySide6` | Windows GUI runtime | Lower bound tracks current project metadata; upper bound blocks unreviewed major updates. |
| `demucs` | Stem separation backend | Keep on v4-compatible releases until separation tests are revalidated. |
| `torch` | Demucs execution backend | Locked separately for CPU and CUDA wheel channels. |
| `torchaudio` | Demucs/PyTorch audio support | Keep in the same major range as `torch`. |
| `numpy` | Numeric processing used by separation stack | Upper bound blocks unreviewed major updates. |
| `SoundCard` | Windows WASAPI loopback recording | Keep compatible with current recorder service. |
| `pytest` | Test runner for build validation | Dev/test dependency included so build machines can run checks from the lock. |
| `pyinstaller` | One-folder portable packaging | Build dependency for Step 12 packaging. |
| Python `wave` module | Current WAV writer for recordings | Standard library; no external `soundfile` package is required unless implementation changes. |

## Windows Lock Generation

Current lock status:

| Lock file | Status | Required validation before replacing placeholder |
| --- | --- | --- |
| `requirements/win-cpu.txt` | Pending Windows generation | `pytest`, CLI import/version smoke, CPU separation smoke with bundled or staged FFmpeg/model assets. |
| `requirements/win-cuda.txt` | Pending Windows generation | CPU checks plus `torch.cuda.is_available()` and one short CUDA separation smoke with fallback behavior observed. |

CPU lock generation outline:

```powershell
py -3.11 -m venv .venv-lock-cpu
.\.venv-lock-cpu\Scripts\python.exe -m pip install -U pip
.\.venv-lock-cpu\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple -r requirements\base.in
.\.venv-lock-cpu\Scripts\python.exe -m pip install --no-deps -e .
.\.venv-lock-cpu\Scripts\python.exe -m pytest
.\.venv-lock-cpu\Scripts\python.exe -m music_decomp --version
.\.venv-lock-cpu\Scripts\python.exe -m pip freeze --all --exclude-editable | Set-Content -Encoding ascii requirements\win-cpu.txt
```

When consuming the CPU lock, install with the same PyTorch index unless the lock
file itself includes equivalent requirement-file index options:

```powershell
.\.venv\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple -r requirements\win-cpu.txt
```

CUDA lock generation outline:

```powershell
$CudaWheelIndex = "https://download.pytorch.org/whl/<chosen-cuda-channel>"
py -3.11 -m venv .venv-lock-cuda
.\.venv-lock-cuda\Scripts\python.exe -m pip install -U pip
.\.venv-lock-cuda\Scripts\python.exe -m pip install --index-url $CudaWheelIndex --extra-index-url https://pypi.org/simple -r requirements\base.in
.\.venv-lock-cuda\Scripts\python.exe -m pip install --no-deps -e .
.\.venv-lock-cuda\Scripts\python.exe -m pytest
.\.venv-lock-cuda\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available())"
.\.venv-lock-cuda\Scripts\python.exe -m pip freeze --all --exclude-editable | Set-Content -Encoding ascii requirements\win-cuda.txt
```

When consuming the CUDA lock, install with the same chosen PyTorch CUDA index
unless the lock file itself includes equivalent requirement-file index options:

```powershell
.\.venv\Scripts\python.exe -m pip install --index-url $CudaWheelIndex --extra-index-url https://pypi.org/simple -r requirements\win-cuda.txt
```

After generating either lock, add a short note here with the build machine OS,
Python version, PyTorch wheel channel, test results, and smoke input used.

## FFmpeg Asset Manifest

No FFmpeg binary is vendored in this Step 11 change.

| Field | Value |
| --- | --- |
| Status | Pending asset staging before Step 12 packaging. |
| Source | Pending exact URL. Use FFmpeg source releases or a Windows binary provider linked from the FFmpeg download page, then record the exact archive URL. |
| Upstream version | Pending. Record `ffmpeg -version` first line and the release/archive version. |
| License | Pending selected build. FFmpeg upstream is LGPL-2.1-or-later by default and becomes GPL-2.0-or-later when GPL components are enabled; the selected binary's bundled license files control the packaged notice. |
| Local path | `vendor/ffmpeg/` with executables under `vendor/ffmpeg/bin/`. |
| Archive checksum | Pending SHA256 of the downloaded archive. |
| Executable checksums | Pending SHA256 for `vendor/ffmpeg/bin/ffmpeg.exe` and `vendor/ffmpeg/bin/ffprobe.exe`. |

Minimum checksum commands on Windows:

```powershell
Get-FileHash -Algorithm SHA256 .\path\to\downloaded-ffmpeg-archive.zip
Get-FileHash -Algorithm SHA256 .\vendor\ffmpeg\bin\ffmpeg.exe
Get-FileHash -Algorithm SHA256 .\vendor\ffmpeg\bin\ffprobe.exe
```

## Model Asset Manifest

No model weights are vendored in this Step 11 change.

| Field | Value |
| --- | --- |
| Status | Pending model staging before Step 12 packaging. |
| Model name | `htdemucs` default 4-stem Demucs model. |
| Source | Demucs pretrained model resolver; record the exact upstream URL or cache filename when the Windows build machine downloads the model. |
| License/terms | Pending verification from the exact model source before vendoring. Demucs code is MIT licensed, but model weight terms must be recorded separately if the source distinguishes them. |
| Local path | Intended package path: `models/htdemucs/` or the exact Demucs cache layout selected by packaging. |
| Checksum | Pending SHA256 for each model weight file and any aggregate manifest file. |

Minimum checksum command on Windows after assets are staged:

```powershell
Get-ChildItem .\models -Recurse -File | Get-FileHash -Algorithm SHA256 | Sort-Object Path
```

## Release Blockers

- Replace both Windows requirement placeholders with tested pinned package
  lines before claiming reproducible Windows installs.
- Replace all pending FFmpeg fields with exact source, version, license, and
  checksum values before packaging.
- Replace all pending model fields with exact source, license/terms, local path,
  and checksum values before packaging.
- Keep binaries, FFmpeg archives, model weights, generated media, and caches out
  of git unless the user explicitly approves tracking them.

## Upstream References

- FFmpeg download and source verification: https://ffmpeg.org/download.html
- FFmpeg license and legal considerations: https://ffmpeg.org/legal.html
- PyTorch local installation selector: https://pytorch.org/get-started/locally/
- Demucs repository and model list: https://github.com/facebookresearch/demucs
- Demucs code license: https://github.com/facebookresearch/demucs/blob/main/LICENSE
