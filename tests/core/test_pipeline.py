from PIL import Image

from cover_generator.core.models import CoverSpec, PaperType, TrimSize
from cover_generator.core.pipeline import generate_cover


def _make_image(path, size=(400, 600), color="green"):
    Image.new("RGB", size, color).save(path)


def test_generate_cover_end_to_end(tmp_path):
    front_path = tmp_path / "front.png"
    back_path = tmp_path / "back.png"
    output_path = tmp_path / "cover.pdf"
    _make_image(front_path)
    _make_image(back_path, color="orange")

    spec = CoverSpec(
        front_path=front_path,
        back_path=back_path,
        output_path=output_path,
        pages=150,
        paper_type=PaperType.CREAM,
        trim_size=TrimSize(148.0, 210.0, "A5"),
        bleed_mm=3.0,
        dpi=150,
        title="My Book",
        author="An Author",
        allow_upscale=False,
    )

    events: list[tuple[str, float]] = []
    result = generate_cover(spec, on_progress=lambda msg, frac: events.append((msg, frac)))

    assert result == output_path
    assert output_path.exists()
    assert events[0][1] == 0.0
    assert events[-1] == ("Done", 1.0)


def test_generate_cover_upscales_small_images(tmp_path):
    front_path = tmp_path / "front.png"
    back_path = tmp_path / "back.png"
    output_path = tmp_path / "cover.pdf"
    _make_image(front_path, size=(50, 50))
    _make_image(back_path, size=(50, 50), color="orange")

    spec = CoverSpec(
        front_path=front_path,
        back_path=back_path,
        output_path=output_path,
        pages=150,
        trim_size=TrimSize(148.0, 210.0, "A5"),
        dpi=150,
        allow_upscale=False,
    )

    result = generate_cover(spec)
    assert result.exists()


def test_generate_cover_exports_png_when_requested(tmp_path):
    front_path = tmp_path / "front.png"
    back_path = tmp_path / "back.png"
    output_path = tmp_path / "cover.pdf"
    _make_image(front_path)
    _make_image(back_path, color="orange")

    spec = CoverSpec(
        front_path=front_path,
        back_path=back_path,
        output_path=output_path,
        pages=150,
        trim_size=TrimSize(148.0, 210.0, "A5"),
        dpi=150,
        allow_upscale=False,
        export_png=True,
    )

    result = generate_cover(spec)
    assert result == output_path
    assert output_path.with_suffix(".png").exists()
