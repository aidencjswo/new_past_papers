from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent
PDF_PATH = ROOT / "source.pdf"
IMAGE_DIR = ROOT / "ocr_images"
MANIFEST = ROOT / "image_manifest.tsv"


def main() -> None:
    IMAGE_DIR.mkdir(exist_ok=True)
    reader = PdfReader(str(PDF_PATH))
    rows = ["page\timage_index\tpath\tbytes\n"]

    for page_number, page in enumerate(reader.pages, 1):
        for image_index, image in enumerate(page.images, 1):
            suffix = Path(image.name).suffix or ".jpg"
            filename = f"page_{page_number:03d}_image_{image_index:02d}{suffix.lower()}"
            target = IMAGE_DIR / filename
            target.write_bytes(image.data)
            rows.append(
                f"{page_number}\t{image_index}\t{target.as_posix()}\t{len(image.data)}\n"
            )

    MANIFEST.write_text("".join(rows), encoding="utf-8")
    print(f"pages={len(reader.pages)} images={len(rows) - 1}")
    print(f"manifest={MANIFEST}")


if __name__ == "__main__":
    main()
