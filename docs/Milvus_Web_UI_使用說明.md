# Milvus 資料庫 Web UI 使用說明

## 🎯 功能概述

Milvus Web UI 是一個現代化的網頁介面，讓您可以透過瀏覽器輕鬆查看和管理 Milvus 向量資料庫的內容。

### ✨ 主要功能

- **📊 集合概覽**: 查看所有集合的統計資訊
- **🔍 向量搜尋**: 執行相似度搜尋
- **📋 資料瀏覽**: 分頁瀏覽集合資料
- **📱 響應式設計**: 支援桌面和行動裝置
- **🎨 現代化 UI**: 美觀的使用者介面

## 🚀 快速開始

### 方法一：使用啟動腳本（推薦）

```bash
# 在專案根目錄執行
./scripts/start_milvus_ui.sh
```

### 方法二：直接啟動

```bash
# 在專案根目錄執行
python3 backend/milvus_ui.py
```

### 方法三：使用 uvicorn

```bash
# 在專案根目錄執行
uvicorn backend.milvus_ui:app --host 0.0.0.0 --port 8080 --reload
```

## 🌐 訪問介面

啟動服務後，在瀏覽器中訪問：

- **主介面**: http://localhost:8080
- **API 文檔**: http://localhost:8080/docs
- **健康檢查**: http://localhost:8080/api/health

## 📖 使用指南

### 1. 集合概覽

進入主頁面後，您會看到所有 Milvus 集合的概覽：

- **集合名稱**: 顯示集合的識別名稱
- **資料量**: 顯示集合中的實體數量
- **欄位數**: 顯示集合的欄位數量
- **操作按鈕**: 
  - `查看資料`: 瀏覽集合內容
  - `在此集合搜尋`: 快速切換到搜尋模式

### 2. 資料瀏覽

點擊 `查看資料` 按鈕後：

- **分頁顯示**: 每頁顯示 20 筆資料
- **欄位資訊**: 動態顯示所有欄位
- **詳細檢視**: 點擊 `詳細` 按鈕查看完整資料
- **導航控制**: 使用上一頁/下一頁按鈕

### 3. 向量搜尋

在搜尋區域：

1. **輸入關鍵字**: 在搜尋框中輸入您要找的內容
2. **選擇集合**: 可以指定要在哪個集合中搜尋
3. **執行搜尋**: 點擊 `搜尋` 按鈕
4. **查看結果**: 
   - 相似度分數
   - 職缺名稱
   - 公司名稱
   - 地點資訊

### 4. 詳細資料檢視

點擊任何記錄的 `詳細` 按鈕：

- **彈出視窗**: 顯示完整的資料內容
- **格式化顯示**: 易於閱讀的格式
- **可滾動**: 支援長內容的滾動檢視

## 🔧 API 端點

### 集合相關

- `GET /api/collections` - 獲取所有集合資訊
- `GET /api/collection/{name}` - 獲取指定集合的資料
- `GET /api/health` - 健康檢查

### 搜尋相關

- `POST /api/search` - 執行向量搜尋

### 請求範例

```bash
# 獲取集合資訊
curl http://localhost:8080/api/collections

# 獲取職缺集合資料（前 20 筆）
curl "http://localhost:8080/api/collection/job_postings_openai?limit=20&offset=0"

# 執行搜尋
curl -X POST http://localhost:8080/api/search \
  -H "Content-Type: application/json" \
  -d '{"collection": "job_postings_openai", "query": "Python 工程師", "limit": 10}'
```

## 🛠️ 技術架構

### 後端技術

- **FastAPI**: 現代化的 Python Web 框架
- **Pymilvus**: Milvus 向量資料庫客戶端
- **Jinja2**: 模板引擎
- **Uvicorn**: ASGI 伺服器

### 前端技術

- **原生 JavaScript**: 無框架依賴
- **現代 CSS**: 響應式設計
- **Fetch API**: 非同步資料載入

### 資料流程

```
瀏覽器 → FastAPI → Pymilvus → Milvus 資料庫
   ↑                                    ↓
   ←────────── JSON 回應 ──────────────←
```

## 🔍 故障排除

### 常見問題

#### 1. 服務無法啟動

**症狀**: 執行啟動腳本時出現錯誤

**解決方案**:
```bash
# 檢查 Python 環境
python3 --version

# 安裝必要套件
pip install fastapi uvicorn pymilvus jinja2

# 檢查 Milvus 連接
python3 scripts/check_milvus_data.py
```

#### 2. 無法連接到 Milvus

**症狀**: 頁面顯示 "無法連接到 Milvus"

**解決方案**:
```bash
# 檢查 Milvus 服務狀態
docker ps | grep milvus

# 檢查環境變數
echo $MILVUS_HOST
echo $MILVUS_PORT

# 測試連接
python3 -c "from pymilvus import connections; connections.connect('default', host='localhost', port='19530')"
```

#### 3. 頁面載入緩慢

**症狀**: 資料載入時間過長

**解決方案**:
- 減少每頁顯示的資料量
- 檢查網路連接
- 確認 Milvus 索引是否正確建立

#### 4. 搜尋無結果

**症狀**: 搜尋功能沒有返回結果

**解決方案**:
- 確認集合中有資料
- 檢查搜尋關鍵字
- 驗證向量索引狀態

### 日誌檢查

```bash
# 查看服務日誌
tail -f logs/milvus_ui.log

# 檢查系統資源
htop
```

## 📊 效能優化

### 資料庫層面

- **索引優化**: 確保向量欄位有適當的索引
- **分頁查詢**: 使用 limit 和 offset 參數
- **欄位選擇**: 只查詢需要的欄位

### 應用層面

- **快取機制**: 考慮實作 Redis 快取
- **非同步處理**: 使用 FastAPI 的非同步特性
- **連接池**: 優化資料庫連接管理

## 🔒 安全性考量

### 生產環境部署

- **HTTPS**: 使用 SSL/TLS 加密
- **認證**: 實作使用者認證機制
- **授權**: 控制資料存取權限
- **日誌**: 記錄所有操作日誌

### 環境變數

```bash
# 建議的環境變數設定
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_USER=your_username
MILVUS_PASSWORD=your_password
```

## 📈 監控與維護

### 健康檢查

```bash
# 定期檢查服務狀態
curl http://localhost:8080/api/health

# 檢查集合狀態
curl http://localhost:8080/api/collections
```

### 備份策略

- **定期備份**: 備份 Milvus 資料
- **版本控制**: 管理配置檔案
- **災難恢復**: 建立恢復程序

## 🤝 貢獻指南

### 開發環境設定

```bash
# 克隆專案
git clone <repository_url>
cd FastMCP-FastAgent2

# 安裝開發依賴
pip install -r requirements.txt

# 啟動開發服務
python3 backend/milvus_ui.py
```

### 程式碼規範

- 遵循 PEP 8 Python 程式碼規範
- 使用型別提示
- 撰寫單元測試
- 更新文件

## 📞 支援與聯絡

如果您遇到問題或有建議：

1. 檢查本文件的故障排除章節
2. 查看 GitHub Issues
3. 聯絡開發團隊

---

**版本**: 1.0.0  
**更新日期**: 2024  
**維護者**: FastMCP-FastAgent2 團隊
