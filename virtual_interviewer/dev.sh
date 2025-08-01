#!/bin/bash
# 虛擬面試顧問 - 開發環境啟動腳本

echo "🔧 啟動開發環境..."
echo "=================================================="

# 安裝所有依賴（包含開發依賴）
echo "📦 安裝開發依賴..."
poetry install

echo "✅ 開發環境已準備就緒"
echo ""
echo "可用指令："
echo "  poetry run python run.py     # 啟動應用程式"
echo "  poetry run black .           # 格式化程式碼"
echo "  poetry run flake8 .          # 程式碼檢查"
echo "  poetry run isort .           # 整理import"
echo "  poetry run pytest            # 執行測試"
echo "  poetry shell                 # 進入虛擬環境shell"
echo ""
echo "=================================================="

# 詢問是否要直接啟動應用程式
read -p "是否要立即啟動應用程式？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 啟動應用程式..."
    poetry run python run.py
else
    echo "💻 開發環境已準備完成，使用上述指令進行開發"
fi 