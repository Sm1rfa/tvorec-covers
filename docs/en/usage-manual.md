# Usage Manual

The app has three tabs:

- **Cover builder** — assembles a full wrap-around cover (back + spine +
  front) into one print-ready PDF. Covered in
  [The Cover builder tab](#the-cover-builder-tab) below.
- **Single image** — makes *one* image print-ready and exports it as a JPG.
  Use this for print services that take the front and back cover as two
  separate uploads and compute the spine themselves (e.g.
  [photopis](https://photopis.bg/prints/books)). Covered in
  [The Single image tab](#the-single-image-tab).
- **Cover mockup** — renders a blank, actual-size template PNG (no artwork)
  with the bleed and a "danger zone" safety margin marked in pink and all the
  sizing numbers printed on it, for use as a real-size guide layer while
  designing cover art in Krita, Inkscape, or similar. Covered in
  [The Cover mockup tab](#the-cover-mockup-tab).

## The Cover builder tab

This is a complete walkthrough of generating a wrap-around cover.

## 1. Choose your images

There are three image slots, left to right: **Back cover**, **Spine**, and
**Front cover**.

- **Back cover** and **Front cover** are required.
- **Spine** is optional — if you leave it empty, the spine area is filled
  with solid black, and the title/author (if set) are still printed on it.

For each slot you can either:

- click **Browse...** and pick a file, or
- drag an image file from your file manager and drop it onto the slot.

Supported formats: PNG, JPG/JPEG, TIFF, BMP, WEBP.

## 2. Set the book parameters

- **Page count** — used (together with paper type) to calculate spine
  thickness.
- **Paper type** — *Cream* or *White*. Cream stock is thicker per page, so it
  produces a wider spine for the same page count.
- **Trim size** — pick a common preset (5"x8", 5.5"x8.5", A5, 6"x9", A4) or
  choose **Custom...** to enter exact width/height in millimetres.
- **Bleed** — extra margin (in mm) added around the trim edges, standard
  practice for print-on-demand. 3mm is a safe default; check your printer's
  requirements.
- **Resolution (DPI)** — the output resolution. 300 DPI is standard for
  print.
- **Color mode** / **CMYK profile** — choose *RGB* (screen / most
  print-on-demand) or *CMYK* (offset / commercial print). In CMYK you can
  also pick an ICC profile — see
  [Color mode and CMYK profiles](#color-mode-and-cmyk-profiles) below.
- **Title** / **Author** — if set and the book has 100+ pages, these are
  printed rotated along the spine. Leave blank to omit spine text entirely.
- **Output PDF** — where the final PDF will be saved. You can also leave this
  blank and you'll be prompted for a location when you click **Generate**.

## 3. Check the layout preview

The panel below the parameters shows a live schematic of how the back,
spine, and front panels will be proportioned on the final canvas, updating
as you change parameters. This is a layout sketch, not the final artwork.

## 4. Preview or Generate

- **Preview** runs the full pipeline at a low resolution (96 DPI) and writes
  a quick low-res PDF to a temporary location — useful for sanity-checking
  composition and spine text placement without waiting for a full-resolution
  export.
- **Generate** runs the full pipeline at your configured DPI and saves the
  final, print-ready PDF to the **Output PDF** path.

Both actions run in the background, so the window stays responsive; progress
is shown in the status bar and progress bar at the bottom. If anything goes
wrong (e.g. an unreadable image file), an error dialog explains what
happened instead of the app crashing silently.

## The Single image tab

Some print services don't want a single wrap-around file — they ask you to
upload the **front cover** and the **back cover** as two separate images and
they calculate the spine for you. This tab prepares one such image at a time.

1. **Choose an image** — drop a file onto the slot or click **Browse...**.
   The line beneath the slot reports its pixel size and whether it's large
   enough for the target, or will need upscaling.
2. **Set the parameters:**
   - **Trim size** — a preset or **Custom...** width/height in millimetres.
   - **Bleed** and **Add bleed around the trim size** — when the checkbox is
     on, the bleed margin is added on all four sides (most services require
     it); turn it off to export at exactly the trim size.
   - **Resolution (DPI)** — 300 DPI is standard for print.
   - **JPG quality** — 95% is a good default; higher means larger files.
   - **Color mode** / **CMYK profile** — *RGB* or *CMYK*, exactly as in the
     Cover builder. In CMYK the image is written as a CMYK JPEG using the
     selected ICC profile; see
     [Color mode and CMYK profiles](#color-mode-and-cmyk-profiles).
   - **Output JPG** — where the file is saved (you're prompted if left
     blank).
3. **Fit mode** — how the image fills the panel when their shapes differ:
   *Fit whole image (pad)* keeps everything and pads the empty sides with the
   **Pad colour**; *Fill & crop* fills the panel and trims the overflow;
   *Stretch* distorts to the exact size. Images smaller than the target are
   upscaled first (AI super-resolution when available, see the installation
   guide, otherwise a high-quality resize) so they don't print blurry.
4. **Spine mode** (optional) — sizes the output to the book's spine instead of
   a full cover panel: the width is calculated from the **Pages** count and
   **Paper** stock, the height is the trim height (plus bleed). Optional
   **Title** and **Author** are drawn rotated along the spine.
   - **Override spine width** — if your print service publishes its own cover
     template with a specific spine width, tick this and enter that exact value
     in millimetres. The output then matches their spine column exactly and
     won't be rescaled (which is what makes a dropped-in spine look blurry),
     bypassing the page-count estimate. For example, if the template's spine is
     18.15 mm, set it to that regardless of what the page count would suggest.
5. **Preview or Generate** — **Preview** produces a quick low-resolution
   version and shows it in the panel so you can check the crop; **Generate**
   writes the full-resolution JPG to the **Output JPG** path.

Repeat once for the front cover and once for the back cover, then upload both
to your print service.

## Color mode and CMYK profiles

Both tabs can export in **RGB** or **CMYK**.

- **RGB** is right for screen use and most print-on-demand services — leave it
  on RGB unless your printer explicitly asks for CMYK.
- **CMYK** is for offset / commercial printing. To get accurate, predictable
  colors, CMYK conversion uses an **ICC profile**.

The app ships with the freely distributed **ECI** profile packs (ECI Offset
2009 and eciCMYK v2), so the common European offset profiles work out of the
box with no download. The default, **Coated FOGRA39 — ISO Coated v2 (EU coated
offset)**, is the standard choice for book covers on coated stock (ISO Coated
v2 is the FOGRA39 characterization, i.e. the same target Adobe calls "Coated
FOGRA39"). Other coated, uncoated and web-offset profiles are available in the
**CMYK profile** dropdown.

To use a profile the app doesn't bundle (for example a US **GRACoL** or
**SWOP** profile, or one your print house supplies):

- pick **Custom...** in the dropdown and point at any `.icc`/`.icm` file, or
- drop the file into your personal profiles folder — the status line under the
  dropdown shows the exact path and filename to use. A file placed there
  overrides the bundled copy of the same name.

If a selected profile can't be read for any reason, the export still succeeds
using a basic, uncalibrated conversion rather than failing. Whichever profile
you use, always confirm final colors with your print house before submitting.

## The Cover mockup tab

This tab doesn't take any images and doesn't produce final artwork. It
renders a blank PNG at the *exact pixel size* your final print file needs to
be, with the bleed and safety-margin zones painted pink and every dimension
printed on the image itself — a real-size scaffold you open in an image
editor (Krita, Inkscape, Photoshop, etc.) and design your cover art on top
of, so you always know exactly where the trim line, bleed, and danger zone
fall.

1. **Set the trim size** — pick a preset or **Custom...**, with a unit
   dropdown (mm/cm/in/pt) for entering exact width/height.
2. **Set the book parameters:**
   - **Paper type** — *Cream*, *White*, or *Offset* — affects the estimated
     spine width, same as the other two tabs.
   - **Page count** — used with paper type to estimate spine thickness.
   - **Bleed** and **Danger zone** — both in the unit chosen in the shared
     **Margin unit** dropdown (mm/cm/in/pt). Bleed is the extra margin
     outside the trim edge that gets cut off; the danger zone is a safety
     margin printed *just inside* the trim edge — keep important text and
     logos out of it. Both are marked pink on the rendered image, matching
     print-service mockup templates. The danger zone only runs along the
     board's four true outer edges (top, bottom, the back cover's outer-left
     edge, the front cover's outer-right edge) — not around the spine-fold
     seams, since art is expected to run right up to those.
   - **Override spine width** — same as in the Single image tab: tick this
     to enter an exact spine width in mm instead of estimating it from page
     count and paper stock, e.g. to match a print service's own template.
   - **Resolution (DPI)** — 300 DPI is standard for print.
   - **Output PNG** — where the file is saved (you're prompted if left
     blank).
3. **Check the layout preview** — the same schematic preview used in the
   Cover builder tab shows the back/spine/front proportions as you adjust
   parameters.
4. **Preview or Generate** — **Preview** renders a quick low-resolution
   (96 DPI) version to check the layout; **Generate** renders the
   full-resolution PNG at your exact final canvas size.

The generated PNG prints, directly on the image: each panel's trim size
("BACK COVER" / "FRONT COVER" with dimensions), the spine width (rotated
along the spine), and a small info block with the trim size, bleed, danger
zone, spine width, page count/paper type, and total canvas size in both mm
and pixels — so you never have to look anything up while designing.

## Switching the app language

Use the **Language** menu to switch between English and Bulgarian. Changing
the language takes effect after restarting the app.

## Help and About

This manual is also built into the app itself — no internet connection
needed. Open **Help > User manual** at any time to view it in your currently
selected language.

The **About** menu has two entries:

- **About Tvorec Cover** — the app version, a short description, and credit
  information.
- **ICC profiles & credits** — details and credits for the bundled CMYK ICC
  profiles (see [Color mode and CMYK profiles](#color-mode-and-cmyk-profiles)
  above).
