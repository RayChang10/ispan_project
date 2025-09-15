import argparse
import asyncio
import atexit
import importlib
import json
import logging
import os
import signal
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import bcrypt
from dotenv import load_dotenv
from pymongo import MongoClient

# 載入環境變數
load_dotenv()

from backend.tools import minio_register_user
from backend.tools.answer_analyzer import answer_analyzer
from backend.tools.question_manager import question_manager

# OCR 和履歷分析功能
from backend.tools.ocr import (
    analyze_single_file,
    run_pipeline, 
    process_one,
    read_text_by_suffix
)

# MongoDB 履歷管理
from backend.tools.resume_manager import resume_manager

# MCP Resources 和 Events
from backend.mcp_resources import (
    get_resume_resource,
    get_job_embeddings_resource, 
    list_resume_resources
)
from backend.mcp_events import (
    emit_interview_start_event,
    emit_interview_answer_event,
    emit_interview_end_event,
    get_interview_events,
    emit_system_event,
    get_global_events
)

# SQL/RAG 工具
from backend.sql_rag_tool import (
    query_sql,
    get_database_schema,
    rag_search_jobs
)

# 多模態工具
from backend.multimodal_tool import (
    transcribe_audio,
    analyze_resume_layout
)

# 職缺搜尋和履歷分析工具（可選導入）
try:
    from backend.tools.job_search_tool import job_search_tool, search_jobs_tool, search_jobs_by_resume_tool, recommend_jobs_tool
    from backend.tools.resume_analysis_tool import resume_analysis_tool, analyze_resume_job_fit_tool, resume_health_check_tool
    JOB_SEARCH_AVAILABLE = True
except ImportError:
    JOB_SEARCH_AVAILABLE = False
    logger.warning("⚠️ 職缺搜尋工具不可用")
# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from mcp.server.fastmcp import FastMCP

    logger.info("FastMCP 導入成功")
except ImportError as e:
    logger.error(f"FastMCP 導入失敗: {e}")
    logger.error("請確保已安裝 MCP 套件: pip install mcp")
    sys.exit(1)

# 創建 MCP 伺服器（支援自動執行）
mcp = FastMCP("interview")

# 創建互動式面試實例
# interviewer = InteractiveInterview()

# MongoDB 連接（可選功能）
try:
    MONGODB_URI = os.getenv(
        "MONGODB_URI", "mongodb://localhost:27017/"
    )
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "interview_db")
    mongo_client = MongoClient(MONGODB_URI)
    mongo_db = mongo_client[MONGODB_DB_NAME]
    logger.info("✅ MongoDB 連接成功")
except Exception as e:
    logger.info("ℹ️  MongoDB 未運行，資料庫功能將不可用（不影響主要功能）")
    mongo_client = None
    mongo_db = None


minio_client = None
MINIO_BUCKET = None
try:
    minio_module = importlib.import_module("minio")  # 動態導入以避免 linter 錯誤
    Minio = getattr(minio_module, "Minio")

    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
    MINIO_BUCKET = os.getenv("MINIO_BUCKET", "fastagent-users")

    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )
    # 確保 bucket 存在
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)
    logger.info("✅ MinIO 連接成功，Bucket: %s", MINIO_BUCKET)
except Exception as e:
    logger.info("ℹ️  MinIO 未運行或未正確配置，相關工具將不可用: %s", e)
    minio_client = None
    MINIO_BUCKET = None


# 註冊 MCP 工具 - 只使用 tools/ 模組中的功能


@mcp.tool()
def get_random_question() -> dict:
    """從 MongoDB 獲取隨機面試問題，用於面試準備或練習"""
    try:
        question_data = question_manager.get_random_question()
        category = _categorize_question(question_data["question"])
        difficulty = _assess_difficulty(question_data["question"])

        return {
            "status": "success",
            "question": question_data["question"],
            "source": question_data["source"],
            "category": category,
            "difficulty": difficulty,
            "standard_answer": question_data["standard_answer"],
        }
    except Exception as e:
        return {"status": "error", "message": f"獲取問題失敗: {str(e)}"}


