# Architecture

This document is for contributors working on the codebase itself.

## Layout

```
src/cover_generator/
  core/      # pure(ish) image/PDF pipeline -- no Qt dependency
  gui/       # PySide6 widgets and application bootstrap
  i18n/      # Qt Linguist .ts/.qm translation files
  resources/
    assets/       # logo.png + generated icon.ico / icon.icns
    icc_profiles/ # bundled ECI CMYK profiles (see core/icc_profiles.py)
    docs/          # bundled copy of docs/{en,bg}/usage-manual.md, read by
                    # the in-app Help > User manual dialog -- keep these two
                    # copies byte-identical (see the sync-docs command)
    models/        # docs only; the FSRCNN model itself is never bundled
packaging/
  tvorec-cover.spec # PyInstaller build spec, see the build-release skill
```

The split between `core/` and `gui/` is deliberate: `core/` has no PySide6
import anywhere, so the image/PDF pipeline can be unit-tested fast, without a
display, and could in principle be reused outside the GUI (e.g. a future CLI).

## Core pipeline

`core/pipeline.py:generate_cover()` is the single entry point the GUI calls.
It orchestrates, in order:

1. `core/geometry.py` — pure math (no I/O): converts the `CoverSpec` (page
   count, paper type, trim size, bleed, DPI) into a `CanvasLayout` describing
   exact pixel positions and sizes for the back/spine/front panels.
2. `core/upscale.py` — loads each source image and guarantees it's at least
   as large as its target panel size. Tries OpenCV's FSRCNN super-resolution
   model first (optional dependency, see `[project.optional-dependencies]`
   in `pyproject.toml`); falls back to a plain Lanczos resize if OpenCV or
   the model file aren't available. This isolation means `core/` tests never
   require OpenCV.
3. `core/compositor.py` — pastes the sized panels onto one canvas and draws
   rotated spine text (title/author) if applicable.
4. `core/exporter.py` — writes the canvas out as a single-page PDF at the
   configured DPI.

`generate_cover()` takes an `on_progress(message, fraction)` callback so
callers (the GUI worker thread) can report progress without `core/` knowing
anything about Qt.

## Single-image pipeline

`core/single.py:process_single_image()` is a second, smaller entry point for
services that take the front and back cover as two separate uploads and
compute the spine themselves — so there's no wrap-around canvas, just one
panel. Given a `SingleImageSpec`, it:

1. sizes the panel via `geometry.py:compute_single_panel_size()` (trim, plus
   bleed on all four sides unless `include_bleed` is off),
2. calls `upscale.py:fit_to_cover()` — scale-to-cover (AI upscale first when
   enlarging, Lanczos otherwise) then centre-crop, so the result exactly
   fills the target with no distortion,
3. writes a high-quality JPEG via `exporter.py:export_jpg()`.

It shares the same `on_progress` callback contract as `generate_cover()`.

## Mockup pipeline

`core/mockup.py:generate_mockup()` is a third entry point that renders a
blank, actual-size *template* PNG — no source images, no real artwork. Given
a `MockupSpec`, it:

1. computes the layout via `geometry.py:compute_canvas_layout_from_params()`
   — the same math `compute_canvas_layout()` uses, factored out so callers
   without a full `CoverSpec` (no front/back/spine image paths) can still get
   a `CanvasLayout`,
2. paints the bleed and a "danger zone" safety margin in pink (matching the
   look of a print service's own mockup templates), the back/front trim
   boxes in white and the spine trim box in gray,
3. draws dimension labels directly on the canvas: the spine width (reusing
   `compositor.py:draw_spine_text()` for the same rotated-text treatment),
   centered panel captions, and a compact info block (trim size, bleed,
   danger zone, spine width, page count/paper, total canvas size in mm and
   px, DPI),
4. exports via a new `exporter.py:export_png()` (which `export_preview_image()`
   now also delegates to, instead of duplicating the save call).

`MockupSpec.labels` lets a caller override the English text baked into the
image with already-translated strings — `core/` has no i18n of its own, so
`gui/widgets/cover_mockup.py` builds this dict from `self.tr(...)` calls,
which is what makes the rendered PNG follow the app's selected language.

It shares the same `on_progress` callback contract as the other two entry
points.

## GUI

- `gui/main_window.py` is a thin `QMainWindow` shell: the **Language**,
  **Help**, and **About** menus, plus a `QTabWidget` holding the three tool
  widgets. Each tab widget owns its own pickers, form, and background
  worker. **Help > User manual** renders the bundled
  `resources/docs/{en,bg}/usage-manual.md` with `QTextBrowser.setMarkdown()`
  for the currently selected language; **About > About Tvorec Cover** shows
  the bundled `resources/assets/logo.png` plus version/author info.
- `gui/widgets/cover_builder.py:CoverBuilderWidget` is the wrap-around cover
  tool, wiring together `gui/widgets/image_picker.py` (drag & drop / file
  dialog image slots), `gui/widgets/parameters_form.py` (all non-image
  `CoverSpec` fields), and `gui/widgets/preview.py` (a schematic layout
  preview).
- `gui/widgets/single_image.py:SingleImageWidget` is the single-image tool: a
  single picker, a compact parameters form, and a result-preview panel,
  driving `core.single.process_single_image()`.
- `gui/widgets/cover_mockup.py:CoverMockupWidget` is the mockup tool: no
  image picker, just trim/paper/bleed/danger-zone/DPI fields (reusing
  `gui/widgets/preview.py:SchematicPreview` for the same layout sketch as the
  Cover builder tab) driving `core.mockup.generate_mockup()`. It builds the
  `MockupSpec.labels` dict from `self.tr(...)` calls so the text baked into
  the rendered PNG is localized too.
- `gui/workers.py` runs the core pipelines off the UI thread on a `QThread`,
  emitting Qt signals for progress/success/failure so upscaling and export
  never block the UI. `GenerateWorker` wraps `pipeline.generate_cover()`;
  `SingleImageWorker` wraps `single.process_single_image()`;
  `MockupWorker` wraps `mockup.generate_mockup()`.
- `gui/theme.qss` is a flat, modern stylesheet layered on top of Qt's
  `Fusion` style (see `app.py:apply_theme`).
- All user-facing strings are wrapped in `self.tr(...)` so they're
  extractable by Qt Linguist tooling — see the `add-translation` skill in
  `.claude/skills/` for the workflow to add new translatable strings.

## Testing

- `tests/core/` — fast, no Qt dependency, exercise geometry math, canvas
  composition (pixel-level assertions), PDF export, and the full pipeline
  end-to-end with synthetic in-memory images.
- `tests/gui/` — a couple of `pytest-qt` smoke tests (window opens; filling
  the form + picking temp images + clicking Generate produces a PDF). Kept
  intentionally minimal: GUI tests are expensive to write and maintain
  relative to the bugs they catch, compared to the `core/` test suite.

Run everything with `uv run pytest`. GUI tests need a display; if running
headless (e.g. CI, this dev container), set `QT_QPA_PLATFORM=offscreen`.
