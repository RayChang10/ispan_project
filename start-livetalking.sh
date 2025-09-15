#!/bin/bash
# LiveTalking 快速啟動腳本

set -e

echo "🎭 LiveTalking 虛擬人系統啟動腳本"
echo "=================================="

# 檢查 Docker 是否安裝
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安裝，請先安裝 Docker"
    exit 1
fi

# 檢查 Docker Compose 是否安裝
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安裝，請先安裝 Docker Compose"
    exit 1
fi

# 檢查是否有 GPU 支援
if command -v nvidia-smi &> /dev/null; then
    echo "✅ 檢測到 NVIDIA GPU"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    GPU_SUPPORT=true
else
    echo "⚠️  未檢測到 GPU，將使用 CPU 模式（性能較差）"
    GPU_SUPPORT=false
fi

# 檢查模型檔案
echo ""
echo "📦 檢查模型檔案..."

if [ ! -f "models/wav2lip.pth" ]; then
    echo "⚠️  模型檔案不存在：models/wav2lip.pth"
    echo "請下載模型檔案："
    echo "1. 訪問: https://pan.quark.cn/s/83a750323ef0"
    echo "2. 下載 wav2lip256.pth"
    echo "3. 放置到 models/ 目錄並重命名為 wav2lip.pth"
    echo ""
    read -p "是否繼續啟動？模型檔案將在運行時提醒下載 [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ 找到模型檔案：models/wav2lip.pth"
fi

if [ ! -d "data/avatars/wav2lip256_avatar1" ]; then
    echo "⚠️  Avatar 資料不存在：data/avatars/wav2lip256_avatar1"
    echo "請下載 Avatar 資料："
    echo "1. 訪問: https://pan.quark.cn/s/83a750323ef0"
    echo "2. 下載 wav2lip256_avatar1.tar.gz"
    echo "3. 解壓到 data/avatars/ 目錄"
    echo ""
    read -p "是否繼續啟動？Avatar 資料將在運行時提醒下載 [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ 找到 Avatar 資料：data/avatars/wav2lip256_avatar1"
fi

# 創建必要的目錄
echo ""
echo "📁 創建必要目錄..."
mkdir -p models data/avatars Livetalking_virtual_interview/web

# 選擇啟動模式
echo ""
echo "🚀 選擇啟動模式："
echo "1. 完整系統 (面試系統 + LiveTalking)"
echo "2. 僅 LiveTalking 服務"
echo "3. 開發模式 (所有服務)"

read -p "請選擇 [1-3]: " -n 1 -r
echo

case $REPLY in
    1)
        echo "🎯 啟動完整系統..."
        if [ "$GPU_SUPPORT" = true ]; then
            echo "選擇 LiveTalking 版本："
            echo "  a) 完整版 (需要 GPU 和模型檔案)"
            echo "  b) 簡化版 (CPU 版本，用於測試)"
            read -p "請選擇 [a/b]: " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Aa]$ ]]; then
                docker-compose --profile gpu up -d main livetalking
                echo "🎭 啟動完整版 LiveTalking"
            else
                docker-compose --profile simple up -d main livetalking-simple
                echo "🎭 啟動簡化版 LiveTalking"
            fi
        else
            echo "⚠️  沒有 GPU，啟動簡化版 LiveTalking"
            docker-compose --profile simple up -d main livetalking-simple
        fi
        echo ""
        echo "✅ 系統啟動完成！"
        echo "🌐 面試系統: http://localhost:8080"
        echo "🎭 LiveTalking: http://localhost:8010/dashboard.html"
        ;;
    2)
        echo "🎭 啟動 LiveTalking 服務..."
        if [ "$GPU_SUPPORT" = true ]; then
            echo "選擇 LiveTalking 版本："
            echo "  a) 完整版 (需要 GPU 和模型檔案)"
            echo "  b) 簡化版 (CPU 版本，用於測試)"
            read -p "請選擇 [a/b]: " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Aa]$ ]]; then
                docker-compose --profile gpu up -d livetalking
                echo "🎭 啟動完整版 LiveTalking"
            else
                docker-compose --profile simple up -d livetalking-simple
                echo "🎭 啟動簡化版 LiveTalking"
            fi
        else
            echo "⚠️  沒有 GPU，啟動簡化版 LiveTalking"
            docker-compose --profile simple up -d livetalking-simple
        fi
        echo ""
        echo "✅ LiveTalking 啟動完成！"
        echo "🌐 Dashboard: http://localhost:8010/dashboard.html"
        ;;
    3)
        echo "🔧 啟動開發模式..."
        if [ "$GPU_SUPPORT" = true ]; then
            docker-compose --profile full up -d
        else
            docker-compose --profile simple up -d main postgres redis mongo minio livetalking-simple
        fi
        echo ""
        echo "✅ 開發環境啟動完成！"
        echo "🌐 主系統: http://localhost:8080"
        echo "📊 API 系統: http://localhost:8001"
        echo "🗄️  MinIO: http://localhost:9001"
        echo "🎭 LiveTalking: http://localhost:8010/dashboard.html"
        if [ "$GPU_SUPPORT" = true ]; then
            echo "🎤 Whisper API: http://localhost:8000"
        fi
        ;;
    *)
        echo "❌ 無效選擇"
        exit 1
        ;;
esac

# 顯示日誌跟蹤指令
echo ""
echo "📋 實用指令："
echo "查看所有服務狀態: docker-compose ps"
echo "查看 LiveTalking 日誌: docker-compose logs -f livetalking"
echo "停止所有服務: docker-compose down"
echo "重啟 LiveTalking: docker-compose restart livetalking"

# 等待服務啟動
echo ""
echo "⏳ 等待服務啟動..."
sleep 10

# 檢查服務狀態
echo ""
echo "🔍 檢查服務狀態..."
docker-compose ps

echo ""
echo "🎉 啟動完成！如有問題請查看日誌或參考 README-LiveTalking.md"
