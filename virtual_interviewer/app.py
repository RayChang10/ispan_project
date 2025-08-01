import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy

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
    def post(self):
        """處理面試對話 - 整合 Fast Agent"""
        try:
            data = request.get_json()
            user_message = data.get("message", "")
            user_id = data.get("user_id")

            print(f"🔍 收到用戶訊息: '{user_message}'")
            print(f"🔍 FAST_AGENT_AVAILABLE: {FAST_AGENT_AVAILABLE}")

            # 優先使用 Fast Agent 處理
            if FAST_AGENT_AVAILABLE:
                print("✅ 使用 Fast Agent 處理")
                ai_response = self._process_with_fast_agent(user_message)
            else:
                print("⚠️ 回退到 mock 處理")
                # 回退到原有邏輯
                ai_response = self._generate_mock_response(user_message)

            print(f"📤 回應: {ai_response[:100]}...")

            # 儲存對話記錄
            session_data = {
                "user_message": user_message,
                "ai_response": ai_response,
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
                "agent_used": "fast_agent" if FAST_AGENT_AVAILABLE else "mock",
            }

        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": f"處理面試對話失敗: {str(e)}"}, 400

    def _process_with_fast_agent(self, user_message):
        """使用 Fast Agent 處理用戶訊息"""
        try:
            lower_message = user_message.lower()

            # 檢查是否為獲取問題的請求
            if any(word in lower_message for word in ["問題", "題目", "面試"]):
                # 獲取面試問題
                result = call_fast_agent_function("get_question")
                if result.get("success"):
                    return result["result"]
                else:
                    return f"獲取問題失敗: {result.get('error', '未知錯誤')}"

            # 檢查是否為其他指令
            elif any(word in lower_message for word in ["標準", "答案", "解釋"]):
                # 獲取標準答案
                result = call_fast_agent_function("get_standard_answer")
                if result.get("success"):
                    return result["result"]
                else:
                    return f"獲取標準答案失敗: {result.get('error', '未知錯誤')}"

            elif any(word in lower_message for word in ["開始", "start"]):
                # 開始面試
                result = call_fast_agent_function("start_interview")
                if result.get("success"):
                    return result["result"]
                else:
                    return f"開始面試失敗: {result.get('error', '未知錯誤')}"

            else:
                # 對於任何其他輸入，都當作回答進行分析
                # 先分析答案
                analysis_result = call_fast_agent_function(
                    "analyze_answer",
                    user_answer=user_message,
                    question="面試問題",
                    standard_answer="標準答案",
                )

                # 再獲取標準答案
                standard_result = call_fast_agent_function("get_standard_answer")

                # 組合結果
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

        except Exception as e:
            return f"Fast Agent 處理失敗: {str(e)}"

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


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)
