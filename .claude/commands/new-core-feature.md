---
description: Scaffold a new feature in the core pipeline with a matching test, following this project's core/ conventions.
---

Add a new feature to the `core/` pipeline of Tvorec Cover: $ARGUMENTS

Follow these conventions (see `.claude/agents/cover-engine.md` for the full
rationale):

1. If the feature needs a new parameter, add it to `CoverSpec` in
   `src/cover_generator/core/models.py` first, with a sensible default so
   existing callers don't break.
2. Keep `core/geometry.py` pure (no I/O, no Pillow/OpenCV imports) if the
   feature is layout math; put image-touching logic in `compositor.py` or
   `upscale.py` instead.
3. If the feature is optional or depends on an optional dependency, follow
   the pattern in `upscale.py`: detect availability, degrade gracefully,
   never raise ImportError up to the caller.
4. Wire it into `core/pipeline.py:generate_cover()` if it's part of the
   main flow, including an `on_progress` call if it's a distinct, possibly
   slow step.
5. Write a test in `tests/core/` covering the new behavior, plus update
   existing tests if the change affects `CanvasLayout` or canvas pixel
   positions.
6. If `gui/main_window.py` or `gui/widgets/parameters_form.py` need a new
   field to expose this, note that explicitly rather than silently leaving
   the feature unreachable from the UI — ask the user if it's in scope for
   this change.
7. Run `uv run pytest tests/core` and `uv run ruff check src/cover_generator/core tests/core`
   before considering it done.
