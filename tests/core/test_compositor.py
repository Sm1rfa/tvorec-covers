from PIL import Image

from cover_generator.core.compositor import build_canvas
from cover_generator.core.geometry import compute_canvas_layout
from cover_generator.core.models import CoverSpec, PaperType, TrimSize


def _spec(tmp_path):
    return CoverSpec(
        front_path=tmp_path / "front.png",
        back_path=tmp_path / "back.png",
        output_path=tmp_path / "out.pdf",
        pages=220,
        paper_type=PaperType.CREAM,
        trim_size=TrimSize(148.0, 210.0, "A5"),
        bleed_mm=3.0,
        dpi=300,
    )


def test_build_canvas_has_expected_size(tmp_path):
    spec = _spec(tmp_path)
    layout = compute_canvas_layout(spec)

    front = Image.new("RGB", (layout.panel_w_px, layout.panel_h_px), "red")
    back = Image.new("RGB", (layout.panel_w_px, layout.panel_h_px), "blue")

    canvas = build_canvas(layout, front, back, None)

    assert canvas.size == (layout.total_w_px, layout.total_h_px)
    assert canvas.getpixel((layout.back_x + 1, 1)) == (0, 0, 255)
    assert canvas.getpixel((layout.front_x + 1, 1)) == (255, 0, 0)


def test_build_canvas_draws_black_spine_when_no_spine_image(tmp_path):
    spec = _spec(tmp_path)
    layout = compute_canvas_layout(spec)

    front = Image.new("RGB", (layout.panel_w_px, layout.panel_h_px), "red")
    back = Image.new("RGB", (layout.panel_w_px, layout.panel_h_px), "blue")

    canvas = build_canvas(layout, front, back, None)

    mid_spine_x = layout.spine_x + layout.spine_w_px // 2
    assert canvas.getpixel((mid_spine_x, layout.total_h_px - 1)) == (0, 0, 0)


def test_build_canvas_flattens_transparent_panel_edges(tmp_path):
    spec = _spec(tmp_path)
    layout = compute_canvas_layout(spec)

    # Simulate exported PNGs with a fully transparent border whose RGB channel
    # happens to be white -- the raw value must not leak through onto the canvas.
    front = Image.new("RGBA", (layout.panel_w_px, layout.panel_h_px), (255, 0, 0, 255))
    for x in range(layout.panel_w_px):
        front.putpixel((x, 0), (255, 255, 255, 0))
    back = Image.new("RGBA", (layout.panel_w_px, layout.panel_h_px), (0, 0, 255, 255))
    for x in range(layout.panel_w_px):
        back.putpixel((x, 0), (255, 255, 255, 0))

    canvas = build_canvas(layout, front, back, None)

    assert canvas.getpixel((layout.front_x, 0)) == (0, 0, 0)
    assert canvas.getpixel((layout.back_x, 0)) == (0, 0, 0)
