#!/usr/bin/env python3
"""
Fast Agent 橋接模組
簡化後只保留橋接邏輯，實際功能委派給 tools 模組
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# 導入核心工具模組
try:
    from backend.tools.answer_analyzer import answer_analyzer
    from backend.tools.question_manager import question_manager
    from backend.tools.minio_user_store import register_user_to_minio, verify_user_from_minio
    TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"部分工具模組不可用: {e}")
    TOOLS_AVAILABLE = False
    answer_analyzer = None
    question_manager = None


# 橋接函數 - 直接委派給核心工具
def get_question():
    """獲取隨機面試問題"""
    if not TOOLS_AVAILABLE or not question_manager:
        return {"success": False, "error": "問題管理工具不可用"}
    
    try:
        question_data = question_manager.get_random_question()
        return {
            "success": True,
            "result": f"""
🎯 面試問題

問題：{question_data['question']}
來源：{question_data['source']}

請回答這個問題，然後使用 analyze_answer 功能來分析您的回答。
            """,
            "question_data": question_data,
        }
    except Exception as e:
        return {"success": False, "error": f"獲取問題失敗：{str(e)}"}


def analyze_answer(user_answer: str = "", question: str = "", standard_answer: str = ""):
    """分析用戶回答"""
    if not TOOLS_AVAILABLE or not answer_analyzer:
        return {"success": False, "error": "答案分析工具不可用"}
    
    try:
        # 如果沒有提供標準答案，嘗試從問題管理器獲取
        if not standard_answer and question_manager:
            question_data = question_manager.get_random_question()
            standard_answer = question_data.get("standard_answer", "")
        
        analysis = answer_analyzer.analyze_answer(user_answer, standard_answer, question)
        
        response = f"""
📊 分析結果

評分：{analysis.get('score', 0)}/100 ({analysis.get('grade', 'N/A')})
相似度：{analysis.get('similarity', 0):.1%}
反饋：{analysis.get('feedback', '無反饋')}

標準答案：{standard_answer}
        """
        
        if analysis.get("differences"):
            response += "\n🔍 具體差異：\n"
            for diff in analysis["differences"]:
                response += f"  • {diff}\n"
        
        return {"success": True, "result": response}
        
    except Exception as e:
        return {"success": False, "error": f"分析失敗：{str(e)}"}


def get_standard_answer(question: str = ""):
    """獲取標準答案"""
    if not TOOLS_AVAILABLE or not question_manager:
        return {"success": False, "error": "問題管理工具不可用"}
    
    try:
        if not question:
            question_data = question_manager.get_random_question()
            question = question_data.get("question", "")
            standard_answer = question_data.get("standard_answer", "")
            source = question_data.get("source", "")
        else:
            # 這裡可以實現根據問題查找標準答案的邏輯
            standard_answer = "標準答案將根據問題提供"
            source = "問題管理器"
        
        response = f"""
✅ 標準答案

問題：{question}
標準答案：{standard_answer}
來源：{source}
        """
        return {"success": True, "result": response}
        
    except Exception as e:
        return {"success": False, "error": f"獲取標準答案失敗：{str(e)}"}


def start_interview():
    """開始面試"""
    return get_question()  # 簡化為直接獲取問題


def interview_system():
    """面試系統介紹"""
    return {
        "success": True,
        "result": """
🤖 智能面試系統已啟動！

可用功能：
1. 獲取隨機面試問題 - get_question
2. 分析您的回答 - analyze_answer  
3. 提供標準答案 - get_standard_answer
4. 生成面試報告 - generate_final_summary

