# Book Cover Generator — Full Project Build

## Context

The repo currently has one prototype script, [book-cover.py](book-cover.py): it builds a single front+spine+back wrap-around cover image from two/three input images, computes spine width from page count, optionally upscales low-res images with OpenCV's FSRCNN model, draws spine text, and exports a print-ready PDF. `.claude/` and `docs/` are empty, there's no `pyproject.toml`, no tests, no GUI, and no git repo yet.

The goal: turn this into a proper cross-platform desktop application — PySide6 GUI, `uv`-managed packaging, testable core engine, BG/EN localization for both the app and the docs, and Claude Code tooling (agents/skills/commands) tailored to this project so future work on it is well-supported.

Decisions already made with the user:
- GUI framework: **PySide6** (Qt) — native look, mature, has built-in i18n tooling (Qt Linguist) that maps directly onto the BG/EN requirement.
- Upscaling: keep the existing OpenCV FSRCNN approach, but make it an **optional** step (optional dependency extra + graceful fallback to Lanczos resize if model/opencv missing).
- Go straight to full plan, no separate MVP-scoping conversation.

## Target project layout

```
pyproject.toml                 # uv-managed, src layout
README.md                      # EN, with BG summary + links to docs/bg
.gitignore

src/cover_generator/
  __init__.py
  __main__.py                  # `python -m cover_generator` / console entry point
  app.py                       # QApplication bootstrap, QTranslator loading, theme
  core/
    __init__.py
    models.py                  # CoverSpec, PaperType, TrimSizePreset dataclasses/enums
    geometry.py                 # mm<->px conversion, spine width calc (pure functions)
    upscale.py                  # AI upscale backend, optional, Lanczos fallback
    compositor.py               # builds the wrap-around canvas, pastes images, spine text
    exporter.py                  # writes the final PDF
    pipeline.py                  # orchestrates geometry -> upscale -> compositor -> exporter
  gui/
    __init__.py
    main_window.py
    widgets/
      image_picker.py           # front/back/spine file pickers + thumbnails
      parameters_form.py        # pages, paper type, trim size, bleed, dpi, title/author
      preview.py                # schematic + generated preview
    workers.py                   # QThread/QRunnable wrapper around core.pipeline
    theme.qss                    # modern flat stylesheet (Fusion style base)
  i18n/
    cover_generator_en.ts/.qm
    cover_generator_bg.ts/.qm
  resources/
    models/README.md             # where to get FSRCNN_x4.pb, not committed (binary)

tests/
  core/
    test_geometry.py
    test_compositor.py
    test_exporter.py
    test_pipeline.py
  gui/
    test_main_window.py          # pytest-qt smoke tests

docs/
  en/{index,installation,usage-manual,architecture}.md
  bg/{index,installation,usage-manual}.md   # architecture.md stays EN-only (dev-facing)

.claude/
  agents/
    cover-engine.md              # image/PDF math + Pillow/OpenCV specialist
    qt-ui.md                     # PySide6 widgets/layout/theming specialist
    i18n-maintainer.md           # keeps .ts files and docs/en+bg in sync
  skills/
    add-translation/SKILL.md     # workflow: wrap string in tr(), update .ts, lupdate/lrelease
    build-release/SKILL.md       # uv-based PyInstaller build for win/mac/linux
  commands/
    new-core-feature.md          # prompt template for adding a core pipeline feature
    sync-docs.md                 # prompt template for keeping EN/BG docs in lockstep
```

## Core engine design

