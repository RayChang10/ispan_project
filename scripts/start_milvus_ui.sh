#!/bin/bash

# Milvus Web UI 啟動腳本
# 用於啟動 Milvus 資料庫的 Web 介面

echo "🚀 啟動 Milvus Web UI 服務..."

# 檢查 Python 環境
if ! command -v python3 &> /dev/null; then
    echo "❌ 錯誤：找不到 python3 命令"
    exit 1
fi

# 檢查必要套件
echo "📦 檢查必要套件..."
python3 -c "import fastapi, uvicorn, pymilvus" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 錯誤：缺少必要套件，請先安裝："
    echo "   pip install fastapi uvicorn pymilvus jinja2"
    exit 1
fi

# 切換到專案根目錄
cd "$(dirname "$0")/.."

# 檢查 Milvus 連接
echo "🔍 檢查 Milvus 連接..."
python3 scripts/check_milvus_data.py > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "⚠️  警告：Milvus 連接可能有問題，但會繼續啟動服務"
fi

# 啟動服務
echo "🌐 啟動 Web UI 服務..."
echo "📊 訪問地址: http://localhost:8080"
echo "📊 API 文檔: http://localhost:8080/docs"
echo ""
echo "按 Ctrl+C 停止服務"
echo ""

# 啟動 FastAPI 服務
python3 backend/milvus_ui.py
