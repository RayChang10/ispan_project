#!/usr/bin/env python3
"""
技能匹配模組
負責比較履歷技能與職缺需求，提供智能出題建議
"""

import logging
import re
from typing import Dict, List, Set, Tuple, Any
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class SkillMatcher:
    """技能匹配器"""
    
    def __init__(self):
        # 技能同義詞映射，用於模糊匹配
        self.skill_synonyms = {
            'python': ['python', 'py', 'python3'],
            'javascript': ['javascript', 'js', 'node.js', 'nodejs', 'ecmascript'],
            'java': ['java', 'jvm'],
            'react': ['react', 'reactjs', 'react.js'],
            'vue': ['vue', 'vuejs', 'vue.js'],
            'angular': ['angular', 'angularjs'],
            'sql': ['sql', 'mysql', 'postgresql', 'sqlite', 'mssql'],
            'docker': ['docker', 'containerization', '容器化'],
            'kubernetes': ['kubernetes', 'k8s'],
            'aws': ['aws', 'amazon web services'],
            'git': ['git', 'github', 'gitlab', 'version control'],
            'linux': ['linux', 'unix', 'ubuntu', 'centos'],
            'mongodb': ['mongodb', 'mongo'],
            'redis': ['redis', 'cache'],
            'machine learning': ['machine learning', 'ml', '機器學習', 'ai', 'artificial intelligence'],
            'data analysis': ['data analysis', '資料分析', 'data science', 'analytics'],
            'web development': ['web development', 'web dev', '網頁開發', 'frontend', 'backend'],
            'mobile development': ['mobile development', 'mobile dev', 'app development', 'ios', 'android'],
        }
        
        # 技能重要性權重
        self.skill_weights = {
            'core': 1.0,        # 核心技能
            'important': 0.8,   # 重要技能  
            'nice_to_have': 0.5 # 加分技能
        }
    
    def extract_skills_from_text(self, text: str) -> Set[str]:
        """從文字中提取技能關鍵字"""
        if not text:
            return set()
            
        # 轉為小寫並分割
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        skills = set()
        
        # 檢查每個同義詞群組
        for main_skill, synonyms in self.skill_synonyms.items():
            for synonym in synonyms:
                if synonym in text_lower:
                    skills.add(main_skill)
                    break
        
        # 直接添加常見技能詞彙
        common_skills = [
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
            'react', 'vue', 'angular', 'django', 'flask', 'spring', 'express',
            'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'linux', 'git',
            'html', 'css', 'bootstrap', 'tailwind',
            'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy'
        ]
        
        for skill in common_skills:
            if skill in text_lower:
                skills.add(skill)
        
        return skills
    
    def get_user_skills(self, user_id: str) -> Dict[str, Any]:
        """從資料庫獲取使用者履歷技能"""
        try:
            from .resume_manager import resume_manager
            
            # 獲取履歷資料
            resume = resume_manager.get_resume(user_id)
            if not resume:
                logger.warning(f"未找到用戶 {user_id} 的履歷")
                return {'skills': set(), 'raw_data': {}}
            
            resume_data = resume.get('resume_data', {})
            
            # 從多個欄位提取技能
            all_skills = set()
            
            # 1. 直接技能列表
            skills_list = resume_data.get('skills', [])
            if isinstance(skills_list, list):
                for skill_item in skills_list:
                    if isinstance(skill_item, dict):
                        skill_name = skill_item.get('skillName', '')
                        if skill_name:
                            all_skills.update(self.extract_skills_from_text(skill_name))
                    elif isinstance(skill_item, str):
                        all_skills.update(self.extract_skills_from_text(skill_item))
            
            # 2. 工作經驗中的技能
            work_experiences = resume_data.get('workExperiences', [])
            if isinstance(work_experiences, list):
                for exp in work_experiences:
                    if isinstance(exp, dict):
                        # 工作描述
                        job_desc = exp.get('jobDescription', '')
                        if job_desc:
                            all_skills.update(self.extract_skills_from_text(job_desc))
                        
                        # 工作技能
                        job_skills = exp.get('jobSkills', '')
                        if job_skills:
                            all_skills.update(self.extract_skills_from_text(job_skills))
            
            # 3. 自我介紹
            introduction = resume_data.get('introduction', '')
            if introduction:
                all_skills.update(self.extract_skills_from_text(introduction))
            
            # 4. 關鍵字
            keywords = resume_data.get('keywords', [])
            if isinstance(keywords, list):
                for keyword in keywords:
                    if isinstance(keyword, str):
                        all_skills.update(self.extract_skills_from_text(keyword))
            
            logger.info(f"用戶 {user_id} 的技能: {all_skills}")
            
            return {
                'skills': all_skills,
                'raw_data': resume_data
            }
            
        except Exception as e:
            logger.error(f"獲取用戶技能失敗: {e}")
            return {'skills': set(), 'raw_data': {}}
    
    def get_job_requirements(self, user_id: str) -> Dict[str, Any]:
        """獲取職缺需求（這裡需要根據實際的職缺資料結構調整）"""
        try:
            # TODO: 實現從資料庫獲取用戶選擇的職缺需求
            # 目前返回示例資料
            
            # 這裡應該從用戶選擇的職缺中獲取技能需求
            # 暫時使用通用的技能需求作為示例
            default_requirements = {
                'core_skills': {'python', 'javascript', 'sql'},
                'important_skills': {'react', 'docker', 'git'},
                'nice_to_have': {'aws', 'mongodb', 'linux'},
                'all_skills': {'python', 'javascript', 'sql', 'react', 'docker', 'git', 'aws', 'mongodb', 'linux'}
            }
            
            logger.info(f"職缺技能需求: {default_requirements['all_skills']}")
            
            return default_requirements
            
        except Exception as e:
            logger.error(f"獲取職缺需求失敗: {e}")
            return {
                'core_skills': set(),
                'important_skills': set(), 
                'nice_to_have': set(),
                'all_skills': set()
            }
    
    def match_skills(self, user_id: str) -> Dict[str, Any]:
        """執行技能匹配分析"""
        try:
            # 獲取用戶技能和職缺需求
            user_data = self.get_user_skills(user_id)
            job_requirements = self.get_job_requirements(user_id)
            
            user_skills = user_data['skills']
            job_skills = job_requirements['all_skills']
            
            # 計算匹配度
            matched_skills = user_skills.intersection(job_skills)
            missing_skills = job_skills - user_skills
            extra_skills = user_skills - job_skills
            
            # 計算匹配分數
            if len(job_skills) > 0:
                match_score = len(matched_skills) / len(job_skills)
            else:
                match_score = 0.0
            
            # 按優先級分類匹配的技能
            core_matched = matched_skills.intersection(job_requirements.get('core_skills', set()))
            important_matched = matched_skills.intersection(job_requirements.get('important_skills', set()))
            nice_matched = matched_skills.intersection(job_requirements.get('nice_to_have', set()))
            
            result = {
                'user_skills': user_skills,
                'job_skills': job_skills,
                'matched_skills': matched_skills,
                'missing_skills': missing_skills,
                'extra_skills': extra_skills,
                'match_score': match_score,
                'core_matched': core_matched,
                'important_matched': important_matched,
                'nice_matched': nice_matched,
                'priority_skills': self._get_priority_skills(matched_skills, missing_skills, job_requirements)
            }
            
            logger.info(f"技能匹配結果: 匹配度 {match_score:.2%}, 匹配技能 {len(matched_skills)}/{len(job_skills)}")
            
            return result
            
        except Exception as e:
            logger.error(f"技能匹配失敗: {e}")
            return {
                'user_skills': set(),
                'job_skills': set(),
                'matched_skills': set(),
                'missing_skills': set(),
                'extra_skills': set(),
                'match_score': 0.0,
                'priority_skills': []
            }
    
    def _get_priority_skills(self, matched_skills: Set[str], missing_skills: Set[str], job_requirements: Dict[str, Any]) -> List[Tuple[str, float]]:
        """獲取優先技能列表（用於出題優先級）"""
        priority_skills = []
        
        # 1. 匹配的核心技能（最高優先級）
        core_matched = matched_skills.intersection(job_requirements.get('core_skills', set()))
        for skill in core_matched:
            priority_skills.append((skill, 1.0))
        
        # 2. 匹配的重要技能
        important_matched = matched_skills.intersection(job_requirements.get('important_skills', set()))
        for skill in important_matched:
            priority_skills.append((skill, 0.8))
        
        # 3. 匹配的加分技能
        nice_matched = matched_skills.intersection(job_requirements.get('nice_to_have', set()))
        for skill in nice_matched:
            priority_skills.append((skill, 0.6))
        
        # 4. 如果沒有匹配的技能，使用用戶擁有的技能
        if not priority_skills:
            for skill in matched_skills:
                priority_skills.append((skill, 0.4))
        
        # 按優先級排序
        priority_skills.sort(key=lambda x: x[1], reverse=True)
        
        return priority_skills
    
    def get_question_skills_for_user(self, user_id: str) -> List[str]:
        """獲取用於出題的技能列表（按優先級排序）"""
        try:
            match_result = self.match_skills(user_id)
            priority_skills = match_result['priority_skills']
            
            # 提取技能名稱
            skills = [skill for skill, priority in priority_skills]
            
            # 如果沒有匹配的技能，使用用戶所有技能
            if not skills:
                skills = list(match_result['user_skills'])
            
            logger.info(f"用戶 {user_id} 出題技能優先級: {skills}")
            
            return skills
            
        except Exception as e:
            logger.error(f"獲取出題技能失敗: {e}")
            return []


# 創建全局實例
skill_matcher = SkillMatcher()
