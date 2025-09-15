#!/usr/bin/env python3
"""
職缺搜尋 MCP 工具
整合 Milvus 向量搜尋和 OpenAI Embedding
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from pymilvus import connections, Collection
from openai import OpenAI

logger = logging.getLogger(__name__)

class JobSearchTool:
    """職缺搜尋工具"""
    
    def __init__(self):
        self.milvus_host = os.getenv("MILVUS_HOST", "localhost")
        self.milvus_port = os.getenv("MILVUS_PORT", "19530")
        self.collection_name = "job_postings_openai"
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = "text-embedding-3-small"
        
    def connect_milvus(self) -> bool:
        """連接到 Milvus"""
        try:
            connections.connect("default", host=self.milvus_host, port=self.milvus_port)
            logger.info("✅ Milvus 連線成功")
            return True
        except Exception as e:
            logger.error(f"❌ Milvus 連線失敗: {e}")
            return False
    
    def get_collection(self) -> Optional[Collection]:
        """獲取 Milvus Collection"""
        try:
            if not self.connect_milvus():
                return None
            collection = Collection(self.collection_name)
            collection.load()
            return collection
        except Exception as e:
            logger.error(f"❌ 獲取 Collection 失敗: {e}")
            return None
    
    def embed_query(self, query_text: str) -> Optional[List[float]]:
        """將查詢文字轉換為向量"""
        try:
            response = self.openai_client.embeddings.create(
                input=[query_text], 
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ 向量化失敗: {e}")
            return None
    
    def _llm_filter_jobs(self, query: str, candidate_jobs: List[Dict], target_count: int) -> List[Dict[str, Any]]:
        """使用 LLM 智能篩選最相關的職缺"""
        try:
            if not candidate_jobs:
                return []
            
            # 構建候選職缺內容供 LLM 分析
            context = ""
            for job in candidate_jobs:
                context += f"--- 參考資料 {job['index']} ---\n"
                context += f"職缺名稱: {job['job_title']}\n"
                context += f"公司: {job['company_name']}\n"
                context += f"職缺連結: {job['job_url']}\n"
                context += f"內容片段: {job['description'][:500]}...\n\n"
            
            # LLM 分析 prompt
            prompt = f"""# [專家角色]: AI 職缺篩選專家
# [任務]: 根據使用者的搜尋條件，從候選職缺中篩選出最相關的職缺
# [規則]:
1. 嚴格根據「使用者搜尋條件」篩選候選職缺
2. 優先匹配關鍵字和職位相關性
3. 你的回答必須只包含一個 MATCH 標記，格式為 `MATCH: [編號1, 編號2, ...]`
4. 最多選擇 {target_count} 個最相關的職缺
5. 如果沒有符合條件的，請回傳 `MATCH: []`

# [使用者搜尋條件]: {query}
# [候選職缺]:
{context}

