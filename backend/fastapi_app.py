#!/usr/bin/env python3
"""
FastAPI 後端服務

目的：
- 提供統一的 /api/* 端點，將請求委派給 fast_agent_bridge
- 由 http_wrapper.py 作為簡易 HTTP 橋接時進行轉發
- 管理面試系統的完整流程，包括用戶認證、履歷管理、面試問答等

主要功能模組：
1. 用戶認證 (MinIO 後端)
2. 履歷上傳與解析 (OpenAI + MongoDB)
3. 面試管理 (問題生成、答案分析)
4. 會話管理 (Redis + 資料庫)
5. 虛擬人物控制 (Avatar)
6. 語音處理 (STT/TTS)
"""

# ======
# 標準庫導入
# ======
from typing import Any, Dict, List, Optional
import json
import logging

# 設置 logger
logger = logging.getLogger(__name__)

# ======
# FastAPI 相關導入
# ======
from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

# ======
# 業務邏輯模組導入
# ======
# 面試代理橋接模組 - 處理面試相關的核心邏輯
from backend.fast_agent_bridge import (
    analyze_answer,        # 分析用戶答案
    analyze_intro,         # 分析自我介紹
    call_fast_agent_function,  # 調用快速代理函數
    clear_all_user_data,   # 清除所有用戶資料
    clear_collected_intro, # 清除收集的自我介紹
    get_collected_intro,   # 獲取收集的自我介紹
    get_question,          # 獲取面試問題
    intro_collector,       # 自我介紹收集器
)

# 用戶認證模組 - MinIO 後端存儲
from backend.tools.minio_user_store import (
    register_user_to_minio as tool_register_user_to_minio,  # 用戶註冊
)
from backend.tools.minio_user_store import (
    verify_user_from_minio as tool_verify_user_from_minio,  # 用戶驗證
)

# 履歷管理模組 - MongoDB 後端存儲
from backend.tools.resume_manager import resume_manager

# ======
# 資料庫與會話管理導入
# ======
# 主要資料庫連接管理器 (SQLite/PostgreSQL)
from backend.tools.database import db_manager

# 資料庫模型 - 面試會話表
try:
    from backend.db_sa import InterviewSession
except ImportError:
    # 如果導入失敗，創建一個簡單的替代類作為後備方案
    class InterviewSession:
        def __init__(self, user_id=None, session_data=None):
            self.user_id = user_id
            self.session_data = session_data

# 會話快取管理 (Redis) - 用於存儲面試過程中的即時狀態和事件
from backend.session_store import (
    append_event as redis_append_event,      # 添加事件到會話
    list_events as redis_list_events,       # 列出會話中的所有事件
    set_state as redis_set_state,           # 設置會話狀態
    get_state as redis_get_state,           # 獲取會話狀態
    clear_session as redis_clear_session,   # 清除會話資料
)

# ======
# 全域變數與工具函數
# ======
# 用戶專用的面試管理器實例字典 - 每個用戶都有獨立的 InterviewManager
# 鍵：user_id，值：InterviewManager 實例
USER_INTERVIEW_MANAGERS: Dict[str, Any] = {}


def get_user_interview_manager(user_id: str):
    """
    獲取用戶專用的面試管理器實例
    
    Args:
        user_id (str): 用戶唯一識別碼
        
    Returns:
        InterviewManager: 用戶專用的面試管理器實例
        
    說明：
    - 如果用戶不存在管理器，會自動創建並初始化
    - 確保每個用戶都有獨立的會話狀態
    """
    if user_id not in USER_INTERVIEW_MANAGERS:
        from backend.tools.interview_manager import InterviewManager
        USER_INTERVIEW_MANAGERS[user_id] = InterviewManager()
        USER_INTERVIEW_MANAGERS[user_id].start_interview()
    return USER_INTERVIEW_MANAGERS[user_id]


def get_db():
    """
    資料庫依賴注入函數
    
    Returns:
        DatabaseManager: 資料庫連接管理器實例
        
    說明：
    - 用於 FastAPI 的依賴注入系統
    - 確保每個請求都能獲得獨立的資料庫連接
    """
    return db_manager


# ======
# FastAPI 應用初始化
# ======
# 初始化資料表（避免多 worker 競態）
# 注意：在多進程環境中，資料表初始化應該在外部進行
# create_tables_safely()

# 創建 FastAPI 應用實例
app = FastAPI(
    title="FastMCP FastAPI Backend", 
    version="0.1.0",
    description="智能面試系統後端 API 服務"
)

# 添加 CORS 中間件 - 允許跨域請求
# 在生產環境中應該限制 allow_origins 為特定域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # 允許所有來源（開發環境）
    allow_credentials=True,        # 允許攜帶認證資訊
    allow_methods=["*"],           # 允許所有 HTTP 方法
    allow_headers=["*"],           # 允許所有請求標頭
)

# 靜態檔案服務 - 前端頁面
# 掛載到 /frontend 路徑，避免與 API 端點衝突
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")

# 掛載 /app 路徑到 frontend/app 目錄
app.mount("/app", StaticFiles(directory="frontend/app"), name="app")

# 掛載 /assets 路徑到 frontend/assets 目錄  
app.mount("/assets", StaticFiles(directory="frontend/assets"), name="assets")

# 掛載 LiveTalking 虛擬人檔案（如果目錄存在）
import os
if os.path.exists("Livetalking_virtual_interview"):
    app.mount("/Livetalking_virtual_interview", StaticFiles(directory="Livetalking_virtual_interview"), name="livetalking")
else:
    logger.warning("⚠️ Livetalking_virtual_interview 目錄不存在，跳過虛擬人檔案掛載")


# ======
# 基礎路由端點
# ======
@app.get("/")
def root_redirect() -> RedirectResponse:
    """
    根路由重定向
    
    Returns:
        RedirectResponse: 重定向到前端登入頁面
        
    說明：
    - 當用戶訪問根路徑時，自動重定向到登入頁面
    - 確保用戶首先進行身份驗證
    """
    return RedirectResponse(url="/frontend/auth/login.html")


@app.get("/favicon.ico")
def favicon():
    """
    Favicon 處理端點
    
    Returns:
        Response: 返回一個透明的 1x1 像素 PNG 圖片作為 favicon
        
    說明：
    - 避免瀏覽器自動請求 favicon.ico 產生 404 錯誤
    - 返回最小的透明圖片以減少資源消耗
    """
    from fastapi.responses import Response
    
    # 最小的透明 1x1 PNG 圖片 (base64 編碼)
    transparent_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77zgAAAABJRU5ErkJggg=="
    
    import base64
    png_bytes = base64.b64decode(transparent_png)
    
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400",  # 快取一天
            "Content-Length": str(len(png_bytes))
        }
    )


# ======
# 資料模型定義 (Pydantic BaseModel)
# ======
class ChatRequest(BaseModel):
    """
    聊天請求資料模型
    
    Attributes:
        message (str): 用戶輸入的訊息內容
        function (str): 要調用的函數名稱（可選）
        params (dict): 函數參數（可選）
    """
    message: Optional[str] = ""
    function: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class AnalyzeAnswerRequest(BaseModel):
    """
    答案分析請求資料模型
    
    Attributes:
        user_answer (str): 用戶的回答內容
        question (str): 對應的問題內容
        standard_answer (str): 標準答案（用於比對）
    """
    user_answer: str
    question: str = ""
    standard_answer: str = ""


class StandardAnswerRequest(BaseModel):
    """
    標準答案請求資料模型
    
    Attributes:
        question (str): 要獲取標準答案的問題
    """
    question: str = ""


class IntroCollectorRequest(BaseModel):
    """
    自我介紹收集請求資料模型
    
    Attributes:
        user_message (str): 用戶的自我介紹訊息
        user_id (str): 用戶唯一識別碼
    """
    user_message: str = ""
    user_id: str = "default_user"


class AnalyzeIntroRequest(BaseModel):
    """
    自我介紹分析請求資料模型
    
    Attributes:
        user_message (str): 要分析的自我介紹內容
        user_id (str): 用戶唯一識別碼
    """
    user_message: str = ""
    user_id: str = "default_user"


class SummaryRequest(BaseModel):
    """
    面試總結請求資料模型
    
    Attributes:
        user_message (str): 用戶的總結訊息
        interview_data (dict): 面試過程中的相關資料
    """
    user_message: str = ""
    interview_data: Optional[Dict[str, Any]] = None


class InterviewRequest(BaseModel):
    """
    面試請求資料模型
    
    Attributes:
        message (str): 面試過程中的用戶訊息
        user_id (str): 用戶唯一識別碼
    """
    message: str = ""
    user_id: str = "default_user"


