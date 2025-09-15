#!/bin/bash
###############################################################################
# LiveTalking Docker 容器啟動腳本
###############################################################################

set -e

echo "🚀 啟動 LiveTalking 虛擬人服務..."

# 確保模型目錄存在
mkdir -p /app/models
mkdir -p /app/data/avatars

# 檢查 GPU 可用性
if command -v nvidia-smi &> /dev/null; then
    echo "✅ GPU 檢測："
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits
else
    echo "⚠️ 未檢測到 GPU，將使用 CPU 模式"
fi

# 檢查模型文件
if [ ! -f "/app/models/wav2lip.pth" ]; then
    echo "❌ 錯誤：找不到模型文件 /app/models/wav2lip.pth"
    echo "   請確保模型文件已正確掛載到容器中"
    echo "   當前 /app/models 目錄內容："
    ls -la /app/models/ || echo "   目錄不存在或為空"
    exit 1
fi

echo "✅ 模型文件檢查通過"

# 在 LiveTalking 目錄中創建模型軟連結
cd /app/Livetalking_virtual_interview
if [ ! -L "models" ]; then
    ln -sf /app/models ./models
    echo "✅ 創建模型目錄軟連結"
fi

# 檢查虛擬人資源目錄
if [ ! -d "/app/Livetalking_virtual_interview" ]; then
    echo "❌ 錯誤：找不到 LiveTalking 程序目錄"
    exit 1
fi

echo "✅ LiveTalking 程序目錄檢查通過"

# 設置環境變數
export PYTHONPATH="/app:${PYTHONPATH}"
export LIVETALKING_MODE="${LIVETALKING_MODE:-webrtc}"
export LIVETALKING_MODEL="${LIVETALKING_MODEL:-wav2lip}"
export LIVETALKING_AVATAR_ID="${LIVETALKING_AVATAR_ID:-wav2lip256_avatar1}"
export LIVETALKING_PORT="${LIVETALKING_PORT:-8010}"
export LIVETALKING_HOST="${LIVETALKING_HOST:-0.0.0.0}"

echo "🔧 環境變數設置："
echo "   LIVETALKING_MODE: ${LIVETALKING_MODE}"
echo "   LIVETALKING_MODEL: ${LIVETALKING_MODEL}"
echo "   LIVETALKING_AVATAR_ID: ${LIVETALKING_AVATAR_ID}"
echo "   LIVETALKING_PORT: ${LIVETALKING_PORT}"
echo "   LIVETALKING_HOST: ${LIVETALKING_HOST}"

# 切換到 LiveTalking 目錄
cd /app/Livetalking_virtual_interview

echo "📂 當前工作目錄: $(pwd)"
echo "📂 目錄內容："
ls -la

# 啟動 LiveTalking 服務
echo "🎭 啟動 LiveTalking 虛擬人服務..."

# 根據模式選擇啟動方式
if [ "${LIVETALKING_MODE}" = "webrtc" ]; then
    echo "🌐 啟動 WebRTC 模式"
    exec python app.py \
        --listenport ${LIVETALKING_PORT} \
        --model ${LIVETALKING_MODEL} \
        --avatar_id ${LIVETALKING_AVATAR_ID} \
        --transport webrtc
else
    echo "📺 啟動簡化模式"
    exec python app.py \
        --listenport ${LIVETALKING_PORT} \
        --model ${LIVETALKING_MODEL} \
        --avatar_id ${LIVETALKING_AVATAR_ID}
fi