@mcp.tool()
def get_question_by_category(category: str) -> dict:
    """根據類別獲取面試問題"""
    try:
        question_data = question_manager.get_question_by_category(category)
        return {
            "status": "success",
            "question": question_data["question"],
            "source": question_data["source"],
            "category": category,
            "standard_answer": question_data["standard_answer"],
        }
    except Exception as e:
        return {"status": "error", "message": f"獲取問題失敗: {str(e)}"}


@mcp.tool()
def get_question_by_difficulty(difficulty: str) -> dict:
    """根據難度獲取面試問題"""
    try:
        question_data = question_manager.get_question_by_difficulty(difficulty)
        return {
            "status": "success",
            "question": question_data["question"],
            "source": question_data["source"],
            "difficulty": difficulty,
            "standard_answer": question_data["standard_answer"],
        }
    except Exception as e:
        return {"status": "error", "message": f"獲取問題失敗: {str(e)}"}


@mcp.tool()
def conduct_interview() -> dict:
    """進行完整的互動式面試流程"""
    try:
        # 1. 使用問題管理器獲取隨機問題
        question_data = question_manager.get_random_question()

        # 2. 顯示問題（在 MCP 工具中，我們返回問題供客戶端顯示）
        interview_info = {
            "status": "question_ready",
            "question": question_data["question"],
            "source": question_data["source"],
            "category": _categorize_question(question_data["question"]),
            "difficulty": _assess_difficulty(question_data["question"]),
            "message": "面試問題已準備好，請回答以下問題：",
            "instruction": f"問題：{question_data['question']}\n來源：{question_data['source']}\n\n請輸入您的回答：",
        }

        return interview_info

    except Exception as e:
        return {"status": "error", "message": f"面試初始化失敗: {str(e)}"}


@mcp.tool()
def analyze_user_answer(
    user_answer: str, question: str, standard_answer: str = ""
) -> dict:
    """分析用戶回答與標準答案的差異"""
    try:
        # 如果沒有提供標準答案，嘗試從問題獲取
        if not standard_answer:
            question_data = question_manager.get_random_question()
            standard_answer = question_data.get("standard_answer", "標準答案未提供")

        # 使用答案分析器分析
        analysis = answer_analyzer.analyze_answer(user_answer, standard_answer)

        return {
            "status": "success",
            "score": analysis.get("score", 0),
            "grade": analysis.get("grade", "未知"),
            "similarity": analysis.get("similarity", 0),
            "feedback": analysis.get("feedback", "無反饋"),
            "differences": analysis.get("differences", []),
            "user_answer": user_answer,
            "question": question,
            "standard_answer": standard_answer,
        }

    except Exception as e:
        return {"status": "error", "message": f"分析失敗: {str(e)}"}


@mcp.tool()
def get_standard_answer(question: str, category: str = "") -> dict:
    """獲取標準答案和解釋"""
    try:
        # 如果沒有提供問題，獲取隨機問題
        if not question:
            question_data = question_manager.get_random_question()
            question = question_data.get("question", "")
            standard_answer = question_data.get("standard_answer", "標準答案未提供")
            source = question_data.get("source", "未知來源")
        else:
            # 這裡可以實現根據問題獲取標準答案的邏輯
            # 暫時返回預設值
            standard_answer = "標準答案將根據問題提供"
            source = "未知來源"

        return {
            "status": "success",
            "question": question,
            "standard_answer": standard_answer,
            "source": source,
            "explanation": "詳細解釋將在這裡提供",
        }
    except Exception as e:
        return {"status": "error", "message": f"獲取標準答案失敗: {str(e)}"}


@mcp.tool()
def provide_answer_with_context(question: str, user_answer: str = "") -> dict:
    """提供帶上下文的答案"""
    try:
        # 獲取問題的標準答案
        question_data = question_manager.get_random_question()
        standard_answer = question_data.get("standard_answer", "標準答案未提供")

        # 如果有用戶答案，進行分析
        if user_answer:
            analysis = answer_analyzer.analyze_answer(user_answer, standard_answer)
            context = f"您的答案評分：{analysis.get('score', 0)}/100"
        else:
            context = "請提供您的答案以獲得分析"

        return {
            "status": "success",
            "question": question,
            "context": context,
            "answer": standard_answer,
            "user_answer": user_answer,
        }
    except Exception as e:
        return {"status": "error", "message": f"提供答案失敗: {str(e)}"}


