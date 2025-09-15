#!/usr/bin/env python3
"""
履歷分析 MCP 工具
提供履歷健檢和職缺契合度分析功能
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

# 詳細履歷評分框架
SCORING_RUBRIC = """
第一部分：基礎評估：結構、清晰度與專業性 (總分：20分)
1.1 版面、可讀性與簡潔度 (8分)
評分標準：+8分： 完美的單頁、單欄式佈局，區塊分明，留白均衡，設計專業，能同時滿足ATS解析與快速人工掃描的需求。+4分： 篇幅為兩頁但有充分的資深經歷支撐；或版面略顯擁擠但整體仍可導航。0分： 超過兩頁，使用多欄式或表格格式，或視覺上過於密集，嚴重影響ATS解析與人工閱讀效率。
1.2 格式與技術合規性 (6分)
評分標準：+6分： 全面符合技術規範：使用標準字體與大小，採用傳統區塊標題，無任何複雜圖形或表格，並以兼容性高的格式提交。+2分： 使用略微非傳統的字體或標題，但整體結構簡單，仍有較高機率被成功解析。0分： 包含表格、圖形、非標準字體，或以圖像檔案格式提交，導致ATS無法解析。
1.3 專業性與準確性 (基礎6分，採扣分制)
基礎分數： 6分。扣分項目：每出現一處拼字或重大語法錯誤，扣3分 (最多扣至0分)。使用不專業的電子郵件地址，扣4分。聯絡資訊不完整，扣2分。使用不專業或低畫質的照片，扣2分。

第二部分：核心內容分析：影響力、成就與敘事 (總分：40分)
2.1 成就量化 (15分)
評分標準：13-15分 (卓越)： 工作經歷中的幾乎每一個要點都使用具體、相關的指標進行了量化。8-12分 (良好)： 在量化成就與描述性職責之間取得了良好平衡。3-7分 (尚可)： 量化描述較少。0-2分 (不良)： 履歷完全是一份工作職責清單。
2.2 敘事結構與行動導向語言 (15分)
評分標準：13-15分 (卓越)： 經歷要點始終遵循清晰的因果結構（如STAR原則），以強力的行動動詞開頭。8-12分 (良好)： 大多數要點使用行動動詞。3-7分 (尚可)： 主要使用被動語句。0-2分 (不良)： 僅為一份職責清單。
2.3 技能與摘要區塊 (10分)
評分標準：9-10分 (卓越)： 擁有一段高度客製化的摘要。技能區塊組織良好。6-8分 (良好)： 摘要內容通用但專業。3-5分 (尚可)： 摘要薄弱或缺失。0-2分 (不良)： 沒有摘要，且技能區塊缺失。

第三部分：策略性對齊：職缺適配度分數 (總分：40分)
3.1 關鍵字與技能匹配 (20分)
評分標準：18-20分： 關鍵字匹配度超過80%。12-17分： 關鍵字匹配度介於50-80%。6-11分： 關鍵字匹配度介於20-50%。0-5分： 關鍵字匹配度低於20%。
3.2 經歷與資格相關性 (15分)
評分標準：13-15分 (卓越)： 在所有必要資格（職稱相似度、工作年資、學位、證照）上達到完美或近乎完美的匹配。8-12分 (良好)： 符合大部分但非全部的核心要求。3-7分 (尚可)： 僅滿足少數基本要求。0-2分 (不良)： 缺乏該職位不可或缺的基礎資格。
3.3 客製化與動機 (5分)
評分標準：+5分： 履歷摘要和/或求職信明顯為該職位和公司量身打造。+2分： 有輕微的客製化跡象。0分： 履歷完全通用。

