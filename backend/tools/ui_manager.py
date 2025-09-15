#!/usr/bin/env python3
"""
用戶介面模組
負責處理用戶互動和顯示
"""

import logging
from typing import Any, Dict

from .flow_summarizer import generate_flow_summary
from .interview_manager import interview_manager

logger = logging.getLogger(__name__)


class UIManager:
    """用戶介面管理器"""

    def __init__(self):
        self.session_active = False

    def display_welcome(self):
        """顯示歡迎訊息"""
        print("🤖 歡迎使用互動式面試系統！")
        print("系統會顯示面試問題，等待您的回答，然後與標準答案比對。")
        print("=" * 60)

    def display_question(self, question_data: Dict[str, Any]):
        """顯示面試問題"""
        print("\n" + "=" * 60)
        print("🎯 面試問題")
        print("=" * 60)
        print(f"問題: {question_data['question']}")
        print(f"來源: {question_data['source']}")
        print("\n請在下方輸入您的回答：")

    def get_user_input(self) -> str:
        """獲取用戶輸入"""
        return input("您的回答: ").strip()

    def display_analysis(self, analysis: Dict[str, Any]):
        """顯示分析結果"""
        print("\n" + "=" * 60)
        print("📊 分析結果")
        print("=" * 60)
        print(f"評分: {analysis['score']}/100 ({analysis['grade']})")
        print(f"相似度: {analysis['similarity']:.1%}")
        print(f"反饋: {analysis['feedback']}")

        if analysis["differences"]:
            print("\n🔍 具體差異:")
            for diff in analysis["differences"]:
                print(f"  • {diff}")

    def display_standard_answer(self, standard_answer: str):
        """顯示標準答案"""
        print("\n" + "=" * 60)
        print("✅ 標準答案")
        print("=" * 60)
        print(f"答案: {standard_answer}")

    def display_session_summary(self, summary: Dict[str, Any]):
        """顯示會話摘要"""
        print("\n" + "=" * 60)
        print("📈 會話摘要")
        print("=" * 60)
        print(f"總問題數: {summary['total_questions']}")
        print(f"平均分數: {summary['average_score']}/100")
        print("=" * 60)

        # 生成 AI 建議摘要（OpenAI）
        try:
            ai_summary = generate_flow_summary(summary)
            text = ai_summary.get("text", "")
            if text:
                print("\n✅ AI 建議總結")
                print("-" * 60)
                print(text)
                print("-" * 60)
        except Exception as e:
            # 若 OpenAI 不可用，不阻塞流程
            print(f"ℹ️  無法產生 AI 建議（{e}）。可稍後再試或確認 OPENAI_API_KEY 設定。")

    def ask_continue(self) -> bool:
        """詢問是否繼續"""
        continue_choice = input("\n是否繼續下一個問題？(y/n/auto): ").strip().lower()
        return continue_choice in ["y", "yes", "是", "auto", ""]

    def ask_auto_mode(self) -> bool:
        """詢問是否啟用自動模式"""
        auto_choice = input("\n是否啟用自動模式？(y/n): ").strip().lower()
        return auto_choice in ["y", "yes", "是", ""]

    def get_user_input_with_auto(self) -> str:
        """獲取用戶輸入，支援自動模式"""
        user_input = input("您的回答 (輸入 'EXIT' 結束，'SKIP' 跳過): ").strip()

        # 檢查特殊指令
        if user_input.upper() in ["EXIT", "退出", "結束"]:
            return "EXIT"
        elif user_input.upper() in ["SKIP", "跳過", ""]:
            return "SKIP"
        else:
            return user_input

    def display_error(self, error_message: str):
        """顯示錯誤訊息"""
        print(f"❌ 錯誤: {error_message}")

    def display_info(self, info_message: str):
        """顯示資訊訊息"""
        print(f"ℹ️  {info_message}")

    def display_success(self, success_message: str):
        """顯示成功訊息"""
        print(f"✅ {success_message}")

    def display_goodbye(self):
        """顯示再見訊息"""
        print("👋 感謝使用互動式面試系統！")


# 全域用戶介面管理器實例
ui_manager = UIManager()