@mcp.tool()
def register_user_to_minio(email: str, password: str, name: str) -> dict:
    """將註冊資料存入 MinIO（作為 JSON 檔）。由 tools 模組負責實作。"""
    return minio_register_user(email=email, password=password, name=name)


@mcp.tool()
def get_question_history() -> dict:
    """獲取問題歷史"""
    try:
        return {
            "status": "success",
            "history": ["問題1", "問題2", "問題3"],
        }
    except Exception as e:
        return {"status": "error", "message": f"獲取歷史失敗: {str(e)}"}


@mcp.tool()
def get_analysis_history() -> dict:
    """獲取分析歷史"""
    try:
        return {
            "status": "success",
            "history": ["分析1", "分析2", "分析3"],
        }
    except Exception as e:
        return {"status": "error", "message": f"獲取分析歷史失敗: {str(e)}"}


@mcp.tool()
def analyze_pdf_file(file_path: str, backend: str = "hf", cluster: str = "kmeans", k: int = 4, splitter: str = "regex") -> dict:
    """分析 PDF 檔案，提取文字並進行語義聚類分析"""
    try:
        from pathlib import Path
        
        # 分析單一檔案
        result = analyze_single_file(
            file_path=Path(file_path),
            output_dir=None,  # 不保存檔案，直接返回結果
            backend=backend,
            cluster=cluster,
            k=k,
            splitter=splitter
        )
        
        return {
            "status": "success",
            "analysis_result": result["result"],
            "message": "PDF 檔案分析完成",
            "file_path": file_path
        }
    except Exception as e:
        return {"status": "error", "message": f"PDF 分析失敗: {str(e)}"}


@mcp.tool()
def cluster_text_content(text: str, backend: str = "hf", cluster_method: str = "kmeans", n_clusters: int = 4) -> dict:
    """對文字內容進行語義聚類分析，將內容分組為教育/經歷/技能/成就等類別"""
    try:
        # 使用聚類管道分析文字
        grouped_result = run_pipeline(
            text=text,
            backend=backend,
            cluster_method=cluster_method,
            n_clusters=n_clusters
        )
        
        return {
            "status": "success",
            "clustered_groups": grouped_result,
            "message": "文字聚類分析完成"
        }
    except Exception as e:
        return {"status": "error", "message": f"文字聚類失敗: {str(e)}"}


@mcp.tool()
def extract_resume_to_frontend(file_path: str, model: str = "gpt-4o-mini", max_chars: int = 60000) -> dict:
    """使用 OpenAI 將履歷檔案轉換為前端標準 JSON 格式"""
    try:
        from pathlib import Path
        import tempfile
        
        # 創建臨時目錄處理輸出
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = process_one(
                input_path=Path(file_path),
                out_dir=Path(temp_dir),
                model=model,
                max_chars=max_chars
            )
            
            # 讀取結果
            import json
            with output_path.open("r", encoding="utf-8") as f:
                result_data = json.load(f)
        
        return {
            "status": "success",
            "resume_data": result_data,
            "message": "履歷轉換為前端格式完成",
            "file_path": file_path
        }
    except Exception as e:
        return {"status": "error", "message": f"履歷格式轉換失敗: {str(e)}"}


@mcp.tool()
def read_document_text(file_path: str) -> dict:
    """讀取文件內容，支援 PDF、DOCX、DOC 格式"""
    try:
        from pathlib import Path
        
        # 讀取文件文字
        text_content = read_text_by_suffix(Path(file_path))
        
        return {
            "status": "success",
            "text_content": text_content,
            "message": "文件讀取完成",
            "file_path": file_path,
            "text_length": len(text_content)
        }
    except Exception as e:
        return {"status": "error", "message": f"文件讀取失敗: {str(e)}"}


