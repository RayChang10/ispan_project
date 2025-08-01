#!/usr/bin/env python3
"""
資料庫連接模組
負責 MongoDB 連接和基本操作
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class DatabaseManager:
    """資料庫管理器"""

    def __init__(self, connection_string: str = "mongodb://localhost:27017/"):
        self.connection_string = connection_string
        self.client = None
        self.db = None

    def connect(self) -> bool:
        """連接到 MongoDB"""
        try:
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure

            self.client = MongoClient(self.connection_string)
            self.db = self.client["interview_db"]

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

    def close(self):
        """關閉資料庫連接"""
        if self.client:
            self.client.close()
            logger.info("資料庫連接已關閉")


# 全域資料庫管理器實例
db_manager = DatabaseManager()
