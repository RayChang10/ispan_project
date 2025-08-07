import os
from datetime import datetime
from enum import Enum

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy


# 面試狀態枚舉
class InterviewState(Enum):
    WAITING = "waiting"  # 等待開始面試
    INTRO = "intro"  # 自我介紹階段
    INTRO_ANALYSIS = "intro_analysis"  # 自我介紹分析階段
    QUESTIONING = "questioning"  # 面試提問階段
    COMPLETED = "completed"  # 面試完成階段


# 狀態管理函數
def get_system_prompt(state: InterviewState) -> str:
    """根據當前狀態獲取系統提示詞"""
    if state == InterviewState.WAITING:
        return """
你現在是一個智能面試官助手，目前處於「等待開始」階段。

- 歡迎用戶，說明面試流程
- 等待用戶按下「開始面試」按鈕
- 在未開始面試前，可以進行一般對話和系統介紹
- 不要主動開始面試流程
"""
    elif state == InterviewState.INTRO:
        return """
你現在是一個面試官助手，目前進行到「自我介紹階段」。

- 請明確要求用戶進行完整的自我介紹
- 不論用戶說什麼，都當成是自我介紹內容
- 收集用戶的自我介紹內容，但不要分析或評論
- 使用 `intro_collector` 工具將內容儲存
- 引導用戶說出完整的自我介紹（開場、學經歷、技能、成果、職缺連結、結語）
- 當用戶說「介紹完了」或類似話語時，進入分析階段
"""
    elif state == InterviewState.INTRO_ANALYSIS:
        return """
你現在是一個面試官助手，目前進行到「自我介紹分析階段」。

- 使用 `analyze_intro` 工具分析用戶的自我介紹
- 依據6個標準進行分析：開場簡介、學經歷概述、核心技能與強項、代表成果、與職缺的連結、結語與期待
- 指出缺失的部分並給出具體建議
- 分析完成後自動進入面試提問階段
"""
    elif state == InterviewState.QUESTIONING:
        return """
你現在是一個面試官助手，目前進行到「面試提問與回答階段」。

- 使用 `get_question` 工具獲取面試題目並給出
- 用戶的回答使用 `analyze_answer` 工具分析並評分
- 顯示標準答案和評分結果
- 自動進入下一題，除非用戶說「退出」或「結束」
- 每次回答後都要提醒：「除非說退出，否則會繼續下一題」
- 完成多個題目後可進入完成階段
"""
    elif state == InterviewState.COMPLETED:
        return """
你現在是一個面試官助手，目前進行到「面試完成階段」。

- 使用 `generate_final_summary` 工具統合整個面試過程
- 包含自我介紹分析、面試表現、整體建議
- 給出專業的面試總結和改進建議
- 感謝用戶參與面試
"""
    else:
        return "你是一個面試官助手。"


def get_available_tools(state: InterviewState):
    """根據當前狀態獲取可用工具"""
    if state == InterviewState.WAITING:
        return ["general_chat"]
    elif state == InterviewState.INTRO:
        return ["intro_collector"]
    elif state == InterviewState.INTRO_ANALYSIS:
        return ["analyze_intro"]
    elif state == InterviewState.QUESTIONING:
        return ["get_question", "analyze_answer"]
    elif state == InterviewState.COMPLETED:
        return ["generate_final_summary"]
    else:
        return []


# 設定 MCP 和 SmartAgent 為不可用
MCP_AVAILABLE = False
SMART_AGENT_AVAILABLE = False

# 嘗試導入 Fast Agent
FAST_AGENT_AVAILABLE = False
try:
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

    # 嘗試導入橋接模組
    from fast_agent_bridge import call_fast_agent_function

    FAST_AGENT_AVAILABLE = True
    print("✅ Fast Agent 橋接模組已成功導入")
except Exception as e:
    print(f"⚠️ Fast Agent 橋接模組導入失敗: {e}")
    FAST_AGENT_AVAILABLE = False

# 載入環境變數
load_dotenv()

# 初始化Flask應用
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "virtual_interview_consultant_2024"
)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///virtual_interview.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# 初始化擴展
db = SQLAlchemy(app)
CORS(app)
api = Api(app)


