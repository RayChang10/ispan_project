#!/usr/bin/env python3
"""
Tools 模組初始化檔案
整合所有面試相關的工具模組
"""

from .answer_analyzer import AnswerAnalyzer, answer_analyzer
from .database import DatabaseManager, db_manager
from .interactive_interview import InteractiveInterview
from .interview_session import InterviewSession, interview_session
from .question_manager import QuestionManager, question_manager
from .ui_manager import UIManager, ui_manager

__all__ = [
    # 類別
    "DatabaseManager",
    "QuestionManager",
    "AnswerAnalyzer",
    "InterviewSession",
    "UIManager",
    "InteractiveInterview",
    # 實例
    "db_manager",
    "question_manager",
    "answer_analyzer",
    "interview_session",
    "ui_manager",
]

# 版本資訊
__version__ = "2.1.0"
__author__ = "MCP Team"
__description__ = "模組化面試工具套件"
