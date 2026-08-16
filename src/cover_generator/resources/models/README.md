# Upscale models

The optional AI upscaling step (see `core/upscale.py`) uses OpenCV's
`dnn_superres` module with an FSRCNN model file, e.g. `FSRCNN_x4.pb`.

This binary model file is **not** committed to the repository. To use AI
upscaling:

1. Install the optional dependency: `uv sync --extra upscale`.
2. Download an FSRCNN model (search for "FSRCNN_x4.pb opencv dnn_superres" —
   it is commonly distributed alongside OpenCV's `opencv_contrib` samples).
3. Place it somewhere on disk and pass its path as `CoverSpec.model_path`.

If no model file is configured, or OpenCV isn't installed, Tvorec Cover
automatically falls back to a standard Lanczos resize.
