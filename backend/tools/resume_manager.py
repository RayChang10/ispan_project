#!/usr/bin/env python3
"""
履歷資料 MongoDB 管理器
將履歷資料儲存到 resume_db 資料庫
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from pymongo import MongoClient
from pymongo.errors import BulkWriteError, ConnectionFailure

# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ResumeManager:
    """履歷資料管理器"""

    def __init__(
        self,
        mongo_uri: Optional[str] = None,
        db_name: Optional[str] = None,
    ):
        """
        初始化履歷管理器

        Args:
            mongo_uri: MongoDB 連接 URI
            db_name: 資料庫名稱
        """
        # 允許以參數或環境變數指定，最後退回預設值
        # 建議在 WSL 設定環境變數 MONGO_URI，例如：
        # mongodb://admin:changeme@localhost:27017/?authSource=admin
        # 在容器內使用 mongo 容器名稱，在主機使用 localhost
        # 在容器內運行，使用容器名稱連接
        default_uri = "mongodb://admin:changeme@mongo:27017/?authSource=admin"
            
        self.mongo_uri = mongo_uri or os.getenv("MONGO_URI", default_uri)
        # 履歷使用 resume_db
        self.db_name = db_name or os.getenv("RESUME_DB_NAME", "resume_db")
        self.client = None
        self.db = None

    def connect_to_mongodb(self) -> bool:
        """連接到 MongoDB"""
        try:
            self.client = MongoClient(self.mongo_uri)
            # 測試連接
            self.client.admin.command("ping")
            self.db = self.client[self.db_name]
            # 避免在日誌中輸出包含帳密的 URI
            logger.info("✅ 成功連接到 MongoDB 伺服器")
            logger.info(f"📊 使用資料庫: {self.db_name}")
            return True
        except ConnectionFailure as e:
            logger.info(f"ℹ️  MongoDB 未運行，資料庫功能將不可用（不影響主要功能）")
            return False
        except Exception as e:
            logger.error(f"❌ 連接錯誤: {e}")
            return False

    def disconnect_from_mongodb(self):
        """斷開 MongoDB 連接"""
        if self.client:
            self.client.close()
            logger.info("🔌 已斷開 MongoDB 連接")

    def save_resume(self, user_id: str, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        儲存履歷資料到 MongoDB

        Args:
            user_id: 用戶 ID
            resume_data: 履歷資料

        Returns:
            儲存結果
        """
        if not self.connect_to_mongodb():
            return {"status": "error", "message": "無法連接到 MongoDB"}

        try:
            collection = self.db["resumes"]
            
            # 準備履歷資料
            resume_doc = {
                "user_id": user_id,
                "resume_data": resume_data,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            # 檢查是否已存在該用戶的履歷
            existing_resume = collection.find_one({"user_id": user_id})
            
            if existing_resume:
                # 更新現有履歷
                result = collection.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "resume_data": resume_data,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                logger.info(f"✅ 更新履歷成功: {user_id}")
                return {"status": "updated", "user_id": user_id}
            else:
                # 插入新履歷
                result = collection.insert_one(resume_doc)
                logger.info(f"✅ 新增履歷成功: {user_id}")
                return {"status": "created", "user_id": user_id, "id": str(result.inserted_id)}

        except Exception as e:
            logger.error(f"❌ 儲存履歷失敗: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            self.disconnect_from_mongodb()

    def get_resume(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取用戶履歷

        Args:
            user_id: 用戶 ID

        Returns:
            履歷資料或 None
        """
        if not self.connect_to_mongodb():
            return None

        try:
            collection = self.db["resumes"]
            resume = collection.find_one({"user_id": user_id})
            return resume
        except Exception as e:
            logger.error(f"❌ 獲取履歷失敗: {e}")
            return None
        finally:
            self.disconnect_from_mongodb()

    def list_resumes(self) -> List[Dict[str, Any]]:
        """
        列出所有履歷

        Returns:
            履歷列表
        """
        if not self.connect_to_mongodb():
            return []

        try:
            collection = self.db["resumes"]
            resumes = list(collection.find({}, {"_id": 0, "user_id": 1, "created_at": 1, "updated_at": 1}))
            return resumes
        except Exception as e:
            logger.error(f"❌ 列出履歷失敗: {e}")
            return []
        finally:
            self.disconnect_from_mongodb()

    def delete_resume(self, user_id: str) -> Dict[str, Any]:
        """
        刪除用戶履歷

        Args:
            user_id: 用戶 ID

        Returns:
            刪除結果字典
        """
        if not self.connect_to_mongodb():
            return {"status": "error", "message": "無法連接到 MongoDB"}

        try:
            collection = self.db["resumes"]
            result = collection.delete_one({"user_id": user_id})
            if result.deleted_count > 0:
                logger.info(f"✅ 刪除履歷成功: {user_id}")
                return {"status": "deleted", "user_id": user_id}
            else:
                logger.warning(f"⚠️ 履歷不存在: {user_id}")
                return {"status": "not_found", "user_id": user_id}
        except Exception as e:
            logger.error(f"❌ 刪除履歷失敗: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            self.disconnect_from_mongodb()

    def create_indexes(self):
        """創建索引"""
        if not self.connect_to_mongodb():
            return

        try:
            collection = self.db["resumes"]
            
            # 為常用查詢欄位創建索引
            collection.create_index("user_id", unique=True)
            collection.create_index("created_at")
            collection.create_index("updated_at")
            
            logger.info("🔍 已為履歷集合創建索引")
        except Exception as e:
            logger.warning(f"⚠️ 創建索引失敗: {e}")
        finally:
            self.disconnect_from_mongodb()


# 全域履歷管理器實例
resume_manager = ResumeManager()


if __name__ == "__main__":
    """主程式 - 測試履歷管理器"""
    print("🚀 履歷資料 MongoDB 管理器")
    print("=" * 50)

    # 創建履歷管理器實例
    manager = ResumeManager()

    # 測試連接
    if manager.connect_to_mongodb():
        print("✅ MongoDB 連接成功")
        
        # 創建索引
        manager.create_indexes()
        
        # 測試儲存履歷
        test_resume = {
            "name": "測試用戶",
            "email": "test@example.com",
            "phone": "0912345678",
            "experience": "3年 Python 開發經驗"
        }
        
        result = manager.save_resume("test_user_001", test_resume)
        print(f"📝 儲存履歷結果: {result}")
        
        # 列出所有履歷
        resumes = manager.list_resumes()
        print(f"📋 履歷數量: {len(resumes)}")
        
        # 獲取特定履歷
        resume = manager.get_resume("test_user_001")
        if resume:
            print(f"👤 獲取履歷: {resume['user_id']}")
        
        manager.disconnect_from_mongodb()
    else:
        print("❌ MongoDB 連接失敗")
