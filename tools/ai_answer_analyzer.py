#!/usr/bin/env python3
"""
AI 智能答案分析模組
使用 OpenAI 來分析用戶回答與標準答案的差異
"""

import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

try:
    import openai
    from openai import OpenAI
except ImportError:
    print("請安裝 openai 套件: pip install openai")
    exit(1)

logger = logging.getLogger(__name__)


class AIAnswerAnalyzer:
    """AI 智能答案分析器"""

    def __init__(self):
        # 初始化 OpenAI 客戶端
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("請在 .env 檔案中設定 OPENAI_API_KEY")

        self.client = OpenAI(api_key=api_key)
        self.grade_thresholds = {"優秀": 80, "良好": 60, "一般": 40, "需要改進": 0}

    def analyze_answer(
        self, user_answer: str, standard_answer: str, question: str = ""
    ) -> Dict[str, Any]:
        """使用 AI 分析用戶回答與標準答案的差異"""

        try:
            # 構建 AI 分析提示
            prompt = self._build_analysis_prompt(user_answer, standard_answer, question)

            # 調用 OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "您是一個專業的面試評分專家，負責分析求職者的回答。請根據以下標準進行評分：\n"
                        "1. 內容準確性（40%）：回答是否涵蓋了問題的核心要點\n"
                        "2. 表達清晰度（30%）：回答是否清楚易懂\n"
                        "3. 邏輯結構（20%）：回答是否有良好的邏輯結構\n"
                        "4. 完整性（10%）：回答是否完整\n\n"
                        "請嚴格按照以下 JSON 格式返回結果，不要添加任何其他文字：\n"
                        "{\n"
                        '  "score": 85,\n'
                        '  "grade": "良好",\n'
                        '  "similarity": 0.85,\n'
                        '  "feedback": "您的回答基本正確，涵蓋了核心要點",\n'
                        '  "differences": ["缺少一些技術細節"],\n'
                        '  "strengths": ["表達清晰", "邏輯合理"],\n'
                        '  "suggestions": ["可以添加更多技術細節"]\n'
                        "}",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            # 解析 AI 回應
            ai_response = response.choices[0].message.content
            analysis_result = self._parse_ai_response(ai_response)

            # 添加額外資訊
            analysis_result.update(
                {
                    "user_answer": user_answer,
                    "standard_answer": standard_answer,
                    "question": question,
                    "analysis_method": "AI",
                }
            )

            return analysis_result

        except Exception as e:
            logger.error(f"AI 分析失敗: {e}")
            # 回退到傳統方法
            return self._fallback_analysis(user_answer, standard_answer)

    def _build_analysis_prompt(
        self, user_answer: str, standard_answer: str, question: str
    ) -> str:
        """構建 AI 分析提示"""

        prompt = f"""
請分析以下面試回答：

問題：{question if question else "未提供具體問題"}

標準答案：{standard_answer}

用戶回答：{user_answer}

請從以下角度進行分析：
1. 內容準確性：用戶回答是否涵蓋了標準答案的核心要點
2. 表達方式：雖然用詞可能不同，但意思是否相同
3. 邏輯結構：回答是否有良好的邏輯性
4. 完整性：是否完整回答了問題

注意：即使用詞不同，只要意思相同或相近，都應該給予較高的相似度評分。

請以 JSON 格式返回分析結果。
"""
        return prompt

    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """解析 AI 回應"""
        try:
            import json
            import re

            # 清理回應內容
            cleaned_response = ai_response.strip()

            # 嘗試提取 JSON 部分
            json_match = re.search(r"\{.*\}", cleaned_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
            else:
                # 嘗試直接解析
                result = json.loads(cleaned_response)

            # 確保必要欄位存在
            required_fields = ["score", "grade", "similarity", "feedback"]
            for field in required_fields:
                if field not in result:
                    result[field] = self._get_default_value(field)

            # 確保分數在有效範圍內
            result["score"] = max(0, min(100, int(result["score"])))
            result["similarity"] = max(0.0, min(1.0, float(result["similarity"])))

            return result

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"解析 AI 回應失敗: {e}")
            logger.error(f"AI 回應內容: {ai_response}")
            return self._get_default_analysis()

    def _get_default_value(self, field: str) -> Any:
        """獲取預設值"""
        defaults = {
            "score": 0,
            "grade": "需要改進",
            "similarity": 0.0,
            "feedback": "AI 分析失敗，請檢查回答內容",
            "differences": ["無法分析差異"],
            "strengths": [],
            "suggestions": ["建議重新回答問題"],
        }
        return defaults.get(field, "")

    def _get_default_analysis(self) -> Dict[str, Any]:
        """獲取預設分析結果"""
        return {
            "score": 0,
            "grade": "需要改進",
            "similarity": 0.0,
            "feedback": "AI 分析失敗，使用預設評分",
            "differences": ["分析失敗"],
            "strengths": [],
            "suggestions": ["請重新嘗試回答"],
        }

    def _fallback_analysis(
        self, user_answer: str, standard_answer: str
    ) -> Dict[str, Any]:
        """回退到傳統分析方法"""
        from difflib import SequenceMatcher

        # 使用傳統的相似度計算
        similarity = SequenceMatcher(
            None, user_answer.lower(), standard_answer.lower()
        ).ratio()
        score = int(similarity * 100)
        grade, feedback = self._evaluate_performance(score)

        return {
            "score": score,
            "grade": grade,
            "similarity": round(similarity, 3),
            "feedback": f"{feedback} (使用傳統方法)",
            "differences": ["使用傳統文字相似度分析"],
            "strengths": [],
            "suggestions": ["建議使用更準確的 AI 分析"],
            "analysis_method": "Traditional",
        }

    def _evaluate_performance(self, score: int) -> tuple:
        """評估表現並給出反饋"""
        if score >= self.grade_thresholds["優秀"]:
            return "優秀", "您的回答非常接近標準答案！"
        elif score >= self.grade_thresholds["良好"]:
            return "良好", "您的回答基本正確，但還有改進空間。"
        elif score >= self.grade_thresholds["一般"]:
            return "一般", "您的回答部分正確，建議參考標準答案。"
        else:
            return "需要改進", "您的回答與標準答案差異較大，建議重新學習相關概念。"

    def get_detailed_analysis(
        self, user_answer: str, standard_answer: str, question: str = ""
    ) -> Dict[str, Any]:
        """獲取詳細分析結果"""
        basic_analysis = self.analyze_answer(user_answer, standard_answer, question)

        # 添加額外的分析資訊
        detailed_analysis = {
            **basic_analysis,
            "word_count": len(user_answer.split()),
            "character_count": len(user_answer),
            "completeness": self._calculate_completeness(user_answer, standard_answer),
        }

        return detailed_analysis

    def _calculate_completeness(self, user_answer: str, standard_answer: str) -> float:
        """計算回答完整度"""
        user_words = set(user_answer.lower().split())
        standard_words = set(standard_answer.lower().split())

        if not standard_words:
            return 0.0

        covered_words = user_words.intersection(standard_words)
        return len(covered_words) / len(standard_words)


# 全域 AI 答案分析器實例
ai_answer_analyzer = AIAnswerAnalyzer()
