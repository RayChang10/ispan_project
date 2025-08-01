#!/usr/bin/env python3
"""
答案分析模組
負責分析用戶回答與標準答案的差異
"""

import logging
from difflib import SequenceMatcher
from typing import Any, Dict

logger = logging.getLogger(__name__)


class AnswerAnalyzer:
    """答案分析器"""

    def __init__(self, use_ai=True):
        self.grade_thresholds = {"優秀": 80, "良好": 60, "一般": 40, "需要改進": 0}
        self.use_ai = use_ai

        # 如果啟用 AI，嘗試導入 AI 分析器
        if self.use_ai:
            try:
                from .ai_answer_analyzer import ai_answer_analyzer

                self.ai_analyzer = ai_answer_analyzer
            except ImportError:
                logger.warning("AI 分析器導入失敗，將使用傳統方法")
                self.use_ai = False
                self.ai_analyzer = None

    def analyze_answer(
        self, user_answer: str, standard_answer: str, question: str = ""
    ) -> Dict[str, Any]:
        """分析用戶回答與標準答案的差異"""

        # 如果啟用 AI 且有 AI 分析器，優先使用 AI
        if self.use_ai and self.ai_analyzer:
            try:
                return self.ai_analyzer.analyze_answer(
                    user_answer, standard_answer, question
                )
            except Exception as e:
                logger.warning(f"AI 分析失敗，回退到傳統方法: {e}")

        # 使用傳統方法
        return self._traditional_analysis(user_answer, standard_answer)

    def _traditional_analysis(
        self, user_answer: str, standard_answer: str
    ) -> Dict[str, Any]:
        """傳統分析方法"""
        # 計算相似度
        similarity = SequenceMatcher(
            None, user_answer.lower(), standard_answer.lower()
        ).ratio()

        # 分析差異
        differences = self._analyze_differences(user_answer, standard_answer)

        # 評分
        score = int(similarity * 100)
        grade, feedback = self._evaluate_performance(score)

        return {
            "score": score,
            "grade": grade,
            "similarity": round(similarity, 3),
            "differences": differences,
            "feedback": feedback,
            "user_answer": user_answer,
            "standard_answer": standard_answer,
            "analysis_method": "Traditional",
        }

    def _analyze_differences(self, user_answer: str, standard_answer: str) -> list:
        """分析回答差異"""
        differences = []

        # 檢查關鍵字
        standard_keywords = set(standard_answer.lower().split())
        user_keywords = set(user_answer.lower().split())

        missing_keywords = standard_keywords - user_keywords
        extra_keywords = user_keywords - standard_keywords

        if missing_keywords:
            differences.append(f"缺少關鍵字: {', '.join(missing_keywords)}")

        if extra_keywords:
            differences.append(f"多餘的關鍵字: {', '.join(extra_keywords)}")

        # 長度比較
        if len(user_answer) < len(standard_answer) * 0.5:
            differences.append("回答過於簡短，建議提供更多細節")
        elif len(user_answer) > len(standard_answer) * 2:
            differences.append("回答過於冗長，建議簡潔明瞭")

        return differences

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
        self, user_answer: str, standard_answer: str
    ) -> Dict[str, Any]:
        """獲取詳細分析結果"""
        basic_analysis = self.analyze_answer(user_answer, standard_answer)

        # 添加額外的分析資訊
        detailed_analysis = {
            **basic_analysis,
            "word_count": len(user_answer.split()),
            "character_count": len(user_answer),
            "completeness": self._calculate_completeness(user_answer, standard_answer),
            "suggestions": self._generate_suggestions(basic_analysis),
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

    def _generate_suggestions(self, analysis: Dict[str, Any]) -> list:
        """根據分析結果生成建議"""
        suggestions = []

        if analysis["score"] < 60:
            suggestions.append("建議多練習相關概念")
            suggestions.append("可以參考標準答案學習")

        if analysis["score"] < 40:
            suggestions.append("建議重新學習基礎知識")

        if len(analysis["differences"]) > 2:
            suggestions.append("注意回答的準確性和完整性")

        return suggestions


# 全域答案分析器實例
answer_analyzer = AnswerAnalyzer()
