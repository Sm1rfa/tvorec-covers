# Tvorec Cover (Творец корици)

Tvorec Cover is a desktop application for building print-ready, wrap-around
book covers (back + spine + front) from separate cover images. It is built
for self-publishers and small presses who need a repeatable way to turn
artwork into a correctly-sized PDF for a print-on-demand service.

## What it does

Given a front cover image, a back cover image, and (optionally) a spine
image, Tvorec Cover:

1. Computes the spine width from the page count and paper stock.
2. Computes the full wrap-around canvas size in pixels from the trim size,
   bleed, and DPI you specify.
3. Upscales any image that is smaller than the size it needs to be (using an
   AI super-resolution model if available, otherwise a standard resize), so
   low-resolution source art doesn't produce a blurry cover.
4. Assembles the back, spine, and front panels into one canvas, optionally
   printing the title and author rotated along the spine.
5. Exports the result as a single-page, print-resolution PDF.

It also has a **Single image** tool for print services that take the front
and back cover as two separate uploads and compute the spine themselves
(e.g. [photopis](https://photopis.bg/prints/books)): it sizes one image to
trim plus bleed at your target DPI, upscales it if needed so it isn't blurry,
and exports a print-ready JPG.

A third **Cover mockup** tool renders a blank, actual-size template PNG (no
artwork) with the bleed and a "danger zone" safety margin marked in pink and
every dimension printed on the image, for use as a real-size guide layer
while designing cover art in an image editor.

## Where to go next

- [Installation](installation.md) — installing and running the app with `uv`.
- [Usage manual](usage-manual.md) — a full walkthrough of the GUI.
- [Architecture](architecture.md) — how the codebase is structured (for contributors).

This manual is also available in [Bulgarian](../bg/index.md).
