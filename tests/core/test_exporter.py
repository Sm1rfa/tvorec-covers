from PIL import Image

from cover_generator.core.exporter import export_jpg, export_pdf, export_preview_image
from cover_generator.core.models import ColorMode


def test_export_pdf_writes_file(tmp_path):
    canvas = Image.new("RGB", (300, 400), "white")
    output_path = tmp_path / "nested" / "cover.pdf"

    result = export_pdf(canvas, output_path, dpi=300)

    assert result == output_path
    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"%PDF")


def test_export_pdf_cmyk_mode_writes_valid_pdf(tmp_path):
    canvas = Image.new("RGB", (300, 400), "white")
    output_path = tmp_path / "cover_cmyk.pdf"

    result = export_pdf(canvas, output_path, dpi=300, color_mode=ColorMode.CMYK)

    assert result == output_path
    assert output_path.read_bytes().startswith(b"%PDF")
    # The source canvas must be untouched -- conversion happens on a copy.
    assert canvas.mode == "RGB"


def test_export_pdf_cmyk_falls_back_when_profile_is_invalid(tmp_path):
    canvas = Image.new("RGB", (300, 400), "white")
    output_path = tmp_path / "cover_cmyk_bad_profile.pdf"
    bogus_profile = tmp_path / "not_a_real.icc"
    bogus_profile.write_bytes(b"this is not a valid ICC profile")

    result = export_pdf(
        canvas, output_path, dpi=300, color_mode=ColorMode.CMYK, cmyk_profile_path=bogus_profile
    )

    assert result == output_path
    assert output_path.read_bytes().startswith(b"%PDF")


def test_export_jpg_rgb_by_default(tmp_path):
    image = Image.new("RGB", (200, 300), "orange")
    output_path = tmp_path / "out.jpg"

    export_jpg(image, output_path, dpi=150)

    with Image.open(output_path) as out:
        assert out.mode == "RGB"
        assert out.info.get("dpi") == (150, 150)


def test_export_jpg_cmyk_mode_writes_cmyk_jpeg(tmp_path):
    image = Image.new("RGB", (200, 300), "orange")
    output_path = tmp_path / "out_cmyk.jpg"

    export_jpg(image, output_path, dpi=150, color_mode=ColorMode.CMYK)

    assert output_path.read_bytes().startswith(b"\xff\xd8")  # JPEG magic
    with Image.open(output_path) as out:
        assert out.mode == "CMYK"
    # The source image must be untouched -- conversion happens on a copy.
    assert image.mode == "RGB"


def test_export_jpg_cmyk_embeds_icc_profile(tmp_path):
    # With a real profile the exported CMYK JPEG must carry the embedded ICC
    # profile, so colour-managed viewers/presses read the FOGRA39 numbers
    # correctly instead of rendering shifted/inverted "broken" colour.
    from cover_generator.core.icc_profiles import known_profile_path

    profile = known_profile_path("Coated FOGRA39 -- ISO Coated v2 (EU coated offset)")
    assert profile is not None  # bundled with the package

    image = Image.new("RGB", (200, 300), "orange")
    output_path = tmp_path / "out_cmyk_profiled.jpg"

    export_jpg(
        image,
        output_path,
        dpi=150,
        color_mode=ColorMode.CMYK,
        cmyk_profile_path=profile,
    )

    with Image.open(output_path) as out:
        assert out.mode == "CMYK"
        assert out.info.get("icc_profile")  # profile embedded, not dropped


def test_export_jpg_cmyk_falls_back_when_profile_is_invalid(tmp_path):
    image = Image.new("RGB", (200, 300), "orange")
    output_path = tmp_path / "out_cmyk_bad.jpg"
    bogus_profile = tmp_path / "not_a_real.icc"
    bogus_profile.write_bytes(b"this is not a valid ICC profile")

    export_jpg(
        image,
        output_path,
        dpi=150,
        color_mode=ColorMode.CMYK,
        cmyk_profile_path=bogus_profile,
    )

    with Image.open(output_path) as out:
        assert out.mode == "CMYK"


def test_export_preview_image_writes_png_next_to_pdf(tmp_path):
    canvas = Image.new("RGB", (300, 400), "white")
    pdf_path = tmp_path / "nested" / "cover.pdf"

    result = export_preview_image(canvas, pdf_path, dpi=300)

    assert result == pdf_path.with_suffix(".png")
    assert result.exists()
    assert result.read_bytes().startswith(b"\x89PNG")
