import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Union, Optional

from .cluster_parser import run_pipeline

# 嘗試讀取 .env（若沒有套件則靜默略過）
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass
from pdfminer.high_level import extract_text  # type: ignore


def read_pdf_text(pdf_path: Union[str, Path]) -> str:
    """嘗試多重策略擷取 PDF 文字：pdfminer → PyMuPDF → pdfplumber → OCR（若可用）。"""
    # 確保路徑是 Path 物件
    pdf_path = Path(pdf_path)
    
    # 先用 pdfminer 嘗試
    text = extract_text(str(pdf_path)) or ""
    if text and len(text.strip()) >= 50:
        return text

    # 後備：PyMuPDF（文字抽取）
    try:
        import fitz  # type: ignore

        doc = fitz.open(str(pdf_path))
        pages: List[str] = []
        for page in doc:  # type: ignore[attr-defined]
            # PyMuPDF Page.get_text 存在於執行期；型別檢查忽略
            pages.append(page.get_text("text"))  # type: ignore[attr-defined]
        text2 = "\n".join(pages).strip()
        if text2 and len(text2) >= 50:
            return text2
    except Exception:
        pass

    # 後備：pdfplumber（同樣基於 pdfminer，但行為不同）
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(str(pdf_path)) as pdf:
            parts: List[str] = []
            for page in pdf.pages:
                t = page.extract_text() or ""
                if t:
                    parts.append(t)
        t3 = "\n".join(parts).strip()
        if t3 and len(t3) >= 50:
            return t3
    except Exception:
        pass

    # 最後後備：OCR（需安裝本機 Tesseract）
    try:
        import shutil

        import fitz  # type: ignore
        import pytesseract  # type: ignore
        from PIL import Image  # noqa: F401

        # 嘗試自動設定 tesseract 路徑（避免 PATH 尚未更新）
        if not shutil.which("tesseract"):
            for candidate in [
                r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
                r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
            ]:
                if os.path.exists(candidate):
                    pytesseract.pytesseract.tesseract_cmd = candidate
                    break

        doc = fitz.open(str(pdf_path))
        ocr_pages: List[str] = []
        mat = fitz.Matrix(2.0, 2.0)  # 放大 2x 提升辨識
        for page in doc:  # type: ignore[attr-defined]
            pix = page.get_pixmap(matrix=mat)  # type: ignore[attr-defined]
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            try:
                txt = pytesseract.image_to_string(img)
            except Exception:
                txt = ""
            if txt:
                ocr_pages.append(txt)
        t4 = "\n".join(ocr_pages).strip()
        if t4:
            return t4
    except Exception:
        pass

    return text


def read_docx_text(docx_path: Union[str, Path]) -> str:
    try:
        import docx  # type: ignore
    except Exception:
        raise RuntimeError("未安裝 python-docx，請先安裝: pip install python-docx")
    
    docx_path = Path(docx_path)
    doc = docx.Document(str(docx_path))  # type: ignore[attr-defined]
    parts: List[str] = []
    for p in doc.paragraphs:  # type: ignore[attr-defined]
        if p.text:
            parts.append(p.text)
    return "\n".join(parts)


