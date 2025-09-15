#!/usr/bin/env python3
"""
多模態工具實作
提供語音轉文字和履歷佈局分析功能
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional
import tempfile
from pathlib import Path

# 設定日誌
logger = logging.getLogger(__name__)

class MultimodalTool:
    """多模態工具"""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.whisper_model = "whisper-1"
        
        # 檢查 OpenAI 是否可用
        try:
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            self.openai_available = True
            logger.info("✅ OpenAI 客戶端初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ OpenAI 客戶端初始化失敗: {e}")
            self.openai_client = None
            self.openai_available = False
    
    def transcribe_audio(self, file_path: str, language: str = "zh") -> Dict[str, Any]:
        """
        語音轉文字功能
        
        Args:
            file_path: 音訊檔案路徑
            language: 語言代碼
        
        Returns:
            轉錄結果
        """
        try:
            if not self.openai_available:
                return {
                    "status": "error",
                    "message": "OpenAI 服務不可用，無法進行語音轉文字"
                }
            
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return {
                    "status": "error",
                    "message": f"檔案不存在: {file_path}"
                }
            
            # 檢查檔案格式
            supported_formats = ['.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm']
            if file_path_obj.suffix.lower() not in supported_formats:
                return {
                    "status": "error",
                    "message": f"不支援的檔案格式: {file_path_obj.suffix}，支援的格式: {supported_formats}"
                }
            
            # 使用 OpenAI Whisper 進行語音轉文字
            with open(file_path_obj, 'rb') as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model=self.whisper_model,
                    file=audio_file,
                    language=language,
                    response_format="verbose_json"
                )
            
            return {
                "status": "success",
                "file_path": file_path,
                "language": language,
                "transcript": transcript.text,
                "duration": getattr(transcript, 'duration', None),
                "segments": getattr(transcript, 'segments', []),
                "message": "語音轉文字完成"
            }
            
        except Exception as e:
            logger.error(f"語音轉文字失敗: {e}")
            return {
                "status": "error",
                "message": f"語音轉文字失敗: {str(e)}",
                "file_path": file_path
            }
    
    def analyze_resume_layout(self, file_path: str) -> Dict[str, Any]:
        """
        分析履歷佈局和結構
        
        Args:
            file_path: 履歷檔案路徑
        
        Returns:
            佈局分析結果
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return {
                    "status": "error",
                    "message": f"檔案不存在: {file_path}"
                }
            
            # 檢查檔案格式
            supported_formats = ['.pdf', '.docx', '.doc', '.txt']
            if file_path_obj.suffix.lower() not in supported_formats:
                return {
                    "status": "error",
                    "message": f"不支援的檔案格式: {file_path_obj.suffix}，支援的格式: {supported_formats}"
                }
            
            # 讀取檔案內容
            if file_path_obj.suffix.lower() == '.pdf':
                # PDF 處理
                try:
                    import PyPDF2
                    with open(file_path_obj, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        text_content = ""
                        for page in pdf_reader.pages:
                            text_content += page.extract_text() + "\n"
                except ImportError:
                    return {
                        "status": "error",
                        "message": "需要安裝 PyPDF2 來處理 PDF 檔案"
                    }
            elif file_path_obj.suffix.lower() in ['.docx', '.doc']:
                # Word 處理
                try:
                    from docx import Document
                    doc = Document(file_path_obj)
                    text_content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                except ImportError:
                    return {
                        "status": "error",
                        "message": "需要安裝 python-docx 來處理 Word 檔案"
                    }
            else:
                # 純文字檔案
                with open(file_path_obj, 'r', encoding='utf-8') as file:
                    text_content = file.read()
            
            # 分析履歷結構
            layout_analysis = self._analyze_resume_structure(text_content)
            
            return {
                "status": "success",
                "file_path": file_path,
                "file_type": file_path_obj.suffix.lower(),
                "text_length": len(text_content),
                "layout_analysis": layout_analysis,
                "message": "履歷佈局分析完成"
            }
            
        except Exception as e:
            logger.error(f"履歷佈局分析失敗: {e}")
            return {
                "status": "error",
                "message": f"履歷佈局分析失敗: {str(e)}",
                "file_path": file_path
            }
    
    def _analyze_resume_structure(self, text_content: str) -> Dict[str, Any]:
        """
        分析履歷文字結構
        
        Args:
            text_content: 履歷文字內容
        
        Returns:
            結構分析結果
        """
        try:
            lines = text_content.split('\n')
            
            # 識別不同區塊
            sections = {
                "personal_info": [],
                "education": [],
                "experience": [],
                "skills": [],
                "projects": [],
                "achievements": [],
                "other": []
            }
            
            current_section = "other"
            
            # 關鍵字匹配
            section_keywords = {
                "personal_info": ["姓名", "電話", "信箱", "地址", "聯絡", "個人資料"],
                "education": ["學歷", "教育", "畢業", "大學", "研究所", "學位"],
                "experience": ["經歷", "工作", "職位", "公司", "任職"],
                "skills": ["技能", "專長", "技術", "能力", "程式語言"],
                "projects": ["專案", "作品", "實作", "開發"],
                "achievements": ["成就", "獲獎", "證照", "認證", "榮譽"]
            }
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 檢查是否為區塊標題
                for section, keywords in section_keywords.items():
                    if any(keyword in line for keyword in keywords):
                        current_section = section
                        break
                
                sections[current_section].append(line)
            
            # 計算統計資訊
            total_lines = len([line for line in lines if line.strip()])
            section_stats = {
                section: {
                    "line_count": len(content),
                    "content": content[:5] if content else []  # 只顯示前5行
                }
                for section, content in sections.items()
            }
            
            return {
                "total_lines": total_lines,
                "sections": section_stats,
                "structure_score": self._calculate_structure_score(sections),
                "recommendations": self._generate_recommendations(sections)
            }
            
        except Exception as e:
            logger.error(f"履歷結構分析失敗: {e}")
            return {
                "error": f"結構分析失敗: {str(e)}"
            }
    
    def _calculate_structure_score(self, sections: Dict[str, List[str]]) -> int:
        """計算履歷結構評分"""
        try:
            score = 0
            
            # 基本區塊存在性評分
            essential_sections = ["personal_info", "education", "experience", "skills"]
            for section in essential_sections:
                if sections[section]:
                    score += 20
            
            # 額外區塊加分
            bonus_sections = ["projects", "achievements"]
            for section in bonus_sections:
                if sections[section]:
                    score += 10
            
            return min(score, 100)
            
        except Exception:
            return 0
    
    def _generate_recommendations(self, sections: Dict[str, List[str]]) -> List[str]:
        """生成改進建議"""
        recommendations = []
        
        if not sections["personal_info"]:
            recommendations.append("建議添加個人聯絡資訊區塊")
        
        if not sections["education"]:
            recommendations.append("建議添加教育背景區塊")
        
        if not sections["experience"]:
            recommendations.append("建議添加工作經歷區塊")
        
        if not sections["skills"]:
            recommendations.append("建議添加技能專長區塊")
        
        if len(sections["experience"]) < 3:
            recommendations.append("建議增加更多工作經歷描述")
        
        if not recommendations:
            recommendations.append("履歷結構完整，建議保持現有格式")
        
        return recommendations

# 創建全域實例
multimodal_tool = MultimodalTool()

# MCP 工具函數
def transcribe_audio(file_path: str, language: str = "zh") -> Dict[str, Any]:
    """MCP 工具：語音轉文字"""
    return multimodal_tool.transcribe_audio(file_path, language)

def analyze_resume_layout(file_path: str) -> Dict[str, Any]:
    """MCP 工具：分析履歷佈局"""
    return multimodal_tool.analyze_resume_layout(file_path)