第四部分：分數評級轉換矩陣
95-100: 卓越 (Exceptional) | 85-94: 穩健 (Competent) | 70-84: 普通 (Satisfactory) | 55-69: 尚可 (Fair) | 40-54: 不良 (Poor) | 40分以下: 極需改善 (Extremely Poor)
"""

class ResumeAnalysisTool:
    """履歷分析工具"""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def analyze_resume_for_job(self, resume_data: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析履歷與職缺的契合度"""
        try:
            # 構建分析提示詞
            prompt = self._build_fit_analysis_prompt(resume_data, job_data)
            
            # 調用 OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "你是一位專業的職涯顧問，擅長分析履歷與職缺的契合度。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            analysis = response.choices[0].message.content
            
            return {
                "status": "success",
                "analysis": analysis,
                "resume_data": resume_data,
                "job_data": job_data
            }
            
        except Exception as e:
            logger.error(f"❌ 履歷分析失敗: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def resume_health_check(self, resume_data: Dict[str, Any], target_job: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """履歷健檢 - 使用詳細評分框架"""
        try:
            # 構建健檢提示詞
            prompt = self._build_detailed_health_check_prompt(resume_data, target_job)
            
            # 調用 OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "你是一位頂尖企業的招聘經理與專業職涯教練，請根據提供的評分框架進行嚴謹的履歷評估。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            health_check = response.choices[0].message.content
            
            return {
                "status": "success",
                "health_check": health_check,
                "resume_data": resume_data,
                "target_job": target_job
            }
            
        except Exception as e:
            logger.error(f"❌ 履歷健檢失敗: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _build_fit_analysis_prompt(self, resume_data: Dict[str, Any], job_data: Dict[str, Any]) -> str:
        """構建契合度分析提示詞"""
        return f"""
請分析以下履歷與職缺的契合度：

**履歷資訊**：
{json.dumps(resume_data, ensure_ascii=False, indent=2)}

**職缺資訊**：
{json.dumps(job_data, ensure_ascii=False, indent=2)}

請從以下維度進行分析：
1. 技能匹配度 (0-100%)
2. 經驗相關性 (0-100%)
3. 學歷要求符合度 (0-100%)
4. 整體契合度 (0-100%)

並提供：
- 優勢分析
- 潛在差距
- 改進建議
- 面試準備重點

請以結構化的方式回答。
"""
    
    def _build_detailed_health_check_prompt(self, resume_data: Dict[str, Any], target_job: Optional[Dict[str, Any]] = None) -> str:
        """構建詳細履歷健檢提示詞 - 使用完整評分框架"""
        job_context = ""
        if target_job:
            job_context = f"""
**目標職缺資訊**：
{json.dumps(target_job, ensure_ascii=False, indent=2)}
"""
        
        return f"""
# [專家角色]: 頂尖企業的招聘經理與專業職涯教練
# [最高優先級規則]: 你的所有輸出都必須是「繁體中文」。

# [任務]: 你將對一份履歷進行評估與優化。

### --- 第一階段：招聘經理（評分） ---
作為一名眼光毒辣的招聘經理，你的任務是根據提供的「全方位履歷評鑑框架」，對「應徵者履歷」進行嚴謹的評分與分析。

# [評分依據]
{SCORING_RUBRIC}

# [核心指令]:
1.  **內心評分**: 在心中對每一個細項（1.1 至 3.3）進行評分。
2.  **撰寫報告**: 將你的洞察匯總成一份專業的「**履歷評估報告**」，報告**必須**包含以下四個部分：
    1.  **總體評價與分數:** 直接給出總分（滿分 100），附上對應的評級，並用一兩句話總結。
    2.  **核心優勢:** 列點說明 2-3 項最突出的優勢。
    3.  **潛在疑慮與待改進處:** 列點提出 1-2 項潛在疑慮或待改進處。
    4.  **評分維度解析:** 簡要說明三大評分維度（基礎評估、核心內容、策略性對齊）的得分概況與關鍵原因。

### --- 第二階段：職涯教練（優化） ---
在完成評分後，你將無縫切換為「專業職涯教練」的角色，針對評分中發現的弱點，主動為使用者提供具體的優化方案。

# [核心指令]:
1.  **識別與優化**: 從履歷中挑選 1 到 2 個最關鍵的**敘述性欄位**進行優化 (例如 `intro`, `autobiography`, 或 `project` 中的 `project_description`)。
2.  **呈現方式**: 在提出優化建議時，**必須**使用中文欄位名稱（例如：『自我介紹』、『專案描述』），**絕對禁止**在給使用者的回覆中，出現 `intro` 或 `project_description` 等程式碼中的欄位關鍵字。
3.  **提供雙版本範例**: 對於每一個被挑選的欄位，你**必須**提供以下兩種範例：
    * **真實經歷優化範例**: 在**不偏離使用者原始經歷事實**的基礎上，潤飾文字，轉換角度，使其更貼近目標職缺的要求，凸顯可轉移的技能與成就。
    * **理想目標參考範例**: 提供一個為該職位量身打造的、完美的「虛擬」參考範例。這個範例可以更大膽，旨在啟發使用者，讓他知道理想的候選人會如何呈現自己。
4.  **銜接對話**: 在提供完所有範例後，詢問使用者下一步的打算，引導對話繼續。例如：「以上是我為您準備的初步建議。請問您對哪個範例比較有感覺，或者希望我們一起討論履歷的其他部分嗎？如果覺得沒問題，請告訴我『完成』。」

# --- 輸入資料 ---
## 目標職缺描述:
{target_job if target_job else "通用履歷評估（無特定職缺目標）"}

## 應徵者履歷:
{json.dumps(resume_data, ensure_ascii=False, indent=2)}
"""

    def _build_health_check_prompt(self, resume_data: Dict[str, Any], target_job: Optional[Dict[str, Any]] = None) -> str:
        """構建履歷健檢提示詞 - 保留原有簡化版本作為備用"""
        job_context = ""
        if target_job:
            job_context = f"\n**目標職缺**：{json.dumps(target_job, ensure_ascii=False, indent=2)}"
        
        return f"""
請對以下履歷進行健檢：

**履歷內容**：
{json.dumps(resume_data, ensure_ascii=False, indent=2)}{job_context}

請從以下方面進行評估：
1. 結構完整性
2. 內容清晰度
3. 技能展示
4. 成就量化
5. 與目標職缺的相關性（如有）

並提供：
- 優點分析
- 改進建議
- 具體優化方案
- 評分 (0-100)

請以專業的角度提供建議。
"""

# 全域實例
resume_analysis_tool = ResumeAnalysisTool()

def analyze_resume_job_fit_tool(resume_data: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, Any]:
    """MCP 工具：分析履歷與職缺契合度"""
    return resume_analysis_tool.analyze_resume_for_job(resume_data, job_data)

def resume_health_check_tool(resume_data: Dict[str, Any], target_job: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """MCP 工具：履歷健檢 - 使用詳細評分框架"""
    return resume_analysis_tool.resume_health_check(resume_data, target_job)


