from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from pypdf import PdfReader


PAGE_FOOTER_PATTERNS = (
    re.compile(r"版权所有.?北京火山引擎科技有限公司"),
    re.compile(r"^\d+/\d+$"),
)


def collapse_spaces(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\xa0", " ")).strip()


def looks_like_page_counter(line: str) -> bool:
    return bool(re.search(r"\b\d+/\d+\b$", line))


def should_insert_space(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return left[-1].isascii() and left[-1].isalnum() and right[0].isascii() and right[0].isalnum()


def join_fragments(parts: list[str]) -> str:
    if not parts:
        return ""
    merged = parts[0]
    for part in parts[1:]:
        if should_insert_space(merged, part):
            merged += " " + part
        else:
            merged += part
    return merged


def clean_lines(page_text: str) -> list[str]:
    cleaned: list[str] = []
    for raw_line in page_text.splitlines():
        line = collapse_spaces(raw_line)
        if not line:
            cleaned.append("")
            continue
        if any(pattern.search(line) for pattern in PAGE_FOOTER_PATTERNS):
            continue
        if looks_like_page_counter(line):
            continue
        cleaned.append(line)

    while cleaned and not cleaned[0]:
        cleaned.pop(0)
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return cleaned


def lines_to_markdown_blocks(lines: list[str]) -> str:
    blocks: list[str] = []
    paragraph_parts: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_parts
        if paragraph_parts:
            blocks.append(join_fragments(paragraph_parts))
            paragraph_parts = []

    for line in lines:
        if not line:
            flush_paragraph()
            continue

        is_short_heading = len(line) <= 32 and not re.search(r"[。；：，,.!?！？]$", line)
        is_numbered_heading = bool(re.match(r"^\d+(\.\d+)*[ )、.]?", line))
        if is_short_heading or is_numbered_heading:
            flush_paragraph()
            blocks.append(f"### {line}")
            continue

        paragraph_parts.append(line)

    flush_paragraph()
    return "\n\n".join(blocks).strip()


def safe_asset_name(name: str) -> str:
    stem = Path(name).stem or "image"
    suffix = Path(name).suffix or ".png"
    stem = re.sub(r"[^0-9A-Za-z._-]+", "_", stem).strip("._-") or "image"
    return f"{stem}{suffix}"


def extract_page_images(page, assets_dir: Path, page_index: int, min_image_bytes: int) -> list[str]:
    image_paths: list[str] = []
    try:
        images = list(page.images)
    except Exception:
        return image_paths

    for image_index, image in enumerate(images, start=1):
        data = image.data or b""
        if len(data) < min_image_bytes:
            continue
        filename = f"page-{page_index:04d}-image-{image_index:02d}-{safe_asset_name(image.name)}"
        output_path = assets_dir / filename
        output_path.write_bytes(data)
        image_paths.append(output_path.name)
    return image_paths


def convert_pdf(
    pdf_path: Path,
    overwrite: bool,
    with_images: bool,
    max_image_pages: int,
    max_images_per_page: int,
    min_image_bytes: int,
) -> Path:
    md_path = pdf_path.with_suffix(".md")
    if md_path.exists() and not overwrite:
        return md_path

    reader = PdfReader(str(pdf_path))
    title = pdf_path.stem
    assets_dir = pdf_path.with_suffix("")
    assets_dir = assets_dir.with_name(f"{assets_dir.name}_assets")

    can_extract_images = with_images and len(reader.pages) <= max_image_pages
    if can_extract_images:
        if assets_dir.exists() and overwrite:
            shutil.rmtree(assets_dir, ignore_errors=True)
        assets_dir.mkdir(exist_ok=True)

    with md_path.open("w", encoding="utf-8") as handle:
        handle.write(f"# {title}\n\n")
        handle.write(f"- Source PDF: `{pdf_path.name}`\n")
        handle.write(f"- Pages: {len(reader.pages)}\n\n")
        if with_images and not can_extract_images:
            handle.write(
                f"> Image extraction skipped because this PDF has {len(reader.pages)} pages. "
                f"Use a smaller page limit or split the PDF first if full image retention is needed.\n\n"
            )
        handle.write("---\n")

        for page_index, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            lines = clean_lines(page_text)
            page_md = lines_to_markdown_blocks(lines)
            handle.write(f"\n\n## Page {page_index}\n\n")
            if page_md:
                handle.write(page_md)
            else:
                handle.write("_No extractable text on this page._")

            if can_extract_images:
                image_paths = extract_page_images(
                    page,
                    assets_dir=assets_dir,
                    page_index=page_index,
                    min_image_bytes=min_image_bytes,
                )
                if len(image_paths) > max_images_per_page:
                    image_paths = image_paths[:max_images_per_page]
                for image_name in image_paths:
                    rel_path = f"{assets_dir.name}/{image_name}"
                    handle.write(f"\n\n![Page {page_index} image]({rel_path})")

    return md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert PDF files to Markdown.")
    parser.add_argument("--input-dir", required=True, help="Directory containing PDF files.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing Markdown files.")
    parser.add_argument("--with-images", action="store_true", help="Extract embedded images and reference them from Markdown.")
    parser.add_argument("--max-image-pages", type=int, default=300, help="Skip image extraction for PDFs above this page count.")
    parser.add_argument("--max-images-per-page", type=int, default=12, help="Maximum images to reference per page.")
    parser.add_argument("--min-image-bytes", type=int, default=2048, help="Skip tiny images such as icons and spacers.")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        raise SystemExit(f"No PDF files found in: {input_dir}")

    for pdf_path in pdf_files:
        md_path = convert_pdf(
            pdf_path,
            overwrite=args.overwrite,
            with_images=args.with_images,
            max_image_pages=args.max_image_pages,
            max_images_per_page=args.max_images_per_page,
            min_image_bytes=args.min_image_bytes,
        )
        print(f"OK {pdf_path.name} -> {md_path.name}")


if __name__ == "__main__":
    main()
