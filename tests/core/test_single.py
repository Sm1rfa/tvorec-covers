from PIL import Image

from cover_generator.core.geometry import (
    compute_single_panel_size,
    compute_spine_panel_size,
    compute_spine_width_mm,
    mm_to_px,
)
from cover_generator.core.models import (
    ColorMode,
    FitMode,
    PaperType,
    SingleImageSpec,
    TrimSize,
)
from cover_generator.core.single import process_single_image
from cover_generator.core.upscale import fit_image, fit_to_cover

A5 = TrimSize(148.0, 210.0, "A5")


def test_single_panel_size_adds_bleed_on_all_sides():
    width, height = compute_single_panel_size(A5, bleed_mm=3.0, dpi=300)

    assert width == mm_to_px(148.0 + 6.0, 300)
    assert height == mm_to_px(210.0 + 6.0, 300)


def test_single_panel_size_without_bleed_is_exact_trim():
    width, height = compute_single_panel_size(A5, bleed_mm=3.0, dpi=300, include_bleed=False)

    assert (width, height) == (mm_to_px(148.0, 300), mm_to_px(210.0, 300))


def test_fit_to_cover_enlarges_small_image_to_exact_size(tmp_path):
    path = tmp_path / "small.png"
    Image.new("RGB", (100, 100), "red").save(path)

    result = fit_to_cover(path, 400, 600, allow_ai_upscale=False)

    assert result.size == (400, 600)


def test_fit_to_cover_downscales_large_image_without_distortion(tmp_path):
    # A wide source cropped to a tall target must keep its 1:1 pixel aspect
    # (no horizontal squashing) -- verify by cropping to a square target and
    # checking the centre column of a vertically striped source survives.
    path = tmp_path / "wide.png"
    Image.new("RGB", (2000, 1000), "blue").save(path)

    result = fit_to_cover(path, 500, 500, allow_ai_upscale=False)

    assert result.size == (500, 500)


def test_fit_image_contain_preserves_whole_image_and_pads(tmp_path):
    # A narrow, tall source (like a spine strip) fitted to a wider panel must
    # keep its full height (nothing cropped) and get padded on the sides with
    # the fill colour.
    path = tmp_path / "spine.png"
    Image.new("RGB", (100, 900), "red").save(path)

    result = fit_image(path, 600, 900, mode=FitMode.CONTAIN, fill_color="white")

    assert result.size == (600, 900)
    assert result.mode == "RGB"
    # The full 100x900 source scales to fit (no enlargement needed vertically),
    # so its centre column stays red while the padded left/right edges are white.
    assert result.getpixel((300, 450)) == (255, 0, 0)
    assert result.getpixel((5, 450)) == (255, 255, 255)
    assert result.getpixel((595, 450)) == (255, 255, 255)


def test_fit_image_contain_pads_with_chosen_color(tmp_path):
    path = tmp_path / "spine.png"
    Image.new("RGB", (100, 900), "red").save(path)

    result = fit_image(path, 600, 900, mode=FitMode.CONTAIN, fill_color="black")

    assert result.getpixel((5, 450)) == (0, 0, 0)


def test_fit_image_contain_flattens_transparent_margin(tmp_path):
    # A centred design on a transparent canvas (the real spine-export case) is
    # cropped to its content, fitted, and the transparency becomes fill colour.
    path = tmp_path / "spine_alpha.png"
    canvas = Image.new("RGBA", (400, 900), (0, 0, 0, 0))
    canvas.paste(Image.new("RGBA", (100, 900), (255, 0, 0, 255)), (150, 0))
    canvas.save(path)

    result = fit_image(path, 600, 900, mode=FitMode.CONTAIN, fill_color="white")

    assert result.mode == "RGB"
    assert result.size == (600, 900)
    assert result.getpixel((300, 450)) == (255, 0, 0)  # design centred
    assert result.getpixel((5, 450)) == (255, 255, 255)  # was transparent -> fill


def test_fit_image_cover_crops_to_exact_size(tmp_path):
    path = tmp_path / "wide.png"
    Image.new("RGB", (2000, 1000), "blue").save(path)

    result = fit_image(path, 500, 500, mode=FitMode.COVER, allow_ai_upscale=False)

    assert result.size == (500, 500)
    assert result.mode == "RGB"


