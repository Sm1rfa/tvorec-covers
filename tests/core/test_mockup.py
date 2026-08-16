from PIL import Image

from cover_generator.core import mockup
from cover_generator.core.geometry import compute_canvas_layout_from_params, compute_spine_width_mm
from cover_generator.core.mockup import generate_mockup
from cover_generator.core.models import MockupSpec, PaperType, TrimSize

A5 = TrimSize(148.0, 210.0, "A5")


def test_mockup_output_size_matches_layout(tmp_path):
    output_path = tmp_path / "mockup.png"
    spec = MockupSpec(
        output_path=output_path,
        trim_size=A5,
        pages=220,
        paper_type=PaperType.CREAM,
        bleed_mm=3.0,
        danger_zone_mm=5.0,
        dpi=300,
    )

    result = generate_mockup(spec)
    expected = compute_canvas_layout_from_params(A5, 3.0, 300, 220, PaperType.CREAM)

    assert result == output_path
    with Image.open(output_path) as out:
        assert out.size == (expected.total_w_px, expected.total_h_px)


def test_mockup_corner_is_bleed_color(tmp_path):
    output_path = tmp_path / "mockup.png"
    spec = MockupSpec(output_path=output_path, trim_size=A5, bleed_mm=3.0, dpi=300)
    generate_mockup(spec)

    with Image.open(output_path) as out:
        assert out.getpixel((1, 1)) == mockup.BLEED_COLOR


def test_mockup_danger_zone_band_is_bleed_color(tmp_path):
    output_path = tmp_path / "mockup.png"
    spec = MockupSpec(
        output_path=output_path,
        trim_size=A5,
        pages=220,
        paper_type=PaperType.CREAM,
        bleed_mm=3.0,
        danger_zone_mm=5.0,
        dpi=300,
    )
    generate_mockup(spec)

    layout = compute_canvas_layout_from_params(A5, 3.0, 300, 220, PaperType.CREAM)
    x = layout.bleed_px + 2  # just inside the back panel's outer-left trim edge
    y = layout.total_h_px // 2  # vertically centered, away from any text

    with Image.open(output_path) as out:
        assert out.getpixel((x, y)) == mockup.BLEED_COLOR


def test_mockup_safe_interior_is_not_bleed_color(tmp_path):
    output_path = tmp_path / "mockup.png"
    spec = MockupSpec(
        output_path=output_path,
        trim_size=A5,
        pages=220,
        paper_type=PaperType.CREAM,
        bleed_mm=3.0,
        danger_zone_mm=5.0,
        dpi=300,
    )
    generate_mockup(spec)

    layout = compute_canvas_layout_from_params(A5, 3.0, 300, 220, PaperType.CREAM)
    # Bottom-right-ish area of the back panel: inside the trim, outside the
    # danger zone band, and away from the centered caption / info block text.
    x = layout.bleed_px + layout.page_w_px - 48
    y = layout.bleed_px + layout.page_h_px - 80

    with Image.open(output_path) as out:
        pixel = out.getpixel((x, y))
        assert pixel != mockup.BLEED_COLOR
        assert pixel == (255, 255, 255)


def test_mockup_spine_width_override_changes_output_size(tmp_path):
    output_path = tmp_path / "mockup.png"
    spec = MockupSpec(
        output_path=output_path,
        trim_size=A5,
        pages=220,
        paper_type=PaperType.CREAM,
        bleed_mm=3.0,
        dpi=300,
        spine_width_mm=20.0,
    )
    generate_mockup(spec)

    expected = compute_canvas_layout_from_params(
        A5, 3.0, 300, 220, PaperType.CREAM, spine_width_mm=20.0
    )
    default_layout = compute_canvas_layout_from_params(A5, 3.0, 300, 220, PaperType.CREAM)

    assert expected.spine_w_px != default_layout.spine_w_px
    with Image.open(output_path) as out:
        assert out.size == (expected.total_w_px, expected.total_h_px)


def test_mockup_offset_paper_type_works_end_to_end(tmp_path):
    output_path = tmp_path / "mockup.png"
    spec = MockupSpec(
        output_path=output_path,
        trim_size=A5,
        pages=300,
        paper_type=PaperType.OFFSET,
        bleed_mm=3.0,
        dpi=300,
    )
    generate_mockup(spec)

    spine_mm = compute_spine_width_mm(300, PaperType.OFFSET)
    assert spine_mm > 0
    expected = compute_canvas_layout_from_params(A5, 3.0, 300, 300, PaperType.OFFSET)
    with Image.open(output_path) as out:
        assert out.size == (expected.total_w_px, expected.total_h_px)