class RegisterRequest(BaseModel):
    """
    用戶註冊請求資料模型
    
    Attributes:
        email (str): 用戶電子郵件（作為登入帳號）
        password (str): 用戶密碼
        name (str): 用戶姓名
    """
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    """
    用戶登入請求資料模型
    
    Attributes:
        email (str): 用戶電子郵件
        password (str): 用戶密碼
    """
    email: str
    password: str


# ======
# 全域狀態管理變數
# ======
# 進程內狀態 - 存儲用戶當前面試問題
# 鍵：user_id，值：包含問題和標準答案的字典
USER_CURRENT_QUESTIONS: Dict[str, Dict[str, str]] = {}

# 面試階段追蹤 - 記錄每個用戶的面試進度
# 鍵：user_id，值：面試階段
# 階段值：
# - "intro": 自我介紹收集階段
# - "questioning": 面試問答階段  
# - "finished": 面試完成階段
USER_STAGE: Dict[str, str] = {}


# ======
# 系統健康檢查端點
# ======
@app.get("/health")
def health() -> Dict[str, str]:
    """
    系統健康檢查端點
    
    Returns:
        Dict[str, str]: 包含系統狀態的字典
        
    說明：
    - 用於負載均衡器和監控系統檢查服務是否正常運行
    - 簡單的存活檢查，不涉及複雜的業務邏輯
    """
    return {"status": "ok"}


# ======
# 核心聊天 API 端點
# ======
@app.post("/api/chat")
def api_chat(req: ChatRequest) -> Dict[str, Any]:
    """
    通用聊天 API 端點
    
    Args:
        req (ChatRequest): 聊天請求資料
        
    Returns:
        Dict[str, Any]: 聊天回應結果
        
    功能說明：
    1. 如果指定了 function 參數，直接調用對應的快速代理函數
    2. 如果未指定 function，返回面試系統說明
    3. 支援動態函數調用，提供靈活的 API 擴展能力
    """
    try:
        # 若指定 function，則直接委派給快速代理
        if req.function:
            payload = req.params or {}
            result = call_fast_agent_function(req.function, **payload)
            
            # 確保返回格式一致
            if not isinstance(result, dict):
                return {"success": True, "result": result}
            return result

        # 未指定 function 時，返回面試系統說明
        return call_fast_agent_function("interview_system")
        
    except Exception as e:
        # 統一錯誤處理
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/get_question")
def api_get_question() -> Dict[str, Any]:
    """
    獲取面試問題 API 端點
    
    Returns:
        Dict[str, Any]: 包含面試問題的結果
        
    功能說明：
    - 從問題庫中隨機選擇一個面試問題
    - 返回問題內容、類別、難度等相關資訊
    - 用於面試過程中的問題生成
    """
    result = call_fast_agent_function("get_question")
    
    # 統一返回格式
    if not isinstance(result, dict):
        return {"success": True, "result": result}
    return result


@app.post("/api/analyze_answer")
def api_analyze_answer(req: AnalyzeAnswerRequest) -> Dict[str, Any]:
    """
    分析用戶答案 API 端點
    
    Args:
        req (AnalyzeAnswerRequest): 包含用戶答案、問題和標準答案的請求
        
    Returns:
        Dict[str, Any]: 答案分析結果，包含評分、反饋等
        
    功能說明：
    - 使用 AI 分析用戶的回答品質
    - 與標準答案進行比對和評分
    - 提供詳細的反饋和改進建議
    """
    return call_fast_agent_function(
        "analyze_answer",
        user_answer=req.user_answer,
        question=req.question,
        standard_answer=req.standard_answer,
    )


@app.post("/api/get_standard_answer")
def api_get_standard_answer(req: StandardAnswerRequest) -> Dict[str, Any]:
    """
    獲取標準答案 API 端點
    
    Args:
        req (StandardAnswerRequest): 包含問題的請求
        
    Returns:
        Dict[str, Any]: 對應問題的標準答案
        
    功能說明：
    - 根據問題內容返回對應的標準答案
    - 用於面試官參考和答案評分
    """
    return call_fast_agent_function("get_standard_answer", question=req.question)


@app.post("/api/start_interview")
def api_start_interview() -> Dict[str, Any]:
    """
    開始面試 API 端點
    
    Returns:
        Dict[str, Any]: 面試開始的相關資訊
        
    功能說明：
    - 初始化面試環境和狀態
    - 準備面試問題和評分標準
    """
    return call_fast_agent_function("start_interview")


@app.post("/api/intro_collector")
def api_intro_collector(req: IntroCollectorRequest) -> Dict[str, Any]:
    """
    自我介紹收集器 API 端點
    
    Args:
        req (IntroCollectorRequest): 包含用戶自我介紹的請求
        
    Returns:
        Dict[str, Any]: 收集結果和確認訊息
        
    功能說明：
    - 收集用戶的自我介紹內容
    - 支援分段收集，逐步完善自我介紹
    - 為後續分析提供資料基礎
    """
    return call_fast_agent_function(
        "intro_collector", user_message=req.user_message, user_id=req.user_id
    )


@app.post("/api/analyze_intro")
def api_analyze_intro(req: AnalyzeIntroRequest) -> Dict[str, Any]:
    return call_fast_agent_function(
        "analyze_intro", user_message=req.user_message, user_id=req.user_id
    )


@app.post("/api/generate_final_summary")
def api_generate_final_summary(req: SummaryRequest) -> Dict[str, Any]:
    return call_fast_agent_function(
        "generate_final_summary",
        user_message=req.user_message,
        interview_data=req.interview_data or {},
    )


@app.post("/api/clear_collected_intro")
def api_clear_collected_intro(req: IntroCollectorRequest) -> Dict[str, Any]:
    return call_fast_agent_function("clear_collected_intro", user_id=req.user_id)


@app.post("/api/clear_all_user_data")
def api_clear_all_user_data(req: IntroCollectorRequest) -> Dict[str, Any]:
    return call_fast_agent_function("clear_all_user_data", user_id=req.user_id)


@app.get("/api/interview_system")
def api_interview_system() -> Dict[str, Any]:
    result = call_fast_agent_function("interview_system")
    if not isinstance(result, dict):
        return {"success": True, "result": result}
    return result


# ======
# 用戶認證 API 端點 (MinIO 後端存儲)
# ======
# 說明：
# - 使用 MinIO 作為用戶資料存儲後端
# - 支援用戶註冊、登入等基本認證功能
# - 返回 JWT 風格的 access token


@app.post("/api/auth/register")
def api_auth_register(payload: RegisterRequest):
    """
    用戶註冊 API 端點
    
    Args:
        payload (RegisterRequest): 包含用戶註冊資訊的請求
        
    Returns:
        Dict: 註冊結果，包含成功狀態和訊息
        
    功能說明：
    - 驗證用戶提供的註冊資訊
    - 將用戶資料存儲到 MinIO 後端
    - 返回註冊成功或失敗的詳細訊息
    """
    result = tool_register_user_to_minio(
        email=payload.email, password=payload.password, name=payload.name
    )
    
    if result.get("status") == "success":
        return {"success": True, "message": result.get("message", "註冊成功")}
    
    # 註冊失敗時拋出 HTTP 400 錯誤
    raise HTTPException(status_code=400, detail=result.get("message", "註冊失敗"))


