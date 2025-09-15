#!/usr/bin/env python3
"""
統一工作流程管理器
整合面試和職缺搜尋功能，按照 withLLM.txt 的流程設計
"""

import json
import logging
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class WorkflowStage(Enum):
    """工作流程階段"""
    LOGIN = "login"
    RESUME_INPUT = "resume_input"
    JOB_SEARCH = "job_search"
    JOB_SELECTION = "job_selection"
    FIT_ANALYSIS = "fit_analysis"
    RESUME_HEALTH_CHECK = "resume_health_check"
    MOCK_INTERVIEW = "mock_interview"
    COMPLETION = "completion"

class UnifiedWorkflowManager:
    """統一工作流程管理器"""
    
    def __init__(self):
        self.current_stage = WorkflowStage.LOGIN
        self.user_data = {}
        self.resume_data = {}
        self.selected_job = {}
        self.search_results = []
        self.interview_data = {}
    
    def set_stage(self, stage: WorkflowStage):
        """設定當前階段"""
        self.current_stage = stage
        logger.info(f"🔄 工作流程階段變更: {stage.value}")
    
    def get_stage(self) -> str:
        """獲取當前階段"""
        return self.current_stage.value
    
    def set_user_data(self, user_data: Dict[str, Any]):
        """設定用戶資料"""
        self.user_data = user_data
    
    def set_resume_data(self, resume_data: Dict[str, Any]):
        """設定履歷資料"""
        self.resume_data = resume_data
        logger.info("📝 履歷資料已設定")
    
    def set_search_results(self, results: List[Dict[str, Any]]):
        """設定搜尋結果"""
        self.search_results = results
        logger.info(f"🔍 職缺搜尋結果已設定: {len(results)} 個職缺")
    
    def set_selected_job(self, job_data: Dict[str, Any]):
        """設定選中的職缺"""
        self.selected_job = job_data
        logger.info(f"🎯 已選擇職缺: {job_data.get('job_title', 'Unknown')}")
    
    def set_interview_data(self, interview_data: Dict[str, Any]):
        """設定面試資料"""
        self.interview_data = interview_data
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """獲取工作流程狀態"""
        return {
            "current_stage": self.current_stage.value,
            "has_resume": bool(self.resume_data),
            "has_search_results": bool(self.search_results),
            "has_selected_job": bool(self.selected_job),
            "has_interview_data": bool(self.interview_data)
        }
    
    def can_proceed_to_job_search(self) -> bool:
        """檢查是否可以進行職缺搜尋"""
        return bool(self.resume_data)
    
    def can_proceed_to_fit_analysis(self) -> bool:
        """檢查是否可以進行契合度分析"""
        return bool(self.resume_data and self.selected_job)
    
    def can_proceed_to_resume_health_check(self) -> bool:
        """檢查是否可以進行履歷健檢"""
        return bool(self.resume_data)
    
    def can_proceed_to_mock_interview(self) -> bool:
        """檢查是否可以進行模擬面試"""
        return bool(self.resume_data and self.selected_job)
    
    def get_next_available_stages(self) -> List[str]:
        """獲取下一個可用的階段"""
        available_stages = []
        
        if self.can_proceed_to_job_search():
            available_stages.append("job_search")
        
        if self.can_proceed_to_fit_analysis():
            available_stages.append("fit_analysis")
        
        if self.can_proceed_to_resume_health_check():
            available_stages.append("resume_health_check")
        
        if self.can_proceed_to_mock_interview():
            available_stages.append("mock_interview")
        
        return available_stages
    
    def reset_workflow(self):
        """重置工作流程"""
        self.current_stage = WorkflowStage.LOGIN
        self.user_data = {}
        self.resume_data = {}
        self.selected_job = {}
        self.search_results = []
        self.interview_data = {}
        logger.info("🔄 工作流程已重置")

# 全域工作流程管理器實例
workflow_manager = UnifiedWorkflowManager()

def get_workflow_manager() -> UnifiedWorkflowManager:
    """獲取工作流程管理器"""
    return workflow_manager

