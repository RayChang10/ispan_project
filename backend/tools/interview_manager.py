#!/usr/bin/env python3
"""
統一面試管理模組
整合 InteractiveInterview 和 InterviewSession 的功能
完全符合流程.txt 的要求
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .answer_analyzer import answer_analyzer
from .question_manager import question_manager

logger = logging.getLogger(__name__)


class InterviewManager:
    """統一的面試管理器 - 完全符合流程.txt 要求"""

    def __init__(self):
        # 會話狀態
        self.current_question = None
        self.current_standard_answer = None
        self.session_history = []
        self.session_started = False
        
        # 階段控制 - 符合流程.txt 要求
        self.current_stage = "waiting"  # waiting, intro, questioning, finished
        
        # 自我介紹相關 - 符合流程.txt 步驟 3-6
        self.intro_content = ""
        self.intro_analyzed = False
        self.intro_agent_active = False
        self.interview_agent_active = False
        
        # 統計數據
        self.total_questions = 0
        self.total_answers = 0
        self.scores = []

    def start_interview(self) -> Dict[str, Any]:
        """開始面試 - 符合流程.txt 步驟 2"""
        try:
            # 重置狀態
            self.session_history = []
            self.current_question = None
            self.current_standard_answer = None
            self.session_started = True
            self.total_questions = 0
            self.total_answers = 0
            self.scores = []
            
            # 進入自我介紹階段 - 符合流程.txt 步驟 2
            self.current_stage = "intro"
            self.intro_content = ""
            self.intro_analyzed = False
            
            # 啟動自我介紹 agent，其他 agent 不啟動 - 符合流程.txt 步驟 2
            self.intro_agent_active = True
            self.interview_agent_active = False
            
            logger.info("開始面試 - 進入自我介紹階段，啟動自我介紹 agent")
            
            return {
                "status": "intro_started",
                "stage": "intro",
                "intro_agent_active": True,
                "interview_agent_active": False,
                "message": "面試已開始！請先進行自我介紹。",
                "instruction": "請按照以下結構進行自我介紹：\n1. 開場簡介（身份與專業定位）\n2. 學經歷概述\n3. 核心技能與強項\n4. 代表成果\n5. 與職缺的連結\n6. 結語與期待"
            }
            
        except Exception as e:
            logger.error(f"開始面試失敗: {e}")
            return {"status": "error", "message": f"開始面試失敗: {str(e)}"}

    def collect_intro(self, user_message: str, user_id: str = "default_user") -> Dict[str, Any]:
        """收集自我介紹 - 符合流程.txt 步驟 3-4"""
        if self.current_stage != "intro":
            return {
                "status": "error",
                "message": "當前不是自我介紹階段"
            }
        
        try:
            # 不管使用者說什麼都認為他是在自我介紹 - 符合流程.txt 步驟 4
            self.intro_content += " " + user_message
            self.intro_content = self.intro_content.strip()
            
            # 記錄到會話歷史
            self.session_history.append({
                "type": "intro_collection",
                "user_message": user_message,
                "user_id": user_id,
                "timestamp": self._get_timestamp()
            })
            
            return {
                "status": "intro_collected",
                "stage": "intro",
                "intro_agent_active": True,
                "interview_agent_active": False,
                "message": "自我介紹內容已記錄",
                "collected_content": self.intro_content,
                "instruction": "完成自我介紹後，請輸入「完成自我介紹」或「自介完成」來進入下一階段"
            }
            
        except Exception as e:
            return {"success": False, "error": f"記錄自我介紹失敗: {str(e)}"}

    def get_collected_intro(self, user_id: str = "default_user") -> str:
        """獲取已收集的自我介紹內容 - 向後相容"""
        return self.intro_content

    def clear_collected_intro(self, user_id: str = "default_user") -> Dict[str, Any]:
        """清除已收集的自我介紹內容 - 向後相容"""
        if self.current_stage == "intro":
            self.intro_content = ""
            return {
                "success": True,
                "result": f"✅ 已清除用戶 {user_id} 的自我介紹內容",
            }
        return {"success": False, "error": "當前不是自我介紹階段"}

    def finish_intro_and_analyze(self) -> Dict[str, Any]:
        """完成自我介紹並分析 - 符合流程.txt 步驟 5-6"""
        if self.current_stage != "intro":
            return {
                "status": "error",
                "message": "當前不是自我介紹階段"
            }
        
        # 檢查自我介紹內容是否為空（移除字數限制）
        if not self.intro_content or len(self.intro_content.strip()) == 0:
            return {
                "status": "intro_incomplete",
                "stage": "intro",
                "intro_agent_active": True,
                "interview_agent_active": False,
                "message": "自我介紹內容為空，請先提供一些自我介紹內容，包含您的背景、技能、經驗等資訊。",
                "instruction": "請提供您的自我介紹內容，完成後再輸入「自介完成」。",
                "current_length": len(self.intro_content.strip()) if self.intro_content else 0,
                "required_length": 1  # 只需要至少1個字符
            }
        
        try:
            # 分析自我介紹 - 按照流程.txt 的 6 個標準
            analysis_result = self._analyze_intro_by_standards(self.intro_content)
            self.intro_analyzed = True
            
            # 記錄分析結果
            self.session_history.append({
                "type": "intro_analysis",
                "intro_content": self.intro_content,
                "analysis_result": analysis_result,
                "timestamp": self._get_timestamp()
            })
            
            # 進入面試模式階段 - 符合流程.txt 步驟 7
            self.current_stage = "questioning"
            
            # 關閉自我介紹 agent，啟動面試 agent - 符合流程.txt 步驟 8
            self.intro_agent_active = False
            self.interview_agent_active = True
            
            logger.info("自我介紹完成，進入面試模式階段，啟動面試 agent")
            
            return {
                "status": "intro_finished",
                "stage": "questioning",
                "intro_agent_active": False,
                "interview_agent_active": True,
                "intro_analysis": analysis_result,
                "intro_score_result": {
                    "score": analysis_result.get('overall_score', 0),
                    "grade": analysis_result.get('grade', 'N/A'),
                    "completion_rate": analysis_result.get('completion_rate', 'N/A'),
                    "analysis": analysis_result.get('analysis', []),
                    "suggestions": analysis_result.get('suggestions', [])
                },
                "message": f"🎉 **自我介紹分析完成！**\n\n📊 **評分結果：{analysis_result.get('overall_score', 0)}/100 ({analysis_result.get('grade', 'N/A')})**\n\n📋 **完成率：{analysis_result.get('completion_rate', 'N/A')}**\n\n💡 **分析摘要：**\n{chr(10).join(analysis_result.get('analysis', [])[:6])}\n\n🔍 **改進建議：**\n{chr(10).join(analysis_result.get('suggestions', [])[:5])}\n\n🎯 **現在進入面試模式！**",
                "next_action": "get_question"
            }
            
        except Exception as e:
            return {"success": False, "error": f"分析自我介紹失敗: {str(e)}"}

    def analyze_intro(self, user_message: str = "", user_id: str = "default_user") -> Dict[str, Any]:
        """分析用戶自我介紹 - 向後相容方法"""
        if self.current_stage == "intro":
            # 如果還在收集階段，先收集內容
            if user_message:
                self.collect_intro(user_message, user_id)
            
            # 然後分析
            return self.finish_intro_and_analyze()
        else:
            return {"success": False, "error": "當前不是自我介紹階段"}

    def get_next_question(self) -> Dict[str, Any]:
        """獲取下一個問題 - 符合流程.txt 步驟 8"""
        if self.current_stage != "questioning":
            return {
                "status": "error",
                "message": "當前不是面試模式階段"
            }
        
        try:
            question_data = question_manager.get_random_question()
            
            self.current_question = question_data["question"]
            self.current_standard_answer = question_data["standard_answer"]
            self.total_questions += 1
            
            # 記錄到會話歷史
            self.session_history.append({
                "type": "question",
                "data": question_data,
                "question_number": self.total_questions,
                "timestamp": self._get_timestamp()
            })
            
            return {
                "status": "question_ready",
                "stage": "questioning",
                "intro_agent_active": False,
                "interview_agent_active": True,
                "question": question_data["question"],
                "source": question_data["source"],
                "question_number": self.total_questions,
                "message": f"面試問題 {self.total_questions} 已準備好，請回答以下問題：",
                "instruction": "回答完成後，系統會自動分析並進入下一題。輸入「結束面試」可完成面試。"
            }
        except Exception as e:
            logger.error(f"獲取問題失敗: {e}")
            return {"status": "error", "message": f"獲取問題失敗: {str(e)}"}

    def submit_answer(self, user_answer: str) -> Dict[str, Any]:
        """提交用戶回答並進行分析 - 符合流程.txt 步驟 8"""
        if self.current_stage != "questioning":
            return {
                "status": "error",
                "message": "當前不是面試模式階段"
            }
        
        if not self.current_question:
            return {
                "status": "error",
                "message": "沒有當前問題，請先獲取問題"
            }
        
        try:
            # 分析回答
            analysis = answer_analyzer.analyze_answer(
                user_answer, 
                self.current_standard_answer,
                self.current_question
            )
            
            self.total_answers += 1
            score = analysis.get("score", 0)
            self.scores.append(score)
            
            # 記錄到會話歷史
            self.session_history.append({
                "type": "answer",
                "user_answer": user_answer,
                "analysis": analysis,
                "question": self.current_question,
                "timestamp": self._get_timestamp()
            })
            
            # 自動準備下一題 - 符合流程.txt 步驟 8 的持續提示
            next_question_ready = True  # 除非說退出不然會一直下一題
            
            return {
                "status": "answer_analyzed",
                "stage": "questioning",
                "intro_agent_active": False,
                "interview_agent_active": True,
                "analysis": analysis,
                "question": self.current_question,
                "user_answer": user_answer,
                "standard_answer": self.current_standard_answer,
                "message": f"回答已分析完成。評分：{score}/100",
                "next_question_ready": next_question_ready,
                "instruction": "系統會自動準備下一題，請繼續回答。輸入「結束面試」可完成面試。"
            }
            
        except Exception as e:
            logger.error(f"分析回答失敗: {e}")
            return {"status": "error", "message": f"分析回答失敗: {str(e)}"}

    def end_interview(self) -> Dict[str, Any]:
        """結束面試 - 符合流程.txt 步驟 9"""
        if self.current_stage not in ["questioning", "intro"]:
            return {"status": "error", "message": "面試尚未開始或已結束"}
        
        try:
            # 生成最終總結 - 統合前面所有面試過程給出建議
            final_summary = self._generate_final_summary()
            
            # 結束會話
            self.current_stage = "finished"
            self.session_started = False
            self.intro_agent_active = False
            self.interview_agent_active = False
            
            logger.info(f"面試結束，總共 {self.total_questions} 個問題")
            
            return {
                "status": "interview_ended",
                "stage": "finished",
                "intro_agent_active": False,
                "interview_agent_active": False,
                "final_summary": final_summary,
                "message": "面試已完成！以下是您的面試總結："
            }
            
        except Exception as e:
            return {"status": "error", "message": f"結束面試失敗: {str(e)}"}

    def get_session_summary(self) -> Dict[str, Any]:
        """獲取會話摘要"""
        if not self.session_started:
            return {"status": "error", "message": "會話尚未開始"}
        
        # 計算統計數據
        average_score = sum(self.scores) / len(self.scores) if self.scores else 0
        max_score = max(self.scores) if self.scores else 0
        min_score = min(self.scores) if self.scores else 0
        
        # 評估整體表現
        if average_score >= 80:
            performance = "優秀"
        elif average_score >= 60:
            performance = "良好"
        elif average_score >= 40:
            performance = "一般"
        else:
            performance = "需要改進"
        
        return {
            "status": "summary_ready",
            "current_stage": self.current_stage,
            "intro_agent_active": self.intro_agent_active,
            "interview_agent_active": self.interview_agent_active,
            "total_questions": self.total_questions,
            "total_answers": self.total_answers,
            "average_score": round(average_score, 1),
            "max_score": max_score,
            "min_score": min_score,
            "performance": performance,
            "scores": self.scores,
            "intro_analyzed": self.intro_analyzed,
            "session_history": self.session_history,
            "message": f"面試進行中！當前階段：{self.current_stage}，總共回答了 {self.total_answers} 個問題，平均分數：{average_score:.1f}"
        }

    def _analyze_intro_by_standards(self, intro_content: str) -> Dict[str, Any]:
        """按照流程.txt 的 6 個標準分析自我介紹"""
        # 完全按照流程.txt 的 6 個標準，使用更精確的關鍵詞檢測
        standards = {
            "1. 開場簡介": {
                "keywords": ["我是", "我叫", "專業", "經驗", "年數", "身份", "定位", "工程師", "開發者", "程式設計師", "資料科學", "系統架構", "資深", "主管"],
                "description": "快速建立初步印象，表明身份與專業定位",
                "example": "「您好，我是 Ray，一位有 10 年以上經驗的資料科學與系統架構師，擅長將數據分析與自動化工具應用於企業決策與產品開發中。」"
            },
            "2. 學經歷概述": {
                "keywords": ["畢業", "大學", "碩士", "博士", "工作", "任職", "擔任", "公司", "學歷", "背景", "交通大學", "資訊工程", "資深工程師", "部門主管"],
                "description": "建立專業可信度，聚焦與職缺相關經歷",
                "example": "「我畢業於交通大學資訊工程系，之後在 ABC 科技任職資深工程師，主導多項 AI 應用專案，近年則擔任部門主管，負責跨部門產品策略與技術選型。」"
            },
            "3. 核心技能與強項": {
                "keywords": ["技術", "技能", "擅長", "熟悉", "專長", "python", "java", "react", "vue", "angular", "node", "django", "flask", "linux", "docker", "資料處理", "分析流程"],
                "description": "說明你「能做什麼」和「比其他人強在哪裡」",
                "example": "「我熟悉 Python、Linux、Docker 等工具，擅長快速搭建資料處理與分析流程，並有豐富的跨部門溝通與團隊管理經驗。」"
            },
            "4. 代表成果": {
                "keywords": ["專案", "項目", "完成", "達成", "提升", "效率", "成果", "開發", "建立", "實作", "自動化", "系統", "60%", "招聘流程", "hr團隊"],
                "description": "具體展示「做過什麼事」以及「產出什麼價值」",
                "example": "「在過去一年，我帶領團隊完成自動化履歷分析系統，將分析效率提升 60%，並應用於企業內部招聘流程，協助 HR 團隊快速媒合人才。」"
            },
            "5. 與職缺的連結": {
                "keywords": ["職位", "公司", "匹配", "適合", "目標", "動機", "希望", "想要", "貢獻", "數據平台", "產品化", "技術文化", "架構升級", "效能優化"],
                "description": "讓面試官知道你是「為這個職位而來」，不是亂槍打鳥",
                "example": "「貴公司在數據平台產品化的發展方向與我過往經驗高度重疊，我特別欣賞你們開放的技術文化，也期待能透過我的背景，協助團隊進行架構升級與效能優化。」"
            },
            "6. 結語與期待": {
                "keywords": ["期待", "希望", "感謝", "合作", "學習", "成長", "請多指教", "謝謝", "加入", "團隊", "貢獻", "專長"],
                "description": "留下積極、合作的印象",
                "example": "「以上是我的簡單介紹，期待能加入貴團隊，為產品貢獻我的專長，也持續學習與成長。謝謝您的聆聽。」"
            }
        }
        
        analysis_result = []
        missing_parts = []
        suggestions = []
        lower_content = intro_content.lower()
        
        # 計算每個標準的完成度
        total_score = 0
        max_score_per_standard = 16.67  # 100/6
        
        for standard_name, standard_info in standards.items():
            found_keywords = []
            for keyword in standard_info["keywords"]:
                if keyword.lower() in lower_content:
                    found_keywords.append(keyword)
            
            # 計算該標準的得分
            if found_keywords:
                # 根據找到的關鍵詞數量給分
                keyword_score = min(len(found_keywords) * 2, max_score_per_standard)
                total_score += keyword_score
                
                analysis_result.append(f"✅ **{standard_name}**: 已提及 - {', '.join(found_keywords[:3])}")
                analysis_result.append(f"   📝 {standard_info['description']}")
                analysis_result.append(f"   💡 範例：{standard_info['example']}")
            else:
                missing_parts.append(f"❌ **{standard_name}**: 缺少相關內容")
                analysis_result.append(f"❌ **{standard_name}**: 缺少相關內容")
                analysis_result.append(f"   📝 {standard_info['description']}")
                analysis_result.append(f"   💡 範例：{standard_info['example']}")
        
        # 生成具體建議
        if len(missing_parts) > 0:
            suggestions.append("🔍 **建議補充以下內容：**")
            for missing in missing_parts:
                suggestions.append(f"  {missing}")
            suggestions.append("")
            suggestions.append("💡 **改進建議：**")
            suggestions.append("1. 在回答時更具體化，提供具體的數據和例子")
            suggestions.append("2. 使用 STAR 方法描述經驗：情境(Situation)、任務(Task)、行動(Action)、結果(Result)")
            suggestions.append("3. 強調與應徵職位的相關性和匹配度")
        else:
            suggestions.append("🎉 **您的自我介紹結構完整！**")
            suggestions.append("")
            suggestions.append("💡 **進一步優化建議：**")
            suggestions.append("1. 可以更具體化數字和成果")
            suggestions.append("2. 加強與職位的連結性描述")
            suggestions.append("3. 練習在 1-2 分鐘內完成自我介紹")
        
        # 計算整體評分
        overall_score = min(100, max(0, round(total_score)))
        
        # 評級
        if overall_score >= 90:
            grade = "優秀"
        elif overall_score >= 80:
            grade = "良好"
        elif overall_score >= 60:
            grade = "一般"
        elif overall_score >= 40:
            grade = "需要改進"
        else:
            grade = "不足"
        
        return {
            "analysis": analysis_result,
            "missing_parts": missing_parts,
            "suggestions": suggestions,
            "overall_score": overall_score,
            "grade": grade,
            "message": f"自我介紹分析完成！評分：{overall_score}/100 ({grade})",
            "completion_rate": f"{len([s for s in standards.keys() if any(k.lower() in lower_content for k in standards[s]['keywords'])])}/{len(standards)} 個標準已完成"
        }

    def _generate_final_summary(self) -> Dict[str, Any]:
        """生成最終面試總結 - 統合前面所有面試過程給出建議"""
        try:
            # 基於實際數據生成總結
            if self.scores:
                average_score = sum(self.scores) / len(self.scores)
                if average_score >= 80:
                    performance = "優秀"
                    feedback = "您的表現非常出色，展現了扎實的專業能力"
                elif average_score >= 60:
                    performance = "良好"
                    feedback = "您的表現良好，有改進空間"
                else:
                    performance = "需要改進"
                    feedback = "建議加強相關知識的學習和練習"
            else:
                performance = "無法評估"
                feedback = "沒有足夠的評分數據"
            
            summary = f"""