@mcp.tool()
def batch_analyze_directory(input_dir: str, output_dir: str = "", backend: str = "hf", cluster: str = "kmeans", k: int = 4, splitter: str = "regex") -> dict:
    """批量分析目錄中的所有文件"""
    try:
        from pathlib import Path
        
        input_path = Path(input_dir)
        if not output_dir:
            output_dir = str(input_path.parent / "output")
            
        output_path = Path(output_dir)
        
        # 批量分析目錄
        from backend.tools.ocr.analyze_pdfs import analyze_dir
        results = analyze_dir(
            input_dir=input_path,
            output_dir=output_path,
            backend=backend,
            cluster=cluster,
            k=k,
            splitter=splitter
        )
        
        # 轉換路徑為字符串
        result_files = {str(k): str(v) for k, v in results.items()}
        
        return {
            "status": "success",
            "processed_files": result_files,
            "total_files": len(results),
            "output_directory": str(output_path),
            "message": f"批量分析完成，處理了 {len(results)} 個檔案"
        }
    except Exception as e:
        return {"status": "error", "message": f"批量分析失敗: {str(e)}"}


@mcp.tool()
def save_resume_to_mongodb(user_id: str, resume_data: dict) -> dict:
    """將履歷資料儲存到 MongoDB"""
    try:
        result = resume_manager.save_resume(user_id, resume_data)
        return {
            "status": "success",
            "result": result,
            "message": f"履歷已儲存到 MongoDB，用戶ID: {user_id}"
        }
    except Exception as e:
        return {"status": "error", "message": f"儲存履歷失敗: {str(e)}"}


@mcp.tool()
def get_resume_from_mongodb(user_id: str) -> dict:
    """從 MongoDB 獲取履歷資料"""
    try:
        resume = resume_manager.get_resume_by_user_id(user_id)
        if resume:
            return {
                "status": "success",
                "resume": resume,
                "message": f"成功獲取用戶 {user_id} 的履歷"
            }
        else:
            return {
                "status": "not_found",
                "message": f"未找到用戶 {user_id} 的履歷"
            }
    except Exception as e:
        return {"status": "error", "message": f"獲取履歷失敗: {str(e)}"}


@mcp.tool()
def search_resumes_in_mongodb(domain: str = "", location: str = "", skills: str = "", limit: int = 10) -> dict:
    """在 MongoDB 中搜尋履歷"""
    try:
        query = {}
        
        if domain:
            query["desired_job.domain"] = {"$regex": domain, "$options": "i"}
        if location:
            query["personal_info.location"] = {"$regex": location, "$options": "i"}
        if skills:
            query["skills.skill_name"] = {"$regex": skills, "$options": "i"}
        
        results = resume_manager.search_resumes(query, limit)
        
        return {
            "status": "success",
            "results": results,
            "count": len(results),
            "query": query,
            "message": f"找到 {len(results)} 份履歷"
        }
    except Exception as e:
        return {"status": "error", "message": f"搜尋履歷失敗: {str(e)}"}


@mcp.tool()
def get_resume_statistics() -> dict:
    """獲取履歷統計資訊"""
    try:
        stats = resume_manager.get_resume_statistics()
        return {
            "status": "success",
            "statistics": stats,
            "message": "成功獲取履歷統計資訊"
        }
    except Exception as e:
        return {"status": "error", "message": f"獲取統計失敗: {str(e)}"}


