#!/usr/bin/env python3
"""
職缺搜尋 API 路由器
提供 RESTful API 端點給前端調用
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 創建路由器
router = APIRouter(prefix="/api/job_search", tags=["job_search"])

# 請求模型
class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 10

class SearchByResumeRequest(BaseModel):
    resume_data: Dict[str, Any]
    query: Optional[str] = ""

class AnalyzeFitRequest(BaseModel):
    resume_data: Dict[str, Any]
    job_data: Dict[str, Any]

class ResumeHealthCheckRequest(BaseModel):
    resume_data: Dict[str, Any]
    target_job: Optional[Dict[str, Any]] = None

# 回應模型
class JobSearchResponse(BaseModel):
    success: bool
    jobs: Optional[List[Dict[str, Any]]] = None
    count: Optional[int] = 0
    message: Optional[str] = None

class AnalyzeResponse(BaseModel):
    success: bool
    result: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class StatusResponse(BaseModel):
    status: str
    message: str
    milvus_connected: bool = False

# 初始化職缺搜尋工具
job_search_tool = None

def get_job_search_tool():
    """獲取職缺搜尋工具實例"""
    global job_search_tool
    if job_search_tool is None:
        try:
            from backend.tools.job_search_tool import JobSearchTool
            job_search_tool = JobSearchTool()
            logger.info("✅ JobSearchTool 初始化成功")
        except Exception as e:
            logger.error(f"❌ JobSearchTool 初始化失敗: {e}")
            job_search_tool = None
    return job_search_tool

@router.get("/status", response_model=StatusResponse)
async def check_status():
    """檢查服務狀態"""
    tool = get_job_search_tool()
    if tool is None:
        return StatusResponse(
            status="error", 
            message="職缺搜尋工具不可用",
            milvus_connected=False
        )
    
    # 檢查 Milvus 連接
    milvus_connected = tool.connect_milvus()
    
    return StatusResponse(
        status="ok" if milvus_connected else "partial",
        message="服務正常運行" if milvus_connected else "Milvus 連接失敗",
        milvus_connected=milvus_connected
    )

@router.post("/search", response_model=JobSearchResponse)
async def search_jobs(request: SearchRequest):
    """一般職缺搜尋"""
    try:
        tool = get_job_search_tool()
        if tool is None:
            raise HTTPException(status_code=503, detail="職缺搜尋工具不可用")
        
        logger.info(f"搜尋職缺: {request.query}, top_k: {request.top_k}")
        
        # 調用搜尋工具
        results = tool.search_jobs(request.query, top_k=request.top_k)
        
        if not results:
            return JobSearchResponse(
                success=True,
                jobs=[],
                count=0,
                message="未找到相關職缺"
            )
        
        return JobSearchResponse(
            success=True,
            jobs=results,
            count=len(results),
            message="搜尋成功"
        )
        
    except Exception as e:
        logger.error(f"職缺搜尋失敗: {e}")
        raise HTTPException(status_code=500, detail=f"搜尋失敗: {str(e)}")

@router.post("/search_by_resume", response_model=JobSearchResponse)
async def search_jobs_by_resume(request: SearchByResumeRequest):
    """根據履歷搜尋職缺"""
    try:
        tool = get_job_search_tool()
        if tool is None:
            raise HTTPException(status_code=503, detail="職缺搜尋工具不可用")
        
        logger.info(f"根據履歷搜尋職缺: {request.query}")
        
        # 調用搜尋工具
        results = tool.search_jobs_by_resume(request.resume_data, query=request.query)
        
        if not results:
            return JobSearchResponse(
                success=True,
                jobs=[],
                count=0,
                message="未找到相關職缺"
            )
        
        return JobSearchResponse(
            success=True,
            jobs=results,
            count=len(results),
            message="搜尋成功"
        )
        
    except Exception as e:
        logger.error(f"履歷職缺搜尋失敗: {e}")
        raise HTTPException(status_code=500, detail=f"搜尋失敗: {str(e)}")

@router.post("/analyze_fit", response_model=AnalyzeResponse)
async def analyze_fit(request: AnalyzeFitRequest):
    """分析履歷與職缺契合度"""
    try:
        # 這裡需要實現履歷分析邏輯
        # 暫時返回模擬結果
        result = {
            "fit_score": 0.85,
            "strengths": ["技能匹配", "經驗相關"],
            "improvements": ["需要加強特定技能"],
            "summary": "整體契合度良好"
        }
        
        return AnalyzeResponse(
            success=True,
            result=result,
            message="分析完成"
        )
        
    except Exception as e:
        logger.error(f"契合度分析失敗: {e}")
        raise HTTPException(status_code=500, detail=f"分析失敗: {str(e)}")

@router.post("/resume_health_check", response_model=AnalyzeResponse)
async def resume_health_check(request: ResumeHealthCheckRequest):
    """履歷健檢"""
    try:
        # 調用實際的履歷分析工具
        from backend.tools.resume_analysis_tool import resume_health_check_tool
        
        logger.info(f"執行履歷健檢，目標職缺: {request.target_job is not None}")
        
        # 調用履歷健檢工具
        analysis_result = resume_health_check_tool(
            resume_data=request.resume_data,
            target_job=request.target_job
        )
        
        if analysis_result["status"] == "success":
            return AnalyzeResponse(
                success=True,
                result={
                    "health_check": analysis_result["health_check"],
                    "resume_data": analysis_result.get("resume_data"),
                    "target_job": analysis_result.get("target_job")
                },
                message="健檢完成"
            )
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"健檢失敗: {analysis_result.get('message', '未知錯誤')}"
            )
        
    except Exception as e:
        logger.error(f"履歷健檢失敗: {e}")
        raise HTTPException(status_code=500, detail=f"健檢失敗: {str(e)}")