🎯 **面試總結報告**

**自我介紹階段**：
✅ 已完成自我介紹和分析

**面試問答階段**：
📝 總共回答了 {self.total_answers} 個問題
📈 平均評分：{sum(self.scores) / len(self.scores) if self.scores else 0:.1f}/100
🎯 整體表現：{performance}

**具體建議**：
{feedback}

**下次面試準備重點**：
1. 🎯 加強技術問題的準備和練習
2. 📝 提高回答的準確性和完整性
3. 🧠 多進行模擬面試練習
4. 📚 學習標準答案的結構和要點

**總評**: 您在本次模擬面試中的表現為 {performance}，建議根據上述建議進行改進。
            """
            
            return {
                "summary": summary,
                "performance": performance,
                "feedback": feedback
            }
            
        except Exception as e:
            return {
                "summary": "面試總結生成失敗",
                "error": str(e)
            }

    # 向後相容的方法
    def start_session(self) -> Dict[str, Any]:
        """開始會話（向後相容）"""
        return self.start_interview()

    def get_random_question(self) -> Dict[str, Any]:
        """獲取隨機問題（向後相容方法）"""
        return question_manager.get_random_question()

    def analyze_answer(self, user_answer: str, standard_answer: str, question: str = "") -> Dict[str, Any]:
        """分析答案（向後相容方法）"""
        return answer_analyzer.analyze_answer(user_answer, standard_answer, question)

    def _get_timestamp(self) -> str:
        """獲取當前時間戳"""
        from datetime import datetime
        return datetime.now().isoformat()


# 全域面試管理器實例
interview_manager = InterviewManager()

# 為了向後相容，保留舊的引用
interview_session = interview_manager
interactive_interview = interview_manager


# 主函數
async def main():
    """主函數 - 運行互動式面試"""
    await interview_manager.run_interactive_session()


if __name__ == "__main__":
    asyncio.run(main())
