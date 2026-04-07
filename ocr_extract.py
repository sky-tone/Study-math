"""
OCR 提取工具
============
从扫描件 PDF 中提取文字内容。
使用 PyMuPDF 渲染页面为图像，再用 RapidOCR 进行中文识别。

用法：
    python ocr_extract.py                   # 提取所有扫描件PDF
    python ocr_extract.py "GZMK数学试卷1.pdf"  # 提取指定PDF
"""

import fitz  # PyMuPDF
import os
import sys
import time
import numpy as np

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DPI = 300  # 渲染分辨率，越高越清晰但越慢

# 扫描件 PDF 列表（PyMuPDF 无法直接提取文字的文件）
SCAN_PDFS = [
    "GZMK数学试卷1.pdf",
    "GZMK数学试卷2.pdf",
]


def pdf_page_to_image(page, dpi=300):
    """将 PDF 页面渲染为 numpy 数组（RGB图像）"""
    zoom = dpi / 72  # PDF 默认 72 DPI
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    # 转为 numpy 数组
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3)
    return img


def extract_pdf_with_ocr(pdf_path, output_path=None, dpi=300, verbose=True):
    """
    对扫描件 PDF 进行 OCR 提取。
    
    Args:
        pdf_path: PDF 文件路径
        output_path: 输出文本文件路径（默认自动生成）
        dpi: 渲染分辨率
        verbose: 是否打印进度
    
    Returns:
        提取的全部文本内容
    """
    from rapidocr_onnxruntime import RapidOCR

    if not os.path.exists(pdf_path):
        print(f"[ERROR] 文件不存在: {pdf_path}")
        return ""

    pdf_name = os.path.basename(pdf_path)
    if output_path is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        out_name = os.path.splitext(pdf_name)[0] + "_ocr.txt"
        output_path = os.path.join(DATA_DIR, out_name)

    if verbose:
        print(f"\n{'='*60}")
        print(f"[OCR] 正在提取: {pdf_name}")
        print(f"{'='*60}")

    # 初始化 OCR 引擎
    ocr = RapidOCR()
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    all_text = []
    start_time = time.time()

    for i, page in enumerate(doc):
        page_start = time.time()
        if verbose:
            print(f"  [Page {i+1}/{total_pages}]", end=" ", flush=True)

        # 渲染页面为图像
        img = pdf_page_to_image(page, dpi=dpi)

        # OCR 识别
        result, _ = ocr(img)

        if result:
            # 提取识别到的文本行
            page_lines = []
            for line in result:
                # result 每项格式: [坐标框, 文本, 置信度]
                text = line[1]
                confidence = float(line[2]) if line[2] is not None else 0
                if confidence > 0.5:  # 过滤低置信度结果
                    page_lines.append(text)

            page_text = "\n".join(page_lines)
            all_text.append(f"=== 第{i+1}页 ===\n{page_text}")
            
            if verbose:
                elapsed = time.time() - page_start
                print(f"OK {len(page_lines)} lines ({elapsed:.1f}s)")
        else:
            all_text.append(f"=== 第{i+1}页 ===\n（空白页或无法识别）")
            if verbose:
                print("(blank)")

    doc.close()

    # 保存结果
    full_text = "\n\n".join(all_text)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    total_time = time.time() - start_time
    if verbose:
        print(f"\n[DONE] OCR 提取完成!")
        print(f"   总用时: {total_time:.1f} 秒")
        print(f"   总页数: {total_pages}")
        print(f"   输出文件: {output_path}")

    return full_text


def extract_all_scans(dpi=300):
    """提取所有扫描件 PDF"""
    for pdf_name in SCAN_PDFS:
        pdf_path = os.path.join(BASE_DIR, pdf_name)
        if os.path.exists(pdf_path):
            extract_pdf_with_ocr(pdf_path, dpi=dpi)
        else:
            print(f"[SKIP] 文件不存在: {pdf_name}")


def quick_preview(pdf_path, pages=None, dpi=200):
    """
    快速预览指定页面的 OCR 结果（不保存文件）。
    
    Args:
        pdf_path: PDF 文件路径
        pages: 要预览的页码列表（从1开始），None=前3页
        dpi: 渲染分辨率（预览用较低分辨率加速）
    """
    from rapidocr_onnxruntime import RapidOCR

    ocr = RapidOCR()
    doc = fitz.open(pdf_path)
    
    if pages is None:
        pages = list(range(1, min(4, len(doc) + 1)))

    for page_num in pages:
        if page_num < 1 or page_num > len(doc):
            print(f"[WARN] 页码 {page_num} 超出范围 (1-{len(doc)})")
            continue

        page = doc[page_num - 1]
        img = pdf_page_to_image(page, dpi=dpi)
        result, _ = ocr(img)

        print(f"\n{'='*50}")
        print(f"[Page {page_num}] OCR 结果：")
        print(f"{'='*50}")

        if result:
            for line in result:
                text, conf = line[1], line[2]
                if conf > 0.5:
                    print(f"  [{conf:.2f}] {text}")
        else:
            print("  （无识别结果）")

    doc.close()


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 提取指定文件
        for pdf_file in sys.argv[1:]:
            pdf_path = os.path.join(BASE_DIR, pdf_file) if not os.path.isabs(pdf_file) else pdf_file
            extract_pdf_with_ocr(pdf_path)
    else:
        # 提取所有扫描件
        print("[*] 开始 OCR 提取所有扫描件 PDF...")
        print(f"   目标文件: {SCAN_PDFS}")
        print(f"   渲染分辨率: {DPI} DPI")
        print()
        extract_all_scans(dpi=DPI)
        print("\n[DONE] 全部完成!")
