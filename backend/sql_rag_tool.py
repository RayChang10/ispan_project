#!/usr/bin/env python3
"""
SQL/RAG 工具實作
提供安全的 SQL 查詢和 RAG 功能
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional
import sqlite3
import psycopg2
from sqlalchemy import create_engine, text
import redis

# 設定日誌
logger = logging.getLogger(__name__)

# 環境變數
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/fastmcp")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

class SQLRAGTool:
    """SQL/RAG 工具"""
    
    def __init__(self):
        self.database_url = DATABASE_URL
        self.redis_client = None
        
        # 初始化資料庫連接
        try:
            self.engine = create_engine(self.database_url)
            logger.info("✅ 資料庫連接成功")
        except Exception as e:
            logger.error(f"❌ 資料庫連接失敗: {e}")
            self.engine = None
        
        # 初始化 Redis 連接
        try:
            self.redis_client = redis.from_url(REDIS_URL)
            self.redis_client.ping()
            logger.info("✅ Redis 連接成功")
        except Exception as e:
            logger.warning(f"⚠️ Redis 連接失敗: {e}")
            self.redis_client = None
        
        # SQL 白名單 - 只允許安全的查詢
        self.allowed_keywords = {
            'SELECT', 'FROM', 'WHERE', 'ORDER BY', 'GROUP BY', 'HAVING',
            'LIMIT', 'OFFSET', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN',
            'UNION', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX',
            'AND', 'OR', 'NOT', 'IN', 'BETWEEN', 'LIKE', 'IS NULL', 'IS NOT NULL'
        }
        
        # 禁止的關鍵字
        self.forbidden_keywords = {
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE',
            'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'CALL', 'PROCEDURE',
            'FUNCTION', 'TRIGGER', 'INDEX', 'VIEW', 'SCHEMA', 'DATABASE'
        }
    
    def validate_sql_query(self, sql_query: str) -> Dict[str, Any]:
        """
        驗證 SQL 查詢的安全性
        
        Args:
            sql_query: SQL 查詢語句
        
        Returns:
            驗證結果
        """
        try:
            sql_upper = sql_query.upper().strip()
            
            # 檢查是否包含禁止的關鍵字
            for forbidden in self.forbidden_keywords:
                if forbidden in sql_upper:
                    return {
                        "valid": False,
                        "reason": f"禁止使用關鍵字: {forbidden}",
                        "message": "只允許 SELECT 查詢，不允許修改資料"
                    }
            
            # 檢查是否以 SELECT 開頭
            if not sql_upper.startswith('SELECT'):
                return {
                    "valid": False,
                    "reason": "查詢必須以 SELECT 開頭",
                    "message": "只允許 SELECT 查詢"
                }
            
            # 檢查查詢長度
            if len(sql_query) > 1000:
                return {
                    "valid": False,
                    "reason": "查詢過長",
                    "message": "查詢長度不能超過 1000 字元"
                }
            
            return {
                "valid": True,
                "message": "SQL 查詢驗證通過"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "reason": f"驗證過程發生錯誤: {str(e)}",
                "message": "SQL 查詢驗證失敗"
            }
    
    def execute_sql_query(self, sql_query: str, limit: int = 100) -> Dict[str, Any]:
        """
        執行安全的 SQL 查詢
        
        Args:
            sql_query: SQL 查詢語句
            limit: 結果限制數量
        
        Returns:
            查詢結果
        """
        try:
            if not self.engine:
                return {
                    "status": "error",
                    "message": "資料庫連接不可用"
                }
            
            # 驗證 SQL 查詢
            validation = self.validate_sql_query(sql_query)
            if not validation["valid"]:
                return {
                    "status": "error",
                    "message": validation["message"],
                    "reason": validation["reason"]
                }
            
            # 添加 LIMIT 限制
            if 'LIMIT' not in sql_query.upper():
                sql_query = f"{sql_query.rstrip(';')} LIMIT {limit}"
            
            # 執行查詢
            with self.engine.connect() as connection:
                result = connection.execute(text(sql_query))
                rows = result.fetchall()
                
                # 轉換結果為字典列表
                columns = result.keys()
                results = []
                for row in rows:
                    row_dict = {}
                    for i, column in enumerate(columns):
                        value = row[i]
                        # 處理特殊類型
                        if hasattr(value, 'isoformat'):  # datetime
                            value = value.isoformat()
                        elif isinstance(value, (bytes, bytearray)):  # binary
                            value = str(value)
                        row_dict[column] = value
                    results.append(row_dict)
                
                return {
                    "status": "success",
                    "query": sql_query,
                    "results": results,
                    "count": len(results),
                    "columns": list(columns),
                    "message": f"查詢成功，返回 {len(results)} 筆記錄"
                }
                
        except Exception as e:
            logger.error(f"SQL 查詢執行失敗: {e}")
            return {
                "status": "error",
                "message": f"SQL 查詢執行失敗: {str(e)}",
                "query": sql_query
            }
    
    def get_database_schema(self) -> Dict[str, Any]:
        """
        獲取資料庫結構資訊
        
        Returns:
            資料庫結構資訊
        """
        try:
            if not self.engine:
                return {
                    "status": "error",
                    "message": "資料庫連接不可用"
                }
            
            schema_info = {
                "tables": [],
                "views": [],
                "functions": []
            }
            
            with self.engine.connect() as connection:
                # 獲取表格資訊
                if "postgresql" in self.database_url.lower():
                    # PostgreSQL
                    tables_query = """
                    SELECT table_name, table_type 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                    """
                else:
                    # SQLite
                    tables_query = """
                    SELECT name as table_name, type as table_type
                    FROM sqlite_master 
                    WHERE type IN ('table', 'view')
                    ORDER BY name
                    """
                
                result = connection.execute(text(tables_query))
                for row in result:
                    schema_info["tables"].append({
                        "name": row[0],
                        "type": row[1] if len(row) > 1 else "table"
                    })
            
            return {
                "status": "success",
                "schema": schema_info,
                "database_type": "postgresql" if "postgresql" in self.database_url.lower() else "sqlite",
                "message": f"成功獲取資料庫結構，包含 {len(schema_info['tables'])} 個表格"
            }
            
        except Exception as e:
            logger.error(f"獲取資料庫結構失敗: {e}")
            return {
                "status": "error",
                "message": f"獲取資料庫結構失敗: {str(e)}"
            }
    
    def get_job_embeddings_rag(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """
        使用 RAG 搜尋職缺嵌入向量
        
        Args:
            query: 查詢文字
            top_k: 返回數量
        
        Returns:
            RAG 搜尋結果
        """
        try:
            # 這裡是 mock 實作，實際應該連接到向量資料庫
            mock_results = [
                {
                    "job_id": f"job_{i+1:03d}",
                    "title": f"職缺標題 {i+1}",
                    "company": f"公司 {i+1}",
                    "similarity_score": 0.9 - (i * 0.1),
                    "description": f"這是職缺 {i+1} 的描述內容，包含相關技能和要求。",
                    "metadata": {
                        "location": f"地點 {i+1}",
                        "salary_range": f"{50000 + i*5000}-{80000 + i*5000}",
                        "experience_level": "中級" if i % 2 == 0 else "高級"
                    }
                }
                for i in range(min(top_k, 5))
            ]
            
            return {
                "status": "success",
                "query": query,
                "results": mock_results,
                "count": len(mock_results),
                "method": "RAG_vector_search",
                "message": f"RAG 搜尋完成，找到 {len(mock_results)} 個相關職缺"
            }
            
        except Exception as e:
            logger.error(f"RAG 搜尋失敗: {e}")
            return {
                "status": "error",
                "message": f"RAG 搜尋失敗: {str(e)}"
            }

# 創建全域實例
sql_rag_tool = SQLRAGTool()

# MCP 工具函數
def query_sql(sql_query: str, limit: int = 100) -> Dict[str, Any]:
    """MCP 工具：執行安全的 SQL 查詢"""
    return sql_rag_tool.execute_sql_query(sql_query, limit)

def get_database_schema() -> Dict[str, Any]:
    """MCP 工具：獲取資料庫結構"""
    return sql_rag_tool.get_database_schema()

def rag_search_jobs(query: str, top_k: int = 10) -> Dict[str, Any]:
    """MCP 工具：使用 RAG 搜尋職缺"""
    return sql_rag_tool.get_job_embeddings_rag(query, top_k)
