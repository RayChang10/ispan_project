#!/usr/bin/env python3
"""
Fast Agent MCP 風格的面試系統
使用真正的 Fast Agent MCP 架構
"""

import asyncio
import os
from typing import Any, Dict

from dotenv import load_dotenv
from mcp_agent.core.fastagent import FastAgent
# 載入環境變數
load_dotenv()

# 導入 Fast Agent MCP（優先使用頂層匯入，失敗則回退，並輸出實際錯誤原因）
try:
    from mcp_agent import FastAgent
except Exception as e_top:
    try:
        from mcp_agent.core.fastagent import FastAgent
    except Exception as e_sub:
        print(f"請先安裝 fast-agent-mcp，或檢查匯入錯誤：{e_sub}")
        exit(1)

# 創建 Fast Agent 應用
fast = FastAgent("Interview Agent System", config_path="configs/fastagent.config.yaml")

# 導入現有的工具模組
from backend.tools.answer_analyzer import answer_analyzer
from backend.tools.question_manager import question_manager


@fast.agent(
    name="interview_system",
    instruction_or_kwarg="""
    完整的智能面試系統 Agent
    
    功能：
    1. 生成面試問題
    2. 分析用戶回答
    3. 提供標準答案
    4. 生成面試報告
    
    使用方式：
    - 直接對話獲取面試問題
    - 提供回答進行分析
    - 請求標準答案和解釋
    """,
    servers=["interview"],
    model="gpt-4o-mini",
)
async def interview_system():
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


@fast.agent(
    name="get_question",
    instruction_or_kwarg="獲取隨機面試問題 - 使用 MCP 工具",
    servers=["interview"],
    model="gpt-4o-mini",
)
async def get_question():
    """獲取隨機面試問題 - 優先使用 MCP 工具"""
    try:
        # 優先使用 MCP 工具
        from backend.server import get_random_question as mcp_get_random_question

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


@fast.agent(
    name="analyze_answer",
    instruction_or_kwarg="分析用戶回答並評分 - 使用 MCP 工具",
    servers=["interview"],
    model="gpt-4o-mini",
)
async def analyze_answer(
    user_answer: str = "", question: str = "", standard_answer: str = ""
):
    """分析用戶回答 - 優先使用 MCP 工具"""
    try:
        # 優先使用 MCP 工具
        from backend.server import analyze_user_answer as mcp_analyze_user_answer

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


@fast.agent(
    name="get_standard_answer",
    instruction_or_kwarg="獲取標準答案和解釋",
    servers=["interview"],
    model="gpt-4o-mini",
)
async def get_standard_answer(question: str = ""):
    """獲取標準答案"""
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


@fast.agent(
    name="start_interview",
    instruction_or_kwarg="開始完整的互動式面試流程",
    servers=["interview"],
    model="gpt-4o-mini",
)
async def start_interview():
    """開始互動式面試"""
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


@fast.agent(
    name="register_user",
    instruction_or_kwarg="將使用者註冊資料寫入 MinIO。",
    servers=["interview"],
    model="gpt-4o-mini",
)
async def register_user(email: str, password: str, name: str):
    """呼叫 MCP 工具將註冊資料寫入 MinIO。"""
    try:
        from backend.server import register_user_to_minio

        result = register_user_to_minio(email=email, password=password, name=name)
        if result.get("status") == "success":
            return f"✅ 註冊成功，已寫入 MinIO（bucket: {result.get('bucket')}, object: {result.get('object_name')}）。"
        return f"❌ 註冊失敗：{result.get('message', '未知錯誤')}"
    except Exception as e:
        return f"❌ 註冊過程發生錯誤：{str(e)}"


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


# 主函數 - 使用 Fast Agent MCP
async def main():
    """主函數 - 使用 Fast Agent MCP"""
    async with fast.run() as agent:
        # 啟動互動式會話
        await agent.interactive()


# 直接運行入口
if __name__ == "__main__":
    asyncio.run(main())
