# MongoDB 履歷存儲遷移說明

## 📋 概覽

本次更新將履歷資料的存儲從 PostgreSQL 遷移到 MongoDB，提供更靈活的文檔結構和更好的擴展性。

## 🏗️ 架構變更

### 之前（PostgreSQL）
```
履歷解析 → PostgreSQL 表格 (app_users, work_experience, skill)
```

### 現在（MongoDB）
```
履歷解析 → MongoDB 集合 (resumes)
```

## 📊 資料結構

### MongoDB 文檔結構
```json
{
  "_id": "ObjectId",
  "user_id": "用戶ID",
  "created_at": "建立時間",
  "updated_at": "更新時間",
  
  "personal_info": {
    "name": "姓名",
    "age": "年齡", 
    "location": "所在地",
    "summary": "個人簡介",
    "keywords": "關鍵字",
    "bio_zh": "中文簡介"
  },
  
  "desired_job": {
    "domain": "期望領域",
    "location": ["期望地點"],
    "remote": "遠程工作意願"
  },
  
  "work_experience": [
    {
      "company": "公司名稱",
      "position": "職位",
      "startDate": "開始日期",
      "endDate": "結束日期",
      "description": "工作描述"
    }
  ],
  
  "education": [
    {
      "school": "學校",
      "major": "科系",
      "degree": "學位",
      "graduationYear": "畢業年份"
    }
  ],
  
  "skills": [
    {
      "skill_name": "技能名稱",
      "skill_level": "熟練程度"
    }
  ],
  
  "projects": [...],
  "languages": [...],
  "certifications": [...],
  
  "raw_data": "原始解析資料",
  "source": "資料來源",
  "version": "版本號"
}
```

## 🔧 新功能

### 1. MongoDB 履歷管理器
- **檔案**: `backend/tools/mongodb_resume_manager.py`
- **類別**: `MongoResumeManager`

#### 主要方法：
- `save_resume(user_id, resume_data)` - 儲存履歷
- `get_resume_by_user_id(user_id)` - 獲取履歷  
- `search_resumes(query, limit)` - 搜尋履歷
- `delete_resume(user_id)` - 刪除履歷
- `get_resume_statistics()` - 統計資訊

### 2. 新增 FastAPI 端點

#### GET `/api/users/resume/{user_id}`
- 獲取指定用戶的履歷資料

#### DELETE `/api/users/resume/{user_id}`  
- 刪除指定用戶的履歷

#### GET `/api/users/resumes/search`
- 搜尋履歷
- 參數: `domain`, `location`, `skills`, `limit`

#### GET `/api/users/resumes/statistics`
- 獲取履歷統計資訊

### 3. 更新 MCP 工具

#### 新增工具：
- `save_resume_to_mongodb` - 儲存履歷到 MongoDB
- `get_resume_from_mongodb` - 從 MongoDB 獲取履歷
- `search_resumes_in_mongodb` - 搜尋履歷
- `get_resume_statistics` - 統計資訊

#### 更新工具：
- `parse_resume` - 增加 `save_to_mongodb` 參數
- `comprehensive_resume_analysis` - 增加 MongoDB 存儲選項

## 🚀 使用方法

### 1. 履歷上傳與解析

```bash
# 上傳履歷並自動存入 MongoDB
curl -X POST "http://localhost:8001/api/users/parse_resume" \
  -F "file=@resume.pdf" \
  -F "user_id=user123" \
  -F "save_to_mongodb=true"
```

### 2. 獲取履歷資料

```bash
# 獲取用戶履歷
curl -X GET "http://localhost:8001/api/users/resume/user123"
```

### 3. 搜尋履歷

```bash
# 搜尋軟體開發相關履歷
curl -X GET "http://localhost:8001/api/users/resumes/search?domain=軟體&limit=10"
```

### 4. 統計資訊

```bash
# 獲取履歷統計
curl -X GET "http://localhost:8001/api/users/resumes/statistics"
```

## 🧪 測試

執行測試腳本驗證功能：

```bash
cd /home/ray/FastMCP-FastAgent
python backend/test_mongodb_resume.py
```

## 🔄 資料遷移

### 如果需要將現有 PostgreSQL 資料遷移到 MongoDB：

1. **匯出 PostgreSQL 資料**
```python
from backend.db_sa import User, WorkExperience, Skill, get_db

def export_postgres_data():
    db = next(get_db())
    users = db.query(User).all()
    
    for user in users:
        resume_data = {
            "name": user.name,
            "desired_position": user.desired_position,
            # ... 轉換其他欄位
        }
        resume_manager.save_resume(str(user.id), resume_data)
```

2. **執行遷移**
```bash
python migration_script.py
```

## 📈 優勢

### MongoDB 存儲優勢：
1. **靈活性** - 文檔結構可動態調整
2. **嵌套資料** - 天然支援複雜的巢狀結構  
3. **查詢能力** - 強大的聚合查詢功能
4. **擴展性** - 水平擴展能力佳
5. **JSON 原生** - 與前端資料格式完美匹配

### 相比 PostgreSQL：
- ✅ 更適合履歷這種半結構化資料
- ✅ 減少表格間的複雜關聯
- ✅ 更好的查詢性能（對於文檔搜尋）
- ✅ 更簡單的資料模型

## 🔧 配置

### MongoDB 連線設定
```bash
# 環境變數
MONGODB_URI=mongodb://admin:changeme@mongo:27017/?authSource=admin
MONGODB_DB_NAME=interview_db
```

### Docker Compose
MongoDB 服務已在 `docker-compose.yml` 中配置：
```yaml
mongo:
  image: mongo:7.0
  container_name: fastmcp-mongo
  environment:
    - MONGO_INITDB_ROOT_USERNAME=admin
    - MONGO_INITDB_ROOT_PASSWORD=changeme
  ports:
    - "27017:27017"
```

## 🚨 注意事項

1. **向後兼容性** - PostgreSQL 的用戶表格保留，主要用於身份驗證
2. **資料一致性** - 建議在遷移期間進行資料驗證
3. **備份策略** - 確保 MongoDB 有適當的備份機制
4. **索引優化** - 根據查詢模式建立適當的索引

## 📝 更新日誌

- **v1.0** - 初始 MongoDB 履歷存儲實現
- 新增履歷管理器類別
- 新增 FastAPI 端點
- 新增 MCP 工具支援
- 新增測試腳本
