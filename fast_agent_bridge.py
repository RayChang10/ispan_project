#!/usr/bin/env python3
"""
Fast Agent 橋接模組
用於在 virtual_interviewer 中調用 Fast Agent 功能
"""

import asyncio
import json
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

# OpenAI 相關導入
try:
    import openai
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI 模組不可用")


def call_openai_for_analysis(prompt: str, max_tokens: int = 1500):
    """調用 OpenAI API 進行分析"""
    try:
        if not OPENAI_AVAILABLE:
            raise Exception("OpenAI 模組不可用")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise Exception("OPENAI_API_KEY 未設定")

        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "您是一個專業的面試官和職涯顧問，擅長分析自我介紹並提供具體的改進建議。請根據要求分析用戶的自我介紹。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content
        return content.strip() if content else ""

    except Exception as e:
        print(f"❌ OpenAI API 調用失敗: {e}")
        raise e


def get_question():
    """獲取隨機面試問題 - 優先使用 MCP 工具"""
    try:
        # 優先使用 MCP 工具
        from server import get_random_question as mcp_get_random_question

        result = mcp_get_random_question()
        if result.get("status") == "success":
            # 返回完整的數據結構，包含標準答案
            return {
                "success": True,
                "result": f"""
🎯 MCP 工具面試問題

問題：{result['question']}
類別：{result['category']}
難度：{result['difficulty']}
來源：{result['source']}

請回答這個問題，然後使用 analyze_answer 功能來分析您的回答。
                """,
                "question_data": {
                    "question": result["question"],
                    "standard_answer": result["standard_answer"],
                    "category": result["category"],
                    "difficulty": result["difficulty"],
                    "source": result["source"],
                },
            }
        else:
            return {
                "success": False,
                "error": f"MCP 工具獲取問題失敗：{result.get('message', '未知錯誤')}",
            }
    except ImportError:
        # 回退到原始工具
        if not TOOLS_AVAILABLE:
            return {"success": False, "error": "工具模組不可用，無法獲取問題"}

        try:
            question_data = question_manager.get_random_question()
            category = _categorize_question(question_data["question"])
            difficulty = _assess_difficulty(question_data["question"])

            return {
                "success": True,
                "result": f"""
🎯 面試問題

問題：{question_data['question']}
類別：{category}
難度：{difficulty}
來源：{question_data['source']}

請回答這個問題，然後使用 analyze_answer 功能來分析您的回答。
                """,
                "question_data": {
                    "question": question_data["question"],
                    "standard_answer": question_data.get(
                        "standard_answer", "標準答案未提供"
                    ),
                    "category": category,
                    "difficulty": difficulty,
                    "source": question_data["source"],
                },
            }
        except Exception as e:
            return {"success": False, "error": f"獲取問題失敗：{str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"MCP 工具錯誤：{str(e)}"}


# 全局變數來儲存自我介紹內容
_user_intro_content = {}


def intro_collector(user_message: str = ""):
    """收集用戶自我介紹內容"""
    try:
        print(f"📝 收集自我介紹內容: {user_message}")

        user_id = "default_user"  # 可以根據需要調整

        # 如果是第一次收集，初始化
        if user_id not in _user_intro_content:
            _user_intro_content[user_id] = []

        # 添加新的自我介紹內容
        _user_intro_content[user_id].append(user_message)

        # 返回當前已收集的內容
        all_content = " ".join(_user_intro_content[user_id])

        return {
            "success": True,
            "result": f"✅ 已記錄您的自我介紹內容",
            "message": "自我介紹內容已成功記錄",
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


def analyze_answer(
    user_answer: str = "", question: str = "", standard_answer: str = ""
):
    """分析用戶回答 - 優先使用 MCP 工具"""

    # 只在明確的自我介紹情況下才返回自我介紹回應
    # 移除過於寬泛的關鍵字匹配，避免誤判面試回答
    lower_answer = user_answer.lower()
    if (
        any(
            phrase in lower_answer
            for phrase in [
                "我叫",
                "我的名字是",
                "我的名字叫",
                "自我介紹一下",
                "讓我自我介紹",
            ]
        )
        and len(user_answer) < 50
    ):  # 只有短句且明確的自我介紹才觸發
        return {
            "success": True,
            "result": f"""
👋 很高興認識您！

您的自我介紹：{user_answer}

這是一個很好的開始！現在我們可以開始正式的面試流程。

請輸入「開始面試」或「問題」來獲取面試問題。
            """,
        }

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

            return {"success": True, "result": response}
        else:
            return {
                "success": False,
                "error": f"MCP 工具分析失敗：{result.get('message', '未知錯誤')}",
            }
    except ImportError:
        # 回退到原始工具
        if not TOOLS_AVAILABLE:
            return {"success": False, "error": "工具模組不可用，無法分析回答"}

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

            return {"success": True, "result": response}

        except Exception as e:
            return {"success": False, "error": f"分析失敗：{str(e)}"}
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


def analyze_intro(user_message: str = ""):
    """分析用戶自我介紹 - 使用 LLM 進行智能分析"""
    try:
        print(f"📊 分析自我介紹內容: {user_message}")

        # 優先使用 LLM 分析
        try:
            return _llm_analyze_intro(user_message)
        except Exception as llm_error:
            print(f"⚠️ LLM 分析失敗，回退到關鍵字分析: {llm_error}")
            return _fallback_keyword_analysis(user_message)

    except Exception as e:
        return {"success": False, "error": f"分析自我介紹失敗: {str(e)}"}


def _llm_analyze_intro(user_message: str):
    """使用 LLM 進行自我介紹分析"""
    analysis_prompt = f"""
請分析以下自我介紹內容，按照6個標準進行專業評估：

**自我介紹內容**：
{user_message}

**評估標準**：
1. 開場簡介：是否包含身份、專業定位、經驗年數等基本信息
2. 學經歷概述：是否包含學歷背景、工作經歷、相關經驗等
3. 核心技能與強項：是否包含技術技能、程式語言、專業能力等
4. 代表成果：是否包含具體項目、成就、數據或影響力等
5. 與職缺的連結：是否表達對職位的理解、匹配度或動機等
6. 結語與期待：是否包含感謝、期待、合作意願等結語

請以 JSON 格式返回分析結果，確保 JSON 格式正確：
{{
    "analysis": [
        {{"standard": "1. 開場簡介", "status": "✅ 已包含" 或 "❌ 缺少", "content": "簡短說明找到的內容或缺失原因", "score": 1-10}},
        {{"standard": "2. 學經歷概述", "status": "✅ 已包含" 或 "❌ 缺少", "content": "簡短說明找到的內容或缺失原因", "score": 1-10}},
        {{"standard": "3. 核心技能與強項", "status": "✅ 已包含" 或 "❌ 缺少", "content": "簡短說明找到的內容或缺失原因", "score": 1-10}},
        {{"standard": "4. 代表成果", "status": "✅ 已包含" 或 "❌ 缺少", "content": "簡短說明找到的內容或缺失原因", "score": 1-10}},
        {{"standard": "5. 與職缺的連結", "status": "✅ 已包含" 或 "❌ 缺少", "content": "簡短說明找到的內容或缺失原因", "score": 1-10}},
        {{"standard": "6. 結語與期待", "status": "✅ 已包含" 或 "❌ 缺少", "content": "簡短說明找到的內容或缺失原因", "score": 1-10}}
    ],
    "overall_score": "整體評分 (1-10)",
    "strengths": ["優點1", "優點2"],
    "suggestions": ["具體改進建議1", "具體改進建議2"]
}}

請確保返回有效的 JSON 格式，不要添加任何額外的文字說明。
"""

    # 調用 LLM
    llm_response = call_openai_for_analysis(analysis_prompt, max_tokens=1500)

    # 解析 JSON 回應
    try:
        # 嘗試提取 JSON 部分
        json_start = llm_response.find("{")
        json_end = llm_response.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            json_content = llm_response[json_start:json_end]
        else:
            json_content = llm_response

        analysis_data = json.loads(json_content)
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON 解析失敗: {e}")
        print(f"LLM 回應: {llm_response}")
        # 如果 JSON 解析失敗，回退到關鍵字分析
        raise Exception(f"LLM 返回格式錯誤: {e}")

    # 生成分析報告
    report = f"""
📊 **LLM 智能自我介紹分析報告**

**您的自我介紹內容**：
{user_message}

**評估結果**：
"""

    for item in analysis_data["analysis"]:
        report += f"{item['status']} **{item['standard']}** (評分: {item['score']}/10): {item['content']}\n"

    # 處理整體評分，確保顯示具體數字
    overall_score = analysis_data.get("overall_score", "0")
    if isinstance(overall_score, str):
        # 如果是字符串，嘗試提取數字
        import re

        score_match = re.search(r"(\d+(?:\.\d+)?)", str(overall_score))
        if score_match:
            overall_score = score_match.group(1)
        else:
            # 如果無法提取，計算平均分
            scores = [
                item.get("score", 0) for item in analysis_data.get("analysis", [])
            ]
            if scores:
                overall_score = round(sum(scores) / len(scores), 1)
            else:
                overall_score = "0"

    report += f"""
**整體評分**：{overall_score}/10

**您的優點**：
"""

    for strength in analysis_data.get("strengths", []):
        report += f"• {strength}\n"

    report += f"""
**改進建議**：
"""

    for suggestion in analysis_data.get("suggestions", []):
        report += f"• {suggestion}\n"

    report += f"""
**參考範例結構**：
1. 開場簡介：「您好，我是XXX，一位有X年經驗的XXX」
2. 學經歷：「我畢業於XXX，在XXX公司擔任XXX」  
3. 技能強項：「我熟悉XXX技術，擅長XXX」
4. 代表成果：「我曾經XXX，提升了X%效率」
5. 職缺連結：「我認為這個職位與我的XXX經驗匹配」
6. 結語期待：「期待能為貴公司貢獻我的專長」
    """

    return {
        "success": True,
        "result": report,
        "message": "LLM 智能分析完成",
        "analysis_data": analysis_data,
    }


def _fallback_keyword_analysis(user_message: str):
    """回退的關鍵字分析方法"""
    try:
        print("🔄 使用關鍵字分析作為回退方案")

        # 改進的關鍵字分析邏輯
        standards = {
            "1. 開場簡介": [
                "我是",
                "我叫",
                "身份",
                "專業定位",
                "經驗",
                "年數",
                "領域",
                "工程師",
                "開發者",
                "程式設計師",
                "資深",
                "初級",
                "中級",
            ],
            "2. 學經歷概述": [
                "學歷",
                "畢業",
                "大學",
                "碩士",
                "博士",
                "工作經歷",
                "任職",
                "擔任",
                "相關經驗",
                "職位",
                "公司",
                "服務",
                "工作",
                "經歷",
                "背景",
            ],
            "3. 核心技能與強項": [
                "技術",
                "技能",
                "軟技能",
                "專長",
                "優勢",
                "擅長",
                "熟悉",
                "會",
                "python",
                "java",
                "javascript",
                "react",
                "vue",
                "angular",
                "node",
                "django",
                "flask",
                "spring",
                "mysql",
                "postgresql",
                "mongodb",
                "docker",
                "kubernetes",
                "aws",
                "azure",
                "linux",
                "git",
                "html",
                "css",
                "typescript",
                "php",
                "c++",
                "golang",
                "rust",
                "程式語言",
                "框架",
                "資料庫",
                "雲端",
                "機器學習",
                "ai",
                "devops",
            ],
            "4. 代表成果": [
                "專案",
                "項目",
                "開發",
                "建立",
                "完成",
                "達成",
                "提升",
                "改善",
                "具體成果",
                "數據",
                "影響力",
                "價值",
                "成就",
                "貢獻",
                "效率",
                "降低",
                "增加",
                "優化",
                "實作",
                "建置",
            ],
            "5. 與職缺的連結": [
                "職位",
                "工作",
                "公司",
                "團隊",
                "匹配",
                "適合",
                "目標",
                "動機",
                "希望",
                "想要",
                "貢獻",
                "加入",
                "發展",
                "成長",
                "學習",
            ],
            "6. 結語與期待": [
                "期待",
                "希望",
                "感謝",
                "謝謝",
                "合作",
                "學習",
                "成長",
                "貢獻",
                "機會",
                "未來",
                "發展",
                "態度",
                "意願",
                "請多指教",
            ],
        }

        # 改進的匹配邏輯
        analysis_result = []
        missing_parts = []
        suggestions = []
        lower_message = user_message.lower()

        for standard, keywords in standards.items():
            found_keywords = []
            for keyword in keywords:
                # 更靈活的匹配邏輯
                if keyword.lower() in lower_message:
                    found_keywords.append(keyword)
                # 特別處理技能相關的匹配
                elif standard == "3. 核心技能與強項" and keyword in [
                    "會",
                    "熟悉",
                    "擅長",
                ]:
                    # 檢查是否有技術相關詞彙
                    tech_keywords = [
                        "python",
                        "java",
                        "javascript",
                        "react",
                        "vue",
                        "angular",
                        "node",
                        "django",
                        "flask",
                        "spring",
                        "mysql",
                        "postgresql",
                        "mongodb",
                        "docker",
                        "kubernetes",
                        "aws",
                        "azure",
                        "linux",
                        "git",
                        "html",
                        "css",
                        "typescript",
                        "php",
                        "c++",
                        "golang",
                        "rust",
                    ]
                    if any(tech in lower_message for tech in tech_keywords):
                        found_keywords.append(keyword)

            if found_keywords:
                unique_keywords = list(set(found_keywords))[:3]
                analysis_result.append(
                    f"✅ **{standard}**: 已提及 - {', '.join(unique_keywords)}"
                )
            else:
                missing_parts.append(f"❌ **{standard}**: 缺少相關內容")
                suggestions.append(f"建議補充{standard}的內容")

        # 生成報告
        report = f"""
📊 **關鍵字分析報告** (回退方案)

**您的自我介紹內容**：
{user_message}

**評估結果**：
{chr(10).join(analysis_result)}

{chr(10).join(missing_parts) if missing_parts else '🎉 您的自我介紹結構完整！'}

**改進建議**：
{chr(10).join([f"• {suggestion}" for suggestion in suggestions]) if suggestions else "• 您的自我介紹已經很完整，繼續保持！"}

**參考範例結構**：
1. 開場簡介：「您好，我是XXX，一位有X年經驗的XXX」
2. 學經歷：「我畢業於XXX，在XXX公司擔任XXX」  
3. 技能強項：「我熟悉XXX技術，擅長XXX」
4. 代表成果：「我曾經XXX，提升了X%效率」
5. 職缺連結：「我認為這個職位與我的XXX經驗匹配」
6. 結語期待：「期待能為貴公司貢獻我的專長」
        """

        return {
            "success": True,
            "result": report,
            "message": "關鍵字分析完成 (回退方案)",
        }
    except Exception as e:
        return {"success": False, "error": f"關鍵字分析失敗: {str(e)}"}


def generate_final_summary(user_message: str = "", interview_data: dict | None = None):
    """生成最終面試總結和建議"""
    try:
        print(f"📋 生成最終面試總結")

        # 收集實際的面試數據
        actual_data = _collect_actual_interview_data(interview_data)

        # 基於實際數據生成總結
        return _generate_comprehensive_summary(actual_data)

    except Exception as e:
        return {"success": False, "error": f"生成最終總結失敗: {str(e)}"}


def _collect_actual_interview_data(interview_data: dict | None = None):
    """收集實際的面試數據"""
    try:
        # 收集自我介紹內容
        intro_content = get_collected_intro("default_user")

        # 初始化數據結構
        actual_data = {
            "intro_content": intro_content,
            "intro_analysis": None,
            "questions_and_answers": [],
            "scores": [],
            "total_questions": 0,
            "average_score": 0,
        }

        # 如果有前端傳來的面試數據，使用它
        if interview_data and "chat_history" in interview_data:
            chat_history = interview_data["chat_history"]

            for chat in chat_history:
                stage = chat.get("stage", "")
                ai_response = chat.get("ai", "")
                user_message = chat.get("user", "")

                # 收集自我介紹分析
                if stage == "intro_analysis" and "自我介紹分析" in ai_response:
                    actual_data["intro_analysis"] = ai_response

                # 收集問答對話和評分
                elif stage == "questioning":
                    if "請給我問題" in user_message and "問題：" in ai_response:
                        # 這是一個問題
                        actual_data["questions_and_answers"].append(
                            {"type": "question", "content": ai_response}
                        )
                    elif "評分：" in ai_response or "分析結果" in ai_response:
                        # 這是答案分析
                        actual_data["questions_and_answers"].append(
                            {
                                "type": "answer_analysis",
                                "user_answer": user_message,
                                "analysis": ai_response,
                            }
                        )

                        # 提取評分
                        score = _extract_score_from_response(ai_response)
                        if score is not None:
                            actual_data["scores"].append(score)

        # 計算統計數據
        actual_data["total_questions"] = len(
            [
                qa
                for qa in actual_data["questions_and_answers"]
                if qa["type"] == "question"
            ]
        )
        if actual_data["scores"]:
            actual_data["average_score"] = sum(actual_data["scores"]) / len(
                actual_data["scores"]
            )

        return actual_data

    except Exception as e:
        print(f"❌ 收集面試數據失敗: {e}")
        return {
            "intro_content": "",
            "intro_analysis": None,
            "questions_and_answers": [],
            "scores": [],
            "total_questions": 0,
            "average_score": 0,
        }


def _extract_score_from_response(response: str):
    """從回應中提取評分"""
    try:
        import re

        # 尋找評分模式
        patterns = [r"評分：(\d+)", r"評分: (\d+)", r"Score: (\d+)", r"Score：(\d+)"]

        for pattern in patterns:
            match = re.search(pattern, response)
            if match:
                return int(match.group(1))
        return None
    except:
        return None


def _generate_comprehensive_summary(actual_data: dict):
    """基於實際數據生成綜合總結"""
    try:
        # 構建總結內容
        summary_parts = []

        # 標題
        summary_parts.append("🎯 **面試總結報告**\n")

        # 自我介紹分析部分
        if actual_data["intro_content"]:
            summary_parts.append("📝 **自我介紹評價**：")
            if actual_data["intro_analysis"]:
                # 提取分析中的關鍵信息
                intro_summary = _extract_intro_summary(actual_data["intro_analysis"])
                summary_parts.append(intro_summary)
            else:
                summary_parts.append("✅ 您提供了自我介紹內容，展現了良好的表達能力。")
            summary_parts.append("")

        # 面試問答分析部分
        if actual_data["questions_and_answers"]:
            summary_parts.append("💬 **面試問答表現**：")
            summary_parts.append(
                f"📊 總共回答了 {actual_data['total_questions']} 個問題"
            )

            if actual_data["scores"]:
                avg_score = actual_data["average_score"]
                summary_parts.append(f"📈 平均評分：{avg_score:.1f}/100")

                # 基於評分給出評價
                if avg_score >= 90:
                    performance = "🌟 優秀 - 回答準確深入，展現了扎實的專業能力"
                elif avg_score >= 80:
                    performance = "👍 良好 - 回答基本正確，具備相關知識基礎"
                elif avg_score >= 70:
                    performance = "✅ 尚可 - 有一定理解，但需要加強深度"
                else:
                    performance = "📚 需要改進 - 建議加強相關知識學習"

                summary_parts.append(f"🎯 整體表現：{performance}")
            summary_parts.append("")

        # 具體建議部分
        summary_parts.append("💡 **改進建議**：")
        suggestions = _generate_specific_suggestions(actual_data)
        summary_parts.extend(suggestions)

        # 合併所有部分
        full_summary = "\n".join(summary_parts)

        return {
            "success": True,
            "result": full_summary,
            "message": "基於實際面試數據生成的綜合總結",
        }

    except Exception as e:
        print(f"❌ 生成綜合總結失敗: {e}")
        # 回退到模板
        return _generate_template_summary()


def _extract_intro_summary(intro_analysis: str):
    """從自我介紹分析中提取關鍵摘要"""
    try:
        # 提取評分和主要建議
        lines = intro_analysis.split("\n")
        summary_points = []

        for line in lines:
            if "評分:" in line or "評分：" in line or "總分" in line:
                summary_points.append(f"📊 {line.strip()}")
            elif line.strip().startswith("✅") and len(line.strip()) < 100:
                summary_points.append(line.strip())
            elif line.strip().startswith("❌") and len(line.strip()) < 100:
                summary_points.append(line.strip())

        if summary_points:
            return "\n".join(summary_points[:3])  # 最多3個要點
        else:
            return "✅ 自我介紹內容已收到並分析，展現了您的背景和能力。"
    except:
        return "✅ 自我介紹階段已完成。"


def _generate_specific_suggestions(actual_data: dict):
    """基於實際數據生成具體建議"""
    suggestions = []

    # 基於自我介紹的建議
    if actual_data.get("intro_content"):
        if len(actual_data["intro_content"]) < 100:
            suggestions.append("🗣️ 自我介紹可以更加詳細，包含更多具體的經驗和成果")
        else:
            suggestions.append("✅ 自我介紹內容豐富，繼續保持這種表達風格")

    # 基於評分的建議
    if actual_data.get("scores") and actual_data.get("average_score"):
        avg_score = actual_data["average_score"]
        if avg_score < 80:
            suggestions.append("📚 建議加強技術知識的深度，多練習具體案例的解釋")
            suggestions.append("💭 回答時可以提供更多具體的例子和實際經驗")
        else:
            suggestions.append("🎯 保持良好的回答品質，可以嘗試更深入的技術討論")

    # 基於問題數量的建議
    if actual_data.get("total_questions", 0) < 3:
        suggestions.append("⏰ 建議完成更多面試問題，以獲得更全面的練習")

    # 至少提供3個建議，使用預設建議補充
    default_suggestions = [
        "📖 建議準備更多技術問題的標準答案",
        "🤝 多進行模擬面試，增加實戰經驗",
        "🎯 繼續練習面試表達，保持自信和清晰的溝通",
    ]

    # 如果建議不足3個，從預設建議中補充
    suggestion_index = 0
    while len(suggestions) < 3 and suggestion_index < len(default_suggestions):
        default_suggestion = default_suggestions[suggestion_index]
        # 檢查是否已經有類似的建議（簡化檢查邏輯）
        is_duplicate = False
        for existing_suggestion in suggestions:
            # 檢查關鍵詞是否重複
            if any(keyword in existing_suggestion for keyword in ["📖", "🤝", "🎯"]):
                if any(keyword in default_suggestion for keyword in ["📖", "🤝", "🎯"]):
                    is_duplicate = True
                    break
        if not is_duplicate:
            suggestions.append(default_suggestion)
        suggestion_index += 1

    # 為所有建議添加連續編號
    numbered_suggestions = []
    for i, suggestion in enumerate(suggestions, 1):
        numbered_suggestions.append(f"{i}. {suggestion}")

    return numbered_suggestions


def _generate_template_summary():
    """生成基於模板的總結（當沒有實際數據時）"""
    summary = f"""
🎯 **面試總結報告**

**面試完成情況**：
✅ 自我介紹階段 - 已完成
✅ 自我介紹分析 - 已完成  
✅ 面試問答階段 - 已完成
✅ 最終總結 - 已完成

**重要提醒**：
⚠️ **注意**：此總結基於系統模板生成，無法反映您的實際表現。

**建議改進**：
• 系統需要改進以讀取和分析實際的面試數據
• 建議根據真實的評分和表現生成準確的總結

**技術改進建議**：
1. 🔧 修改系統以傳遞實際面試數據
2. 📊 分析真實的評分記錄
3. 🎯 根據實際表現生成準確的評價
4. 📈 提供基於數據的改進建議
    """

    return {
        "success": True,
        "result": summary,
        "message": "最終總結生成完成（基於模板）",
    }


def _generate_data_based_summary(interview_data: dict):
    """基於實際數據生成總結"""
    try:
        # 解析面試數據
        chat_history = interview_data.get("chat_history", [])

        # 分析評分數據
        scores = []
        total_questions = 0
        analysis_results = []

        for chat in chat_history:
            if chat.get("stage") == "questioning" and "ai" in chat:
                ai_response = chat["ai"]
                # 提取評分信息
                if "評分：" in ai_response or "Score:" in ai_response:
                    total_questions += 1
                    # 嘗試提取分數
                    score = _extract_score_from_response(ai_response)
                    if score is not None:
                        scores.append(score)
                        analysis_results.append(
                            {
                                "question": chat.get("user", ""),
                                "score": score,
                                "response": ai_response,
                            }
                        )

        # 計算統計數據
        if scores:
            average_score = sum(scores) / len(scores)
            min_score = min(scores)
            max_score = max(scores)

            # 根據平均分數生成評價
            if average_score >= 80:
                overall_rating = "優秀"
                performance_desc = "表現出色，回答準確且完整"
            elif average_score >= 60:
                overall_rating = "良好"
                performance_desc = "表現良好，有改進空間"
            elif average_score >= 40:
                overall_rating = "中等"
                performance_desc = "表現一般，需要加強練習"
            else:
                overall_rating = "需要改進"
                performance_desc = "表現較差，需要大量練習"
        else:
            average_score = 0
            overall_rating = "無法評估"
            performance_desc = "沒有足夠的評分數據"

        # 生成總結
        summary = f"""
🎯 **面試總結報告**

**面試完成情況**：
✅ 自我介紹階段 - 已完成
✅ 自我介紹分析 - 已完成  
✅ 面試問答階段 - 已完成 ({total_questions} 題)
✅ 最終總結 - 已完成

**實際表現評估**：
• **總題數**: {total_questions} 題
• **平均分數**: {average_score:.1f}/100
• **最高分數**: {max_score if scores else 'N/A'}/100
• **最低分數**: {min_score if scores else 'N/A'}/100
• **整體評級**: {overall_rating}

**表現分析**：
{performance_desc}

**具體建議**：
{_generate_specific_advice(average_score, scores)}

**下次面試準備重點**：
1. 🎯 加強技術問題的準備和練習
2. 📊 提高回答的準確性和完整性
3. 🔍 多進行模擬面試練習
4. 💡 學習標準答案的結構和要點

**總評**: 您在本次模擬面試中的表現為 {overall_rating}，建議根據上述建議進行改進。
        """

        return {
            "success": True,
            "result": summary,
            "message": "最終總結生成完成（基於實際數據）",
        }

    except Exception as e:
        print(f"❌ 生成數據基礎總結失敗: {e}")
        return _generate_template_summary()


def _generate_specific_advice(average_score: float, scores: list) -> str:
    """根據分數生成具體建議"""
    if not scores:
        return "• 建議多進行模擬面試練習，提高回答質量"

    if average_score >= 80:
        return """• 保持優秀的表現，繼續深化技術知識
• 可以嘗試更具挑戰性的問題
• 建議分享您的學習方法和經驗"""
    elif average_score >= 60:
        return """• 加強技術問題的準備和練習
• 提高回答的準確性和完整性
• 多學習標準答案的結構和要點"""
    elif average_score >= 40:
        return """• 需要大量練習技術問題
• 加強基礎知識的學習
• 建議參加更多模擬面試"""
    else:
        return """• 需要從基礎開始加強學習
• 建議參加培訓課程或學習小組
• 多進行基礎知識的練習"""


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
            result = get_question()
            # 確保返回統一格式
            if isinstance(result, str):
                return {"success": True, "result": result}
            else:
                return result
        elif function_name == "analyze_answer":
            result = analyze_answer(**kwargs)
            return result  # analyze_answer 現在返回統一格式
        elif function_name == "intro_collector":
            result = intro_collector(**kwargs)
            return result  # intro_collector 返回統一格式
        elif function_name == "analyze_intro":
            result = analyze_intro(**kwargs)
            return result  # analyze_intro 返回統一格式
        elif function_name == "generate_final_summary":
            result = generate_final_summary(**kwargs)
            return result  # generate_final_summary 返回統一格式
        elif function_name == "get_standard_answer":
            result = get_standard_answer(**kwargs)
            # 確保返回統一格式
            if isinstance(result, str):
                return {"success": True, "result": result}
            else:
                return result
        elif function_name == "start_interview":
            result = start_interview()
            # 確保返回統一格式
            if isinstance(result, str):
                return {"success": True, "result": result}
            else:
                return result
        elif function_name == "interview_system":
            result = interview_system()
            # 確保返回統一格式
            if isinstance(result, str):
                return {"success": True, "result": result}
            else:
                return result
        else:
            return {
                "success": False,
                "error": f"Fast Agent 函數 {function_name} 不存在",
            }
    except Exception as e:
        return {"success": False, "error": f"Fast Agent 調用失敗: {str(e)}"}


if __name__ == "__main__":
    # 測試橋接功能
    print("測試 Fast Agent 橋接功能...")

    result = call_fast_agent_function("get_question")
    print(f"get_question 結果: {result}")

    result = call_fast_agent_function("interview_system")
    print(f"interview_system 結果: {result}")
