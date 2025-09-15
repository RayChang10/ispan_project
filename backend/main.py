#!/usr/bin/env python3
"""
MCP 多智能體系統主啟動腳本
整合 HTTP 包裝器、Fast Agent、tools 模組和虛擬面試系統
"""

import argparse
import asyncio
import logging
import sys
import threading
import time
from pathlib import Path

# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 確保專案根目錄在 sys.path 中，避免在 backend 目錄內執行時出現 `No module named 'backend'`
try:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
except Exception:
    # 若此步驟失敗，不影響後續；實際錯誤會在匯入時顯示
    pass


def start_mcp_server():
    """啟動 MCP 伺服器"""
    try:
        from backend.server import main as server_main

        logger.info("🚀 啟動 MCP 伺服器...")
        server_main()
    except Exception as e:
        logger.error(f"❌ MCP 伺服器啟動失敗: {e}")


def start_http_wrapper():
    """啟動 HTTP 包裝器"""
    try:
        from backend.http_wrapper import main as http_main

        logger.info("🌐 啟動 HTTP 包裝器...")
        http_main()
    except Exception as e:
        logger.error(f"❌ HTTP 包裝器啟動失敗: {e}")


def start_fastapi_background():
    """在背景啟動 FastAPI（提供靜態頁與 API）"""
    try:
        logger.info("🌀 在背景啟動 FastAPI (uvicorn:5000)...")

        def run_fastapi():
            try:
                import uvicorn

                uvicorn.run(
                    "backend.fastapi_app:app", host="0.0.0.0", port=5000, reload=False
                )
            except Exception as e:
                logger.error(f"❌ 背景 FastAPI 執行失敗: {e}")

        t = threading.Thread(target=run_fastapi, daemon=True)
        t.start()
        logger.info("✅ FastAPI 已在背景啟動 (http://localhost:5000)")
    except Exception as e:
        logger.error(f"❌ FastAPI 背景啟動失敗: {e}")


def start_fast_agent():
    """啟動 Fast Agent"""
    try:
        from backend.fast_agent_interview import main as fast_agent_main

        logger.info("🤖 啟動 Fast Agent...")
        asyncio.run(fast_agent_main())
    except Exception as e:
        logger.error(f"❌ Fast Agent 啟動失敗: {e}")


def start_fast_agent_background():
    """在背景啟動 Fast Agent"""
    try:
        logger.info("🤖 在背景啟動 Fast Agent...")

        # 創建新線程運行 Fast Agent
        def run_fast_agent():
            try:
                from backend.fast_agent_interview import main as fast_agent_main

                asyncio.run(fast_agent_main())
            except Exception as e:
                logger.error(f"❌ 背景 Fast Agent 執行失敗: {e}")

        fast_agent_thread = threading.Thread(target=run_fast_agent, daemon=True)
        fast_agent_thread.start()
        logger.info("✅ Fast Agent 已在背景啟動")

    except Exception as e:
        logger.error(f"❌ Fast Agent 背景啟動失敗: {e}")


def test_tools_modules():
    """測試 tools 模組"""
    try:
        from backend.tools.answer_analyzer import answer_analyzer
        from backend.tools.question_manager import question_manager

        logger.info("🧪 測試 tools 模組...")

        # 測試問題管理器
        question = question_manager.get_random_question()
        logger.info(f"✅ 問題管理器測試成功: {question.get('question', 'N/A')}")

        # 測試答案分析器
        analysis = answer_analyzer.analyze_answer("測試回答", "標準答案")
        logger.info(f"✅ 答案分析器測試成功: 評分 {analysis.get('score', 0)}")

        logger.info("✅ 所有 tools 模組測試通過")

    except Exception as e:
        logger.error(f"❌ tools 模組測試失敗: {e}")




def test_database():
    """測試資料庫"""
    try:
        # 檢查是否有現有的測試文件（動態導入避免靜態依賴）
        import importlib

        interview_test_mod = importlib.import_module("test_interview_flow")
        question_test_mod = importlib.import_module("test_question_analysis")

        logger.info("🗄️ 測試面試流程...")
        interview_test_mod.main()

        logger.info("🗄️ 測試問題分析...")
        question_test_mod.main()

        logger.info("✅ 資料庫相關測試完成")
    except Exception as e:
        logger.error(f"❌ 資料庫測試失敗: {e}")
        logger.info("⚠️ 某些測試模組可能不可用，繼續執行")


def start_integrated_system():
    """啟動整合系統 - 所有組件同時運行"""
    try:
        logger.info("🚀 啟動整合智能面試系統...")

        # 測試 tools 模組
        test_tools_modules()

        # 在背景啟動 FastAPI（提供前端與 API）
        start_fastapi_background()

        # 在背景啟動 Fast Agent
        start_fast_agent_background()

        # 虛擬面試系統已移除（由 FastAPI 提供靜態與 API）

        # 等待一下讓背景服務啟動
        time.sleep(3)

        # 啟動 HTTP 包裝器作為主要介面
        logger.info("🌐 啟動 HTTP 包裝器作為主要介面...")
        start_http_wrapper()

    except Exception as e:
        logger.error(f"❌ 整合系統啟動失敗: {e}")


def start_chat_only_system():
    """啟動純對話系統 - 不包含虛擬人服務"""
    try:
        logger.info("💬 啟動純對話面試系統...")

        # 測試 tools 模組
        test_tools_modules()

        # 在背景啟動 FastAPI（提供前端與 API）
        start_fastapi_background()

        # 在背景啟動 Fast Agent
        start_fast_agent_background()

        # 等待一下讓背景服務啟動
        time.sleep(3)

        # 啟動 HTTP 包裝器作為主要介面
        logger.info("🌐 啟動 HTTP 包裝器作為主要介面...")
        logger.info("📝 純對話模式：虛擬人服務已停用，專注於對話功能")
        start_http_wrapper()

    except Exception as e:
        logger.error(f"❌ 純對話系統啟動失敗: {e}")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="智能面試系統")
    parser.add_argument(
        "--mode",
        choices=[
            "all",
            "integrated",
            "chat-only",
            "http",
            "fast-agent",
            "interviewer",
            "test-tools",
            "test-database",
            "auto-interview",
        ],
        default="integrated",
        help="啟動模式",
    )
    parser.add_argument("--port", type=int, default=8080, help="HTTP 包裝器埠號")

    args = parser.parse_args()

    logger.info("🚀 智能面試系統啟動")
    logger.info(f"📋 啟動模式: {args.mode}")

    if args.mode == "integrated":
        # 啟動整合系統
        start_integrated_system()
    elif args.mode == "chat-only":
        # 啟動純對話模式（不包含虛擬人服務）
        start_chat_only_system()
    elif args.mode == "all":
        # 啟動所有組件
        logger.info("🔄 啟動所有組件...")


        # 測試 tools 模組
        test_tools_modules()

        # 啟動 HTTP 包裝器
        logger.info("🌐 啟動 HTTP 包裝器...")
        start_http_wrapper()
    elif args.mode == "http":
        start_http_wrapper()
    elif args.mode == "fast-agent":
        start_fast_agent()
    elif args.mode == "test-tools":
        test_tools_modules()
    elif args.mode == "test-database":
        test_database()
    elif args.mode == "auto-interview":
        # 啟動自動面試系統
        try:
            import importlib

            simple_auto_interview_mod = importlib.import_module("simple_auto_interview")
            simple_auto_interview_mod.main()
        except Exception as e:
            logger.error(f"❌ 自動面試系統啟動失敗: {e}")

    logger.info("✅ 系統啟動完成")


if __name__ == "__main__":
    main()
