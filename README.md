# Tvorec Cover (Творец корици)

A cross-platform desktop app (Windows, macOS, Linux) for building
print-ready, wrap-around book covers — back cover, spine, and front cover —
from separate images. Built for self-publishers and small presses who need a
repeatable way to turn artwork into a correctly-sized PDF for a
print-on-demand service.

🇧🇬 **Български:** Настолно приложение за изготвяне на готови за печат корици
на книги от отделни изображения за предна корица, гръб и задна корица.
Пълна документация на български: [docs/bg/index.md](docs/bg/index.md).

## What it does

Given a front cover image, a back cover image, and (optionally) a spine
image, plus page count, paper type, trim size, bleed and DPI, Cover
Generator:

- computes the correct spine width and the full wrap-around canvas size,
- upscales undersized source images (AI super-resolution if available,
  otherwise a standard resize) so low-res art doesn't end up blurry,
- assembles everything into one canvas, optionally with title/author text
  rotated along the spine,
- exports a single-page, print-resolution PDF.

It's a GUI app (PySide6) with drag-and-drop image pickers, a live layout
preview, background processing (the UI never freezes during generation),
and full English/Bulgarian localization.

A third tab, **Cover mockup**, renders a blank, actual-size template PNG (no
artwork) with the bleed and a "danger zone" safety margin marked in pink and
every dimension printed on the image -- open it in Krita, Inkscape, or a
similar editor as a real-size guide layer while designing cover art.

## Quickstart

Requires [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run tvorec-cover
```

See [docs/en/installation.md](docs/en/installation.md) for details,
including the optional AI-upscaling extra.

Prefer not to install Python at all? Standalone Windows/macOS/Linux binaries
are built automatically on every tagged release and attached to the
project's GitHub Releases page.

The full usage manual is also built into the app itself (**Help > User
manual**), in whichever language you have selected — no internet connection
needed.

## Documentation

- [English docs](docs/en/index.md) — overview, installation, full usage
  manual, and architecture notes for contributors.
- [Bulgarian docs](docs/bg/index.md) — overview, installation, and usage
  manual.

## Development

```bash
uv sync --group dev
uv run pytest      # run tests
uv run ruff check  # lint
```

The codebase is split into a Qt-free, unit-tested `core/` pipeline and a
`gui/` layer built on top of it — see
[docs/en/architecture.md](docs/en/architecture.md) for the full breakdown.

Every push and pull request runs lint + tests on Windows, macOS, and Linux
via GitHub Actions (`.github/workflows/ci.yml`); pushing a `v*` tag builds
and publishes standalone binaries for all three OSes as a GitHub Release
(`.github/workflows/release.yml`) — see the `build-release` skill in
`.claude/skills/` for building one locally.

## License

GNU GENERAL PUBLIC LICENSE
