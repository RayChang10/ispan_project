#!/usr/bin/env python3
"""
職缺搜尋 Fast Agent
整合職缺搜尋、履歷分析和職缺媒合功能
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional

# 導入 Fast Agent MCP
try:
    from mcp_agent.core.fastagent import FastAgent
except ImportError:
    print("請先安裝 fast-agent-mcp: pip install fast-agent-mcp")
    exit(1)

# 導入工具
from backend.tools.job_search_tool import search_jobs_tool, search_jobs_by_resume_tool
from backend.tools.resume_analysis_tool import analyze_resume_job_fit_tool, resume_health_check_tool

logger = logging.getLogger(__name__)

# 創建 Fast Agent 應用
job_search_fast = FastAgent("Job Search Agent System", config_path="configs/fastagent.config.yaml")

@job_search_fast.agent(
    name="job_search_system",
    instruction_or_kwarg="""
    職缺搜尋系統 Agent
    
    功能：
    1. 根據履歷搜尋合適職缺
    2. 分析履歷與職缺契合度
    3. 提供履歷健檢建議
    4. 職缺媒合推薦
    
    使用方式：
    - 提供履歷資料進行職缺搜尋
    - 選擇職缺進行契合度分析
    - 請求履歷健檢服務
    """,
    servers=["job_search"],
    model="gpt-4o-mini",
)
async def job_search_system():
    """職缺搜尋系統主 Agent"""
    return """
職缺搜尋系統已啟動！

可用功能：
1. 根據履歷搜尋職缺
2. 分析職缺契合度
3. 履歷健檢
4. 職缺媒合推薦

請提供您的履歷資料或告訴我您需要什麼幫助？
    """

@job_search_fast.agent(
    name="search_jobs_by_resume",
    instruction_or_kwarg="根據履歷搜尋合適職缺",
    servers=["job_search"],
    model="gpt-4o-mini",
)
async def search_jobs_by_resume(resume_data: Dict[str, Any], query: str = ""):
    """根據履歷搜尋職缺"""
    try:
        result = search_jobs_by_resume_tool(resume_data, query)
        
        if result["status"] == "success":
            jobs = result["jobs"]
            response = f"""
🔍 職缺搜尋結果

根據您的履歷，找到 {len(jobs)} 個相關職缺：

"""
            for i, job in enumerate(jobs[:5], 1):  # 顯示前5個
                response += f"""
{i}. **{job['job_title']}** - {job['company_name']}
    📍 地點：{job['location']}
    🔗 連結：{job['job_url']}
    📊 相似度：{job['similarity_score']:.2f}
    
"""
            
            if len(jobs) > 5:
                response += f"\n... 還有 {len(jobs) - 5} 個職缺"
            
            response += """
請選擇您感興趣的職缺編號，我可以為您進行詳細的契合度分析。
"""
            return response
        else:
            return f"❌ 職缺搜尋失敗：{result.get('message', '未知錯誤')}"
            
    except Exception as e:
        return f"❌ 職缺搜尋錯誤：{str(e)}"

@job_search_fast.agent(
    name="analyze_job_fit",
    instruction_or_kwarg="分析履歷與職缺的契合度",
    servers=["job_search"],
    model="gpt-4o-mini",
)
async def analyze_job_fit(resume_data: Dict[str, Any], job_data: Dict[str, Any]):
    """分析履歷與職缺契合度"""
    try:
        result = analyze_resume_job_fit_tool(resume_data, job_data)
        
        if result["status"] == "success":
            return f"""
📊 職缺契合度分析

{result['analysis']}

---
分析完成！您可以：
1. 選擇其他職缺進行分析
2. 進行履歷健檢
3. 開始模擬面試
"""
        else:
            return f"❌ 契合度分析失敗：{result.get('message', '未知錯誤')}"
            
    except Exception as e:
        return f"❌ 契合度分析錯誤：{str(e)}"

@job_search_fast.agent(
    name="resume_health_check",
    instruction_or_kwarg="提供履歷健檢服務",
    servers=["job_search"],
    model="gpt-4o-mini",
)
async def resume_health_check(resume_data: Dict[str, Any], target_job: Optional[Dict[str, Any]] = None):
    """履歷健檢"""
    try:
        result = resume_health_check_tool(resume_data, target_job)
        
        if result["status"] == "success":
            return f"""
📋 履歷健檢報告

{result['health_check']}

---
健檢完成！您可以：
1. 根據建議優化履歷
2. 搜尋更多職缺
3. 開始模擬面試
"""
        else:
            return f"❌ 履歷健檢失敗：{result.get('message', '未知錯誤')}"
            
    except Exception as e:
        return f"❌ 履歷健檢錯誤：{str(e)}"

@job_search_fast.agent(
    name="job_matching_recommendation",
    instruction_or_kwarg="提供職缺媒合推薦",
    servers=["job_search"],
    model="gpt-4o-mini",
)
async def job_matching_recommendation(resume_data: Dict[str, Any]):
    """職缺媒合推薦"""
    try:
        # 搜尋職缺
        search_result = search_jobs_by_resume_tool(resume_data)
        
        if search_result["status"] != "success":
            return f"❌ 職缺搜尋失敗：{search_result.get('message', '未知錯誤')}"
        
        jobs = search_result["jobs"]
        
        # 分析前3個職缺的契合度
        recommendations = []
        for i, job in enumerate(jobs[:3]):
            fit_result = analyze_resume_job_fit_tool(resume_data, job)
            if fit_result["status"] == "success":
                recommendations.append({
                    "job": job,
                    "analysis": fit_result["analysis"]
                })
        
        # 生成推薦報告
        response = f"""
🎯 職缺媒合推薦

根據您的履歷，為您推薦以下職缺：

"""
        
        for i, rec in enumerate(recommendations, 1):
            job = rec["job"]
            response += f"""
{i}. **{job['job_title']}** - {job['company_name']}
    📍 地點：{job['location']}
    📊 相似度：{job['similarity_score']:.2f}
    
    📋 契合度分析：
    {rec['analysis'][:200]}...
    
"""
        
        response += """
---
推薦完成！您可以：
1. 選擇職缺進行詳細分析
2. 進行履歷健檢
3. 開始模擬面試
"""
        
        return response
        
    except Exception as e:
        return f"❌ 職缺媒合推薦錯誤：{str(e)}"

# 主函數
async def main():
    """主函數"""
    async with job_search_fast.run() as agent:
        # 啟動互動式會話
        await agent.interactive()

# 直接運行入口
if __name__ == "__main__":
    asyncio.run(main())