# 資料庫模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    desired_position = db.Column(db.String(200))
    desired_field = db.Column(db.String(100))
    desired_location = db.Column(db.String(100))
    introduction = db.Column(db.Text)
    keywords = db.Column(db.Text)  # JSON格式儲存
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 關聯
    work_experiences = db.relationship(
        "WorkExperience", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    skills = db.relationship(
        "Skill", backref="user", lazy=True, cascade="all, delete-orphan"
    )


class WorkExperience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    industry_type = db.Column(db.String(100))
    work_location = db.Column(db.String(100))
    position_title = db.Column(db.String(200))
    position_category_1 = db.Column(db.String(100))
    position_category_2 = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    job_description = db.Column(db.Text)
    job_skills = db.Column(db.Text)
    salary = db.Column(db.String(100))
    salary_type = db.Column(db.String(50))
    management_responsibility = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    skill_name = db.Column(db.String(100), nullable=False)
    skill_description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class InterviewSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    session_data = db.Column(db.Text)  # JSON格式儲存對話內容
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# Fast Agent 橋接函數已移至 fast_agent_bridge.py


# API資源類別
class UserAPI(Resource):
    def post(self):
        """創建新用戶履歷"""
        try:
            data = request.get_json()

            # 創建用戶
            user = User(
                name=data.get("name"),
                desired_position=data.get("desired_position"),
                desired_field=data.get("desired_field"),
                desired_location=data.get("desired_location"),
                introduction=data.get("introduction"),
                keywords=data.get("keywords"),
            )

            db.session.add(user)
            db.session.flush()  # 取得user.id

            # 創建工作經驗
            work_experiences = data.get("work_experiences", [])
            for exp_data in work_experiences:
                experience = WorkExperience(
                    user_id=user.id,
                    company_name=exp_data.get("company_name"),
                    industry_type=exp_data.get("industry_type"),
                    work_location=exp_data.get("work_location"),
                    position_title=exp_data.get("position_title"),
                    position_category_1=exp_data.get("position_category_1"),
                    position_category_2=exp_data.get("position_category_2"),
                    start_date=(
                        datetime.strptime(exp_data.get("start_date"), "%Y-%m-%d").date()
                        if exp_data.get("start_date")
                        else None
                    ),
                    end_date=(
                        datetime.strptime(exp_data.get("end_date"), "%Y-%m-%d").date()
                        if exp_data.get("end_date")
                        else None
                    ),
                    job_description=exp_data.get("job_description"),
                    job_skills=exp_data.get("job_skills"),
                    salary=exp_data.get("salary"),
                    salary_type=exp_data.get("salary_type"),
                    management_responsibility=exp_data.get("management_responsibility"),
                )
                db.session.add(experience)

            # 創建技能
            skills = data.get("skills", [])
            for skill_data in skills:
                skill = Skill(
                    user_id=user.id,
                    skill_name=skill_data.get("skill_name"),
                    skill_description=skill_data.get("skill_description"),
                )
                db.session.add(skill)

            db.session.commit()

            return {"success": True, "message": "履歷建立成功", "user_id": user.id}, 201

        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": f"建立履歷失敗: {str(e)}"}, 400

    def get(self, user_id=None):
        """取得用戶履歷資料"""
        try:
            if user_id:
                user = User.query.get_or_404(user_id)
                work_experiences = [
                    {
                        "id": exp.id,
                        "company_name": exp.company_name,
                        "industry_type": exp.industry_type,
                        "work_location": exp.work_location,
                        "position_title": exp.position_title,
                        "position_category_1": exp.position_category_1,
                        "position_category_2": exp.position_category_2,
                        "start_date": (
                            exp.start_date.strftime("%Y-%m-%d")
                            if exp.start_date
                            else None
                        ),
                        "end_date": (
                            exp.end_date.strftime("%Y-%m-%d") if exp.end_date else None
                        ),
                        "job_description": exp.job_description,
                        "job_skills": exp.job_skills,
                        "salary": exp.salary,
                        "salary_type": exp.salary_type,
                        "management_responsibility": exp.management_responsibility,
                    }
                    for exp in user.work_experiences
                ]

                skills = [
                    {
                        "id": skill.id,
                        "skill_name": skill.skill_name,
                        "skill_description": skill.skill_description,
                    }
                    for skill in user.skills
                ]

                return {
                    "success": True,
                    "data": {
                        "id": user.id,
                        "name": user.name,
                        "desired_position": user.desired_position,
                        "desired_field": user.desired_field,
                        "desired_location": user.desired_location,
                        "introduction": user.introduction,
                        "keywords": user.keywords,
                        "work_experiences": work_experiences,
                        "skills": skills,
                    },
                }
            else:
                users = User.query.all()
                return {
                    "success": True,
                    "data": [
                        {
                            "id": user.id,
                            "name": user.name,
                            "desired_position": user.desired_position,
                            "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        for user in users
                    ],
                }
        except Exception as e:
            return {"success": False, "message": f"取得履歷資料失敗: {str(e)}"}, 400


class InterviewAPI(Resource):
    # 類級別的靜態變數，確保狀態在請求之間保持
    session_states = {}
    # 用戶當前問題存儲 - 結構: {user_id: {"question": str, "standard_answer": str, "question_data": dict}}
    user_current_questions = {}

    def __init__(self):
        # 初始化狀態管理
        self.current_state = InterviewState.INTRO
        # 移除 self.session_states = {}，使用類級別的 session_states

    def _get_user_state(self, user_id):
        """獲取用戶的當前狀態"""
        if user_id not in InterviewAPI.session_states:
            InterviewAPI.session_states[user_id] = InterviewState.WAITING
        return InterviewAPI.session_states[user_id]

    def _set_user_state(self, user_id, state):
        """設置用戶的狀態"""
        InterviewAPI.session_states[user_id] = state
        print(f"🔄 用戶 {user_id} 狀態變更為: {state.value}")

    def _set_user_current_question(
        self, user_id, question, standard_answer, question_data=None
    ):
        """設置用戶當前問題"""
        InterviewAPI.user_current_questions[user_id] = {
            "question": question,
            "standard_answer": standard_answer,
            "question_data": question_data,
        }
        print(f"📝 用戶 {user_id} 當前問題已設置: {question[:50]}...")

    def _get_user_current_question(self, user_id):
        """獲取用戶當前問題"""
        return InterviewAPI.user_current_questions.get(user_id, None)

    def _parse_question_result(self, question_result):
        """解析問題結果，提取問題文本和標準答案"""
        try:
            # 嘗試直接從 MCP 結果獲取
            if "問題：" in question_result:
                lines = question_result.split("\n")
                question_text = ""
                standard_answer = ""

                for line in lines:
                    if line.startswith("問題："):
                        question_text = line.replace("問題：", "").strip()
                        break

                # 由於這裡只有顯示文本，我們需要直接調用 MCP 獲取完整數據
                from server import get_random_question as mcp_get_random_question

                mcp_result = mcp_get_random_question()
                if mcp_result.get("status") == "success":
                    return mcp_result["question"], mcp_result["standard_answer"]

                return question_text, "標準答案未提供"

            return "問題解析失敗", "標準答案未提供"
        except Exception as e:
            print(f"⚠️ 解析問題結果失敗: {str(e)}")
            return "問題解析失敗", "標準答案未提供"

    def _transition_state(self, user_id, user_message):
        """根據用戶訊息判斷是否需要狀態轉換"""
        lower_message = user_message.lower()
        current_state = self._get_user_state(user_id)

        # 從 WAITING 轉換到 INTRO（按下開始面試按鈕）
        if current_state == InterviewState.WAITING:
            start_keywords = [
                "開始面試",
                "開始",
                "start_interview",
                "開始練習",
                "準備好了",
                "可以開始了",
            ]
            if any(keyword in lower_message for keyword in start_keywords):
                self._set_user_state(user_id, InterviewState.INTRO)
                return True

        # 從 INTRO 轉換到 INTRO_ANALYSIS（完成自我介紹）
        elif current_state == InterviewState.INTRO:
            intro_complete_keywords = [
                "介紹完了",
                "介紹完畢",
                "自我介紹完成",
                "就這樣",
                "結束了",
                "完成了",
                "說完了",
            ]
            if any(keyword in lower_message for keyword in intro_complete_keywords):
                self._set_user_state(user_id, InterviewState.INTRO_ANALYSIS)
                return True

        # 從 INTRO_ANALYSIS 自動轉換到 QUESTIONING（分析完成後）
        elif current_state == InterviewState.INTRO_ANALYSIS:
            # 這個轉換通常由系統自動觸發，不需要用戶訊息
            pass

        # 從 QUESTIONING 轉換到 COMPLETED（用戶要求退出）
        elif current_state == InterviewState.QUESTIONING:
            exit_keywords = ["退出", "結束", "完成", "不想繼續", "停止"]
            if any(keyword in lower_message for keyword in exit_keywords):
                self._set_user_state(user_id, InterviewState.COMPLETED)
                return True

        # 重新開始的情況
        restart_keywords = ["重新開始", "重新來過", "重新面試", "重來"]
        if any(keyword in lower_message for keyword in restart_keywords):
            self._set_user_state(user_id, InterviewState.WAITING)
            return True

        return False

    def post(self):
        """處理面試對話 - 整合狀態控制與 Fast Agent"""
        try:
            data = request.get_json()
            user_message = data.get("message", "")
            user_id = data.get("user_id", "default_user")

            print(f"🔍 收到用戶訊息: '{user_message}'")
            print(f"🔍 FAST_AGENT_AVAILABLE: {FAST_AGENT_AVAILABLE}")

            # 獲取當前狀態
            current_state = self._get_user_state(user_id)
            print(f"🎯 當前狀態: {current_state.value}")

            # 檢查狀態轉換
            state_changed = self._transition_state(user_id, user_message)
            if state_changed:
                current_state = self._get_user_state(user_id)
                print(f"🔄 狀態已轉換為: {current_state.value}")

            # 根據狀態選擇處理方式
            if FAST_AGENT_AVAILABLE:
                print("✅ 使用狀態控制的 Fast Agent 處理")
                ai_response = self._process_with_state_controlled_agent(
                    user_message, current_state
                )
            else:
                print("⚠️ 回退到狀態控制的 mock 處理")
                ai_response = self._generate_state_controlled_mock_response(
                    user_message, current_state
                )

            print(f"📤 回應: {ai_response[:100]}...")

            # 儲存對話記錄（包含狀態信息）
            session_data = {
                "user_message": user_message,
                "ai_response": ai_response,
                "current_state": current_state.value,
                "timestamp": datetime.utcnow().isoformat(),
            }

            interview_session = InterviewSession(
                user_id=user_id, session_data=str(session_data)
            )
            db.session.add(interview_session)
            db.session.commit()

            return {
                "success": True,
                "response": ai_response,
                "session_id": interview_session.id,
                "current_state": current_state.value,
                "agent_used": (
                    "state_controlled_fast_agent"
                    if FAST_AGENT_AVAILABLE
                    else "state_controlled_mock"
                ),
            }

        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": f"處理面試對話失敗: {str(e)}"}, 400

    def _process_with_state_controlled_agent(
        self, user_message, current_state, interview_data=None
    ):
        """使用狀態控制的 Fast Agent 處理用戶訊息"""
        try:
            print(
                f"🔍 開始狀態控制處理: '{user_message}' (狀態: {current_state.value})"
            )

            # 根據狀態獲取系統提示詞和可用工具
            system_prompt = get_system_prompt(current_state)
            available_tools = get_available_tools(current_state)

            print(f"🎯 系統提示詞: {system_prompt[:100]}...")
            print(f"🛠️ 可用工具: {available_tools}")

            # 檢查是否有面試數據且用戶要求退出/總結（任何狀態下都可以）
            lower_message = user_message.lower()
            exit_keywords = ["退出", "結束", "完成", "不想繼續", "停止"]
            if interview_data and any(
                keyword in lower_message for keyword in exit_keywords
            ):
                # 強制進入完成狀態並生成總結
                user_id = "default_user"
                self._set_user_state(user_id, InterviewState.COMPLETED)
                return self._process_completed_state(
                    user_message, system_prompt, interview_data
                )

            # 根據狀態選擇處理策略
            if current_state == InterviewState.WAITING:
                return self._process_waiting_state(user_message, system_prompt)
            elif current_state == InterviewState.INTRO:
                return self._process_intro_state(user_message, system_prompt)
            elif current_state == InterviewState.INTRO_ANALYSIS:
                return self._process_intro_analysis_state(user_message, system_prompt)
            elif current_state == InterviewState.QUESTIONING:
                return self._process_questioning_state(user_message, system_prompt)
            elif current_state == InterviewState.COMPLETED:
                return self._process_completed_state(
                    user_message, system_prompt, interview_data
                )
            else:
                return self._default_response(user_message)

        except Exception as e:
            print(f"❌ 狀態控制處理失敗: {e}")
            return f"處理失敗: {str(e)}"

    def _process_waiting_state(self, user_message, system_prompt):
        """處理等待開始階段的訊息"""
        try:
            # 檢查是否為開始面試的關鍵字
            lower_message = user_message.lower()
            start_keywords = [
                "開始面試",
                "開始",
                "start_interview",
                "開始練習",
                "準備好了",
                "可以開始了",
            ]

            if any(keyword in lower_message for keyword in start_keywords):
                return """
🎯 面試開始！

歡迎參加智能面試系統！接下來我們將進行以下流程：

1️⃣ **自我介紹階段**：請進行完整的自我介紹
2️⃣ **自我介紹分析**：我會分析您的介紹並給出建議  
3️⃣ **面試問答**：進行技術或行為面試問題
4️⃣ **總結建議**：給出最終的面試表現總結

現在請開始您的自我介紹。請盡量包含以下要素：
- 開場簡介（身份與專業定位）
- 學經歷概述  
- 核心技能與強項
- 代表成果
- 與職缺的連結
- 結語與期待

請開始您的自我介紹：
                """
            else:
                return f"""
👋 您好！歡迎使用智能面試系統！

我是您的AI面試官，準備為您提供專業的模擬面試體驗。

🎯 **面試流程說明**：
1. 自我介紹 → 2. 介紹分析 → 3. 技術問答 → 4. 總結建議

請點擊「開始面試」按鈕，或輸入「開始面試」來開始您的面試之旅！

您也可以隨時向我詢問面試相關的問題。

您說：「{user_message}」
                """
        except Exception as e:
            return f"處理等待階段訊息失敗: {str(e)}"

    def _process_intro_state(self, user_message, system_prompt):
        """處理自我介紹階段的訊息"""
        try:
            lower_message = user_message.lower()

            # 特殊處理：如果是「開始面試」訊息，返回歡迎和指導訊息
            start_keywords = ["開始面試", "start_interview"]
            if any(keyword in lower_message for keyword in start_keywords):
                # 不清除自我介紹內容，因為用戶可能已經開始介紹了

                return """
🎯 面試開始！

歡迎參加智能面試系統！接下來我們將進行以下流程：

1️⃣ **自我介紹階段**：請進行完整的自我介紹
2️⃣ **自我介紹分析**：我會分析您的介紹並給出建議  
3️⃣ **面試問答**：進行技術或行為面試問題
4️⃣ **總結建議**：給出最終的面試表現總結

現在請開始您的自我介紹。請盡量包含以下要素：
- 開場簡介（身份與專業定位）
- 學經歷概述  
- 核心技能與強項
- 代表成果
- 與職缺的連結
- 結語與期待

請開始您的自我介紹：
                """

            # 檢查是否為結束自我介紹的關鍵字
            intro_end_keywords = [
                "介紹完了",
                "介紹完畢",
                "自我介紹完成",
                "就這樣",
                "結束了",
                "完成了",
                "說完了",
                "介紹結束",
            ]
            if any(keyword in lower_message for keyword in intro_end_keywords):
                # 觸發狀態轉換到自我介紹分析階段
                user_id = "default_user"  # 這裡應該從請求中獲取
                self._set_user_state(user_id, InterviewState.INTRO_ANALYSIS)
                # 直接調用分析階段的處理
                return self._process_intro_analysis_state(user_message, system_prompt)
            # 不論內容為何都呼叫 intro_collector
            result = call_fast_agent_function(
                "intro_collector", user_message=user_message
            )
            if result.get("success"):
                return "✅ 已記錄您的自我介紹內容。請繼續介紹，或說「介紹完了」來開始面試。"
            else:
                return f"記錄自我介紹失敗: {result.get('error', '未知錯誤')}"
        except Exception as e:
            return f"處理自我介紹失敗: {str(e)}"

    def _process_questioning_state(self, user_message, system_prompt):
        """處理面試提問階段的訊息"""
        try:
            lower_message = user_message.lower()

            # 檢查是否為退出關鍵字
            exit_keywords = ["退出", "結束", "完成", "不想繼續", "停止"]
            if any(keyword in lower_message for keyword in exit_keywords):
                # 用戶要求退出，轉換到完成階段
                user_id = "default_user"  # 這裡應該從請求中獲取
                self._set_user_state(user_id, InterviewState.COMPLETED)
                return self._process_completed_state(user_message, system_prompt, None)

            # 檢查是否為自動請求問題（前端發出的精確請求）
            if user_message.strip() == "請給我問題":
                # 前端自動請求下一題 - 需要先檢查是否有待分析的答案
                user_id = "default_user"  # 這裡應該從請求中獲取

                # 清除舊的問題數據，為新問題做準備
                print(f"🔄 清除用戶 {user_id} 的舊問題數據，準備新問題")

                result = call_fast_agent_function("get_question")
                if result.get("success"):
                    # 從新的問題數據結構中獲取信息
                    question_data = result.get("question_data", {})
                    question_text = question_data.get("question", "問題獲取失敗")
                    standard_answer = question_data.get(
                        "standard_answer", "標準答案未提供"
                    )

                    # 存儲當前問題數據，包含完整的問題信息
                    self._set_user_current_question(
                        user_id, question_text, standard_answer, question_data
                    )

                    print(f"✅ 新問題已設置: {question_text[:50]}...")
                    print(f"📝 標準答案已設置: {standard_answer[:50]}...")

                    return f"""
🎯 **面試問題**

{result["result"]}

---

💡 **提示**: 請仔細回答上述問題。除非您說「退出」，否則我們會在您回答後繼續下一題。
                    """
                else:
                    return f"獲取問題失敗: {result.get('error', '未知錯誤')}"
            else:
                # 用戶的回答，使用 analyze_answer 工具分析
                user_id = "default_user"  # 這裡應該從請求中獲取
                current_question_data = self._get_user_current_question(user_id)

                if current_question_data:
                    print(
                        f"📊 分析用戶回答對應問題: {current_question_data['question'][:50]}..."
                    )

                    # 傳遞完整的問題上下文
                    result = call_fast_agent_function(
                        "analyze_answer",
                        user_answer=user_message,
                        question=current_question_data["question"],
                        standard_answer=current_question_data["standard_answer"],
                    )

                    if result.get("success"):
                        # 分析成功後，保持問題數據直到下一題被請求
                        print(f"✅ 答案分析完成，問題數據保持不變")

                        response = f"""
{result["result"]}

---

💡 **提示**: 請等待系統準備下一題...
                        """
                        return response
                    else:
                        return f"分析回答失敗: {result.get('error', '未知錯誤')}"
                else:
                    # 沒有當前問題數據，嘗試進行基礎分析
                    print(f"⚠️ 警告：沒有找到對應的問題數據，進行基礎分析")
                    result = call_fast_agent_function(
                        "analyze_answer", user_answer=user_message
                    )

                    if result.get("success"):
                        response = f"""
{result["result"]}

---

⚠️ **注意**: 無法找到對應的問題，這可能導致分析不夠準確。
💡 **提示**: 請等待系統準備下一題...
                        """
                        return response
                    else:
                        return f"分析回答失敗: {result.get('error', '未知錯誤')}"

        except Exception as e:
            return f"處理面試回答失敗: {str(e)}"

    def _process_intro_analysis_state(self, user_message, system_prompt):
        """處理自我介紹分析階段"""
        try:
            # 獲取收集到的完整自我介紹內容
            from fast_agent_bridge import get_collected_intro

            collected_intro = get_collected_intro("default_user")

            # 如果沒有收集到內容，使用當前訊息
            intro_content = collected_intro if collected_intro else user_message

            print(f"📊 準備分析自我介紹: {intro_content[:100]}...")

            # 分析完整的自我介紹內容
            result = call_fast_agent_function(
                "analyze_intro", user_message=intro_content
            )
            if result.get("success"):
                # 分析完成後自動轉換到面試階段
                user_id = "default_user"  # 這裡應該從請求中獲取
                self._set_user_state(user_id, InterviewState.QUESTIONING)

                # 只返回分析結果，不包含面試問題
                return f"""
📊 **自我介紹分析結果**

{result["result"]}

---

🎯 **分析完成！現在進入面試問答階段**

我將為您提供面試問題，請認真回答。除非您說「退出」，否則我們會繼續下一題。
                """
            else:
                return f"自我介紹分析失敗: {result.get('error', '未知錯誤')}"
        except Exception as e:
            return f"處理自我介紹分析失敗: {str(e)}"

    def _process_completed_state(
        self, user_message, system_prompt, interview_data=None
    ):
        """處理面試完成階段"""
        try:
            lower_message = user_message.lower()

            # 檢查是否為重新開始的請求
            restart_keywords = ["重新開始", "再來一次", "重新面試", "開始新的面試"]
            if any(keyword in lower_message for keyword in restart_keywords):
                # 重置狀態到等待階段
                user_id = "default_user"
                self._set_user_state(user_id, InterviewState.WAITING)
                return """
🔄 **重新開始面試**

系統已重置，歡迎再次使用智能面試系統！

請點擊「開始面試」或輸入「開始面試」來開始新的面試流程。
                """

            # 如果面試已經完成，不要重複生成總結
            # 檢查是否是第一次進入完成階段（通過檢查用戶訊息是否為退出相關）
            exit_keywords = ["退出", "結束", "完成", "不想繼續", "停止"]
            if any(keyword in lower_message for keyword in exit_keywords):
                # 第一次進入完成階段，生成總結
                result = call_fast_agent_function(
                    "generate_final_summary",
                    user_message=user_message,
                    interview_data=interview_data,
                )
                if result.get("success"):
                    return f"""
🎉 **面試完成！**

{result["result"]}

---

感謝您參與本次模擬面試！希望這次經驗對您的求職之路有所幫助。

如需重新開始，請說「重新開始」。
                    """
                else:
                    return f"""
🎉 **面試完成！**

感謝您參與本次智能面試系統的模擬面試！

基於您的表現，我建議您：
1. 繼續練習技術問題的表達
2. 加強自我介紹的結構化
3. 多進行模擬面試練習

如需重新開始，請說「重新開始」。
                    """
            else:
                # 面試已經完成，提示用戶選項
                return """
✅ **面試已完成**

您的面試總結已經生成完畢。

📋 您現在可以：
- 說「重新開始」開始新的面試
- 查看之前的面試總結

如需重新開始面試，請說「重新開始」。
                """

        except Exception as e:
            return f"處理面試完成階段失敗: {str(e)}"

    def _get_first_question(self):
        """獲取第一個面試問題"""
        try:
            result = call_fast_agent_function("get_question")
            if result.get("success"):
                return result["result"]
            else:
                return "第一題：請介紹一下您最熟悉的程式語言及其應用場景。"
        except Exception as e:
            return "無法獲取問題，請稍後再試。"

    def _generate_state_controlled_mock_response(self, user_message, current_state):
        """生成狀態控制的模擬回應"""
        try:
            print(f"🎭 生成狀態控制模擬回應 (狀態: {current_state.value})")

            if current_state == InterviewState.INTRO:
                return f"🎯 自我介紹階段：謝謝您的分享「{user_message}」。請繼續介紹或說「介紹完了」來開始面試。"
            elif current_state == InterviewState.QUESTIONING:
                # 檢查是否為請求題目
                question_request_keywords = [
                    "請給我問題",
                    "想要問題",
                    "需要問題",
                    "可以給我問題",
                    "提供問題",
                    "出題",
                    "測試",
                    "開始面試",
                    "開始練習",
                ]
                lower_message = user_message.lower()

                if any(
                    keyword in lower_message for keyword in question_request_keywords
                ):
                    return f"🎯 面試題目階段：這是一個模擬面試題目。請回答這個問題，我會給您評分和標準答案。"
                else:
                    return f"📝 面試回答階段：您說「{user_message}」。這是一個很好的回答！我會分析您的回答並給出評分。"
            else:
                return f"💬 一般回應：{user_message}"

        except Exception as e:
            return f"生成模擬回應失敗: {str(e)}"

    def _process_with_fast_agent(self, user_message):
        """使用 Fast Agent 處理用戶訊息 - 混合策略"""
        try:
            print(f"🔍 開始處理用戶訊息: '{user_message}'")

            # 第一層：快速關鍵字匹配（低成本、高速度）
            result = self._keyword_based_processing(user_message)
            if result:
                print(f"✅ 關鍵字匹配成功: {result[:50]}...")
                return result

            # 第二層：LLM 意圖識別（高理解能力）
            result = self._llm_intent_processing(user_message)
            if result:
                print(f"🤖 LLM 意圖識別成功: {result[:50]}...")
                return result

            # 第三層：預設回應（兜底）
            result = self._default_response(user_message)
            print(f"💬 使用預設回應: {result[:50]}...")
            return result

        except Exception as e:
            print(f"❌ 處理失敗: {e}")
            return f"處理失敗: {str(e)}"

    def _keyword_based_processing(self, user_message):
        """關鍵字基礎處理 - 快速匹配"""
        lower_message = user_message.lower()

        # 檢查是否為獲取問題的請求（非常精確的匹配）
        question_keywords = [
            "請給我問題",
            "想要問題",
            "需要問題",
            "可以給我問題",
            "提供問題",
            "出題",
            "測試",
        ]
        if any(word in lower_message for word in question_keywords):
            result = call_fast_agent_function("get_question")
            if result.get("success"):
                return result["result"]
            else:
                return f"獲取問題失敗: {result.get('error', '未知錯誤')}"

        # 檢查是否為標準答案請求（非常精確的匹配）
        standard_keywords = [
            "請給我標準答案",
            "想要標準答案",
            "需要標準答案",
            "提供標準答案",
        ]
        if any(word in lower_message for word in standard_keywords):
            result = call_fast_agent_function("get_standard_answer")
            if result.get("success"):
                return result["result"]
            else:
                return f"獲取標準答案失敗: {result.get('error', '未知錯誤')}"

        # 檢查是否為開始面試（非常精確的匹配）
        start_keywords = ["開始面試", "開始練習", "開始測試", "準備開始", "可以開始了"]
        if any(word in lower_message for word in start_keywords):
            result = call_fast_agent_function("start_interview")
            if result.get("success"):
                return result["result"]
            else:
                return f"開始面試失敗: {result.get('error', '未知錯誤')}"

        # 檢查是否為自我介紹（非常精確的匹配）
        intro_keywords = [
            "我叫",
            "我是",
            "我的名字",
            "自我介紹",
            "我的背景",
            "我的經驗",
            "我的學歷",
            "我的工作",
        ]
        if any(word in lower_message for word in intro_keywords):
            return f"""
👋 很高興認識您！

您的自我介紹：{user_message}

這是一個很好的開始！現在我們可以開始正式的面試流程。

請輸入「開始面試」或「問題」來獲取面試問題。
            """

        # 檢查是否為明確的面試回答（非常嚴格的條件）
        answer_indicators = [
            "我認為",
            "我的看法",
            "我的回答",
            "我的答案",
            "我的理解",
            "根據我的經驗",
            "我的做法",
            "我的方法",
            "我的策略",
            "我的觀點",
            "我的想法",
            "我的見解",
        ]

        if len(user_message) > 80 and any(
            word in lower_message for word in answer_indicators
        ):
            return self._analyze_interview_answer(user_message)

        # 檢查是否為一般對話（非常精確的匹配）
        chat_keywords = [
            "謝謝",
            "感謝",
            "再見",
            "拜拜",
            "好的",
            "了解",
            "明白",
            "知道了",
            "沒問題",
            "可以",
            "行",
            "ok",
            "okay",
            "嗯",
            "是的",
        ]
        if any(word in lower_message for word in chat_keywords):
            return self._handle_general_chat(user_message)

        # 如果沒有匹配到任何關鍵字，返回 None 讓下一層處理
        return None

    def _llm_intent_processing(self, user_message):
        """LLM 意圖識別處理 - 高理解能力"""
        try:
            # 只有在 FAST_AGENT_AVAILABLE 時才使用 LLM
            if not FAST_AGENT_AVAILABLE:
                return None

            # 使用真正的 LLM 意圖識別
            intent = self._llm_based_intent_recognition(user_message)
            print(f"🤖 LLM 識別到意圖: {intent}")

            if intent == "get_question":
                result = call_fast_agent_function("get_question")
                return result.get("result") if result.get("success") else None
            elif intent == "analyze_answer":
                return self._analyze_interview_answer(user_message)
            elif intent == "get_standard_answer":
                result = call_fast_agent_function("get_standard_answer")
                return result.get("result") if result.get("success") else None
            elif intent == "start_interview":
                result = call_fast_agent_function("start_interview")
                return result.get("result") if result.get("success") else None
            elif intent == "introduction":
                return f"""
👋 很高興認識您！

您的自我介紹：{user_message}

這是一個很好的開始！現在我們可以開始正式的面試流程。

請輸入「開始面試」或「問題」來獲取面試問題。
                """
            elif intent == "general_chat":
                return self._handle_general_chat(user_message)

        except Exception as e:
            print(f"❌ LLM 意圖識別失敗: {e}")
            return None

    def _llm_based_intent_recognition(self, user_message):
        """使用 LLM 進行真正的意圖識別"""
        try:
            # 導入 OpenAI
            import os

            import openai
            from openai import OpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("⚠️ OPENAI_API_KEY 未設定，回退到規則匹配")
                return self._smart_intent_recognition(user_message)

            client = OpenAI(api_key=api_key)

            # 構建 LLM 意圖識別提示詞
            prompt = f"""
請分析以下用戶輸入的意圖，並返回對應的意圖類型：

用戶輸入：{user_message}

可能的意圖類型：
1. "get_question" - 用戶想要獲取面試問題
2. "analyze_answer" - 用戶正在回答面試問題
3. "get_standard_answer" - 用戶想要查看標準答案
4. "start_interview" - 用戶想要開始面試
5. "introduction" - 用戶在做自我介紹
6. "general_chat" - 一般對話或問候

請只返回意圖類型名稱，不要添加任何其他文字。
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "您是一個意圖識別專家，負責分析用戶輸入的意圖。請準確識別用戶想要執行的操作。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=50,
            )

            intent = response.choices[0].message.content.strip().lower()
            print(f"🔍 LLM 識別結果: {intent}")

            # 驗證意圖是否有效
            valid_intents = [
                "get_question",
                "analyze_answer",
                "get_standard_answer",
                "start_interview",
                "introduction",
                "general_chat",
            ]

            if intent and intent in valid_intents:
                return intent
            else:
                print(f"⚠️ LLM 返回無效意圖: {intent}，回退到規則匹配")
                return self._smart_intent_recognition(user_message)

        except Exception as e:
            print(f"❌ LLM 意圖識別失敗: {e}，回退到規則匹配")
            return self._smart_intent_recognition(user_message)

    def _smart_intent_recognition(self, user_message):
        """智能意圖識別 - 結合規則和語義分析"""
        lower_message = user_message.lower()

        # 1. 問題相關意圖
        question_patterns = [
            "問題",
            "題目",
            "面試",
            "問",
            "考",
            "請給我",
            "想要",
            "需要",
            "可以給我",
            "提供",
            "出題",
            "測試",
        ]
        if any(pattern in lower_message for pattern in question_patterns):
            return "get_question"

        # 2. 答案分析相關意圖
        answer_patterns = [
            "我認為",
            "我的看法",
            "我的回答",
            "我的答案",
            "我的理解",
            "根據我的經驗",
            "我的做法",
            "我的方法",
            "我的策略",
            "我的觀點",
            "我的想法",
            "我的見解",
        ]
        if any(pattern in lower_message for pattern in answer_patterns):
            return "analyze_answer"

        # 3. 標準答案相關意圖
        standard_patterns = [
            "標準",
            "答案",
            "解釋",
            "正確",
            "參考",
            "對照",
            "標準答案",
            "正確答案",
            "參考答案",
        ]
        if any(pattern in lower_message for pattern in standard_patterns):
            return "get_standard_answer"

        # 4. 開始面試意圖
        start_patterns = [
            "開始",
            "start",
            "開始面試",
            "準備",
            "準備好",
            "可以開始",
            "開始吧",
            "開始練習",
            "開始測試",
        ]
        if any(pattern in lower_message for pattern in start_patterns):
            return "start_interview"

        # 5. 自我介紹意圖
        intro_patterns = [
            "我叫",
            "我是",
            "我的名字",
            "自我介紹",
            "介紹",
            "背景",
            "經歷",
            "你好",
            "hello",
            "hi",
            "您好",
            "初次見面",
            "認識",
        ]
        if any(pattern in lower_message for pattern in intro_patterns):
            return "introduction"

        # 6. 一般對話意圖
        chat_patterns = [
            "謝謝",
            "感謝",
            "再見",
            "拜拜",
            "好的",
            "了解",
            "明白",
            "知道了",
            "沒問題",
            "可以",
            "行",
            "ok",
            "okay",
        ]
        if any(pattern in lower_message for pattern in chat_patterns):
            return "general_chat"

        # 7. 根據內容長度和結構判斷
        if len(user_message) > 20 and any(
            word in lower_message for word in ["我", "我的", "我們"]
        ):
            # 較長的包含第一人稱的內容，可能是面試回答
            return "analyze_answer"

        # 8. 預設為一般對話
        return "general_chat"

    def _analyze_interview_answer(self, user_message):
        """分析面試答案"""
        analysis_result = call_fast_agent_function(
            "analyze_answer",
            user_answer=user_message,
            question="面試問題",
            standard_answer="標準答案",
        )

        standard_result = call_fast_agent_function("get_standard_answer")

        if analysis_result.get("success") and standard_result.get("success"):
            combined_response = f"""
{analysis_result["result"]}

============================================================
{standard_result["result"]}
            """
            return combined_response
        elif analysis_result.get("success"):
            return analysis_result["result"]
        elif standard_result.get("success"):
            return standard_result["result"]
        else:
            return f"分析失敗: {analysis_result.get('error', '未知錯誤')}"

    def _handle_general_chat(self, user_message):
        """處理一般對話"""
        return f"""
💬 我理解您的輸入：{user_message}

如果您想要：
- 開始面試：請輸入「開始面試」或「問題」
- 回答面試問題：請明確說明您的答案
- 查看標準答案：請輸入「標準答案」

請告訴我您希望進行哪種操作？
        """

    def _default_response(self, user_message):
        """預設回應"""
        return f"""
💬 我理解您的輸入：{user_message}

這看起來像是一般對話或自我介紹。如果您想要：
- 開始面試：請輸入「開始面試」或「問題」
- 回答面試問題：請明確說明您的答案
- 查看標準答案：請輸入「標準答案」

請告訴我您希望進行哪種操作？
        """

    def _generate_mock_response(self, user_message):
        """生成AI回應 - 優先使用 SmartAgent，回退到 MCP 工具"""

        # 優先使用 SmartAgent
        if SMART_AGENT_AVAILABLE:
            try:

                class SimpleClient:
                    async def call_tool(self, tool_name, arguments):
                        if tool_name == "greet_user":
                            return greet_user(arguments.get("name", ""))
                        elif tool_name == "add_numbers":
                            return add_numbers(
                                arguments.get("a", 0), arguments.get("b", 0)
                            )
                        elif tool_name == "get_random_question":
                            return get_random_question()
                        elif tool_name == "analyze_resume":
                            return analyze_resume(arguments.get("resume_text", ""))
                        elif tool_name == "recommend_jobs":
                            return recommend_jobs(arguments.get("skills", []))
                        elif tool_name == "get_server_info":
                            return get_server_info()
                        elif tool_name == "handle_multi_channel":
                            return handle_multi_channel(
                                arguments.get("channel", ""), arguments.get("payload")
                            )
                        elif tool_name == "file_operations":
                            return file_operations(
                                arguments.get("operation", "read"),
                                arguments.get("file_path", ""),
                                arguments.get("content"),
                            )
                        elif tool_name == "code_analysis":
                            return code_analysis(
                                arguments.get("code", ""),
                                arguments.get("language", "python"),
                            )
                        else:
                            return {"error": f"未知工具: {tool_name}"}

                smart_agent = SmartAgent(SimpleClient())

                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                result = loop.run_until_complete(
                    smart_agent.process_user_request(user_message)
                )

                if result["success"]:
                    print(f"🤖 SmartAgent 處理成功: {result['tool_used']}")
                    return str(result["result"])
                else:
                    print(f"⚠️ SmartAgent 處理失敗: {result.get('error', '未知錯誤')}")
            except Exception as e:
                print(f"❌ SmartAgent 執行錯誤: {e}")

        # 如果 SmartAgent 不可用，使用 MCP 工具
        if MCP_AVAILABLE:
            try:
                # 使用MCP工具處理
                lower_message = user_message.lower()

                # 面試問題
                if any(word in lower_message for word in ["面試", "問題", "題目"]):
                    result = get_random_question()
                    return (
                        f"面試問題：{result.get('instruction', '請介紹您的專案經驗')}"
                    )

                # 履歷分析
                elif any(
                    word in lower_message for word in ["履歷", "簡歷", "技能", "經驗"]
                ):
                    result = analyze_resume(user_message)
                    skills = result.get("skills", [])
                    return f"根據您的履歷，我發現您具備以下技能：{', '.join(skills) if skills else '需要更多資訊'}"

                # 工作推薦
                elif any(
                    word in lower_message for word in ["工作", "職缺", "推薦", "職位"]
                ):
                    # 簡單提取技能
                    skills = []
                    skill_keywords = [
                        "python",
                        "javascript",
                        "java",
                        "react",
                        "vue",
                        "node",
                        "sql",
                        "mongodb",
                    ]
                    for skill in skill_keywords:
                        if skill in lower_message:
                            skills.append(skill)

                    if not skills:
                        skills = ["Python", "JavaScript"]  # 預設技能

                    result = recommend_jobs(skills)
                    recommendations = result.get("recommendations", [])
                    return f"根據您的技能，推薦以下職缺：{', '.join(recommendations) if recommendations else '暫無推薦'}"

                # 問候
                elif any(word in lower_message for word in ["你好", "hello", "hi"]):
                    result = greet_user("")
                    return result

                # 計算
                elif any(word in lower_message for word in ["計算", "加", "+"]):
                    import re

                    numbers = re.findall(r"\d+", user_message)
                    if len(numbers) >= 2:
                        result = add_numbers(int(numbers[0]), int(numbers[1]))
                        return f"計算結果：{result}"

                # 伺服器資訊
                elif any(
                    word in lower_message for word in ["資訊", "信息", "介紹", "系統"]
                ):
                    result = get_server_info()
                    return f"系統資訊：{result.get('name', '')} - {result.get('description', '')}"

            except Exception as e:
                print(f"⚠️ MCP工具執行失敗: {e}")

        # 如果都不可用，使用原有的模擬回應
        mock_responses = [
            "很好的問題！請您詳細說明一下相關經驗。",
            "根據您的背景，我想了解您如何處理挑戰性的工作情境。",
            "您提到的技能很有趣，能否分享一個具體的應用案例？",
            "感謝您的分享。接下來我想了解您的職涯規劃。",
            "這個經驗很寶貴。您從中學到了什麼重要的課題？",
        ]

        # 簡單的關鍵字匹配邏輯
        if any(keyword in user_message.lower() for keyword in ["經驗", "工作", "專案"]):
            return (
                "很好的經驗分享！能否再詳細說明您在這個過程中遇到的挑戰以及如何解決？"
            )
        elif any(
            keyword in user_message.lower() for keyword in ["技能", "能力", "專長"]
        ):
            return "您的技能組合很有價值。請舉一個具體例子說明您如何運用這些技能解決實際問題？"
        elif any(
            keyword in user_message.lower() for keyword in ["目標", "規劃", "未來"]
        ):
            return "您的職涯規劃很清晰。請問您認為這個職位如何幫助您達成這些目標？"
        else:
            import random

            return random.choice(mock_responses)


# 新增 Fast Agent API 端點
class FastAgentAPI(Resource):
    def post(self):
        """Fast Agent 專用 API 端點"""
        try:
            data = request.get_json()
            function_name = data.get("function")
            arguments = data.get("arguments", {})

            if not function_name:
                return {"success": False, "message": "缺少 function 參數"}, 400

            # 調用 Fast Agent 函數
            result = call_fast_agent_function(function_name, **arguments)

            return {
                "success": result.get("success", False),
                "result": result.get("result", ""),
                "error": result.get("error", ""),
                "agent": "fast_agent",
            }

        except Exception as e:
            return {"success": False, "message": f"Fast Agent API 失敗: {str(e)}"}, 400


class FileUploadAPI(Resource):
    def post(self):
        """處理檔案上傳 (履歷檔案)"""
        try:
            # TODO: 實現履歷檔案解析功能
            # 目前返回模擬回應
            return {
                "success": True,
                "message": "檔案上傳成功，履歷解析功能開發中",
                "parsed_data": {},
            }
        except Exception as e:
            return {"success": False, "message": f"檔案上傳失敗: {str(e)}"}, 400


class AvatarAPI(Resource):
    def post(self):
        """虛擬人狀態控制API - 支援Fay等數字人模型"""
        try:
            data = request.get_json()
            action = data.get("action")  # speak, listen, idle, emotion

            if action == "speak":
                return self._handle_speak_action(data)
            elif action == "listen":
                return self._handle_listen_action(data)
            elif action == "emotion":
                return self._handle_emotion_action(data)
            elif action == "idle":
                return self._handle_idle_action(data)
            else:
                return {"success": False, "message": "不支援的操作"}, 400

        except Exception as e:
            return {"success": False, "message": f"虛擬人控制失敗: {str(e)}"}, 400

    def _handle_speak_action(self, data):
        """處理說話動作 - TTS與唇形同步"""
        text = data.get("text", "")
        voice_config = data.get("voice_config", {})

        # TODO: 整合TTS引擎 (Azure Speech, Google TTS, 本地TTS)
        # TODO: 生成音頻檔案
        # TODO: 計算唇形同步資料

        return {
            "success": True,
            "audio_url": "/api/avatar/audio/latest",  # 音頻檔案URL
            "lip_sync_data": [],  # 唇形同步時間軸
            "duration": 3.5,  # 音頻時長(秒)
            "emotion": voice_config.get("emotion", "neutral"),
        }

    def _handle_listen_action(self, data):
        """處理聆聽狀態"""
        return {
            "success": True,
            "state": "listening",
            "animation": "listening_idle",
            "duration": -1,  # 無限期直到其他動作
        }

    def _handle_emotion_action(self, data):
        """處理表情變化"""
        emotion = data.get(
            "emotion", "neutral"
        )  # happy, sad, surprised, angry, neutral
        intensity = data.get("intensity", 0.5)  # 0.0-1.0

        return {
            "success": True,
            "emotion": emotion,
            "intensity": intensity,
            "transition_duration": 1.0,
        }

    def _handle_idle_action(self, data):
        """處理待機狀態"""
        return {
            "success": True,
            "state": "idle",
            "animation": "breathing",
            "blink_interval": 3.0,
        }


class TTSEngine(Resource):
    def post(self):
        """文字轉語音API - 支援多種TTS引擎"""
        try:
            data = request.get_json()
            text = data.get("text", "")
            voice = data.get("voice", "zh-TW-female")
            speed = data.get("speed", 1.0)
            emotion = data.get("emotion", "neutral")

            # TODO: 整合多種TTS引擎
            # 1. Azure Cognitive Services Speech
            # 2. Google Cloud Text-to-Speech
            # 3. Amazon Polly
            # 4. 本地TTS (如：espeak, festival)
            # 5. Fay專用TTS接口

            audio_data = self._generate_speech(text, voice, speed, emotion)

            return {
                "success": True,
                "audio_url": f'/api/tts/audio/{audio_data["file_id"]}',
                "duration": audio_data["duration"],
                "phonemes": audio_data["phonemes"],  # 音素資料用於唇形同步
                "voice_config": {"voice": voice, "speed": speed, "emotion": emotion},
            }

        except Exception as e:
            return {"success": False, "message": f"語音合成失敗: {str(e)}"}, 400

    def _generate_speech(self, text, voice, speed, emotion):
        """生成語音檔案 - 模擬實現"""
        # TODO: 實際TTS實現
        import uuid

        file_id = str(uuid.uuid4())

        return {
            "file_id": file_id,
            "duration": len(text) * 0.15,  # 估算時長
            "phonemes": [],  # 音素時間軸
        }


class LipSyncAPI(Resource):
    def post(self):
        """唇形同步API - 音頻與視覺對齊"""
        try:
            data = request.get_json()
            audio_file = data.get("audio_file")
            text = data.get("text", "")

            # TODO: 實現唇形同步算法
            # 1. 音頻分析提取音素
            # 2. 文字音素對齊
            # 3. 生成口型關鍵幀
            # 4. 輸出Fay兼容格式

            lip_sync_data = self._generate_lip_sync(audio_file, text)

            return {
                "success": True,
                "lip_sync_data": lip_sync_data,
                "keyframes": lip_sync_data["keyframes"],
                "format": "fay_compatible",
            }

        except Exception as e:
            return {"success": False, "message": f"唇形同步失敗: {str(e)}"}, 400

    def _generate_lip_sync(self, audio_file, text):
        """生成唇形同步資料"""
        # TODO: 實際唇形同步實現
        return {
            "keyframes": [
                {"time": 0.0, "mouth_shape": "A"},
                {"time": 0.5, "mouth_shape": "O"},
                {"time": 1.0, "mouth_shape": "closed"},
            ],
            "duration": 3.0,
        }


class FayIntegrationAPI(Resource):
    def post(self):
        """Fay數字人專用整合API"""
        try:
            data = request.get_json()
            command = data.get(
                "command"
            )  # start_conversation, send_message, set_emotion, etc.

            if command == "start_conversation":
                return self._start_fay_conversation(data)
            elif command == "send_message":
                return self._send_message_to_fay(data)
            elif command == "set_emotion":
                return self._set_fay_emotion(data)
            elif command == "get_status":
                return self._get_fay_status()
            else:
                return {"success": False, "message": "不支援的Fay指令"}, 400

        except Exception as e:
            return {"success": False, "message": f"Fay整合失敗: {str(e)}"}, 400

    def _start_fay_conversation(self, data):
        """啟動Fay對話會話"""
        # TODO: 與Fay系統建立WebSocket連接
        return {
            "success": True,
            "session_id": "fay_session_123",
            "status": "ready",
            "websocket_url": "ws://localhost:8080/fay",
        }

    def _send_message_to_fay(self, data):
        """向Fay發送訊息"""
        message = data.get("message", "")
        # TODO: 通過WebSocket發送到Fay
        return {"success": True, "message_sent": message, "fay_response_pending": True}

    def _set_fay_emotion(self, data):
        """設定Fay表情"""
        emotion = data.get("emotion", "neutral")
        # TODO: 發送表情指令到Fay
        return {"success": True, "emotion_set": emotion, "transition_time": 1.0}

    def _get_fay_status(self):
        """取得Fay系統狀態"""
        # TODO: 查詢Fay系統當前狀態
        return {
            "success": True,
            "current_emotion": "neutral",
            "is_speaking": False,
            "conversation_active": True,
        }


class STTEngine(Resource):
    def post(self):
        """語音轉文字API - 支援多種STT引擎"""
        try:
            # 檢查是否有音頻檔案上傳
            if "audio" not in request.files:
                return {"success": False, "message": "未找到音頻檔案"}, 400

            audio_file = request.files["audio"]
            if audio_file.filename == "":
                return {"success": False, "message": "未選擇音頻檔案"}, 400

            # 取得額外參數
            form_data = request.form
            engine = form_data.get("engine", "whisper")  # 預設使用Whisper
            language = form_data.get("language", "zh-TW")
            model_size = form_data.get("model_size", "base")

            # 根據不同引擎處理
            if engine == "whisper":
                result = self._whisper_transcribe(audio_file, language, model_size)
            elif engine == "azure":
                result = self._azure_stt(audio_file, language)
            elif engine == "google":
                result = self._google_stt(audio_file, language)
            elif engine == "custom":
                result = self._custom_stt(audio_file, language)
            else:
                return {"success": False, "message": f"不支援的STT引擎: {engine}"}, 400

            return {
                "success": True,
                "transcription": result["text"],
                "confidence": result.get("confidence", 0.95),
                "language": language,
                "engine": engine,
                "processing_time": result.get("processing_time", 0.0),
                "segments": result.get("segments", []),
            }

        except Exception as e:
            return {"success": False, "message": f"語音識別失敗: {str(e)}"}, 400

    def _whisper_transcribe(self, audio_file, language, model_size):
        """Whisper語音識別"""
        # TODO: 實現Whisper STT
        # import whisper
        # model = whisper.load_model(model_size)
        # result = model.transcribe(audio_file, language=language)

        # 模擬回傳結果
        return {
            "text": "這是Whisper識別的測試結果",
            "confidence": 0.96,
            "processing_time": 1.2,
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "這是Whisper識別的測試結果"}
            ],
        }

    def _azure_stt(self, audio_file, language):
        """Azure語音服務STT"""
        # TODO: 實現Azure STT
        return {
            "text": "這是Azure STT識別結果",
            "confidence": 0.94,
            "processing_time": 0.8,
        }

    def _google_stt(self, audio_file, language):
        """Google Cloud Speech-to-Text"""
        # TODO: 實現Google STT
        return {
            "text": "這是Google STT識別結果",
            "confidence": 0.93,
            "processing_time": 1.0,
        }

    def _custom_stt(self, audio_file, language):
        """自定義STT引擎"""
        # TODO: 實現自定義STT
        return {
            "text": "這是自定義STT識別結果",
            "confidence": 0.90,
            "processing_time": 1.5,
        }


class SpeechAPI(Resource):
    def post(self):
        """語音處理綜合API - 整合STT和TTS"""
        try:
            data = request.get_json()
            action = data.get("action")  # transcribe, synthesize, realtime

            if action == "transcribe":
                # 語音轉文字
                return self._handle_transcription(data)
            elif action == "synthesize":
                # 文字轉語音 (調用現有TTS)
                return self._handle_synthesis(data)
            elif action == "realtime":
                # 即時語音處理
                return self._handle_realtime(data)
            else:
                return {"success": False, "message": "不支援的語音處理動作"}, 400

        except Exception as e:
            return {"success": False, "message": f"語音處理失敗: {str(e)}"}, 400

    def _handle_transcription(self, data):
        """處理語音轉文字請求"""
        # 轉發到STT引擎
        return {
            "success": True,
            "action": "transcribe",
            "redirect_to": "/api/stt",
            "message": "請使用POST /api/stt上傳音頻檔案",
        }

    def _handle_synthesis(self, data):
        """處理文字轉語音請求"""
        # 轉發到TTS引擎
        return {
            "success": True,
            "action": "synthesize",
            "redirect_to": "/api/tts/generate",
            "message": "請使用POST /api/tts/generate進行語音合成",
        }

    def _handle_realtime(self, data):
        """處理即時語音互動"""
        # TODO: 實現即時語音處理
        return {
            "success": True,
            "action": "realtime",
            "websocket_url": "ws://localhost:5000/speech-realtime",
            "session_id": "speech_session_123",
        }


# 註冊API路由
api.add_resource(UserAPI, "/api/users", "/api/users/<int:user_id>")
api.add_resource(InterviewAPI, "/api/interview")
api.add_resource(FastAgentAPI, "/api/fast-agent")  # 新增 Fast Agent API
api.add_resource(FileUploadAPI, "/api/upload")
api.add_resource(AvatarAPI, "/api/avatar/control")  # 虛擬人控制
api.add_resource(TTSEngine, "/api/tts/generate")  # 文字轉語音
api.add_resource(LipSyncAPI, "/api/avatar/lipsync")  # 唇形同步
api.add_resource(FayIntegrationAPI, "/api/fay/integration")  # Fay專用整合
api.add_resource(STTEngine, "/api/stt")  # 語音轉文字
api.add_resource(SpeechAPI, "/api/speech")  # 語音處理綜合


# 網頁路由
@app.route("/")
def index():
    """主頁面"""
    return render_template("index.html")


@app.route("/resume")
def resume():
    """履歷輸入頁面"""
    return render_template("resume.html")


@app.route("/test")
def test():
    """面試系統測試頁面"""
    return render_template("browser_test.html")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)
