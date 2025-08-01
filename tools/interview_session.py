#!/usr/bin/env python3
"""
面試流程模組
負責管理整個面試流程
"""

import logging
from typing import Any, Dict, Optional

from .answer_analyzer import answer_analyzer
from .question_manager import question_manager

logger = logging.getLogger(__name__)


class InterviewSession:
    """面試會話管理器"""

    def __init__(self):
        self.current_question = None
        self.current_answer = None
        self.session_history = []

    def start_session(self) -> Dict[str, Any]:
        """開始新的面試會話"""
        self.session_history = []
        logger.info("開始新的面試會話")
        return {"status": "started", "message": "面試會話已開始"}

    def get_next_question(self) -> Dict[str, Any]:
        """獲取下一個問題"""
        question_data = question_manager.get_random_question()

        self.current_question = question_data["question"]
        self.current_answer = question_data["standard_answer"]

        # 記錄到會話歷史
        self.session_history.append({"type": "question", "data": question_data})

        return {
            "status": "question_ready",
            "question": question_data["question"],
            "source": question_data["source"],
            "message": "面試問題已準備好，請回答以下問題：",
            "instruction": f"問題：{question_data['question']}\n來源：{question_data['source']}\n\n請輸入您的回答：",
        }

    def submit_answer(self, user_answer: str) -> Dict[str, Any]:
        """提交用戶回答"""
        if not self.current_question:
            return {"status": "error", "message": "沒有當前問題"}

        if not user_answer.strip():
            return {"status": "skipped", "message": "您跳過了這個問題"}

        # 分析回答
        analysis = answer_analyzer.analyze_answer(user_answer, self.current_answer)

        # 記錄到會話歷史
        self.session_history.append(
            {"type": "answer", "user_answer": user_answer, "analysis": analysis}
        )

        return {
            "status": "analysis_complete",
            "user_answer": user_answer,
            "question": self.current_question,
            "standard_answer": self.current_answer,
            "analysis": analysis,
            "summary": f"評分：{analysis['score']}/100 ({analysis['grade']})\n相似度：{analysis['similarity']:.1%}\n反饋：{analysis['feedback']}",
        }

    def get_session_summary(self) -> Dict[str, Any]:
        """獲取會話摘要"""
        if not self.session_history:
            return {"status": "empty", "message": "會話歷史為空"}

        questions = [
            item for item in self.session_history if item["type"] == "question"
        ]
        answers = [item for item in self.session_history if item["type"] == "answer"]

        total_score = 0
        total_questions = len(answers)

        for answer in answers:
            total_score += answer["analysis"]["score"]

        average_score = total_score / total_questions if total_questions > 0 else 0

        return {
            "status": "summary",
            "total_questions": total_questions,
            "average_score": round(average_score, 2),
            "session_history": self.session_history,
        }

    def end_session(self) -> Dict[str, Any]:
        """結束面試會話"""
        summary = self.get_session_summary()
        logger.info("面試會話已結束")
        return {"status": "ended", "message": "面試會話已結束", "summary": summary}


# 全域面試會話管理器實例
interview_session = InterviewSession()
