from cover_generator.core.geometry import (
    compute_canvas_layout,
    compute_canvas_layout_from_params,
    compute_spine_panel_size,
    compute_spine_width_mm,
    mm_to_px,
    unit_to_mm,
)
from cover_generator.core.models import CoverSpec, PaperType, TrimSize


def test_mm_to_px_at_300_dpi():
    assert mm_to_px(25.4, 300) == 300


def test_spine_width_uses_cream_thickness():
    assert compute_spine_width_mm(220, PaperType.CREAM) == 14.3


def test_spine_width_uses_white_thickness():
    assert compute_spine_width_mm(220, PaperType.WHITE) == 11.0


def test_spine_width_has_a_minimum():
    assert compute_spine_width_mm(10, PaperType.CREAM) == 10.0


def test_spine_panel_width_derives_from_pages_by_default():
    trim = TrimSize(148.0, 210.0, "A5")
    width_px, height_px = compute_spine_panel_size(
        trim, 3.0, 300, 329, PaperType.CREAM, include_bleed=True
    )
    assert width_px == mm_to_px(compute_spine_width_mm(329, PaperType.CREAM), 300)
    assert height_px == mm_to_px(216.0, 300)


def test_spine_panel_width_honours_override():
    trim = TrimSize(148.0, 210.0, "A5")
    width_px, _ = compute_spine_panel_size(
        trim, 3.0, 300, 329, PaperType.CREAM, include_bleed=True, spine_width_mm=18.15
    )
    # Override ignores the pages x paper estimate and uses the exact width.
    assert width_px == mm_to_px(18.15, 300)


def test_canvas_layout_total_width_matches_panels_plus_spine(tmp_path):
    spec = CoverSpec(
        front_path=tmp_path / "front.png",
        back_path=tmp_path / "back.png",
        output_path=tmp_path / "out.pdf",
        pages=220,
        paper_type=PaperType.CREAM,
        trim_size=TrimSize(148.0, 210.0, "A5"),
        bleed_mm=3.0,
        dpi=300,
    )
    layout = compute_canvas_layout(spec)

    assert layout.total_w_px == layout.panel_w_px * 2 + layout.spine_w_px
    assert layout.back_x == 0
    assert layout.spine_x == layout.panel_w_px
    assert layout.front_x == layout.panel_w_px + layout.spine_w_px


def test_canvas_layout_from_params_matches_canvas_layout_from_spec(tmp_path):
    spec = CoverSpec(
        front_path=tmp_path / "front.png",
        back_path=tmp_path / "back.png",
        output_path=tmp_path / "out.pdf",
        pages=220,
        paper_type=PaperType.CREAM,
        trim_size=TrimSize(148.0, 210.0, "A5"),
        bleed_mm=3.0,
        dpi=300,
    )

    from_spec = compute_canvas_layout(spec)
    from_params = compute_canvas_layout_from_params(
        spec.trim_size, spec.bleed_mm, spec.dpi, spec.pages, spec.paper_type
    )

    assert from_params == from_spec


def test_canvas_layout_from_params_honours_spine_width_override():
    trim = TrimSize(148.0, 210.0, "A5")

    default_layout = compute_canvas_layout_from_params(trim, 3.0, 300, 220, PaperType.CREAM)
    override_layout = compute_canvas_layout_from_params(
        trim, 3.0, 300, 220, PaperType.CREAM, spine_width_mm=18.15
    )

    assert override_layout.spine_w_px == mm_to_px(18.15, 300)
    assert override_layout.spine_w_px != default_layout.spine_w_px


def test_unit_to_mm_conversions():
    assert unit_to_mm(10, "mm") == 10.0
    assert unit_to_mm(1, "cm") == 10.0
    assert unit_to_mm(1, "in") == 25.4
    assert unit_to_mm(2, "pt") == 2 * 25.4 / 72
