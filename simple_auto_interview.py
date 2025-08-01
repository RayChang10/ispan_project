#!/usr/bin/env python3
"""
簡化自動面試系統
確保自動下一題功能正常工作
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# 添加 tools 目錄到 Python 路徑
sys.path.append(str(Path(__file__).parent / "tools"))

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from tools.answer_analyzer import answer_analyzer
from tools.question_manager import question_manager


class SimpleAutoInterview:
    """簡化自動面試類別"""

    def __init__(self):
        self.question_count = 0
        self.total_score = 0

    def display_welcome(self):
        """顯示歡迎訊息"""
        print("🤖 歡迎使用簡化自動面試系統！")
        print("🎯 自動面試模式已啟用")
        print("💡 輸入 'EXIT' 可隨時結束面試")
        print("💡 輸入 'SKIP' 可跳過當前問題")
        print("💡 直接按 Enter 也會跳過問題")
        print("=" * 60)

    def display_question(self, question_data):
        """顯示問題"""
        print(f"\n📝 第 {self.question_count} 題")
        print("-" * 40)
        print("🎯 面試問題")
        print("=" * 60)
        print(f"問題: {question_data['question']}")
        print(f"來源: {question_data['source']}")
        print("\n請在下方輸入您的回答：")

    def get_user_input(self):
        """獲取用戶輸入"""
        user_input = input("您的回答 (輸入 'EXIT' 結束，'SKIP' 跳過): ").strip()

        # 檢查特殊指令
        if user_input.upper() in ["EXIT", "退出", "結束"]:
            return "EXIT"
        elif user_input.upper() in ["SKIP", "跳過", ""]:
            return "SKIP"
        else:
            return user_input

    def display_analysis(self, analysis):
        """顯示分析結果"""
        print("\n" + "=" * 60)
        print("📊 分析結果")
        print("=" * 60)
        print(f"評分: {analysis['score']}/100 ({analysis['grade']})")
        print(f"相似度: {analysis['similarity']:.1%}")
        print(f"反饋: {analysis['feedback']}")

    def display_standard_answer(self, standard_answer):
        """顯示標準答案"""
        print("\n" + "=" * 60)
        print("✅ 標準答案")
        print("=" * 60)
        print(f"答案: {standard_answer}")

    def display_statistics(self, score):
        """顯示統計資訊"""
        self.total_score += score
        average_score = self.total_score / self.question_count

        print(f"\n📊 當前統計:")
        print(f"   已完成題數: {self.question_count}")
        print(f"   當前題分數: {score}/100")
        print(f"   平均分數: {average_score:.1f}/100")

    def run_auto_session(self):
        """運行自動面試會話"""
        self.display_welcome()

        while True:
            try:
                self.question_count += 1

                # 獲取隨機問題
                question_data = question_manager.get_random_question()

                # 顯示問題
                self.display_question(question_data)

                # 獲取用戶回答
                user_answer = self.get_user_input()

                # 檢查特殊指令
                if user_answer == "EXIT":
                    print("您選擇結束面試")
                    break
                elif user_answer == "SKIP":
                    print("您跳過了這個問題")
                    print("⏭️  跳過此題，進入下一題...")
                    continue

                # 分析回答
                analysis = answer_analyzer.analyze_answer(
                    user_answer, question_data["standard_answer"]
                )

                # 顯示分析結果
                self.display_analysis(analysis)

                # 顯示標準答案
                self.display_standard_answer(question_data["standard_answer"])

                # 顯示統計資訊
                self.display_statistics(analysis["score"])

                # 自動進入下一題
                print("⏭️  自動進入下一題...")
                time.sleep(2)  # 等待2秒讓用戶看到結果

            except KeyboardInterrupt:
                print("面試被中斷")
                break
            except Exception as e:
                logger.error(f"面試過程中發生錯誤: {e}")
                print(f"發生錯誤: {e}")
                break

        # 顯示最終摘要
        self.display_final_summary()
        print("👋 感謝使用簡化自動面試系統！")

    def display_final_summary(self):
        """顯示最終摘要"""
        print("\n" + "=" * 60)
        print("🎯 自動面試完成 - 最終統計")
        print("=" * 60)

        if self.question_count > 0:
            average_score = self.total_score / self.question_count
            print(f"📊 總題數: {self.question_count}")
            print(f"📊 總分數: {self.total_score}")
            print(f"📊 平均分數: {average_score:.1f}/100")

            # 評級
            if average_score >= 90:
                grade = "優秀"
            elif average_score >= 80:
                grade = "良好"
            elif average_score >= 70:
                grade = "中等"
            elif average_score >= 60:
                grade = "及格"
            else:
                grade = "需要改進"

            print(f"📊 評級: {grade}")
        else:
            print("📊 沒有完成任何題目")

        print("=" * 60)


def main():
    """主函數"""
    try:
        auto_interviewer = SimpleAutoInterview()
        auto_interviewer.run_auto_session()
    except Exception as e:
        logger.error(f"簡化自動面試系統啟動失敗: {e}")
        print(f"❌ 系統錯誤: {e}")


if __name__ == "__main__":
    print("🚀 啟動簡化自動面試系統...")
    main()
