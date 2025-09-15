#!/usr/bin/env python3
"""
OCR 工具模組初始化檔案
整合履歷分析、文件解析和語義聚類功能
"""

from .analyze_pdfs import (
    read_pdf_text,
    read_docx_text, 
    read_doc_text,
    read_text_by_suffix,
    analyze_single_file,
    analyze_dir
)

from .cluster_parser import (
    run_pipeline,
    split_into_sentences,
    preprocess_text,
    Embedder,
    cluster_embeddings,
    name_clusters,
    ClusterResult
)

from .openai_to_frontend import (
    call_openai,
    extract_json,
    normalize_output,
    process_one,
    read_text
)

__all__ = [
    # analyze_pdfs 功能
    "read_pdf_text",
    "read_docx_text", 
    "read_doc_text",
    "read_text_by_suffix",
    "analyze_single_file",
    "analyze_dir",
    
    # cluster_parser 功能
    "run_pipeline",
    "split_into_sentences", 
    "preprocess_text",
    "Embedder",
    "cluster_embeddings",
    "name_clusters",
    "ClusterResult",
    
    # openai_to_frontend 功能
    "call_openai",
    "extract_json", 
    "normalize_output",
    "process_one",
    "read_text"
]

__version__ = "1.0.0"
__author__ = "OCR Team"
__description__ = "OCR 和履歷分析工具套件"