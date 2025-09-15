#!/usr/bin/env python3
"""
MCP Resources 實作
提供履歷和資料庫資源的 MCP 介面
"""

import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
import os

# 設定日誌
logger = logging.getLogger(__name__)

# MongoDB 履歷管理
from backend.tools.resume_manager import resume_manager

# MinIO 檔案管理
try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False

# 環境變數
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "fastagent-users")

class MCPResourceManager:
    """MCP 資源管理器"""
    
    def __init__(self):
        self.minio_client = None
        if MINIO_AVAILABLE:
            try:
                self.minio_client = Minio(
                    MINIO_ENDPOINT,
                    access_key=MINIO_ACCESS_KEY,
                    secret_key=MINIO_SECRET_KEY,
                    secure=MINIO_SECURE,
                )
                # 確保 bucket 存在
                if not self.minio_client.bucket_exists(MINIO_BUCKET):
                    self.minio_client.make_bucket(MINIO_BUCKET)
                logger.info("✅ MinIO 連接成功，用於資源管理")
            except Exception as e:
                logger.warning(f"⚠️ MinIO 連接失敗: {e}")
                self.minio_client = None
    
    def get_resume_resource(self, resume_id: str, resource_type: str = "parsed") -> Dict[str, Any]:
        """
        獲取履歷資源
        
        Args:
            resume_id: 履歷 ID
            resource_type: 資源類型 ("raw" 或 "parsed")
        
        Returns:
            履歷資源資料
        """
        try:
            if resource_type == "parsed":
                # 從 MongoDB 獲取解析後的履歷
                resume_data = resume_manager.get_resume_by_user_id(resume_id)
                if resume_data:
                    return {
                        "status": "success",
                        "resource_type": "parsed",
                        "resume_id": resume_id,
                        "data": resume_data,
                        "message": "成功獲取解析後的履歷資料"
                    }
                else:
                    return {
                        "status": "not_found",
                        "resource_type": "parsed",
                        "resume_id": resume_id,
                        "message": f"未找到履歷 ID: {resume_id}"
                    }
            
            elif resource_type == "raw":
                # 從 MinIO 獲取原始檔案
                if not self.minio_client:
                    return {
                        "status": "error",
                        "message": "MinIO 不可用，無法獲取原始檔案"
                    }
                
                try:
                    # 嘗試獲取原始檔案
                    object_name = f"resumes/{resume_id}/original"
                    response = self.minio_client.get_object(MINIO_BUCKET, object_name)
                    file_data = response.read()
                    response.close()
                    response.release_conn()
                    
                    return {
                        "status": "success",
                        "resource_type": "raw",
                        "resume_id": resume_id,
                        "data": file_data,
                        "content_type": "application/octet-stream",
                        "message": "成功獲取原始履歷檔案"
                    }
                except S3Error as e:
                    if e.code == "NoSuchKey":
                        return {
                            "status": "not_found",
                            "resource_type": "raw",
                            "resume_id": resume_id,
                            "message": f"未找到原始檔案: {resume_id}"
                        }
                    else:
                        raise e
            
            else:
                return {
                    "status": "error",
                    "message": f"不支援的資源類型: {resource_type}"
                }
                
        except Exception as e:
            logger.error(f"獲取履歷資源失敗: {e}")
            return {
                "status": "error",
                "message": f"獲取履歷資源失敗: {str(e)}"
            }
    
    def get_job_embeddings_resource(self) -> Dict[str, Any]:
        """
        獲取職缺嵌入向量資源（目前為 mock 資料）
        
        Returns:
            職缺嵌入向量資料
        """
        try:
            # Mock 職缺嵌入向量資料
            mock_embeddings = {
                "total_jobs": 1000,
                "embedding_dimension": 1536,
                "last_updated": "2024-01-01T00:00:00Z",
                "sample_embeddings": [
                    {
                        "job_id": "job_001",
                        "title": "Python 開發工程師",
                        "embedding": [0.1] * 1536,  # 簡化的向量表示
                        "metadata": {
                            "company": "科技公司A",
                            "location": "台北",
                            "salary_range": "50000-80000"
                        }
                    },
                    {
                        "job_id": "job_002", 
                        "title": "前端工程師",
                        "embedding": [0.2] * 1536,
                        "metadata": {
                            "company": "科技公司B",
                            "location": "新竹",
                            "salary_range": "45000-70000"
                        }
                    }
                ],
                "description": "這是職缺嵌入向量的 mock 資料，實際應用中會連接到向量資料庫"
            }
            
            return {
                "status": "success",
                "resource_type": "job_embeddings",
                "data": mock_embeddings,
                "message": "成功獲取職缺嵌入向量資源（mock 資料）"
            }
            
        except Exception as e:
            logger.error(f"獲取職缺嵌入向量資源失敗: {e}")
            return {
                "status": "error",
                "message": f"獲取職缺嵌入向量資源失敗: {str(e)}"
            }
    
    def list_resume_resources(self) -> Dict[str, Any]:
        """
        列出所有可用的履歷資源
        
        Returns:
            履歷資源列表
        """
        try:
            # 從 MongoDB 獲取所有履歷 ID
            stats = resume_manager.get_resume_statistics()
            resume_ids = []
            
            # 這裡簡化處理，實際應該從資料庫查詢所有用戶 ID
            if stats and "total_resumes" in stats:
                # Mock 一些履歷 ID
                for i in range(min(stats["total_resumes"], 10)):
                    resume_ids.append(f"user_{i+1}")
            
            resources = []
            for resume_id in resume_ids:
                resources.extend([
                    {
                        "resource_id": f"resume/{resume_id}",
                        "resource_type": "parsed",
                        "description": f"解析後的履歷資料 - {resume_id}"
                    },
                    {
                        "resource_id": f"resume/{resume_id}/raw",
                        "resource_type": "raw", 
                        "description": f"原始履歷檔案 - {resume_id}"
                    }
                ])
            
            return {
                "status": "success",
                "resources": resources,
                "total_count": len(resources),
                "message": f"找到 {len(resources)} 個履歷資源"
            }
            
        except Exception as e:
            logger.error(f"列出履歷資源失敗: {e}")
            return {
                "status": "error",
                "message": f"列出履歷資源失敗: {str(e)}"
            }

# 創建全域實例
resource_manager = MCPResourceManager()

# MCP Resource 函數
def get_resume_resource(resume_id: str, resource_type: str = "parsed") -> Dict[str, Any]:
    """MCP Resource: 獲取履歷資源"""
    return resource_manager.get_resume_resource(resume_id, resource_type)

def get_job_embeddings_resource() -> Dict[str, Any]:
    """MCP Resource: 獲取職缺嵌入向量資源"""
    return resource_manager.get_job_embeddings_resource()

def list_resume_resources() -> Dict[str, Any]:
    """MCP Resource: 列出所有履歷資源"""
    return resource_manager.list_resume_resources()