@mcp.tool()
def comprehensive_resume_analysis(file_path: str, use_openai: bool = True, model: str = "gpt-4o-mini", user_id: str = "default_user", save_to_mongodb: bool = True) -> dict:
    """綜合履歷分析：結合聚類分析和 OpenAI 結構化提取"""
    try:
        from pathlib import Path
        
        file_path_obj = Path(file_path)
        
        # 1. 讀取文件內容
        text_content = read_text_by_suffix(file_path_obj)
        
        # 2. 進行聚類分析
        cluster_result = run_pipeline(
            text=text_content,
            backend="hf",
            cluster_method="kmeans",
            n_clusters=4
        )
        
        # 3. 如果啟用 OpenAI，進行結構化提取
        openai_result = None
        if use_openai:
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = process_one(
                    input_path=file_path_obj,
                    out_dir=Path(temp_dir),
                    model=model,
                    max_chars=60000
                )
                
                import json
                with output_path.open("r", encoding="utf-8") as f:
                    openai_result = json.load(f)
        
        # 儲存到 MongoDB (可選)
        mongodb_result = None
        if save_to_mongodb and openai_result:
            try:
                mongodb_result = resume_manager.save_resume(user_id, openai_result)
            except Exception as mongo_error:
                mongodb_result = {"status": "error", "message": str(mongo_error)}
        
        return {
            "status": "success",
            "file_path": file_path,
            "user_id": user_id,
            "text_length": len(text_content),
            "cluster_analysis": cluster_result,
            "structured_data": openai_result,
            "mongodb_result": mongodb_result,
            "message": "綜合履歷分析完成" + (f"，已存入 MongoDB (用戶: {user_id})" if save_to_mongodb and mongodb_result and mongodb_result.get("status") == "success" else "")
        }
    except Exception as e:
        return {"status": "error", "message": f"綜合分析失敗: {str(e)}"}


# ==================== 職缺搜尋工具 ====================

@mcp.tool()
def search_jobs(query: str, top_k: int = 10) -> dict:
    """搜尋職缺（使用 Milvus 向量搜尋和 LLM 智能篩選）"""
    try:
        result = search_jobs_tool(query, top_k)
        return result
    except Exception as e:
        return {"status": "error", "message": f"職缺搜尋失敗: {str(e)}"}


@mcp.tool()
def search_jobs_by_resume(resume_data: dict, query: str = "") -> dict:
    """根據履歷資料搜尋相關職缺"""
    try:
        result = search_jobs_by_resume_tool(resume_data, query)
        return result
    except Exception as e:
        return {"status": "error", "message": f"履歷職缺搜尋失敗: {str(e)}"}


@mcp.tool()
def recommend_jobs(resume_id: str, top_k: int = 5) -> dict:
    """根據履歷 ID 推薦職缺"""
    try:
        result = recommend_jobs_tool(resume_id, top_k)
        return result
    except Exception as e:
        return {"status": "error", "message": f"職缺推薦失敗: {str(e)}"}


# ==================== 履歷分析工具 ====================

@mcp.tool()
def analyze_resume_job_fit(resume_data: dict, job_data: dict) -> dict:
    """分析履歷與職缺的契合度"""
    try:
        result = analyze_resume_job_fit_tool(resume_data, job_data)
        return result
    except Exception as e:
        return {"status": "error", "message": f"履歷契合度分析失敗: {str(e)}"}


@mcp.tool()
def resume_health_check(resume_data: dict, target_job: dict = None) -> dict:
    """履歷健檢 - 使用詳細評分框架進行專業評估"""
    try:
        result = resume_health_check_tool(resume_data, target_job)
        return result
    except Exception as e:
        return {"status": "error", "message": f"履歷健檢失敗: {str(e)}"}


# ==================== MCP Resources ====================

@mcp.resource("resume/{resume_id}")
def get_resume_resource_tool(resume_id: str) -> dict:
    """MCP Resource: 獲取履歷資源 (resource://resume/{id})"""
    return get_resume_resource(resume_id, "parsed")

@mcp.resource("resume/{resume_id}/parsed") 
def get_resume_parsed_resource_tool(resume_id: str) -> dict:
    """MCP Resource: 獲取解析後的履歷資源 (resource://resume/{id}/parsed)"""
    return get_resume_resource(resume_id, "parsed")

@mcp.resource("resume/{resume_id}/raw")
def get_resume_raw_resource_tool(resume_id: str) -> dict:
    """MCP Resource: 獲取原始履歷檔案 (resource://resume/{id}/raw)"""
    return get_resume_resource(resume_id, "raw")

