import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pymongo import MongoClient

# 載入環境變數
load_dotenv()

from tools.answer_analyzer import answer_analyzer
from tools.interactive_interview import InteractiveInterview
from tools.question_manager import question_manager

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
mcp = FastMCP("Multi-Agent MCP Server")

# 創建互動式面試實例
interviewer = InteractiveInterview()

# MongoDB 連接（可選功能）
try:
    mongo_client = MongoClient("mongodb://localhost:27017/")
    mongo_db = mongo_client.interview_db
    logger.info("✅ MongoDB 連接成功")
except Exception as e:
    logger.info("ℹ️  MongoDB 未運行，資料庫功能將不可用（不影響主要功能）")
    mongo_client = None
    mongo_db = None


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

    try:
        # 使用 FastMCP 的標準運行方式
        mcp.run()
    except KeyboardInterrupt:
        logger.info("伺服器被用戶中斷")
    except Exception as e:
        logger.error(f"伺服器啟動失敗: {e}")
    finally:
        logger.info("伺服器關閉")


if __name__ == "__main__":
    main()
