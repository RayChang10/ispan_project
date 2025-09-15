#!/usr/bin/env python3
"""
資料庫連接模組
負責 MongoDB 連接和基本操作
"""

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class DatabaseManager:
    """資料庫管理器"""

    def __init__(self, connection_string: Optional[str] = None):
        # 允許以參數或環境變數指定，最後退回預設值（容器內預設連 mongo 服務）
        self.connection_string = connection_string or os.getenv(
            "MONGODB_URI", "mongodb://admin:changeme@mongo:27017/?authSource=admin"
        )
        self.client = None
        self.db = None

    def connect(self) -> bool:
        """連接到 MongoDB"""
        try:
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure

            self.client = MongoClient(self.connection_string)
            self.db = self.client[os.getenv("MONGODB_DB_NAME", "interview_db")]

            # 測試連接
            self.client.admin.command("ping")
            logger.info("✅ MongoDB 連接成功")
            return True

        except ImportError:
            logger.warning("pymongo 未安裝")
            return False
        except ConnectionFailure:
            logger.warning("無法連接到 MongoDB")
            return False
        except Exception as e:
            logger.error(f"資料庫連接失敗: {e}")
            return False

    def get_collections(self) -> list:
        """獲取所有集合名稱"""
        if self.db is None:
            return []

        try:
            return self.db.list_collection_names()
        except Exception as e:
            logger.error(f"獲取集合失敗: {e}")
            return []

    def get_random_document(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """從指定集合獲取隨機文檔"""
        if self.db is None:
            return None

        try:
            import random

            collection = self.db[collection_name]
            total_docs = collection.count_documents({})

            if total_docs == 0:
                return None

            random_skip = random.randint(0, total_docs - 1)
            return collection.find_one({}, skip=random_skip)

        except Exception as e:
            logger.error(f"獲取隨機文檔失敗: {e}")
            return None

    def find_documents_by_keyword(self, collection_name: str, keyword: str, limit: int = 10):
        """根據關鍵字搜尋文檔"""
        if not self.db:
            logger.error("資料庫未連接")
            return []
        
        try:
            collection = self.db[collection_name]
            
            # 建立文字搜尋查詢
            # 在多個可能的欄位中搜尋關鍵字（不區分大小寫）
            query = {
                "$or": [
                    {"問題": {"$regex": keyword, "$options": "i"}},
                    {"Question": {"$regex": keyword, "$options": "i"}},
                    {"題目": {"$regex": keyword, "$options": "i"}},
                    {"instruction": {"$regex": keyword, "$options": "i"}},
                    {"question": {"$regex": keyword, "$options": "i"}},
                    {"答案": {"$regex": keyword, "$options": "i"}},
                    {"Answer": {"$regex": keyword, "$options": "i"}},
                    {"標準答案": {"$regex": keyword, "$options": "i"}},
                    {"standard_answer": {"$regex": keyword, "$options": "i"}},
                    {"content": {"$regex": keyword, "$options": "i"}},
                    {"description": {"$regex": keyword, "$options": "i"}},
                ]
            }
            
            # 執行查詢
            documents = list(collection.find(query).limit(limit))
            
            logger.info(f"在集合 {collection_name} 中找到 {len(documents)} 個包含關鍵字 '{keyword}' 的文檔")
            
            return documents
            
        except Exception as e:
            logger.error(f"搜尋關鍵字 '{keyword}' 失敗: {e}")
            return []

    def close(self):
        """關閉資料庫連接"""
        if self.client:
            self.client.close()
            logger.info("資料庫連接已關閉")


# 全域資料庫管理器實例
db_manager = DatabaseManager()