請分析以上職缺並選出最符合條件的 {target_count} 個職缺："""

            # 調用 OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一位專業的職缺篩選專家，專門幫助求職者找到最適合的工作機會。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            llm_response = response.choices[0].message.content.strip()
            
            # 解析 LLM 推薦
            import re
            match_line = re.search(r"MATCH:\s*\[(.*?)\]", llm_response)
            if match_line:
                try:
                    indices = [int(i.strip()) for i in match_line.group(1).split(',') if i.strip()]
                    
                    # 根據 LLM 推薦的索引返回對應職缺
                    filtered_jobs = []
                    for idx in indices:
                        if 1 <= idx <= len(candidate_jobs):
                            job = candidate_jobs[idx - 1].copy()
                            job.pop('index', None)  # 移除內部索引
                            filtered_jobs.append(job)
                    
                    logger.info(f"✅ LLM 推薦職缺索引: {indices}")
                    return filtered_jobs
                    
                except ValueError:
                    logger.warning("❌ LLM 回應格式錯誤，返回原始搜尋結果")
                    
            # 如果 LLM 分析失敗，返回前 N 個最高相似度的職缺
            sorted_jobs = sorted(candidate_jobs, key=lambda x: x['similarity_score'], reverse=True)
            fallback_jobs = []
            for job in sorted_jobs[:target_count]:
                job_copy = job.copy()
                job_copy.pop('index', None)
                fallback_jobs.append(job_copy)
            
            logger.warning(f"⚠️ LLM 分析失敗，使用相似度排序返回前 {len(fallback_jobs)} 個職缺")
            return fallback_jobs
            
        except Exception as e:
            logger.error(f"❌ LLM 職缺篩選失敗: {e}")
            # 降級到基於相似度的簡單篩選
            sorted_jobs = sorted(candidate_jobs, key=lambda x: x['similarity_score'], reverse=True)
            fallback_jobs = []
            for job in sorted_jobs[:target_count]:
                job_copy = job.copy()
                job_copy.pop('index', None)
                fallback_jobs.append(job_copy)
            return fallback_jobs
    
    def search_jobs(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """搜尋職缺（包含 LLM 智能分析）"""
        try:
            collection = self.get_collection()
            if not collection:
                return []
            
            # 向量化查詢
            query_vector = self.embed_query(query)
            if not query_vector:
                return []
            
            # 搜尋更多候選結果供 LLM 分析（最多30個）
            search_limit = min(30, max(top_k * 3, 20))
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
            results = collection.search(
                data=[query_vector],
                anns_field="embedding",
                param=search_params,
                limit=search_limit,
                output_fields=["full_text", "title", "company", "url", "location"]
            )
            
            # 轉換候選結果
            candidate_jobs = []
            for i, hit in enumerate(results[0]):
                job_data = {
                    "index": i + 1,  # LLM 需要的索引
                    "job_title": hit.entity.get("title", ""),
                    "company_name": hit.entity.get("company", ""),
                    "location": hit.entity.get("location", ""),
                    "job_url": hit.entity.get("url", ""),
                    "description": hit.entity.get("full_text", ""),
                    "similarity_score": hit.score
                }
                candidate_jobs.append(job_data)
            
            # 使用 LLM 智能篩選最相關的職缺
            filtered_jobs = self._llm_filter_jobs(query, candidate_jobs, top_k)
            
            logger.info(f"✅ LLM 從 {len(candidate_jobs)} 個候選職缺中篩選出 {len(filtered_jobs)} 個最相關職缺")
            return filtered_jobs
            
        except Exception as e:
            logger.error(f"❌ 職缺搜尋失敗: {e}")
            return []
    
    def search_jobs_by_resume(self, resume_data: Dict[str, Any], query: str = "") -> List[Dict[str, Any]]:
        """根據履歷搜尋職缺"""
        try:
            # 從履歷提取關鍵資訊
            keywords = resume_data.get("keywords", "")
            desired_position = resume_data.get("desired_position", "")
            skills = resume_data.get("skillList", [])
            
            # 組合搜尋查詢
            if query:
                search_query = query
            else:
                search_query = f"{desired_position} {' '.join(skills)} {keywords}"
            
            return self.search_jobs(search_query)
            
        except Exception as e:
            logger.error(f"❌ 履歷職缺搜尋失敗: {e}")
            return []

# 全域實例
job_search_tool = JobSearchTool()

def search_jobs_tool(query: str, top_k: int = 10) -> Dict[str, Any]:
    """MCP 工具：搜尋職缺"""
    try:
        jobs = job_search_tool.search_jobs(query, top_k)
        return {
            "status": "success",
            "jobs": jobs,
            "count": len(jobs),
            "query": query
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def search_jobs_by_resume_tool(resume_data: Dict[str, Any], query: str = "") -> Dict[str, Any]:
    """MCP 工具：根據履歷搜尋職缺"""
    try:
        jobs = job_search_tool.search_jobs_by_resume(resume_data, query)
        return {
            "status": "success",
            "jobs": jobs,
            "count": len(jobs),
            "resume_based": True
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def recommend_jobs_tool(resume_id: str, top_k: int = 5) -> Dict[str, Any]:
    """MCP 工具：根據履歷 ID 推薦職缺"""
    try:
        # 從 MongoDB 獲取履歷資料
        from backend.tools.resume_manager import resume_manager
        resume_data = resume_manager.get_resume_by_user_id(resume_id)
        
        if not resume_data:
            return {
                "status": "not_found",
                "message": f"未找到履歷 ID: {resume_id}"
            }
        
        # 根據履歷推薦職缺
        jobs = job_search_tool.search_jobs_by_resume(resume_data)
        
        # 限制推薦數量
        recommended_jobs = jobs[:top_k]
        
        return {
            "status": "success",
            "resume_id": resume_id,
            "recommended_jobs": recommended_jobs,
            "count": len(recommended_jobs),
            "message": f"為履歷 {resume_id} 推薦了 {len(recommended_jobs)} 個職缺"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"職缺推薦失敗: {str(e)}"
        }


