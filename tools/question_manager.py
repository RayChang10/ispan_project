#!/usr/bin/env python3
"""
問題管理模組
負責獲取和管理面試問題
"""

import logging
import random
from typing import Any, Dict, Optional

from .database import db_manager

logger = logging.getLogger(__name__)


class QuestionManager:
    """問題管理器"""

    def __init__(self):
        self.default_question = {
            "question": "請介紹一下您自己",
            "standard_answer": "我是一位熱愛程式設計的工程師，擅長 Python 和 Web 開發。",
            "source": "預設問題",
        }

    def get_random_question(self) -> Dict[str, Any]:
        """獲取隨機面試問題"""
        # 嘗試連接資料庫
        if not db_manager.connect():
            logger.warning("無法連接資料庫，使用預設問題")
            return self.default_question

        try:
            # 獲取所有集合名稱
            collections = db_manager.get_collections()

            if not collections:
                logger.warning("MongoDB 中沒有找到面試資料集合")
                return self.default_question

            # 隨機選擇一個集合
            random_collection_name = random.choice(collections)
            logger.info(f"選擇集合: {random_collection_name}")

            # 獲取隨機文檔
            random_doc = db_manager.get_random_document(random_collection_name)

            if not random_doc:
                logger.warning(f"無法從集合 {random_collection_name} 獲取隨機文檔")
                return self.default_question

            # 提取問題和答案
            question = self._extract_question(random_doc)
            answer = self._extract_answer(random_doc)

            logger.info(f"從集合 {random_collection_name} 獲取隨機問題")

            return {
                "question": question,
                "standard_answer": answer if answer else "（請根據您的經驗回答）",
                "source": random_collection_name,
                "source_file": random_doc.get("_source_file", "未知"),
                "raw_data": random_doc,  # 保留原始資料供調試
            }

        except Exception as e:
            logger.error(f"獲取隨機問題時發生錯誤: {e}")
            return self.default_question

    def get_question_by_category(self, category: str) -> Dict[str, Any]:
        """按類別獲取問題"""
        # 這裡可以實現按類別篩選的邏輯
        return self.get_random_question()

    def get_question_by_difficulty(self, difficulty: str) -> Dict[str, Any]:
        """按難度獲取問題"""
        # 這裡可以實現按難度篩選的邏輯
        return self.get_random_question()

    def _extract_question(self, doc: Dict[str, Any]) -> str:
        """從文檔中提取問題"""
        # 嘗試不同的欄位名稱
        question_fields = ["問題", "Question", "題目", "instruction", "question"]

        for field in question_fields:
            if field in doc and doc[field]:
                return str(doc[field])

        # 如果沒有找到問題，使用文檔的其他欄位
        for key, value in doc.items():
            if (
                key not in ["_id", "_source_file", "_row_number", "_import_time"]
                and value
            ):
                return f"{key}: {value}"

        return self.default_question["question"]

    def _extract_answer(self, doc: Dict[str, Any]) -> str:
        """從文檔中提取答案"""
        answer_fields = ["答案", "Answer", "answer", "output", "standard_answer"]

        for field in answer_fields:
            if field in doc and doc[field]:
                return str(doc[field])

        return self.default_question["standard_answer"]


# 全域問題管理器實例
question_manager = QuestionManager()
