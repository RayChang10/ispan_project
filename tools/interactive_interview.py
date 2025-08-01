#!/usr/bin/env python3
"""
互動式面試工具 - 重構版本
整合所有模組化的功能
"""

import asyncio
import logging
from typing import Any, Dict

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .answer_analyzer import answer_analyzer

# 導入模組化組件
from .database import db_manager
from .interview_session import interview_session
from .question_manager import question_manager
from .ui_manager import ui_manager


class InteractiveInterview:
    """互動式面試主類別 - 整合所有模組"""

    def __init__(self):
        self.session = interview_session
        self.ui = ui_manager

    def get_random_question(self) -> Dict[str, Any]:
        """獲取隨機面試問題（向後相容）"""
        return question_manager.get_random_question()

    def analyze_answer(self, user_answer: str, standard_answer: str) -> Dict[str, Any]:
        """分析用戶回答（向後相容）"""
        return answer_analyzer.analyze_answer(user_answer, standard_answer)

    async def conduct_interview(self, auto_mode: bool = False) -> Dict[str, Any]:
        """進行互動式面試"""

        # 開始會話
        self.session.start_session()

        # 獲取下一個問題
        question_result = self.session.get_next_question()

        if question_result["status"] != "question_ready":
            return {"status": "error", "message": "無法獲取問題"}

        # 顯示問題
        self.ui.display_question(question_result)

        # 獲取用戶回答（支援自動模式）
        if auto_mode:
            user_answer = self.ui.get_user_input_with_auto()
        else:
            user_answer = self.ui.get_user_input()

        # 檢查特殊指令
        if user_answer == "EXIT":
            return {"status": "exit", "message": "用戶選擇結束面試"}
        elif user_answer == "SKIP" or not user_answer:
            return {"status": "skipped", "message": "您跳過了這個問題"}

        # 提交回答並分析
        analysis_result = self.session.submit_answer(user_answer)

        if analysis_result["status"] != "analysis_complete":
            return analysis_result

        # 顯示分析結果
        self.ui.display_analysis(analysis_result["analysis"])

        # 顯示標準答案
        self.ui.display_standard_answer(analysis_result["standard_answer"])

        # 在自動模式下，顯示自動下一題提示
        if auto_mode:
            print("\n⏭️  自動進入下一題...")
            print("-" * 40)

        return {
            "status": "completed",
            "question": analysis_result["question"],
            "user_answer": analysis_result["user_answer"],
            "analysis": analysis_result["analysis"],
            "standard_answer": analysis_result["standard_answer"],
            "source": question_result["source"],
        }

    async def run_interactive_session(self):
        """運行互動式會話"""
        self.ui.display_welcome()

        # 詢問是否啟用自動模式
        auto_mode = self.ui.ask_auto_mode()
        if auto_mode:
            self.ui.display_info("已啟用自動模式，系統將自動進入下一題")
            self.ui.display_info(
                "輸入 'EXIT' 可隨時結束面試，輸入 'SKIP' 可跳過當前問題"
            )

        while True:
            try:
                result = await self.conduct_interview(auto_mode)

                if result["status"] == "exit":
                    self.ui.display_info("您選擇結束面試")
                    break
                elif result["status"] == "skipped":
                    self.ui.display_info("您跳過了這個問題。")
                elif result["status"] == "completed":
                    self.ui.display_success(f"面試完成！問題來源: {result['source']}")
                else:
                    self.ui.display_error(result.get("message", "未知錯誤"))

                # 在自動模式下，自動繼續下一題
                if auto_mode:
                    self.ui.display_info("自動進入下一題...")
                    continue
                else:
                    # 手動模式下詢問是否繼續
                    if not self.ui.ask_continue():
                        break

            except KeyboardInterrupt:
                self.ui.display_info("面試被中斷")
                break
            except Exception as e:
                logger.error(f"面試過程中發生錯誤: {e}")
                self.ui.display_error(f"發生錯誤: {e}")

        # 顯示會話摘要
        summary = self.session.get_session_summary()
        if summary["status"] == "summary":
            self.ui.display_session_summary(summary)

        # 結束會話
        self.session.end_session()
        self.ui.display_goodbye()


async def main():
    """主函數"""
    interviewer = InteractiveInterview()
    await interviewer.run_interactive_session()


if __name__ == "__main__":
    asyncio.run(main())
