---
name: build-release
description: Use when asked to build, package, or produce a standalone executable/installer of Tvorec Cover for Windows, macOS, or Linux, so end users don't need Python or uv installed.
---

# Build a standalone release

Tvorec Cover end users shouldn't need Python or `uv` installed — package
a standalone executable per platform with [PyInstaller](https://pyinstaller.org/),
run via `uv` on each target OS (PyInstaller does not cross-compile; you must
run this on each platform you want to build for).

## One-time setup (per platform)

```bash
uv sync --group dev
uv add --dev pyinstaller   # if not already a dev dependency
```

## Build

```bash
uv run pyinstaller packaging/tvorec-cover.spec --noconfirm
```

`packaging/tvorec-cover.spec` is the single source of truth for the build
(bundles `theme.qss`, the Bulgarian `.qm` translation, the ICC profiles, the
bundled `resources/assets` -- logo, app icon -- and `resources/docs` -- the
in-app user manual), and picks the right app icon (`icon.ico` / `icon.icns`)
for the OS it's run on. There's no separate Windows-vs-macOS/Linux command
to keep in sync, unlike raw `--add-data` CLI flags (which do need a
different path separator per OS).

Notes:

- If the optional AI-upscale extra is wanted in the bundled build, install
  it first (`uv sync --extra upscale`) so PyInstaller's dependency analysis
  picks up `cv2`.
- The output binary lands in `dist/tvorec-cover` (or
  `dist/tvorec-cover.exe` on Windows). It's a windowed, single-file build
  (no console window) on every OS.
- `.github/workflows/release.yml` runs this exact command on all three
  OSes (matrix build) whenever a `v*` tag is pushed, and attaches the
  resulting binaries to a GitHub Release. `.github/workflows/ci.yml` runs
  lint + tests on every push/PR.

## Verify

Run the built binary directly (not via `uv run`) on a machine without the
dev environment, or at minimum in a fresh shell with the `.venv`
deactivated, and confirm:

- the window opens with the themed UI (not default Qt styling — confirms
  `theme.qss` was bundled),
- switching to Bulgarian in the Language menu and restarting shows
  Bulgarian text (confirms the `.qm` file was bundled),
- **Help > User manual** opens and shows rendered text (confirms
  `resources/docs` was bundled),
- **About > About Tvorec Cover** shows the logo and version (confirms
  `resources/assets` was bundled),
- generating a cover from sample images produces a valid PDF.

## Repeating for each OS

Repeat the build step on a Windows machine/VM and a macOS machine to produce
all three platform binaries — there is no single cross-platform build step
(or just push a `v*` tag and let `.github/workflows/release.yml` build all
three in CI).

## Adding a new bundled resource

If a change adds a new file under `src/cover_generator/resources/` (or any
other data file the app reads via `importlib.resources` at runtime), add it
to the `datas` list in `packaging/tvorec-cover.spec` too — PyInstaller only
bundles what's explicitly listed there; it won't discover it on its own.