@mcp.resource("db/job_embeddings")
def get_job_embeddings_resource_tool() -> dict:
    """MCP Resource: 獲取職缺嵌入向量資源 (resource://db/job_embeddings)"""
    return get_job_embeddings_resource()

# ==================== MCP Events ====================

@mcp.tool()
def emit_interview_start_event_tool(session_id: str, interview_data: dict = None) -> dict:
    """MCP Event: 發出面試開始事件 (event://interview/start)"""
    return emit_interview_start_event(session_id, interview_data)

@mcp.tool()
def emit_interview_answer_event_tool(session_id: str, answer_data: dict = None) -> dict:
    """MCP Event: 發出面試回答事件 (event://interview/answer)"""
    return emit_interview_answer_event(session_id, answer_data)

@mcp.tool()
def emit_interview_end_event_tool(session_id: str, end_data: dict = None) -> dict:
    """MCP Event: 發出面試結束事件 (event://interview/end)"""
    return emit_interview_end_event(session_id, end_data)

@mcp.tool()
def get_interview_events_tool(session_id: str, event_type: str = None) -> dict:
    """MCP Event: 獲取面試事件"""
    return get_interview_events(session_id, event_type)

@mcp.tool()
def emit_system_event_tool(event_type: str, data: dict = None) -> dict:
    """MCP Event: 發出系統事件"""
    return emit_system_event(event_type, data)

@mcp.tool()
def get_global_events_tool(limit: int = 50) -> dict:
    """MCP Event: 獲取全域事件"""
    return get_global_events(limit)

# ==================== SQL/RAG 工具 ====================

@mcp.tool()
def query_sql_tool(sql_query: str, limit: int = 100) -> dict:
    """MCP 工具：執行安全的 SQL 查詢（只讀白名單）"""
    try:
        result = query_sql(sql_query, limit)
        return result
    except Exception as e:
        return {"status": "error", "message": f"SQL 查詢失敗: {str(e)}"}

@mcp.tool()
def get_database_schema_tool() -> dict:
    """MCP 工具：獲取資料庫結構資訊"""
    try:
        result = get_database_schema()
        return result
    except Exception as e:
        return {"status": "error", "message": f"獲取資料庫結構失敗: {str(e)}"}

@mcp.tool()
def rag_search_jobs_tool(query: str, top_k: int = 10) -> dict:
    """MCP 工具：使用 RAG 搜尋職缺嵌入向量"""
    try:
        result = rag_search_jobs(query, top_k)
        return result
    except Exception as e:
        return {"status": "error", "message": f"RAG 搜尋失敗: {str(e)}"}

# ==================== 多模態工具 ====================

@mcp.tool()
def transcribe_audio_tool(file_path: str, language: str = "zh") -> dict:
    """MCP 工具：語音轉文字 (transcribe_audio)"""
    try:
        result = transcribe_audio(file_path, language)
        return result
    except Exception as e:
        return {"status": "error", "message": f"語音轉文字失敗: {str(e)}"}

@mcp.tool()
def analyze_resume_layout_tool(file_path: str) -> dict:
    """MCP 工具：分析履歷佈局 (analyze_resume_layout)"""
    try:
        result = analyze_resume_layout(file_path)
        return result
    except Exception as e:
        return {"status": "error", "message": f"履歷佈局分析失敗: {str(e)}"}

# ==================== 整合功能工具 ====================

@mcp.tool()
def complete_job_matching_workflow(resume_data: dict, search_query: str = "", top_k: int = 5) -> dict:
    """完整的職缺匹配工作流程：搜尋職缺 + 契合度分析"""
    try:
        # 1. 根據履歷搜尋職缺
        search_result = search_jobs_by_resume_tool(resume_data, search_query)
        if search_result["status"] != "success":
            return search_result
        
        jobs = search_result["jobs"][:top_k]  # 限制分析數量
        
        # 2. 對每個職缺進行契合度分析
        fit_analyses = []
        for job in jobs:
            fit_result = analyze_resume_job_fit_tool(resume_data, job)
            if fit_result["status"] == "success":
                fit_analyses.append({
                    "job": job,
                    "fit_analysis": fit_result["analysis"]
                })
        
        return {
            "status": "success",
            "resume_data": resume_data,
            "search_query": search_query,
            "total_jobs_found": len(search_result["jobs"]),
            "analyzed_jobs": len(fit_analyses),
            "job_fit_analyses": fit_analyses,
            "message": f"完成職缺匹配分析，分析了 {len(fit_analyses)} 個職缺"
        }
        
    except Exception as e:
        return {"status": "error", "message": f"職缺匹配工作流程失敗: {str(e)}"}


