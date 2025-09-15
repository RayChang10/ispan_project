#!/usr/bin/env python3
"""
FastMCP Main 服務
主要 API 服務，整合 LiveTalking 和資料庫
"""

import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import redis
import httpx
from pydantic import BaseModel
from typing import Optional, List
import asyncio

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/main.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 環境變數
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/fastmcp")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
LIVETALKING_URL = os.getenv("LIVETALKING_URL", "http://livetalking:8000")

# FastAPI 應用程式
app = FastAPI(
    title="FastMCP Main Service",
    description="主要 API 服務，整合 LiveTalking 和資料庫",
    version="1.0.0"
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 資料庫連接
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis 連接
redis_client = redis.from_url(REDIS_URL)

# HTTP 客戶端
http_client = httpx.AsyncClient()

# Pydantic 模型
class TaskRequest(BaseModel):
    task_type: str
    input_data: dict
    priority: Optional[int] = 1

class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None

class HealthResponse(BaseModel):
    status: str
    services: dict

# 依賴注入
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 健康檢查
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """檢查所有服務的健康狀態"""
    services = {}
    
    # 檢查資料庫
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        services["database"] = "healthy"
    except Exception as e:
        services["database"] = f"unhealthy: {str(e)}"
    
    # 檢查 Redis
    try:
        redis_client.ping()
        services["redis"] = "healthy"
    except Exception as e:
        services["redis"] = f"unhealthy: {str(e)}"
    
    # 檢查 LiveTalking
    try:
        response = await http_client.get(f"{LIVETALKING_URL}/health", timeout=5.0)
        services["livetalking"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception as e:
        services["livetalking"] = f"unhealthy: {str(e)}"
    
    overall_status = "healthy" if all("healthy" in status for status in services.values()) else "unhealthy"
    
    return HealthResponse(status=overall_status, services=services)

# 任務處理
@app.post("/tasks", response_model=TaskResponse)
async def create_task(task: TaskRequest, db=Depends(get_db)):
    """創建新任務"""
    try:
        # 這裡可以添加任務到資料庫
        task_id = f"task_{int(asyncio.get_event_loop().time())}"
        
        # 根據任務類型處理
        if task.task_type == "livetalking":
            # 調用 LiveTalking 服務
            response = await http_client.post(
                f"{LIVETALKING_URL}/process",
                json=task.input_data,
                timeout=30.0
            )
            result = response.json() if response.status_code == 200 else None
        else:
            result = {"message": f"處理任務類型: {task.task_type}"}
        
        # 將結果存儲到 Redis
        redis_client.setex(f"task:{task_id}", 3600, str(result))
        
        return TaskResponse(task_id=task_id, status="completed", result=result)
        
    except Exception as e:
        logger.error(f"任務處理錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 獲取任務狀態
@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """獲取任務狀態"""
    try:
        result = redis_client.get(f"task:{task_id}")
        if result:
            return TaskResponse(task_id=task_id, status="completed", result=eval(result))
        else:
            return TaskResponse(task_id=task_id, status="not_found")
    except Exception as e:
        logger.error(f"獲取任務錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 根路徑
@app.get("/")
async def root():
    """根路徑"""
    return {
        "message": "FastMCP Main Service",
        "version": "1.0.0",
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
