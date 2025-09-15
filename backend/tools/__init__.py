#!/usr/bin/env python3
"""
Tools 模組初始化檔案
整合所有面試相關的工具模組
"""

from .answer_analyzer import AnswerAnalyzer, answer_analyzer
from .interview_manager import InterviewManager, interview_manager
from .minio_user_store import register_user_to_minio as minio_register_user
from .question_manager import QuestionManager, question_manager

# 向後相容的引用
from .interview_manager import interview_manager as interview_session
from .interview_manager import interview_manager as interactive_interview
InteractiveInterview = InterviewManager
InterviewSession = InterviewManager

__all__ = [
    # 類別
    "QuestionManager", 
    "AnswerAnalyzer",
    "InterviewManager",
    "InterviewSession",  # 向後相容
    "InteractiveInterview",  # 向後相容
    "minio_register_user",
    # 實例
    "question_manager",
    "answer_analyzer",
    "interview_manager",
    "interview_session",  # 向後相容
    "interactive_interview",  # 向後相容
    "minio_register_user",
]

# 版本資訊
__version__ = "2.1.0"
__author__ = "MCP Team"
__description__ = "模組化面試工具套件"
