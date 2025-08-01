#!/usr/bin/env python3
"""
AI 評分系統測試腳本
比較 AI 評分和傳統評分的差異
"""

import os

from dotenv import load_dotenv

# 載入環境變數
load_dotenv()


def test_scoring_comparison():
    """測試評分系統比較"""

    # 測試案例
    test_cases = [
        {
            "question": "請介紹一下您的技術背景",
            "standard_answer": "我使用 Python 開發了一個網站",
            "user_answer": "我用 Python 做了一個網站",
            "description": "字不一樣但意思相同",
        },
        {
            "question": "您如何處理團隊衝突？",
            "standard_answer": "我會先聽取各方意見，然後尋找共同點來解決問題",
            "user_answer": "我通常會先了解大家的想法，然後找出解決方案",
            "description": "表達方式不同但核心意思相同",
        },
        {
            "question": "您對敏捷開發有什麼了解？",
            "standard_answer": "敏捷開發是一種迭代的開發方法，強調快速交付和持續改進",
            "user_answer": "敏捷就是快速開發，不斷改進",
            "description": "簡化表達但核心概念正確",
        },
        {
            "question": "您如何學習新技術？",
            "standard_answer": "我會先閱讀官方文檔，然後動手實踐，最後參與開源項目",
            "user_answer": "我喜歡看文檔，然後自己試試，有時候也會做開源",
            "description": "用詞不同但學習方法相同",
        },
    ]

    print("🤖 AI 評分系統測試")
    print("=" * 60)

    # 檢查 API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 請在 .env 檔案中設定 OPENAI_API_KEY")
        return

    try:
        # 導入分析器
        from tools.ai_answer_analyzer import ai_answer_analyzer
        from tools.answer_analyzer import answer_analyzer

        print("✅ 分析器導入成功")

        for i, case in enumerate(test_cases, 1):
            print(f"\n📝 測試案例 {i}: {case['description']}")
            print("-" * 40)
            print(f"問題: {case['question']}")
            print(f"標準答案: {case['standard_answer']}")
            print(f"用戶回答: {case['user_answer']}")

            # 傳統評分
            traditional_result = answer_analyzer._traditional_analysis(
                case["user_answer"], case["standard_answer"]
            )

            # AI 評分
            try:
                ai_result = ai_answer_analyzer.analyze_answer(
                    case["user_answer"], case["standard_answer"], case["question"]
                )
            except Exception as e:
                print(f"❌ AI 評分失敗: {e}")
                ai_result = {
                    "score": 0,
                    "grade": "錯誤",
                    "similarity": 0,
                    "feedback": "AI 分析失敗",
                }

            # 比較結果
            print(f"\n📊 評分比較:")
            print(
                f"傳統方法: {traditional_result['score']}/100 ({traditional_result['grade']}) - 相似度: {traditional_result['similarity']}"
            )
            print(
                f"AI 方法:   {ai_result['score']}/100 ({ai_result['grade']}) - 相似度: {ai_result.get('similarity', 0)}"
            )

            # 顯示差異
            score_diff = ai_result["score"] - traditional_result["score"]
            if score_diff > 0:
                print(f"✅ AI 評分更高 (+{score_diff}分) - 更準確地識別了意思相同")
            elif score_diff < 0:
                print(f"⚠️  AI 評分更低 ({score_diff}分) - 可能過於嚴格")
            else:
                print(f"🔄 評分相同")

            print(f"AI 反饋: {ai_result.get('feedback', '無反饋')}")

    except ImportError as e:
        print(f"❌ 導入失敗: {e}")
        print("請確保已安裝 openai 套件: pip install openai")
    except Exception as e:
        print(f"❌ 測試失敗: {e}")


def test_ai_analysis_detailed():
    """詳細測試 AI 分析功能"""

    print("\n🔍 詳細 AI 分析測試")
    print("=" * 60)

    try:
        from tools.ai_answer_analyzer import ai_answer_analyzer

        # 測試案例
        question = "請描述您的專案經驗"
        standard_answer = "我參與了一個電商平台的開發，負責後端 API 設計和資料庫優化，使用 Python Flask 框架，最終提升了系統性能 30%"
        user_answer = "我做過一個購物網站，主要做後端開發，用 Python 寫 API，還優化了資料庫，讓網站速度變快了"

        print(f"問題: {question}")
        print(f"標準答案: {standard_answer}")
        print(f"用戶回答: {user_answer}")

        # AI 分析
        result = ai_answer_analyzer.analyze_answer(
            user_answer, standard_answer, question
        )

        print(f"\n📊 AI 分析結果:")
        print(f"分數: {result['score']}/100")
        print(f"評級: {result['grade']}")
        print(f"相似度: {result.get('similarity', 0)}")
        print(f"反饋: {result.get('feedback', '無反饋')}")

        if "strengths" in result and result["strengths"]:
            print(f"優點: {', '.join(result['strengths'])}")

        if "suggestions" in result and result["suggestions"]:
            print(f"建議: {', '.join(result['suggestions'])}")

        if "differences" in result and result["differences"]:
            print(f"差異: {', '.join(result['differences'])}")

    except Exception as e:
        print(f"❌ 詳細測試失敗: {e}")


if __name__ == "__main__":
    test_scoring_comparison()
    test_ai_analysis_detailed()
