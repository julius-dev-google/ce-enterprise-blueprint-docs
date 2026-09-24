#!/usr/bin/env python3
"""
Convert PDF document pages into high-resolution PNG preview images.
===================================================================

Supports:
  1. macOS native rendering via PDFKit (scripts/pdf_to_images.swift) - zero dependencies.
  2. PyMuPDF (fitz) if installed in Python environment.
  3. pdf2image (poppler) if installed.

Usage:
  python3 pdf_to_images.py <input.pdf> <output_dir> [--scale 2.0]
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def convert_with_swift(pdf_path: Path, output_dir: Path) -> bool:
    swift_bin = shutil.which("swift")
    swift_script = Path(__file__).resolve().parent / "pdf_to_images.swift"
    if swift_bin and swift_script.exists():
        print("Using macOS native Swift/PDFKit renderer...")
        res = subprocess.run([swift_bin, str(swift_script), str(pdf_path), str(output_dir)])
        return res.returncode == 0
    return False

def convert_with_pymupdf(pdf_path: Path, output_dir: Path, scale: float = 2.0) -> bool:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return False

    print(f"Using PyMuPDF (fitz) at {scale}x resolution...")
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    matrix = fitz.Matrix(scale, scale)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix)
        out_path = output_dir / f"page_{i + 1}.png"
        pix.save(str(out_path))
        print(f"Rendered page {i + 1}/{len(doc)} -> {out_path}")
    return True

def convert_with_pdf2image(pdf_path: Path, output_dir: Path) -> bool:
    try:
        from pdf2image import convert_from_path
    except ImportError:
        return False

    print("Using pdf2image (poppler) at 150 DPI...")
    output_dir.mkdir(parents=True, exist_ok=True)
    images = convert_from_path(str(pdf_path), dpi=150)
    for i, img in enumerate(images):
        out_path = output_dir / f"page_{i + 1}.png"
        img.save(str(out_path), "PNG")
        print(f"Rendered page {i + 1}/{len(images)} -> {out_path}")
    return True

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 pdf_to_images.py <input.pdf> <output_dir> [scale]")
        sys.exit(1)

    pdf_path = Path(sys.argv[1]).resolve()
    output_dir = Path(sys.argv[2]).resolve()
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0

    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Try PyMuPDF
    if convert_with_pymupdf(pdf_path, output_dir, scale):
        print(f"Successfully converted pages to {output_dir}")
        return

    # 2. Try macOS Swift PDFKit
    if sys.platform == "darwin" and convert_with_swift(pdf_path, output_dir):
        print(f"Successfully converted pages to {output_dir}")
        return

    # 3. Try pdf2image
    if convert_with_pdf2image(pdf_path, output_dir):
        print(f"Successfully converted pages to {output_dir}")
        return

    print("Error: No PDF rasterizer available. Install 'pymupdf' (`pip install pymupdf`) or run on macOS with Swift.")
    sys.exit(1)

if __name__ == "__main__":
    main()