請告訴我您需要什麼幫助？
        """
    }


# 簡化的自我介紹相關功能
_user_intro_content = {}

def intro_collector(user_message: str = "", user_id: str = "default_user"):
    """收集用戶自我介紹內容"""
    try:
        if user_id not in _user_intro_content:
            _user_intro_content[user_id] = []

        _user_intro_content[user_id].append(user_message)
        all_content = " ".join(_user_intro_content[user_id])

        return {
            "success": True,
            "result": "✅ 已記錄您的自我介紹內容",
            "collected_content": all_content,
        }
    except Exception as e:
        return {"success": False, "error": f"記錄自我介紹失敗: {str(e)}"}


def get_collected_intro(user_id: str = "default_user"):
    """獲取已收集的自我介紹內容"""
    if user_id in _user_intro_content and _user_intro_content[user_id]:
        return " ".join(_user_intro_content[user_id])
    return ""


def clear_collected_intro(user_id: str = "default_user"):
    """清除已收集的自我介紹內容"""
    if user_id in _user_intro_content:
        _user_intro_content[user_id] = []
    return {
        "success": True,
        "result": f"✅ 已清除用戶 {user_id} 的自我介紹內容",
    }


def clear_all_user_data(user_id: str = "default_user"):
    """清除用戶的所有相關數據"""
    try:
        if user_id in _user_intro_content:
            del _user_intro_content[user_id]

        return {
            "success": True,
            "result": f"✅ 已清除用戶 {user_id} 的所有相關數據",
        }
    except Exception as e:
        return {"success": False, "error": f"清除用戶數據失敗: {str(e)}"}


def analyze_intro(user_message: str = "", user_id: str = "default_user"):
    """分析用戶自我介紹 - 簡化版本"""
    try:
        # 基本的關鍵字分析
        standards = {
            "開場簡介": ["我是", "我叫", "專業", "經驗", "年數"],
            "技能強項": ["技術", "技能", "擅長", "熟悉", "專長"],
            "工作經驗": ["工作", "經歷", "任職", "擔任", "公司"],
            "結語期待": ["期待", "希望", "感謝", "合作", "學習"],
        }
        
        analysis_result = []
        lower_message = user_message.lower()

        for standard, keywords in standards.items():
            found = any(keyword in lower_message for keyword in keywords)
            status = "✅ 已包含" if found else "❌ 缺少"
            analysis_result.append(f"{status} **{standard}**")
        
        report = f"""
📊 **自我介紹分析報告**

**您的自我介紹內容**：
{user_message}

**評估結果**：
{chr(10).join(analysis_result)}

**改進建議**：
• 確保包含個人背景和經驗
• 強調相關技能和專長
• 表達對職位的期待和熱忱
        """

        return {
            "success": True,
            "result": report,
        }
    except Exception as e:
        return {"success": False, "error": f"分析自我介紹失敗: {str(e)}"}


def generate_final_summary(user_message: str = "", interview_data: dict = None):
    """生成最終面試總結"""
    try:
        # 簡化的總結生成
        summary = """
🎯 **面試總結報告**

**面試完成情況**：
✅ 自我介紹階段 - 已完成
✅ 面試問答階段 - 已完成
✅ 最終總結 - 已完成

**改進建議**：
• 繼續加強技術知識的深度學習
• 多進行模擬面試練習
• 提高回答的結構化和條理性

**總評**：感謝您參與模擬面試，請繼續努力提升面試技巧！
        """
        
        return {
            "success": True,
            "result": summary,
        }
        
    except Exception as e:
        return {"success": False, "error": f"生成總結失敗: {str(e)}"}


# 統一的橋接函數
def call_fast_agent_function(function_name: str, **kwargs) -> Dict[str, Any]:
    """調用 Fast Agent 功能的統一橋接函數"""
    try:
        # 函數映射表
        function_map = {
            "get_question": get_question,
            "analyze_answer": analyze_answer,
            "get_standard_answer": get_standard_answer,
            "start_interview": start_interview,
            "interview_system": interview_system,
            "intro_collector": intro_collector,
            "analyze_intro": analyze_intro,
            "generate_final_summary": generate_final_summary,
            "clear_collected_intro": clear_collected_intro,
            "clear_all_user_data": clear_all_user_data,
        }
        
        if function_name in function_map:
            func = function_map[function_name]
            result = func(**kwargs)
            
            # 確保返回統一格式
            if isinstance(result, dict):
                return result
            else:
                return {"success": True, "result": str(result)}
        else:
            return {
                "success": False,
                "error": f"Fast Agent 函數 {function_name} 不存在",
            }
            
    except Exception as e:
        return {"success": False, "error": f"Fast Agent 調用失敗: {str(e)}"}


if __name__ == "__main__":
    # 測試橋接功能
    print("🧪 測試 Fast Agent 橋接功能...")

    result = call_fast_agent_function("get_question")
    print(f"get_question 結果: {result}")

    result = call_fast_agent_function("interview_system")
    print(f"interview_system 結果: {result}")