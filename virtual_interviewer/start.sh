#!/bin/bash
# 虛擬面試顧問 - Poetry啟動腳本

echo "🚀 使用Poetry啟動虛擬面試顧問..."
echo "=================================================="

# 檢查Poetry是否安裝
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry未安裝，請先安裝Poetry"
    echo "安裝指令: curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# 檢查pyproject.toml是否存在
if [ ! -f "pyproject.toml" ]; then
    echo "❌ pyproject.toml文件不存在"
    exit 1
fi

# 安裝依賴（如果需要）
echo "📦 檢查並安裝依賴..."
poetry install --only=main

# 啟動應用程式
echo "🌐 應用程式將在 http://localhost:5000 啟動"
echo "📝 主頁面: http://localhost:5000"
echo "📋 履歷建立: http://localhost:5000/resume"
echo "=================================================="
echo "按 Ctrl+C 停止應用程式"
echo ""

poetry run python run.py 