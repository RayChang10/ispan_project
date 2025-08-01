# 環境變數設定說明

## 概述

本專案已更新為使用環境變數來管理敏感資訊（如 API keys），提高安全性和可維護性。

## 設定步驟

### 1. 複製環境變數範例檔案

```bash
cp env.example .env
```

### 2. 編輯 .env 檔案

將您的實際 API key 填入 `.env` 檔案：

```env
# OpenAI API Key
OPENAI_API_KEY=your_actual_openai_api_key_here

# 其他環境變數
PYTHONPATH=.
PYTHONUNBUFFERED=1
```

### 3. 安全注意事項

- `.env` 檔案已加入 `.gitignore`，不會被提交到版本控制
- 請確保 `.env` 檔案包含您的實際 API key
- 不要將 `.env` 檔案分享給他人

## 支援的環境變數

| 變數名稱 | 說明 | 範例 |
|---------|------|------|
| `OPENAI_API_KEY` | OpenAI API 金鑰 | `sk-...` |
| `PYTHONPATH` | Python 路徑設定 | `.` |
| `PYTHONUNBUFFERED` | Python 輸出緩衝設定 | `1` |

## 程式碼變更

### 已修改的檔案

1. **fastagent.config.yaml**
   - API key 改為使用環境變數：`"${OPENAI_API_KEY}"`

2. **fast_agent_interview.py**
   - 添加 `python-dotenv` 支援
   - 自動載入 `.env` 檔案

3. **server.py**
   - 添加 `python-dotenv` 支援
   - 自動載入 `.env` 檔案

### 新增檔案

1. **env.example**
   - 環境變數範例檔案
   - 提供設定參考

## 驗證設定

執行以下指令確認環境變數已正確載入：

```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('OPENAI_API_KEY:', os.environ.get('OPENAI_API_KEY', 'Not set'))"
```

## 故障排除

### 問題：環境變數未載入

**解決方案：**
1. 確認 `.env` 檔案存在且格式正確
2. 檢查檔案權限
3. 重新啟動應用程式

### 問題：API key 無效

**解決方案：**
1. 確認 API key 格式正確
2. 檢查 OpenAI 帳戶餘額
3. 確認 API key 權限設定

## 開發環境建議

- 使用不同的 API key 進行開發和生產
- 定期輪換 API key
- 監控 API 使用量 