- Refactor the logic in `book-cover.py` into pure, testable functions instead of one monolithic function:
  - `geometry.py`: `mm_to_px`, `compute_spine_width_mm`, `compute_canvas_dimensions` — no I/O, easy to unit test with known values (e.g. 220 pages cream → spine mm).
  - `upscale.py`: `needs_upscale(image, target_w, target_h)` and `upscale(image, ...)`. Try `cv2.dnn_superres` + bundled model path; if OpenCV/model unavailable, log a warning and fall back to `Image.resize(..., LANCZOS)`. This isolates the optional dependency so core tests don't require OpenCV installed.
  - `compositor.py`: takes already-sized PIL images + a `CoverSpec` and returns the assembled canvas, including the rotated spine text logic (ported from the existing script, using a bundled/system font lookup that also works without `Arial.ttf` present — fall back to Pillow's default font with a warning).
  - `exporter.py`: `export_pdf(canvas, output_path, dpi)`.
  - `pipeline.py`: `generate_cover(spec: CoverSpec) -> Path`, the single entry point the GUI calls; emits progress callbacks for the GUI worker to surface in a progress bar.
- `models.py` defines `PaperType` (cream/white) enum and `CoverSpec` dataclass (front/back/spine paths, pages, paper type, trim size, bleed, dpi, title, author, output path) — this is what both the GUI and tests construct.

## GUI design

- `main_window.py`: left/center panel with `parameters_form.py` (pages, paper type dropdown, trim size with common presets + custom mm entry, bleed, dpi, title/author fields, output path picker) and `image_picker.py` (three drag-and-drop/file-dialog slots with thumbnails for front/back/spine, spine optional).
- `preview.py`: schematic showing front/spine/back proportions live as parameters change, plus a "Generate Preview" (downscaled, fast) and "Generate" (full-res, real PDF) action.
- Generation runs in a `QThread` (`workers.py`) so upscaling/PDF export never blocks the UI; status bar + progress bar reflect pipeline callbacks; errors surface as a dialog instead of crashing.
- Styling: Qt `Fusion` style + a custom `theme.qss` (flat, modern palette, light theme to start) — avoids pulling in a heavy third-party theming library while still looking modern.
- Menu has a language switcher (EN/BG) persisted via `QSettings`; on change, reload `QTranslator` and `retranslateUi` (all GUI strings wrapped in `self.tr(...)` from the start so Qt Linguist tooling works).

## Packaging & tooling

- `pyproject.toml` via `uv`: `src` layout, console entry point `cover-generator = "cover_generator.app:main"`, dependency groups: core (`Pillow`, `PySide6`), optional extra `upscale` (`opencv-python`), dev group (`pytest`, `pytest-qt`, `ruff`).
- `uv run cover-generator` launches the app; `uv run pytest` runs tests.
- Document a PyInstaller-based build for Windows/macOS/Linux binaries (driven by the `build-release` skill), since "ready to distribute" GUI apps typically need a packaged executable rather than requiring end users to have Python/uv installed.

## Documentation

- `README.md`: English overview (what/why/how), short BG summary section near the top linking to `docs/bg/index.md`, install + quickstart, link to full docs.
- `docs/en/` and `docs/bg/`: `index.md` (overview), `installation.md` (uv setup, running, optional upscale extra), `usage-manual.md` (full GUI walkthrough — this is "the manual" requested in both languages). `docs/en/architecture.md` covers the core/gui split and pipeline for contributors (EN-only, dev-facing, not duplicated in BG since it's not user-facing).

## Testing strategy

- `tests/core/`: pure unit tests against `geometry`, `compositor` (pixel-level assertions: output canvas size, paste positions), `exporter` (PDF written, page size matches expected DPI/mm), `pipeline` (end-to-end with small synthetic PIL images, no real upscale model needed — exercise the Lanczos fallback path).
- `tests/gui/`: a couple of `pytest-qt` smoke tests (main window opens, filling the form + picking temp images + clicking Generate produces a PDF) — kept minimal given GUI test cost/value tradeoff.
- `ruff` for linting via `uv run ruff check`.

## .claude tooling

- **Agents** (`.claude/agents/`): `cover-engine.md` (Pillow/OpenCV/PDF math specialist for `core/`), `qt-ui.md` (PySide6 specialist for `gui/`), `i18n-maintainer.md` (keeps `.ts` translation files and `docs/en` + `docs/bg` content in sync, flags untranslated strings).
- **Skills** (`.claude/skills/`): `add-translation` (end-to-end workflow for adding a new translatable string: wrap in `tr()`, update `.ts` files, regenerate `.qm`), `build-release` (uv + PyInstaller cross-platform build steps).
- **Commands** (`.claude/commands/`): `new-core-feature.md` (prompt template scaffolding a new pipeline feature with matching test), `sync-docs.md` (prompt template for reconciling `docs/en` and `docs/bg` after a doc change).

## Build order

1. `pyproject.toml` + `src/cover_generator` skeleton + `uv sync` working, empty app launches.
2. Port `book-cover.py` logic into `core/` modules with unit tests passing.
3. Build GUI (`parameters_form`, `image_picker`, `main_window`) wired to `pipeline.generate_cover` via `workers.py`.
4. Add `theme.qss` styling and the schematic `preview.py`.
5. Wrap all GUI strings in `tr()`, generate `.ts` files, fill in EN/BG translations, wire `QTranslator` + language switcher.
6. Write `docs/en` + `docs/bg` + `README.md`.
7. Add `.claude/agents`, `.claude/skills`, `.claude/commands`.
8. Copy this plan into `docs/planning/initial-build-plan.md` (EN-only, dev-facing) so the project's own history of "why it's structured this way" lives in the repo, not just in the Claude plan cache.
9. Remove/retire `book-cover.py` (superseded by `core/` + GUI), confirming with user first since it's the only existing artifact.

## Verification

- `uv run pytest` green for all core tests.
- `uv run cover-generator` launches the GUI on the current (Linux) machine; manually generate a cover from sample images and confirm the output PDF opens and matches expected dimensions.
- Switch language in the GUI and confirm UI strings change to Bulgarian.
- Spot-check `docs/en` vs `docs/bg` cover the same sections.