@mcp.tool()
def resume_optimization_workflow(resume_data: dict, target_job: dict = None) -> dict:
    """履歷優化工作流程：健檢 + 改進建議"""
    try:
        # 1. 進行履歷健檢
        health_check_result = resume_health_check_tool(resume_data, target_job)
        if health_check_result["status"] != "success":
            return health_check_result
        
        # 2. 如果有目標職缺，進行契合度分析
        fit_analysis = None
        if target_job:
            fit_result = analyze_resume_job_fit_tool(resume_data, target_job)
            if fit_result["status"] == "success":
                fit_analysis = fit_result["analysis"]
        
        return {
            "status": "success",
            "resume_data": resume_data,
            "target_job": target_job,
            "health_check": health_check_result["health_check"],
            "fit_analysis": fit_analysis,
            "message": "履歷優化分析完成"
        }
        
    except Exception as e:
        return {"status": "error", "message": f"履歷優化工作流程失敗: {str(e)}"}


# 輔助函數
def _categorize_question(question: str) -> str:
    """對問題進行分類"""
    categories = {
        "自我介紹": ["介紹", "自己", "背景", "經歷"],
        "技術能力": ["技術", "技能", "程式", "開發", "程式設計"],
        "專案經驗": ["專案", "經驗", "實作", "作品"],
        "問題解決": ["問題", "解決", "困難", "挑戰"],
        "團隊合作": ["團隊", "合作", "溝通", "協作"],
        "學習能力": ["學習", "成長", "進步", "新技術"],
    }

    question_lower = question.lower()
    for category, keywords in categories.items():
        if any(keyword in question_lower for keyword in keywords):
            return category

    return "一般問題"


def _assess_difficulty(question: str) -> str:
    """評估問題難度"""
    question_lower = question.lower()

    if len(question) < 50:
        return "簡單"
    elif len(question) < 100:
        return "中等"
    else:
        return "困難"


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="MCP 伺服器")
    parser.add_argument("--host", default="localhost", help="主機地址")
    parser.add_argument("--port", type=int, default=8000, help="埠號")

    args = parser.parse_args()

    logger.info("🚀 啟動 MCP 伺服器...")
    logger.info(f"📍 地址: {args.host}:{args.port}")

    # 資源關閉函數
    def close_resources() -> None:
        try:
            if "mongo_client" in globals() and mongo_client is not None:
                mongo_client.close()
                logger.info("MongoDB 連線已關閉")
        except Exception as close_err:
            logger.debug(f"關閉 MongoDB 連線時發生非致命錯誤: {close_err}")

    # 註冊 atexit 與訊號處理，避免 atexit 期末階段才嘗試關閉造成噪音
    atexit.register(close_resources)

    def _handle_signal(signum, frame):
        logger.info(f"接收到結束訊號: {signum}，正在關閉資源...")
        close_resources()
        # 以 0 結束，避免在 atexit 期間再觸發 KeyboardInterrupt 噪音
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, _handle_signal)
        # Windows 亦支援 SIGTERM 標識，但是否可由外部送達視環境而定
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _handle_signal)
    except Exception as sig_err:
        logger.debug(f"註冊訊號處理器失敗（可忽略）: {sig_err}")

    try:
        # 使用 FastMCP 的標準運行方式
        mcp.run()
    except KeyboardInterrupt:
        logger.info("伺服器被用戶中斷，正在關閉資源...")
        close_resources()
    except Exception as e:
        logger.error(f"伺服器啟動失敗: {e}")
    finally:
        close_resources()
        logger.info("伺服器關閉")


if __name__ == "__main__":
    main()
