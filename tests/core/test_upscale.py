from PIL import Image

from cover_generator.core.upscale import crop_to_visible_content, ensure_min_size


def test_crop_to_visible_content_removes_transparent_padding():
    image = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
    for x in range(60, 140):
        for y in range(20, 80):
            image.putpixel((x, y), (255, 0, 0, 255))

    cropped = crop_to_visible_content(image)

    assert cropped.size == (80, 60)


def test_crop_to_visible_content_leaves_opaque_image_untouched():
    image = Image.new("RGB", (200, 100), "red")

    assert crop_to_visible_content(image) is image


def test_ensure_min_size_crops_padding_before_upscaling(tmp_path):
    path = tmp_path / "spine.png"
    image = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
    for x in range(60, 140):
        for y in range(20, 80):
            image.putpixel((x, y), (255, 0, 0, 255))
    image.save(path)

    result = ensure_min_size(path, 800, 600, allow_ai_upscale=False)

    assert result.size == (800, 600)