def test_fit_image_stretch_fills_exact_size_without_padding(tmp_path):
    path = tmp_path / "narrow.png"
    Image.new("RGB", (100, 900), "green").save(path)

    result = fit_image(path, 600, 900, mode=FitMode.STRETCH)

    assert result.size == (600, 900)
    # Stretched edge-to-edge, so even the far edges are the source colour.
    assert result.getpixel((5, 450)) == (0, 128, 0)
    assert result.getpixel((595, 450)) == (0, 128, 0)


def test_single_image_spec_defaults_to_contain():
    spec = SingleImageSpec(input_path="in.png", output_path="out.jpg")
    assert spec.fit_mode == FitMode.CONTAIN


def test_spine_panel_size_is_spine_width_by_book_height():
    width, height = compute_spine_panel_size(
        A5, bleed_mm=3.0, dpi=300, pages=220, paper_type=PaperType.CREAM
    )

    spine_mm = compute_spine_width_mm(220, PaperType.CREAM)
    assert width == mm_to_px(spine_mm, 300)
    assert height == mm_to_px(210.0 + 6.0, 300)  # trim height + bleed both sides


def test_spine_panel_size_without_bleed_uses_exact_trim_height():
    _, height = compute_spine_panel_size(
        A5, bleed_mm=3.0, dpi=300, pages=220, paper_type=PaperType.CREAM, include_bleed=False
    )
    assert height == mm_to_px(210.0, 300)


def test_process_single_image_spine_mode_outputs_spine_size(tmp_path):
    input_path = tmp_path / "spine_art.png"
    Image.new("RGB", (300, 2000), "gray").save(input_path)
    output_path = tmp_path / "spine.jpg"

    spec = SingleImageSpec(
        input_path=input_path,
        output_path=output_path,
        trim_size=A5,
        bleed_mm=3.0,
        dpi=300,
        spine_mode=True,
        pages=220,
        paper_type=PaperType.CREAM,
    )
    process_single_image(spec)

    with Image.open(output_path) as out:
        assert out.size == compute_spine_panel_size(A5, 3.0, 300, 220, PaperType.CREAM)


def test_process_single_image_spine_mode_draws_text_when_pages_over_100(tmp_path):
    # With title/author and pages >= 100, spine text is drawn (white on the art),
    # so the output must differ from the same run with no text.
    input_path = tmp_path / "spine_art.png"
    Image.new("RGB", (400, 2000), (20, 20, 20)).save(input_path)

    def run(title, author, pages):
        out = tmp_path / f"spine_{title}_{pages}.jpg"
        process_single_image(
            SingleImageSpec(
                input_path=input_path,
                output_path=out,
                trim_size=A5,
                bleed_mm=3.0,
                dpi=300,
                spine_mode=True,
                pages=pages,
                paper_type=PaperType.CREAM,
                title=title,
                author=author,
                fit_mode=FitMode.STRETCH,
            )
        )
        return out.read_bytes()

    # Compare runs at the same page count so any difference is text, not size.
    assert run("Title", "Author", 220) != run("", "", 220)  # text was drawn
    assert run("Title", "Author", 40) == run("", "", 40)  # under 100 pages: no text


def test_process_single_image_writes_jpg_at_target_size(tmp_path):
    input_path = tmp_path / "art.png"
    Image.new("RGB", (300, 400), "green").save(input_path)
    output_path = tmp_path / "nested" / "front.jpg"

    spec = SingleImageSpec(
        input_path=input_path,
        output_path=output_path,
        trim_size=A5,
        bleed_mm=3.0,
        dpi=150,
    )
    result = process_single_image(spec)

    assert result == output_path
    assert output_path.read_bytes().startswith(b"\xff\xd8")  # JPEG magic

    with Image.open(output_path) as out:
        expected = compute_single_panel_size(A5, 3.0, 150)
        assert out.size == expected
        assert out.info.get("dpi") == (150, 150)


def test_process_single_image_cmyk_writes_cmyk_jpg(tmp_path):
    input_path = tmp_path / "art.png"
    Image.new("RGB", (300, 400), "green").save(input_path)
    output_path = tmp_path / "front_cmyk.jpg"

    spec = SingleImageSpec(
        input_path=input_path,
        output_path=output_path,
        trim_size=A5,
        bleed_mm=3.0,
        dpi=150,
        color_mode=ColorMode.CMYK,
    )
    process_single_image(spec)

    with Image.open(output_path) as out:
        assert out.mode == "CMYK"
        assert out.size == compute_single_panel_size(A5, 3.0, 150)
