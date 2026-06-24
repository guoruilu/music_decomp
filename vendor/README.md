# Vendor Assets

This directory is reserved for locally staged third-party runtime assets used by
the portable Windows package.

Only this README is intended to be tracked. FFmpeg binaries, model weights,
generated archives, caches, and extracted vendor payloads must stay out of git
unless the user explicitly approves a different tracking policy.

Expected FFmpeg layout once the Windows build owner stages an approved asset:

```text
vendor/
`-- ffmpeg/
    |-- bin/
    |   |-- ffmpeg.exe
    |   `-- ffprobe.exe
    |-- LICENSES/
    |-- SOURCE.txt
    `-- SHA256SUMS.txt
```

Before packaging, update
`docs/by-feature/dependency-and-asset-manifest.md` with the exact FFmpeg source
URL, upstream version, distribution license, local path, and SHA256 checksums for
both the downloaded archive and the staged executables.