def read_doc_text(doc_path: Union[str, Path]) -> str:
    doc_path = Path(doc_path)
    
    # 優先使用已安裝的 Microsoft Word COM 自動化（Windows）
    try:
        import win32com.client  # type: ignore
        from win32com.client import constants  # type: ignore

        word = win32com.client.Dispatch("Word.Application")  # type: ignore[attr-defined]
        word.Visible = False
        doc = word.Documents.Open(str(doc_path))  # type: ignore[attr-defined]
        tmp_txt = Path(tempfile.gettempdir()) / f"{doc_path.stem}.txt"
        doc.SaveAs(str(tmp_txt), FileFormat=constants.wdFormatText)  # type: ignore[attr-defined]
        doc.Close(False)
        word.Quit()
        for enc in ("utf-8", "utf-16", "cp950", "big5", "latin1"):
            try:
                return tmp_txt.read_text(encoding=enc)
            except Exception:
                continue
        return tmp_txt.read_text(errors="ignore")
    except Exception:
        pass

    # 後備：LibreOffice headless 轉 txt
    try:
        out_dir = Path(tempfile.gettempdir())
        subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "txt:Text",
                "--outdir",
                str(out_dir),
                str(doc_path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out_txt = out_dir / f"{doc_path.stem}.txt"
        if out_txt.exists():
            for enc in ("utf-8", "utf-16", "cp950", "big5", "latin1"):
                try:
                    return out_txt.read_text(encoding=enc)
                except Exception:
                    continue
            return out_txt.read_text(errors="ignore")
    except Exception:
        pass

    raise RuntimeError(
        "無法讀取 .doc 檔。請安裝 Microsoft Word 或 LibreOffice 後重試。"
    )


def read_text_by_suffix(path: Union[str, Path]) -> str:
    path = Path(path)
    suf = path.suffix.lower()
    if suf == ".pdf":
        return read_pdf_text(path)
    if suf == ".docx":
        return read_docx_text(path)
    if suf == ".doc":
        return read_doc_text(path)
    raise RuntimeError(f"不支援的檔案格式: {suf}")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def analyze_single_file(
    file_path: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    backend: str = "hf",
    cluster: str = "kmeans",
    k: int = 4,
    splitter: str = "regex",
) -> Dict[str, any]:
    """分析單一檔案並返回結果"""
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"檔案不存在: {file_path}")
    
    # 讀取檔案文字
    text = read_text_by_suffix(file_path)
    
    # 設定環境變數
    os.environ["SENT_SPLITTER"] = splitter
    
    # 執行分析管道
    grouped = run_pipeline(
        text=text,
        backend=backend,  # type: ignore[arg-type]
        cluster_method=cluster,  # type: ignore[arg-type]
        n_clusters=k,
    )
    
    # 如果指定了輸出目錄，保存結果
    if output_dir:
        output_dir = Path(output_dir)
        ensure_dir(output_dir)
        out_path = output_dir / f"{file_path.stem}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(grouped, f, ensure_ascii=False, indent=2)
        return {"result": grouped, "output_file": str(out_path)}
    
    return {"result": grouped}


def analyze_dir(
    input_dir: Union[str, Path],
    output_dir: Union[str, Path],
    backend: str = "hf",
    cluster: str = "kmeans",
    k: int = 4,
    splitter: str = "regex",
) -> Dict[str, Path]:
    """分析目錄中的所有文件（保持向後兼容）"""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    
    ensure_dir(output_dir)
    results: Dict[str, Path] = {}

    doc_files: List[Path] = []
    for pattern in ("*.pdf", "*.docx", "*.doc"):
        doc_files.extend(input_dir.glob(pattern))
    doc_files = sorted(doc_files)

    for f in doc_files:
        text = read_text_by_suffix(f)
        os.environ["SENT_SPLITTER"] = splitter
        grouped = run_pipeline(
            text=text,
            backend=backend,  # type: ignore[arg-type]
            cluster_method=cluster,  # type: ignore[arg-type]
            n_clusters=k,
        )

        out_path = output_dir / f"{f.stem}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(grouped, f, ensure_ascii=False, indent=2)
        results[f.name] = out_path

    return results


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Analyze PDFs and documents using sentence clustering"
    )
    p.add_argument(
        "--input-dir", type=str, default="ocr/data", help="文件目錄（預設 ocr/data）"
    )
    p.add_argument(
        "--output-dir",
        type=str,
        default="ocr/output",
        help="輸出 JSON 目錄（預設 ocr/output）",
    )
    p.add_argument("--backend", choices=["openai", "hf"], default="hf", help="嵌入後端")
    p.add_argument(
        "--cluster", choices=["kmeans", "hdbscan"], default="kmeans", help="聚類方法"
    )
    p.add_argument("--k", type=int, default=4, help="KMeans 的群數")
    p.add_argument(
        "--splitter",
        choices=["regex", "spacy", "nltk"],
        default="regex",
        help="斷句策略",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    results = analyze_dir(
        input_dir=input_dir,
        output_dir=output_dir,
        backend=args.backend,
        cluster=args.cluster,
        k=args.k,
        splitter=args.splitter,
    )

    print("分析完成：")
    for fname, out in results.items():
        print(f"- {fname} -> {out}")


if __name__ == "__main__":
    main()
