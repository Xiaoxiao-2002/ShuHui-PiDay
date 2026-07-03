"""Generate deterministic PWA icons without storing a design-tool source file."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "public" / "icons"


def font_for(size: int) -> ImageFont.FreeTypeFont:
    candidates = (
        Path("C:/Windows/Fonts/cambria.ttc"),
        Path("C:/Windows/Fonts/seguisym.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
    )
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), int(size * 0.56))
    return ImageFont.load_default(size=int(size * 0.5))


def generate(size: int) -> None:
    image = Image.new("RGB", (size, size), "#f5f2e9")
    draw = ImageDraw.Draw(image)
    inset = int(size * 0.055)
    radius = int(size * 0.22)
    draw.rounded_rectangle(
        (inset, inset, size - inset, size - inset),
        radius=radius,
        fill="#132b49",
    )
    accent = int(size * 0.025)
    draw.arc(
        (size * 0.17, size * 0.17, size * 0.83, size * 0.83),
        200,
        520,
        fill="#e99a3e",
        width=max(accent, 2),
    )
    font = font_for(size)
    bbox = draw.textbbox((0, 0), "π", font=font)
    x = (size - (bbox[2] - bbox[0])) / 2 - bbox[0]
    y = (size - (bbox[3] - bbox[1])) / 2 - bbox[1] - size * 0.015
    draw.text((x, y), "π", font=font, fill="#ffffff")
    image.save(OUT / f"icon-{size}.png", optimize=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        generate(size)
    print(f"Generated PWA icons in {OUT}")


if __name__ == "__main__":
    main()
