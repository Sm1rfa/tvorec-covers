# Installation

Tvorec Cover is managed with [uv](https://docs.astral.sh/uv/). You don't
need to manage a virtual environment yourself — `uv` does it for you.

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
  (works the same way on Windows, macOS, and Linux).
- Python 3.11+ (uv will download a matching interpreter automatically if one
  isn't already installed).

## Install and run

From the project root:

```bash
uv sync
uv run tvorec-cover
```

This installs the core dependencies (PySide6, Pillow) and launches the GUI.

## Optional: AI image upscaling

If your source images are smaller than the final print size, Tvorec Cover
can upscale them with an AI super-resolution model (FSRCNN) via OpenCV,
instead of a plain resize. This is an optional extra because OpenCV is a
fairly large dependency:

```bash
uv sync --extra upscale
```

If this extra isn't installed (or the model file is missing), Cover
Generator automatically falls back to a standard Lanczos resize — the app
still works, just with lower quality on undersized source images.

To use the AI upscaler, download an FSRCNN model file (e.g. `FSRCNN_x4.pb`)
and point the app at it; see
[`src/cover_generator/resources/models/README.md`](../../src/cover_generator/resources/models/README.md)
for where to put it.

## Running the test suite

```bash
uv run pytest
```

## Using the app without installing anything

Tvorec Cover doesn't have to be run from source. Standalone, double-clickable
executables for Windows, macOS, and Linux are built automatically on every
tagged release and attached to the project's GitHub Releases page — no
Python or `uv` needed.

## Building a standalone executable yourself

```bash
uv run pyinstaller packaging/tvorec-cover.spec --noconfirm
```

See the `build-release` skill in `.claude/skills/` for the full PyInstaller-based
process (PyInstaller does not cross-compile, so this must be run once on
each target OS).
