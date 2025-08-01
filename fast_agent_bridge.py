#!/usr/bin/env python3
"""
Fast Agent 橋接模組
用於在 virtual_interviewer 中調用 Fast Agent 功能
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加父目錄到路徑
sys.path.append(str(Path(__file__).parent))

try:
    from tools.answer_analyzer import answer_analyzer
    from tools.question_manager import question_manager

    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False
    print("⚠️ tools 模組不可用")


def get_question():
    """獲取隨機面試問題 - 優先使用 MCP 工具"""
    try:
        # 優先使用 MCP 工具
        from server import get_random_question as mcp_get_random_question

        result = mcp_get_random_question()
        if result.get("status") == "success":
            response = f"""
🎯 MCP 工具面試問題

問題：{result['question']}
類別：{result['category']}
難度：{result['difficulty']}
來源：{result['source']}

請回答這個問題，然後使用 analyze_answer 功能來分析您的回答。
            """
            return response
        else:
            return f"MCP 工具獲取問題失敗：{result.get('message', '未知錯誤')}"
    except ImportError:
        # 回退到原始工具
        if not TOOLS_AVAILABLE:
            return "工具模組不可用，無法獲取問題"

        try:
            question_data = question_manager.get_random_question()
            category = _categorize_question(question_data["question"])
            difficulty = _assess_difficulty(question_data["question"])

            response = f"""
🎯 面試問題

問題：{question_data['question']}
類別：{category}
難度：{difficulty}
來源：{question_data['source']}

請回答這個問題，然後使用 analyze_answer 功能來分析您的回答。
            """
            return response
        except Exception as e:
            return f"獲取問題失敗：{str(e)}"
    except Exception as e:
        return f"MCP 工具錯誤：{str(e)}"


def analyze_answer(
    user_answer: str = "", question: str = "", standard_answer: str = ""
):
    """分析用戶回答 - 優先使用 MCP 工具"""
    try:
        # 優先使用 MCP 工具
        from server import analyze_user_answer as mcp_analyze_user_answer

        result = mcp_analyze_user_answer(
            user_answer=user_answer, question=question, standard_answer=standard_answer
        )

        if result.get("status") == "success":
            response = f"""
📊 MCP 工具分析結果

評分：{result.get('score', 'N/A')}/100 ({result.get('grade', 'N/A')})
相似度：{result.get('similarity', 'N/A')}
反饋：{result.get('feedback', '無反饋')}

標準答案：{result.get('standard_answer', standard_answer)}
            """

            if result.get("differences"):
                response += "\n🔍 具體差異：\n"
                for diff in result["differences"]:
                    response += f"  • {diff}\n"

            return response
        else:
            return f"MCP 工具分析失敗：{result.get('message', '未知錯誤')}"
    except ImportError:
        # 回退到原始工具
        if not TOOLS_AVAILABLE:
            return "工具模組不可用，無法分析回答"

        try:
            # 如果沒有提供標準答案，嘗試從問題獲取
            if not standard_answer:
                question_data = question_manager.get_random_question()
                standard_answer = question_data.get("standard_answer", "標準答案未提供")

            # 使用答案分析器分析
            analysis = answer_analyzer.analyze_answer(user_answer, standard_answer)

            response = f"""
📊 分析結果

評分：{analysis['score']}/100 ({analysis['grade']})
相似度：{analysis['similarity']:.1%}
反饋：{analysis['feedback']}

標準答案：{standard_answer}
            """

            if analysis["differences"]:
                response += "\n🔍 具體差異：\n"
                for diff in analysis["differences"]:
                    response += f"  • {diff}\n"

            return response

        except Exception as e:
            return f"分析失敗：{str(e)}"
    except Exception as e:
        return f"MCP 工具錯誤：{str(e)}"


def get_standard_answer(question: str = ""):
    """獲取標準答案 - 優先使用 MCP 工具"""
    try:
        # 優先使用 MCP 工具
        from server import get_standard_answer as mcp_get_standard_answer

        result = mcp_get_standard_answer(question=question)
        if result.get("status") == "success":
            response = f"""
✅ MCP 工具標準答案

問題：{result['question']}
標準答案：{result['standard_answer']}
來源：{result['source']}
            """
            return response
        else:
            return f"MCP 工具獲取標準答案失敗：{result.get('message', '未知錯誤')}"
    except ImportError:
        # 回退到原始工具
        if not TOOLS_AVAILABLE:
            return "工具模組不可用，無法獲取標準答案"

        try:
            question_data = question_manager.get_random_question()

            response = f"""
✅ 標準答案

問題：{question_data['question']}
標準答案：{question_data['standard_answer']}
來源：{question_data['source']}
            """
            return response
        except Exception as e:
            return f"獲取標準答案失敗：{str(e)}"
    except Exception as e:
        return f"MCP 工具錯誤：{str(e)}"


def start_interview():
    """開始互動式面試 - 優先使用 MCP 工具"""
    try:
        # 優先使用 MCP 工具
        from server import conduct_interview as mcp_conduct_interview

        result = mcp_conduct_interview()
        if result.get("status") == "success":
            response = f"""
🤖 MCP 工具智能面試系統！

============================================================
🎯 面試系統
============================================================
{result.get('message', '面試已開始')}

請回答問題，然後使用 analyze_answer 功能來分析您的回答。
            """
            return response
        else:
            return f"MCP 工具面試失敗：{result.get('message', '未知錯誤')}"
    except ImportError:
        # 回退到原始工具
        if not TOOLS_AVAILABLE:
            return "工具模組不可用，無法開始面試"

        try:
            question_data = question_manager.get_random_question()
            category = _categorize_question(question_data["question"])
            difficulty = _assess_difficulty(question_data["question"])

            response = f"""
🤖 歡迎使用智能面試系統！

============================================================
🎯 面試問題
============================================================
問題：{question_data['question']}
類別：{category}
難度：{difficulty}
來源：{question_data['source']}

請回答這個問題，然後使用 analyze_answer 功能來分析您的回答。
            """
            return response
        except Exception as e:
            return f"開始面試失敗：{str(e)}"
    except Exception as e:
        return f"MCP 工具錯誤：{str(e)}"


def interview_system():
    """智能面試系統主 Agent"""
    return """
智能面試系統已啟動！

可用功能：
1. 獲取隨機面試問題
2. 分析您的回答
3. 提供標準答案
4. 生成面試報告

請告訴我您需要什麼幫助？
    """


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


# 橋接函數
def call_fast_agent_function(function_name, **kwargs):
    """調用 Fast Agent 功能"""
    try:
        if function_name == "get_question":
            return {"success": True, "result": get_question()}
        elif function_name == "analyze_answer":
            return {"success": True, "result": analyze_answer(**kwargs)}
        elif function_name == "get_standard_answer":
            return {"success": True, "result": get_standard_answer(**kwargs)}
        elif function_name == "start_interview":
            return {"success": True, "result": start_interview()}
        elif function_name == "interview_system":
            return {"success": True, "result": interview_system()}
        else:
            return {"error": f"Fast Agent 函數 {function_name} 不存在"}
    except Exception as e:
        return {"error": f"Fast Agent 調用失敗: {str(e)}"}


if __name__ == "__main__":
    # 測試橋接功能
    print("測試 Fast Agent 橋接功能...")

    result = call_fast_agent_function("get_question")
    print(f"get_question 結果: {result}")

    result = call_fast_agent_function("interview_system")
    print(f"interview_system 結果: {result}")