def process_workflow_request(request_type: str, **kwargs) -> Dict[str, Any]:
    """處理工作流程請求"""
    try:
        manager = get_workflow_manager()
        
        if request_type == "set_resume":
            """設定履歷資料"""
            resume_data = kwargs.get("resume_data", {})
            manager.set_resume_data(resume_data)
            manager.set_stage(WorkflowStage.RESUME_INPUT)
            
            return {
                "status": "success",
                "message": "履歷資料已設定",
                "next_stages": manager.get_next_available_stages(),
                "current_stage": manager.get_stage()
            }
        
        elif request_type == "search_jobs":
            """職缺搜尋"""
            if not manager.can_proceed_to_job_search():
                return {
                    "status": "error",
                    "message": "請先提供履歷資料"
                }
            
            query = kwargs.get("query", "")
            from backend.fast_agent_bridge import call_fast_agent_function
            
            result = call_fast_agent_function(
                "search_jobs_by_resume",
                resume_data=manager.resume_data,
                query=query
            )
            
            if result.get("status") == "success":
                manager.set_search_results(result.get("jobs", []))
                manager.set_stage(WorkflowStage.JOB_SEARCH)
            
            return result
        
        elif request_type == "select_job":
            """選擇職缺"""
            job_index = kwargs.get("job_index", 0)
            
            if job_index < len(manager.search_results):
                selected_job = manager.search_results[job_index]
                manager.set_selected_job(selected_job)
                manager.set_stage(WorkflowStage.JOB_SELECTION)
                
                return {
                    "status": "success",
                    "message": f"已選擇職缺: {selected_job.get('job_title', 'Unknown')}",
                    "selected_job": selected_job,
                    "next_stages": manager.get_next_available_stages()
                }
            else:
                return {
                    "status": "error",
                    "message": "無效的職缺索引"
                }
        
        elif request_type == "analyze_fit":
            """分析契合度"""
            if not manager.can_proceed_to_fit_analysis():
                return {
                    "status": "error",
                    "message": "請先選擇職缺"
                }
            
            from backend.fast_agent_bridge import call_fast_agent_function
            
            result = call_fast_agent_function(
                "analyze_job_fit",
                resume_data=manager.resume_data,
                job_data=manager.selected_job
            )
            
            if result.get("status") == "success":
                manager.set_stage(WorkflowStage.FIT_ANALYSIS)
            
            return result
        
        elif request_type == "resume_health_check":
            """履歷健檢"""
            if not manager.can_proceed_to_resume_health_check():
                return {
                    "status": "error",
                    "message": "請先提供履歷資料"
                }
            
            from backend.fast_agent_bridge import call_fast_agent_function
            
            result = call_fast_agent_function(
                "resume_health_check",
                resume_data=manager.resume_data,
                target_job=manager.selected_job if manager.selected_job else None
            )
            
            if result.get("status") == "success":
                manager.set_stage(WorkflowStage.RESUME_HEALTH_CHECK)
            
            return result
        
        elif request_type == "start_mock_interview":
            """開始模擬面試"""
            if not manager.can_proceed_to_mock_interview():
                return {
                    "status": "error",
                    "message": "請先選擇職缺"
                }
            
            manager.set_stage(WorkflowStage.MOCK_INTERVIEW)
            
            return {
                "status": "success",
                "message": "模擬面試已開始",
                "current_stage": manager.get_stage()
            }
        
        elif request_type == "get_status":
            """獲取工作流程狀態"""
            return {
                "status": "success",
                "workflow_status": manager.get_workflow_status(),
                "next_stages": manager.get_next_available_stages()
            }
        
        elif request_type == "reset":
            """重置工作流程"""
            manager.reset_workflow()
            return {
                "status": "success",
                "message": "工作流程已重置"
            }
        
        else:
            return {
                "status": "error",
                "message": f"未知的請求類型: {request_type}"
            }
    
    except Exception as e:
        logger.error(f"❌ 工作流程處理失敗: {str(e)}")
        return {
            "status": "error",
            "message": f"工作流程處理失敗: {str(e)}"
        }


