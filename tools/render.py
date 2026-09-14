#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""渲染来源 PDF 的页面/局部为 PNG，供转录和核对公式使用。

用法：
    python3 tools/render.py sources/2024-2025-秋冬-期中.pdf
    python3 tools/render.py sources/2016-2025-期中-历年真题汇编.pdf 11
    python3 tools/render.py sources/2016-2025-期中-历年真题汇编.pdf 11 --box 40,140,600,240 --zoom 5
输出：系统临时目录下的 png（整页默认 2.2 倍，局部默认 5 倍），路径会打印出来。
--box 为 PDF 点坐标 x0,y0,x1,y1（左上角为原点，A4 页面为 595×842）。
"""
import argparse
import sys
import tempfile
from pathlib import Path

CACHE = Path(tempfile.gettempdir()) / "线性代数-pages"


def parse_pages(spec: str) -> list[int]:
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            pages.extend(range(int(a), int(b) + 1))
        else:
            pages.append(int(part))
    return pages


def main() -> int:
    ap = argparse.ArgumentParser(description="渲染来源 PDF 为 PNG")
    ap.add_argument("pdf", help="来源 PDF 路径")
    ap.add_argument("pages", nargs="?", help="页码，如 1,2,5-7；缺省为全部")
    ap.add_argument("--box", help="只渲染局部：x0,y0,x1,y1")
    ap.add_argument("-z", "--zoom", type=float, default=None, help="缩放倍数（整页默认 2.2，局部默认 5）")
    args = ap.parse_args()

    import pymupdf

    src = Path(args.pdf)
    if not src.exists():
        print(f"找不到 {src}", file=sys.stderr)
        return 1
    doc = pymupdf.open(str(src))
    pages = parse_pages(args.pages) if args.pages else list(range(1, doc.page_count + 1))

    if args.box:
        box = [float(x) for x in args.box.split(",")]
        if len(box) != 4:
            print("--box 需要 x0,y0,x1,y1 四个数", file=sys.stderr)
            return 1
        zoom = args.zoom or 5.0
        outdir = CACHE / "crops"
        outdir.mkdir(parents=True, exist_ok=True)
        for n in pages:
            tag = "_".join(str(int(v)) for v in box)
            out = outdir / f"{src.stem}-p{n:02d}-{tag}.png"
            doc[n - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box)).save(str(out))
            print(out)
        return 0

    zoom = args.zoom or 2.2
    outdir = CACHE / src.stem
    outdir.mkdir(parents=True, exist_ok=True)
    for n in pages:
        if not 1 <= n <= doc.page_count:
            print(f"  跳过第 {n} 页（共 {doc.page_count} 页）", file=sys.stderr)
            continue
        out = outdir / f"p{n:02d}.png"
        doc[n - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).save(str(out))
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