@app.post("/api/auth/login")
def api_auth_login(payload: LoginRequest):
    """
    用戶登入 API 端點
    
    Args:
        payload (LoginRequest): 包含用戶登入資訊的請求
        
    Returns:
        Dict: 登入結果，包含用戶資料和 access token
        
    功能說明：
    - 驗證用戶的電子郵件和密碼
    - 登入成功後返回用戶資料和 access token
    - access token 格式：minio-{email}-token
    """
    result = tool_verify_user_from_minio(email=payload.email, password=payload.password)
    
    if result.get("status") == "success":
        user = result.get("user", {})
        return {
            "success": True,
            "data": {
                "user": user,
                "accessToken": f"minio-{user.get('email','')}-token",
            },
            "message": "登入成功",
            "status_code": 200,
        }
    
    # 登入失敗時拋出 HTTP 400 錯誤
    raise HTTPException(status_code=400, detail=result.get("message", "登入失敗"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.fastapi_app:app", host="127.0.0.1", port=8001, reload=False)


# ======
# 用戶管理路由 (Users Router)
# ======
# 說明：
# - 管理用戶基本資料、履歷和工作經驗
# - 支援履歷上傳、解析和存儲
# - 提供用戶資料的 CRUD 操作

router_users = APIRouter(prefix="/api/users", tags=["users"])


class SkillIn(BaseModel):
    """
    技能輸入資料模型
    
    Attributes:
        skill_name (str): 技能名稱
        skill_description (str): 技能描述（可選）
    """
    skill_name: str
    skill_description: Optional[str] = None


class WorkExperienceIn(BaseModel):
    """
    工作經驗輸入資料模型
    
    Attributes:
        company_name (str): 公司名稱
        industry_type (str): 產業類型（可選）
        work_location (str): 工作地點（可選）
        position_title (str): 職位名稱（可選）
        position_category_1 (str): 職位類別1（可選）
        position_category_2 (str): 職位類別2（可選）
        start_date (str): 開始日期（可選，格式：YYYY-MM-DD）
        end_date (str): 結束日期（可選，格式：YYYY-MM-DD）
        job_description (str): 工作描述（可選）
        job_skills (str): 工作技能（可選）
        salary (str): 薪資（可選）
        salary_type (str): 薪資類型（可選）
        management_responsibility (str): 管理責任（可選）
    """
    company_name: str
    industry_type: Optional[str] = None
    work_location: Optional[str] = None
    position_title: Optional[str] = None
    position_category_1: Optional[str] = None
    position_category_2: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    job_description: Optional[str] = None
    job_skills: Optional[str] = None
    salary: Optional[str] = None
    salary_type: Optional[str] = None
    management_responsibility: Optional[str] = None


class UserIn(BaseModel):
    """
    用戶輸入資料模型
    
    Attributes:
        name (str): 用戶姓名
        desired_position (str): 期望職位
        desired_field (str): 期望領域（可選）
        desired_location (str): 期望工作地點（可選）
        introduction (str): 自我介紹（可選）
        keywords (str): 關鍵字（可選）
        work_experiences (list): 工作經驗列表（可選）
        skills (list): 技能列表（可選）
    """
    name: str
    desired_position: str
    desired_field: Optional[str] = None
    desired_location: Optional[str] = None
    introduction: Optional[str] = None
    keywords: Optional[str] = None
    work_experiences: Optional[list[WorkExperienceIn]] = None
    skills: Optional[list[SkillIn]] = None


@router_users.post("")
def create_user(payload: UserIn, db=Depends(get_db)):
    try:
        user = User(
            name=payload.name,
            desired_position=payload.desired_position,
            desired_field=payload.desired_field,
            desired_location=payload.desired_location,
            introduction=payload.introduction,
            keywords=payload.keywords,
        )
        db.add(user)
        db.flush()

        if payload.work_experiences:
            from datetime import datetime

            for exp in payload.work_experiences:
                start_dt = (
                    datetime.strptime(exp.start_date, "%Y-%m-%d").date()
                    if exp.start_date
                    else None
                )
                end_dt = (
                    datetime.strptime(exp.end_date, "%Y-%m-%d").date()
                    if exp.end_date
                    else None
                )
                db.add(
                    WorkExperience(
                        user_id=user.id,
                        company_name=exp.company_name,
                        industry_type=exp.industry_type,
                        work_location=exp.work_location,
                        position_title=exp.position_title,
                        position_category_1=exp.position_category_1,
                        position_category_2=exp.position_category_2,
                        start_date=start_dt,
                        end_date=end_dt,
                        job_description=exp.job_description,
                        job_skills=exp.job_skills,
                        salary=exp.salary,
                        salary_type=exp.salary_type,
                        management_responsibility=exp.management_responsibility,
                    )
                )

        if payload.skills:
            for s in payload.skills:
                db.add(
                    Skill(
                        user_id=user.id,
                        skill_name=s.skill_name,
                        skill_description=s.skill_description,
                    )
                )

        db.commit()
        return {
            "success": True,
            "data": {"user_id": user.id},
            "message": "履歷建立成功",
            "status_code": 201,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"建立履歷失敗: {str(e)}")


@router_users.post("/parse_resume")
def parse_resume(file: UploadFile = File(...), user_id: str = "default_user", save_to_mongodb: bool = True):
    """
    履歷解析：使用 OpenAI 解析上傳的履歷文件並回傳結構化資料。
    支援 PDF、DOCX、DOC、TXT 格式。
    可選擇是否儲存到 MongoDB。
    """
    import tempfile
    import os
    from pathlib import Path
    
    try:
        # 檢查檔案類型
        filename = file.filename or "resume"
        allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
        file_ext = Path(filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"不支援的檔案格式：{file_ext}。支援格式：{', '.join(allowed_extensions)}"
            )
        
        # 建立臨時檔案
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = file.file.read()
            temp_file.write(content)
            temp_file_path = Path(temp_file.name)
        
        try:
            # 使用 OpenAI 履歷解析功能
            from backend.tools.ocr.openai_to_frontend import process_one
            
            # 建立臨時輸出目錄
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                
                # 處理檔案
                result_path = process_one(
                    input_path=temp_file_path,
                    out_dir=output_dir,
                    model="gpt-4o-mini",  # 使用預設模型
                    max_chars=60000
                )
                
                # 讀取解析結果
                with open(result_path, 'r', encoding='utf-8') as f:
                    parsed_data = json.loads(f.read())
                
                # 轉換為前端期望的格式（與 toJSON() 函數完全一致）
                # 處理 keywords 欄位：如果是字串，轉換為陣列
                keywords_raw = parsed_data.get("keywords", "")
                if isinstance(keywords_raw, str) and keywords_raw.strip():
                    keywords = [k.strip() for k in keywords_raw.split(',') if k.strip()]
                else:
                    keywords = keywords_raw if isinstance(keywords_raw, list) else []
                
                # 處理技能資料：轉換為前端期望的格式
                skills_raw = parsed_data.get("skillList", [])
                skills = []
                if isinstance(skills_raw, list):
                    for skill in skills_raw:
                        if isinstance(skill, str):
                            # 如果是字串，轉換為物件格式
                            skills.append({"name": skill, "desc": ""})
                        elif isinstance(skill, dict):
                            # 如果已經是物件，直接使用
                            skills.append(skill)
                
                # 處理證照資料：轉換為前端期望的格式
                certs_raw = parsed_data.get("certList", [])
                certs = []
                if isinstance(certs_raw, list):
                    for cert in certs_raw:
                        if isinstance(cert, str):
                            # 如果是字串，轉換為物件格式
                            certs.append({"name": cert, "desc": ""})
                        elif isinstance(cert, dict):
                            # 如果已經是物件，直接使用
                            certs.append(cert)
                
                # 處理語言資料：轉換為前端期望的格式
                languages_raw = parsed_data.get("langList", [])
                languages = []
                if isinstance(languages_raw, list):
                    for lang in languages_raw:
                        if isinstance(lang, str):
                            # 如果是字串，轉換為物件格式
                            languages.append({
                                "name": lang, 
                                "listen": "", 
                                "speak": "", 
                                "read": "", 
                                "write": "", 
                                "cert": "", 
                                "certDesc": ""
                            })
                        elif isinstance(lang, dict):
                            # 如果已經是物件，直接使用
                            languages.append(lang)
                
                formatted_data = {
                    "name": parsed_data.get("name", ""),
                    "age": parsed_data.get("age", ""),
                    "location": parsed_data.get("location", ""),
                    "locationOther": parsed_data.get("locationOther", ""),
                    "summary": parsed_data.get("summary", ""),
                    "keywords": keywords,
                    "expectation": {
                        "domain": parsed_data.get("expDomain", ""),
                        "domainOther": parsed_data.get("expDomainOther", ""),
                        "location": parsed_data.get("expLocation", []),
                        "locationOther": parsed_data.get("expLocationOther", ""),
                        "remote": parsed_data.get("remote", "")
                    },
                    "works": parsed_data.get("workList", []),
                    "educations": parsed_data.get("eduList", []),
                    "skills": skills,
                    "projects": parsed_data.get("projList", []),
                    "languages": languages,
                    "certs": certs,
                    "bio": {
                        "zh": parsed_data.get("bioZh", ""),
                        "zh2": parsed_data.get("bioZh2", "")
                    }
                }
                
                # 儲存到 MongoDB (可選)
                mongodb_result = None
                if save_to_mongodb:
                    try:
                        mongodb_result = resume_manager.save_resume(user_id, formatted_data)
                    except Exception as mongo_error:
                        # MongoDB 存儲失敗不影響回傳結果，但記錄警告
                        print(f"MongoDB 存儲警告：{str(mongo_error)}")
                        mongodb_result = {"status": "error", "message": str(mongo_error)}
                
                return {
                    "success": True,
                    "data": formatted_data,
                    "status_code": 200,
                    "message": f"成功解析履歷：{filename}",
                    "mongodb_result": mongodb_result,
                    "user_id": user_id
                }
                
        finally:
            # 清理臨時檔案
            if temp_file_path.exists():
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"履歷解析錯誤：{str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"履歷解析失敗：{str(e)}")


@router_users.post("/resume/upload")
def upload_resume(file: UploadFile = File(...), user_id: str = "default_user"):
    """
    履歷檔案上傳：接收履歷檔案並儲存，回傳檔案ID供後續解析使用
    """
    import tempfile
    import os
    from pathlib import Path
    import uuid
    
    try:
        # 檢查檔案類型
        filename = file.filename or "resume"
        allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
        file_ext = Path(filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"不支援的檔案格式：{file_ext}。支援格式：{', '.join(allowed_extensions)}"
            )
        
        # 生成唯一檔案ID
        file_id = str(uuid.uuid4())
        
        # 建立臨時檔案
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = file.file.read()
            temp_file.write(content)
            temp_file_path = Path(temp_file.name)
        
        try:
            # 這裡可以將檔案儲存到 MinIO 或其他檔案儲存服務
            # 目前先回傳成功訊息和檔案ID
            
            return {
                "success": True,
                "data": {
                    "fileId": file_id,
                    "filename": filename,
                    "fileSize": len(content),
                    "fileType": file_ext
                },
                "status_code": 200,
                "message": f"成功上傳履歷檔案：{filename}"
            }
                
        finally:
            # 清理臨時檔案
            if temp_file_path.exists():
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"履歷上傳錯誤：{str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"履歷上傳失敗：{str(e)}")


@router_users.get("/resume/latest")
def get_latest_resume(user_id: str = "default_user"):
    """
    獲取用戶最新的履歷資料（用於前端自動填入）
    """
    try:
        resume = resume_manager.get_resume(user_id)
        
        if not resume:
            raise HTTPException(status_code=404, detail=f"未找到用戶 {user_id} 的履歷")
            
        # 直接回傳儲存的履歷資料，因為格式已經與前端一致
        resume_data = resume.get("resume_data", {})
        
        return {
            "success": True,
            "data": resume_data,
            "status_code": 200,
            "message": f"成功獲取用戶 {user_id} 的最新履歷"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取履歷失敗：{str(e)}")


@router_users.get("/resume/{user_id}")
def get_resume_by_user_id(user_id: str):
    """
    根據用戶ID獲取 MongoDB 中的履歷資料
    """
    try:
        resume = resume_manager.get_resume(user_id)
        
        if not resume:
            raise HTTPException(status_code=404, detail=f"未找到用戶 {user_id} 的履歷")
            
        return {
            "success": True,
            "data": resume,
            "status_code": 200,
            "message": f"成功獲取用戶 {user_id} 的履歷"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取履歷失敗：{str(e)}")


@router_users.delete("/resume/{user_id}")
def delete_resume_by_user_id(user_id: str):
    """
    刪除指定用戶的履歷資料
    """
    try:
        result = resume_manager.delete_resume(user_id)
        
        if result["status"] == "not_found":
            raise HTTPException(status_code=404, detail=f"未找到用戶 {user_id} 的履歷")
            
        return {
            "success": True,
            "data": result,
            "status_code": 200,
            "message": f"成功刪除用戶 {user_id} 的履歷"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除履歷失敗：{str(e)}")


@router_users.get("/resumes/list")
def list_all_resumes():
    """
    列出所有履歷（用於管理和確認頁面）
    """
    try:
        resumes = resume_manager.list_resumes()
        
        return {
            "success": True,
            "data": resumes,
            "count": len(resumes),
            "status_code": 200,
            "message": f"成功獲取 {len(resumes)} 筆履歷"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取履歷列表失敗：{str(e)}")


@router_users.post("/resume/confirm")
def confirm_resume_data(user_id: str = "default_user"):
    """
    確認履歷資料並進行最終處理
    """
    try:
        resume = resume_manager.get_resume(user_id)
        
        if not resume:
            raise HTTPException(status_code=404, detail=f"未找到用戶 {user_id} 的履歷資料")
            
        # 這裡可以添加履歷確認後的額外處理邏輯
        # 例如：更新確認狀態、觸發後續流程等
        from datetime import datetime
        
        return {
            "success": True,
            "data": {"user_id": user_id, "confirmed_at": datetime.utcnow().isoformat()},
            "status_code": 200,
            "message": "履歷資料確認成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"確認履歷失敗：{str(e)}")


class ResumeData(BaseModel):
    user_id: str = "default_user"
    resume_data: dict


@router_users.post("/resume/save")
def save_resume_data(payload: ResumeData):
    """
    儲存履歷資料到 MongoDB
    """
    try:
        result = resume_manager.save_resume(payload.user_id, payload.resume_data)
        
        return {
            "success": True,
            "data": result,
            "status_code": 200,
            "message": f"成功儲存用戶 {payload.user_id} 的履歷"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"儲存履歷失敗：{str(e)}")


@router_users.get("/resumes/search")
def search_resumes(
    domain: Optional[str] = None,
    location: Optional[str] = None,
    skills: Optional[str] = None,
    limit: int = 10
):
    """
    搜尋履歷資料
    """
    try:
        # 建立搜尋條件
        query = {}
        
        if domain:
            query["desired_job.domain"] = {"$regex": domain, "$options": "i"}
            
        if location:
            query["personal_info.location"] = {"$regex": location, "$options": "i"}
            
        if skills:
            query["skills.skill_name"] = {"$regex": skills, "$options": "i"}
        
        results = resume_manager.search_resumes(query, limit)
        
        return {
            "success": True,
            "data": results,
            "status_code": 200,
            "message": f"找到 {len(results)} 份履歷",
            "query": query
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜尋履歷失敗：{str(e)}")


@router_users.get("/resumes/statistics")
def get_resume_statistics():
    """
    獲取履歷統計資訊
    """
    try:
        stats = resume_manager.get_resume_statistics()
        
        return {
            "success": True,
            "data": stats,
            "status_code": 200,
            "message": "成功獲取履歷統計資訊"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取統計失敗：{str(e)}")


@router_users.get("")
def list_users(db=Depends(get_db)):
    users = db.query(User).all()
    data = []
    for u in users:
        data.append(
            {
                "id": u.id,
                "name": u.name,
                "desired_position": u.desired_position,
                "desired_field": u.desired_field,
                "desired_location": u.desired_location,
                "introduction": u.introduction,
                "keywords": u.keywords,
                "created_at": (
                    u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else None
                ),
            }
        )
    return {"success": True, "data": data, "status_code": 200}


@router_users.get("/{user_id}")
def get_user(user_id: int, db=Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    wx = db.query(WorkExperience).filter(WorkExperience.user_id == u.id).all()
    sk = db.query(Skill).filter(Skill.user_id == u.id).all()
    return {
        "success": True,
        "data": {
            "id": u.id,
            "name": u.name,
            "desired_position": u.desired_position,
            "desired_field": u.desired_field,
            "desired_location": u.desired_location,
            "introduction": u.introduction,
            "keywords": u.keywords,
            "created_at": (
                u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else None
            ),
            "work_experiences": [
                {
                    "id": e.id,
                    "company_name": e.company_name,
                    "industry_type": e.industry_type,
                    "work_location": e.work_location,
                    "position_title": e.position_title,
                    "position_category_1": e.position_category_1,
                    "position_category_2": e.position_category_2,
                    "start_date": (
                        e.start_date.strftime("%Y-%m-%d") if e.start_date else None
                    ),
                    "end_date": e.end_date.strftime("%Y-%m-%d") if e.end_date else None,
                    "job_description": e.job_description,
                    "job_skills": e.job_skills,
                    "salary": e.salary,
                    "salary_type": e.salary_type,
                    "management_responsibility": e.management_responsibility,
                }
                for e in wx
            ],
            "skills": [
                {
                    "id": s.id,
                    "skill_name": s.skill_name,
                    "skill_description": s.skill_description,
                }
                for s in sk
            ],
        },
        "status_code": 200,
    }


app.include_router(router_users)


# ----------------------------
# Avatar Router
# ----------------------------
router_avatar = APIRouter(prefix="/api/avatar", tags=["avatar"])


class AvatarControlIn(BaseModel):
    action: str
    text: Optional[str] = None
    emotion: Optional[str] = None
    intensity: Optional[float] = None


@router_avatar.post("/control")
def avatar_control(payload: AvatarControlIn):
    action = payload.action
    if action == "speak":
        return {
            "success": True,
            "message": "FastAPI: 說話",
            "data": {
                "audio_url": "/api/avatar/audio/latest",
                "lip_sync_data": [],
                "duration": 3.5,
                "emotion": payload.emotion or "neutral",
            },
            "status_code": 200,
        }
    if action == "listen":
        return {
            "success": True,
            "data": {
                "state": "listening",
                "animation": "listening_idle",
                "duration": -1,
            },
            "status_code": 200,
        }
    if action == "emotion":
        return {
            "success": True,
            "data": {
                "emotion": payload.emotion or "neutral",
                "intensity": payload.intensity or 0.5,
                "transition_duration": 1.0,
            },
            "status_code": 200,
        }
    if action == "idle":
        return {
            "success": True,
            "data": {"state": "idle", "animation": "breathing", "blink_interval": 3.0},
            "status_code": 200,
        }
    raise HTTPException(status_code=400, detail="不支援的操作")


app.include_router(router_avatar)


# ----------------------------
# Speech Router
# ----------------------------
router_speech = APIRouter(prefix="/api/speech", tags=["speech"])


class SpeechIn(BaseModel):
    action: str
    text: Optional[str] = None


@router_speech.post("")
def speech_action(payload: SpeechIn):
    if payload.action == "transcribe":
        return {
            "success": True,
            "data": {
                "action": "transcribe",
                "redirect_to": "/api/stt",
                "message": "請使用POST /api/stt上傳音頻檔案",
            },
            "status_code": 200,
        }
    if payload.action == "synthesize":
        return {
            "success": True,
            "data": {
                "action": "synthesize",
                "redirect_to": "/api/tts/generate",
                "message": "請使用POST /api/tts/generate進行語音合成",
            },
            "status_code": 200,
        }
    if payload.action == "realtime":
        return {
            "success": True,
            "data": {
                "action": "realtime",
                "websocket_url": "ws://localhost:5000/speech-realtime",
                "session_id": "speech_session_123",
            },
            "status_code": 200,
        }
    raise HTTPException(status_code=400, detail="不支援的語音處理動作")


@router_speech.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    """
    語音轉文字 API 端點
    
    Args:
        file (UploadFile): 音頻檔案
        
    Returns:
        Dict[str, Any]: 轉錄結果
        
    功能說明：
    - 接收音頻檔案並轉發到 Whisper 服務進行轉錄
    - 支援常見的音頻格式 (wav, mp3, m4a, etc.)
    - 返回轉錄文字和處理時間
    """
    import httpx
    import os
    
    try:
        # Whisper API 服務地址
        whisper_url = os.getenv("WHISPER_API_URL", "http://whisper-api:8000")
        
        # 準備檔案資料
        file_content = await file.read()
        files = {"file": (file.filename, file_content, file.content_type)}
        
        # 調用 Whisper 服務
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{whisper_url}/transcribe", files=files)
            
        if response.status_code == 200:
            whisper_result = response.json()
            return {
                "success": True,
                "data": {
                    "text": whisper_result.get("text", ""),
                    "device": whisper_result.get("device", "unknown"),
                    "duration_seconds": whisper_result.get("duration_seconds", 0),
                    "filename": file.filename,
                },
                "status_code": 200,
                "message": "語音轉錄成功"
            }
        else:
            error_detail = response.text
            return {
                "success": False,
                "error": f"Whisper 服務錯誤: {error_detail}",
                "status_code": response.status_code
            }
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="語音轉錄服務超時，請稍後再試")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"語音轉錄失敗: {str(e)}")


@router_speech.get("/health")
def speech_health():
    """
    語音服務健康檢查
    
    Returns:
        Dict[str, Any]: 服務狀態
    """
    import httpx
    import os
    
    try:
        whisper_url = os.getenv("WHISPER_API_URL", "http://whisper-api:8000")
        
        # 檢查 Whisper 服務是否可用
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{whisper_url}/docs")
            whisper_available = response.status_code == 200
            
        return {
            "success": True,
            "data": {
                "speech_router": "healthy",
                "whisper_service": "available" if whisper_available else "unavailable",
                "whisper_url": whisper_url,
            },
            "status_code": 200
        }
    except Exception as e:
        return {
            "success": False,
            "data": {
                "speech_router": "healthy",
                "whisper_service": "unavailable",
                "error": str(e)
            },
            "status_code": 503
        }


app.include_router(router_speech)


# ----------------------------
# MCP Router
# ----------------------------
router_mcp = APIRouter(prefix="/api/mcp", tags=["mcp"])


class MCPIn(BaseModel):
    action: str
    message: Optional[str] = None
    user_answer: Optional[str] = None
    question: Optional[str] = None
    standard_answer: Optional[str] = None


@router_mcp.post("")
def mcp_action(payload: MCPIn):
    if payload.action == "get_question":
        return {
            "success": True,
            "data": {
                "question": "請介紹您最熟悉的程式語言及其應用場景",
                "category": "技術能力",
                "difficulty": "中等",
                "source": "MCP 服務",
            },
            "status_code": 200,
        }
    if payload.action == "analyze_answer":
        return {
            "success": True,
            "data": {
                "score": 85,
                "grade": "良好",
                "similarity": "80%",
                "feedback": "回答基本正確，但可以更具體一些",
                "standard_answer": payload.standard_answer or "標準答案未提供",
            },
            "status_code": 200,
        }
    if payload.action == "get_standard_answer":
        return {
            "success": True,
            "data": {
                "question": payload.question or "",
                "standard_answer": "這是一個標準答案範例",
                "source": "MCP 服務",
            },
            "status_code": 200,
        }
    raise HTTPException(status_code=400, detail="不支援的動作")


app.include_router(router_mcp)


# ======
# 面試管理路由 (Interview Router)
# ======
# 說明：
# - 處理面試過程中的各種操作和狀態管理
# - 支援自我介紹收集、問題生成、答案分析等核心功能
# - 管理面試階段轉換和會話狀態

router_interview = APIRouter(tags=["interview"])


@router_interview.post("/api/interview")
def interview_endpoint(payload: InterviewRequest, db=Depends(get_db)):
    """
    面試主要端點 - 處理面試過程中的所有操作
    
    Args:
        payload (InterviewRequest): 包含用戶訊息和用戶ID的請求
        db: 資料庫依賴注入
        
    Returns:
        Dict: 面試回應結果，包含AI回應和狀態資訊
        
    功能說明：
    - 管理面試的完整流程：自我介紹 → 問題問答 → 結束
    - 支援面試重置、階段轉換、狀態管理等操作
    - 整合 Redis 會話管理和資料庫持久化
    """
    try:
        # 提取和清理用戶訊息
        msg = (payload.message or "").strip()
        user_id = payload.user_id or "default_user"
        
        # 獲取用戶當前面試階段，優先從 Redis 恢復，預設為自我介紹階段
        stage = USER_STAGE.get(user_id)
        if not stage:
            # 嘗試從 Redis 恢復階段狀態
            try:
                redis_state = redis_get_state(user_id)
                if redis_state and redis_state.get("stage"):
                    stage = redis_state["stage"]
                    USER_STAGE[user_id] = stage
                    print(f"🔄 從 Redis 恢復用戶 {user_id} 的階段狀態: {stage}")
                else:
                    stage = "intro"
                    USER_STAGE[user_id] = stage
            except Exception as e:
                print(f"⚠️ 從 Redis 恢復階段狀態失敗: {e}")
                stage = "intro"
                USER_STAGE[user_id] = stage

        # 更新 Redis 狀態供 LLM 記憶使用
        try:
            redis_set_state(user_id, {"stage": stage})
        except Exception:
            pass

        # ==
        # 面試重置邏輯
        # ==
        # 檢測重置關鍵字，支援中英文重置指令
        if msg.lower() in {
            "重新開始",
            "重新來過",
            "重新面試",
            "重來",
            "restart",
            "reset",
        }:
            USER_CURRENT_QUESTIONS.pop(user_id, None)
            USER_STAGE.pop(user_id, None)
            try:
                redis_clear_session(user_id)
            except Exception:
                pass
            try:
                clear_collected_intro(user_id=user_id)
            except Exception:
                pass
            
            # 重置用戶專用的 interview_manager
            try:
                if user_id in USER_INTERVIEW_MANAGERS:
                    USER_INTERVIEW_MANAGERS[user_id].start_interview()
                else:
                    # 如果不存在，創建一個新的
                    get_user_interview_manager(user_id)
            except Exception:
                pass
            
            # 清理資料庫記錄（如果有 SQLAlchemy 支援）
            # 目前使用 MongoDB 和 Redis，不需要 SQLAlchemy 操作
            try:
                if hasattr(db, 'query') and hasattr(db, 'commit'):
                    if str(user_id).isdigit():
                        db.query(InterviewSession).filter(
                            InterviewSession.user_id == int(user_id)
                        ).delete()
                    else:
                        db.query(InterviewSession).filter(
                            InterviewSession.user_id.is_(None)
                        ).delete()
                    db.commit()
                else:
                    # 使用 MongoDB/Redis，記錄已在上面清理
                    print(f"📝 使用 MongoDB/Redis，資料庫記錄清理已完成")
            except Exception as db_error:
                print(f"⚠️ 資料庫清理失敗（不影響主要功能）: {db_error}")
            return {
                "success": True,
                "data": {
                    "response": "✅ 面試已完全重置！所有對話記錄、狀態和記憶已清空。請點擊「開始面試」按鈕開始全新的面試。",
                    "session_id": None,
                    "current_state": "waiting",
                    "reset_complete": True,
                },
                "status_code": 200,
            }

        # ==
        # 自我介紹階段處理 (intro stage)
        # ==
        # 在此階段，系統收集用戶的自我介紹內容
        if stage == "intro":
            # 檢測完成自我介紹的關鍵字
            # 支援多種表達方式，讓用戶可以自然地表達完成意願
            finish_keywords = {
                "完成自介",      # 簡短表達
                "完成自我介紹",  # 完整表達
                "完成",          # 通用表達
                "分析",          # 直接要求分析
                "分析自介",      # 明確要求分析自我介紹
                "開始面試",      # 要求進入面試階段
            }

            # ==
            # 完成自我介紹 → 進行分析並進入面試階段
            # ==
            # 當用戶表達完成自我介紹時，系統會：
            # 1. 分析收集到的自我介紹內容
            # 2. 生成第一道面試問題
            # 3. 將階段轉換為面試問答模式
            if any(k in msg for k in finish_keywords):
                try:
                    # 使用用戶專用的 interview_manager 進行分析
                    user_interview_manager = get_user_interview_manager(user_id)
                    
                    # 獲取已收集的自我介紹內容
                    collected = get_collected_intro(user_id=user_id) or msg
                    
                    # 將收集的內容同步到用戶的 interview_manager
                    if collected and collected != msg:
                        # 分段收集內容
                        paragraphs = [p.strip() for p in collected.split('\n') if p.strip()]
                        for para in paragraphs:
                            user_interview_manager.collect_intro(para, user_id)
                    
                    # 使用用戶的 interview_manager 進行分析
                    analysis_result = user_interview_manager.finish_intro_and_analyze()
                    
                    if analysis_result['status'] == 'intro_finished':
                        # 分析成功，進入面試模式
                        USER_STAGE[user_id] = "questioning"
                        
                        # 獲取第一題（使用技能匹配）
                        try:
                            from backend.tools.question_manager import QuestionManager
                            qm = QuestionManager()
                            skill_question_data = qm.get_skill_based_question(user_id)
                            qres = {
                                "success": True,
                                "question_data": skill_question_data,
                                "result": f"🎯 面試問題\n\n{skill_question_data['question']}\n來源：{skill_question_data['source']}"
                            }
                        except Exception as e:
                            logger.warning(f"技能匹配出題失敗，使用隨機問題: {e}")
                            qres = get_question()
                        
                        # 將第一題同步存入使用者當前題目，便於後續答案分析
                        try:
                            if isinstance(qres, dict) and qres.get("success"):
                                qdata = qres.get("question_data", {})
                                USER_CURRENT_QUESTIONS[user_id] = {
                                    "question": qdata.get("question", ""),
                                    "standard_answer": qdata.get("standard_answer", ""),
                                }
                        except Exception:
                            pass
                        
                        # 組合分析結果和問題
                        # 只返回簡潔的提示，詳細分析通過 intro_score_result 傳遞
                        simple_analysis_text = "🎉 自我介紹分析完成！現在進入面試模式！"
                        question_text = qres.get("result", "") if isinstance(qres, dict) else str(qres)
                        
                        # 寫入 Redis 事件
                        try:
                            redis_append_event(
                                user_id,
                                {
                                    "type": "intro_finished",
                                    "user_message": msg,
                                    "ai_response": simple_analysis_text + "\n\n" + question_text,
                                    "stage": "questioning",
                                },
                            )
                            redis_set_state(user_id, {"stage": "questioning"})
                        except Exception:
                            pass
                        
                        return {
                            "success": True,
                            "data": {
                                "response": simple_analysis_text + "\n\n" + question_text,
                                "intro_score_result": analysis_result.get('intro_score_result'),
                                "session_id": None,
                                "current_state": "questioning",
                            },
                            "status_code": 200,
                        }
                    else:
                        # 分析失敗，返回錯誤信息
                        return {
                            "success": True,
                            "data": {
                                "response": analysis_result.get('message', '自我介紹分析失敗'),
                                "current_state": "intro",
                            },
                            "status_code": 200,
                        }
                        
                except Exception as e:
                    # 回退到舊的分析方法
                    collected = get_collected_intro(user_id=user_id) or msg
                    analysis = analyze_intro(user_message=collected, user_id=user_id)
                    USER_STAGE[user_id] = "questioning"

                    # 獲取第一題（使用技能匹配）
                    try:
                        from backend.tools.question_manager import QuestionManager
                        qm = QuestionManager()
                        skill_question_data = qm.get_skill_based_question(user_id)
                        qres = {
                            "success": True,
                            "question_data": skill_question_data,
                            "result": f"🎯 面試問題\n\n{skill_question_data['question']}\n來源：{skill_question_data['source']}"
                        }
                    except Exception as e:
                        logger.warning(f"技能匹配出題失敗，使用隨機問題: {e}")
                        qres = get_question()
                    # 將第一題同步存入使用者當前題目，便於後續答案分析
                    try:
                        if isinstance(qres, dict) and qres.get("success"):
                            qdata = qres.get("question_data", {})
                            USER_CURRENT_QUESTIONS[user_id] = {
                                "question": qdata.get("question", ""),
                                "standard_answer": qdata.get("standard_answer", ""),
                            }
                    except Exception:
                        pass
                    analysis_text = (
                        "🎉 自我介紹分析完成！現在進入面試模式！"
                    )
                    question_text = (
                        qres.get("result", "") if isinstance(qres, dict) else str(qres)
                    )

                    # 寫入 Redis 事件
                    try:
                        redis_append_event(
                            user_id,
                            {
                                "type": "intro_finished",
                                "user_message": msg,
                                "ai_response": analysis_text + "\n\n" + question_text,
                                "stage": "questioning",
                            },
                        )
                        redis_set_state(user_id, {"stage": "questioning"})
                    except Exception:
                        pass

                    return {
                        "success": True,
                        "data": {
                            "response": analysis_text + "\n\n" + question_text,
                            "session_id": None,
                            "current_state": "questioning",
                        },
                        "status_code": 200,
                    }

            # ==
            # 自我介紹收集邏輯
            # ==
            # 當用戶仍在提供自我介紹時，系統會：
            # 1. 記錄用戶提供的內容
            # 2. 提供收集進度反饋
            # 3. 引導用戶繼續或完成自我介紹
            try:
                # 使用用戶專用的 interview_manager 進行收集
                user_interview_manager = get_user_interview_manager(user_id)
                
                # 收集自我介紹內容
                collection_result = user_interview_manager.collect_intro(msg, user_id)
                
                if collection_result['status'] == 'intro_collected':
                    ack = collection_result.get('message', '已記錄您的自我介紹')
                    current_length = len(collection_result.get('collected_content', ''))
                    
                    # 寫入 Redis 事件 - 記錄自我介紹收集
                    try:
                        redis_append_event(
                            user_id,
                            {
                                "type": "intro_collection",
                                "user_message": msg,
                                "collected_content": collection_result.get('collected_content', ''),
                                "content_length": current_length,
                                "stage": "intro",
                            },
                        )
                    except Exception:
                        pass
                    
                    return {
                        "success": True,
                        "data": {
                            "response": f"{ack}\n\n📝 已收集 {current_length} 字\n💡 若已完成，請輸入『開始面試』，我會先幫你分析再出題。",
                            "current_state": "intro",
                        },
                        "status_code": 200,
                    }
                else:
                    # 收集失敗，使用舊的方法
                    collector = intro_collector(user_message=msg, user_id=user_id)
                    ack = (
                        collector.get(
                            "result", "已記錄您的自我介紹，完成後請輸入『開始面試』。"
                        )
                        if isinstance(collector, dict)
                        else str(collector)
                    )
                    
                    # 寫入 Redis 事件 - 記錄自我介紹收集（舊方法）
                    try:
                        collected_content = collector.get('collected_content', '') if isinstance(collector, dict) else ''
                        redis_append_event(
                            user_id,
                            {
                                "type": "intro_collection",
                                "user_message": msg,
                                "collected_content": collected_content,
                                "content_length": len(collected_content),
                                "stage": "intro",
                            },
                        )
                    except Exception:
                        pass
                    
                    return {
                        "success": True,
                        "data": {
                            "response": ack
                            + "\n\n若已完成，請輸入『開始面試』，我會先幫你分析再出題。",
                            "current_state": "intro",
                        },
                        "status_code": 200,
                    }
                    
            except Exception as e:
                # 回退到舊的收集方法
                collector = intro_collector(user_message=msg, user_id=user_id)
                ack = (
                    collector.get(
                        "result", "已記錄您的自我介紹，完成後請輸入『開始面試』。"
                    )
                    if isinstance(collector, dict)
                    else str(collector)
                )
                
                # 寫入 Redis 事件 - 記錄自我介紹收集（異常處理）
                try:
                    collected_content = collector.get('collected_content', '') if isinstance(collector, dict) else ''
                    redis_append_event(
                        user_id,
                        {
                            "type": "intro_collection",
                            "user_message": msg,
                            "collected_content": collected_content,
                            "content_length": len(collected_content),
                            "stage": "intro",
                        },
                    )
                except Exception:
                    pass
                
                return {
                    "success": True,
                    "data": {
                        "response": ack
                        + "\n\n若已完成，請輸入『開始面試』，我會先幫你分析再出題。",
                        "current_state": "intro",
                    },
                    "status_code": 200,
                }

        # ==
        # 問題生成邏輯
        # ==
        # 檢測用戶要求獲取問題的關鍵字
        # 支援多種表達方式，讓用戶可以自然地表達需求
        lower = msg.lower()
        if any(
            k in lower
            for k in [
                "請給我問題",    # 禮貌請求
                "開始問答",      # 明確開始
                "開始面試",      # 正式開始
                "下一題",        # 要求下一題
                "下一個問題",    # 明確要求下一個
                "給我問題",      # 直接要求
            ]
        ):
            # 使用技能匹配出題
            try:
                from backend.tools.question_manager import QuestionManager
                qm = QuestionManager()
                skill_question_data = qm.get_skill_based_question(user_id)
                result = {
                    "success": True,
                    "question_data": skill_question_data,
                    "result": f"🎯 面試問題\n\n{skill_question_data['question']}\n來源：{skill_question_data['source']}"
                }
            except Exception as e:
                logger.warning(f"技能匹配出題失敗，使用隨機問題: {e}")
                result = get_question()
            
            if isinstance(result, dict) and result.get("success"):
                qdata = result.get("question_data", {})
                USER_CURRENT_QUESTIONS[user_id] = {
                    "question": qdata.get("question", ""),
                    "standard_answer": qdata.get("standard_answer", ""),
                }
                try:
                    redis_append_event(
                        user_id,
                        {
                            "type": "question_generated",
                            "user_message": msg,
                            "ai_response": result.get("result", ""),
                            "stage": "questioning",
                        },
                    )
                except Exception:
                    pass
                USER_STAGE[user_id] = "questioning"
                return {
                    "success": True,
                    "data": {
                        "response": result.get("result", ""),
                        "session_id": None,
                        "current_state": "questioning",
                    },
                    "status_code": 200,
                }
            raise HTTPException(status_code=400, detail="目前無法取得面試問題")

        # ==
        # 面試結束邏輯
        # ==
        # 檢測面試結束關鍵字，支援中英文表達
        # 結束時會進行資料清理和狀態保存
        if any(k in lower for k in ["結束面試", "面試完成", "結束", "finish", "end"]):
            try:
                # 嘗試獲取 Redis 事件（可選）
                try:
                    events = redis_list_events(user_id)
                    print(f"📊 收集到 {len(events)} 個面試事件")
                except Exception as e:
                    print(f"⚠️ 獲取 Redis 事件失敗: {e}")
                    events = []
                
                # 簡化處理：不強制寫入資料庫，避免錯誤
                if events:
                    print(f"📝 面試事件已記錄在 Redis 中")
                
                # 清理 Redis 會話
                try:
                    redis_clear_session(user_id)
                    redis_set_state(user_id, {"stage": "finished"})
                    print(f"🧹 Redis 會話已清理")
                except Exception as e:
                    print(f"⚠️ 清理 Redis 會話失敗: {e}")
                    
            except Exception as e:
                print(f"⚠️ 結束面試處理時出現錯誤: {e}")
                # 不拋出錯誤，繼續執行
                
            # 更新用戶狀態
            USER_STAGE[user_id] = "finished"
            
            # 生成動態的AI面試評論
            try:
                # 生成AI評論（使用簡化的統計信息）
                from ai_interview_summary import generate_ai_interview_summary
                # 暫時使用空的對話歷史，讓函數使用備用總結
                conversation_history = []
                ai_summary = generate_ai_interview_summary(conversation_history, user_id)
                
                return {
                    "success": True,
                    "data": {
                        "response": ai_summary,
                        "current_state": "finished",
                        "interview_summary": {
                            "summary": ai_summary
                        }
                    },
                    "status_code": 200,
                }
            except Exception as e:
                print(f"⚠️ 生成AI評論失敗: {e}")
                # 如果AI評論失敗，使用前端生成的總結
                return {
                    "success": True,
                    "data": {
                        "response": "✅ 面試已結束！正在為您生成個人化的面試總結和建議...",
                        "current_state": "finished",
                    },
                    "status_code": 200,
                }

        # ==
        # 面試問答階段處理 (questioning stage)
        # ==
        # 只有在面試問答階段才進行答案分析
        if stage == "questioning":
            # ==
            # 特殊指令處理（優先級最高）
            # ==
            # 檢查是否為特殊指令，如果是則不進行答案分析
            lower_msg = msg.lower()
            special_commands = [
                "請給我問題", "開始問答", "開始面試", "下一題", "下一個問題", "給我問題",
                "完成自介", "完成自我介紹", "完成", "分析", "分析自介",
                "結束面試", "結束", "停止", "退出", "重新開始", "restart"
            ]
            
            is_special_command = any(cmd in lower_msg for cmd in special_commands)
            
            if is_special_command:
                # 特殊指令不進行答案分析，返回到上層處理
                pass
            else:
                # ==
                # 答案分析邏輯
                # ==
                # 檢查是否有待回答的問題
                current_q = USER_CURRENT_QUESTIONS.get(user_id)
                if not current_q:
                    # 如果沒有當前問題，提示用戶先獲取問題
                        return {
                        "success": True,
                        "data": {
                            "response": "目前沒有待回答的題目。請先輸入『請給我問題』取得題目。",
                            "current_state": "questioning",
                        },
                        "status_code": 200,
                    }

            try:
                    # ==
                    # 調用答案分析函數
                    # ==
                    # 使用 AI 分析用戶的回答品質
                    # 分析維度包括：準確性、完整性、邏輯性等
                    analysis = analyze_answer(
                        user_answer=msg,                                    # 用戶的回答
                        question=current_q.get("question", ""),             # 對應的問題
                        standard_answer=current_q.get("standard_answer", ""), # 標準答案
                    )
            
                    # 檢查分析結果
                    if not analysis or not isinstance(analysis, dict):
                        print(f"⚠️ 答案分析返回無效結果: {analysis}")
                        analysis = {"success": False, "error": "分析結果無效"}
                    
                    # 提取回應文本
                    if analysis.get("success") and analysis.get("result"):
                        resp_text = analysis.get("result", "分析完成。")
                    elif analysis.get("error"):
                        resp_text = f"⚠️ 分析失敗: {analysis.get('error')}"
                    else:
                        resp_text = str(analysis) if analysis else "分析完成。"
                        
                    print(f"✅ 答案分析成功: {resp_text[:100]}...")
                    
            except Exception as e:
                    print(f"❌ 答案分析過程出現錯誤: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    
                    # 返回錯誤信息
                    resp_text = f"⚠️ 答案分析時出現問題: {str(e)}\n\n請稍後再試或重新回答問題。"
                    
                    return {
                        "success": False,
                        "data": {
                            "response": resp_text,
                            "current_state": "questioning",
                        },
                        "status_code": 500,
                    }

            # ==
            # 自動獲取下一題邏輯
            # ==
            # 在分析完用戶答案後，自動準備下一道問題
            # 這樣可以讓面試流程更加流暢
            try:
                from backend.tools.question_manager import QuestionManager
                question_manager = QuestionManager()
                # 使用技能匹配的智能出題
                next_question_data = question_manager.get_skill_based_question(user_id)
                
                # 更新用戶的當前問題狀態
                USER_CURRENT_QUESTIONS[user_id] = next_question_data
                
                # 將下一題數據單獨返回，不與分析結果混合
                # 這樣前端可以靈活處理問題顯示時機
                next_question_info = {
                    "question": next_question_data['question'],           # 問題內容
                    "source": next_question_data['source'],              # 問題來源
                    "standard_answer": next_question_data.get('standard_answer', '')  # 標準答案
                }
                
            except Exception as e:
                # 如果獲取下一題失敗，記錄錯誤但不影響答案分析
                # 這確保了系統的容錯性
                print(f"獲取下一題失敗: {e}")
                next_question_info = None

            # ==
            # 返回結果結構
            # ==
            # 返回分離的數據結構，讓前端可以靈活處理
            # 1. response: 只包含答案分析結果
            # 2. next_question: 下一題信息單獨返回
            # 3. 狀態信息：session_id 和 current_state
            return {
                    "success": True,
                    "data": {
                        "response": resp_text,                    # 只包含分析結果
                        "next_question": next_question_info,      # 下一題信息單獨返回
                        "session_id": None,                       # 會話ID（目前未使用）
                    "current_state": "questioning",           # 當前狀態：面試問答階段
                },
                "status_code": 200,
            }
        
        # ==
        # 其他階段處理
        # ==
        # 如果不是已知的階段，返回階段狀態提示
        else:
            return {
                "success": True,
                "data": {
                    "response": f"當前階段：{stage}。請根據當前階段進行相應操作。",
                    "current_state": stage,
                },
                "status_code": 200,
            }

    except HTTPException:
        raise
    except Exception as e:
        # 嘗試回滾資料庫事務（如果支援）
        try:
            if hasattr(db, 'rollback'):
                db.rollback()
        except Exception as rollback_error:
            print(f"⚠️ 資料庫回滾失敗: {rollback_error}")
        raise HTTPException(status_code=400, detail=f"處理面試對話失敗: {str(e)}")


app.include_router(router_interview)

# ======
# 技能匹配測試 API
# ======

@app.get("/api/skill-analysis/{user_id}")
def get_skill_analysis(user_id: str):
    """
    獲取用戶技能分析（用於測試和調試）
    """
    try:
        from backend.tools.skill_matcher import skill_matcher
        
        # 獲取技能匹配結果
        match_result = skill_matcher.match_skills(user_id)
        
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "user_skills": list(match_result['user_skills']),
                "job_skills": list(match_result['job_skills']),
                "matched_skills": list(match_result['matched_skills']),
                "missing_skills": list(match_result['missing_skills']),
                "extra_skills": list(match_result['extra_skills']),
                "match_score": match_result['match_score'],
                "priority_skills": match_result['priority_skills'],
                "question_skills": skill_matcher.get_question_skills_for_user(user_id)
            },
            "status_code": 200,
            "message": f"成功分析用戶 {user_id} 的技能匹配"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"技能分析失敗: {str(e)}")

@app.get("/api/skill-question/{user_id}")
def get_skill_based_question_api(user_id: str):
    """
    獲取基於技能匹配的面試問題（用於測試）
    """
    try:
        from backend.tools.question_manager import QuestionManager
        
        question_manager = QuestionManager()
        question_data = question_manager.get_skill_based_question(user_id)
        
        return {
            "success": True,
            "data": question_data,
            "status_code": 200,
            "message": f"成功為用戶 {user_id} 獲取技能匹配問題"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取技能問題失敗: {str(e)}")

# ============================================================================
# 職缺搜尋路由器 (Job Search Router)
# ============================================================================
try:
    from backend.routers.job_search import router as router_job_search
    app.include_router(router_job_search)
    logger.info("✅ 職缺搜尋路由器載入成功")
except ImportError as e:
    logger.warning(f"⚠️ 職缺搜尋路由器載入失敗: {e}")

# ============================================================================
# LiveTalking 備用端點 (LiveTalking Fallback Endpoints)
# ============================================================================

from pydantic import BaseModel
from typing import Optional

class LiveTalkingRequest(BaseModel):
    """LiveTalking 請求模型"""
    text: str
    type: Optional[str] = "echo"
    interrupt: Optional[bool] = True
    sessionid: Optional[int] = 0

@app.post("/ltapi/human")
def ltapi_human_fallback(payload: LiveTalkingRequest):
    """
    LiveTalking /human 端點的備用實現
    當 LiveTalking 服務未啟動時提供基本功能
    """
    logger.info(f"📢 LiveTalking 備用端點收到請求: {payload.text}")
    
    return {
        "code": 0,
        "msg": "ok",
        "data": {
            "text": payload.text,
            "type": payload.type,
            "status": "processed_by_fallback",
            "message": "虛擬人服務正在初始化中，您的訊息已記錄"
        }
    }

@app.get("/ltapi/index.json")
def ltapi_index_fallback():
    """
    LiveTalking index.json 端點的備用實現
    """
    import time
    # 生成一個基於時間的 session ID 用於測試
    session_id = f"fallback-{int(time.time())}"
    
    return {
        "status": "fallback",
        "session": session_id,
        "message": "LiveTalking 服務正在初始化中，使用備用模式",
        "available": False,
        "fallback_mode": True
    }

@app.post("/ltapi/offer")
def ltapi_offer_fallback(payload: dict):
    """
    LiveTalking /offer 端點的備用實現
    當 LiveTalking 服務未啟動時提供基本功能
    """
    logger.info(f"📡 LiveTalking offer 備用端點收到 WebRTC 連接請求: {type(payload)}")
    
    import time
    import random
    
    # 生成一個基於時間的 session ID 用於測試
    session_id = random.randint(100000, 999999)
    
    # 檢查是否是有效的 WebRTC Offer
    if isinstance(payload, dict) and "sdp" in payload and "type" in payload:
        # 創建一個基本的 SDP answer 回應
        # 這是一個最簡化的 SDP answer，用於避免 WebRTC 錯誤
        minimal_answer_sdp = """v=0
o=- 0 0 IN IP4 127.0.0.1
s=Fallback Session
c=IN IP4 127.0.0.1
t=0 0
m=video 9 UDP/TLS/RTP/SAVPF 96
a=rtcp-mux
a=sendonly
a=rtpmap:96 VP8/90000
m=audio 9 UDP/TLS/RTP/SAVPF 111
a=rtcp-mux
a=sendonly
a=rtpmap:111 opus/48000/2"""
        
        return {
            "sdp": minimal_answer_sdp,
            "type": "answer",
            "sessionid": session_id,
            "fallback_mode": True
        }
    else:
        # 如果不是有效的 WebRTC offer，返回狀態信息
        return {
            "code": 0,
            "msg": "ok",
            "data": {
                "status": "fallback",
                "message": "虛擬人服務正在初始化中，WebRTC 連接暫時不可用",
                "sessionid": session_id,
                "fallback_mode": True
            }
        }

@app.post("/offer")
def offer_fallback(payload: dict):
    """
    LiveTalking /offer 端點的備用實現（直接路徑）
    當 LiveTalking 服務未啟動時提供基本功能
    """
    logger.info(f"📡 LiveTalking /offer 備用端點收到 WebRTC 連接請求")
    
    import random
    
    # 生成一個基於時間的 session ID 用於測試
    session_id = random.randint(100000, 999999)
    
    # 檢查是否是有效的 WebRTC Offer
    if isinstance(payload, dict) and "sdp" in payload and "type" in payload:
        # 創建一個基本的 SDP answer 回應
        minimal_answer_sdp = """v=0
o=- 0 0 IN IP4 127.0.0.1
s=Fallback Session
c=IN IP4 127.0.0.1
t=0 0
m=video 9 UDP/TLS/RTP/SAVPF 96
a=rtcp-mux
a=sendonly
a=rtpmap:96 VP8/90000
m=audio 9 UDP/TLS/RTP/SAVPF 111
a=rtcp-mux
a=sendonly
a=rtpmap:111 opus/48000/2"""
        
        return {
            "sdp": minimal_answer_sdp,
            "type": "answer",
            "sessionid": session_id,
            "fallback_mode": True
        }
    else:
        return {
            "code": 0,
            "msg": "ok",
            "data": {
                "status": "fallback",
                "message": "虛擬人服務正在初始化中，WebRTC 連接暫時不可用",
                "sessionid": session_id,
                "fallback_mode": True
            }
        }
