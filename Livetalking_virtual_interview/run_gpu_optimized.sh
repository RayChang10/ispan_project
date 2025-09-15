#!/bin/bash
###############################################################################
# LiveTalking GPU 優化啟動腳本
# 用於在 Linux/WSL 環境下啟動 GPU 加速的虛擬面試系統
###############################################################################

set -e  # 遇到錯誤時退出

echo "=========================================="
echo "LiveTalking GPU 優化啟動腳本"
echo "=========================================="

# 檢查是否在 WSL 環境
if [[ -n "$WSL_DISTRO_NAME" ]]; then
    echo "檢測到 WSL 環境: $WSL_DISTRO_NAME"
    export DISPLAY=:0
fi

# 檢查 CUDA 環境
echo "檢查 CUDA 環境..."
if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA 驅動已安裝"
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits
else
    echo "警告: 未檢測到 NVIDIA 驅動，請確保已安裝"
fi

# 檢查 Python 環境
echo "檢查 Python 環境..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "Python 版本: $PYTHON_VERSION"
else
    echo "錯誤: 未找到 Python3"
    exit 1
fi

# 檢查虛擬環境
if [[ -d ".venv" ]]; then
    echo "激活虛擬環境..."
    source .venv/bin/activate
elif [[ -d ".venv_linux" ]]; then
    echo "激活 Linux 虛擬環境..."
    source .venv_linux/bin/activate
else
    echo "警告: 未找到虛擬環境，使用系統 Python"
fi

# 檢查依賴
echo "檢查依賴..."
python3 -c "
import torch
print(f'PyTorch 版本: {torch.__version__}')
if torch.cuda.is_available():
    print(f'CUDA 可用: {torch.version.cuda}')
    print(f'GPU 數量: {torch.cuda.device_count()}')
    for i in range(torch.cuda.device_count()):
        print(f'  GPU {i}: {torch.cuda.get_device_name(i)}')
else:
    print('CUDA 不可用')
"

# 設置環境變數
echo "設置 GPU 環境變數..."
export CUDA_VISIBLE_DEVICES=0
export TORCH_CUDNN_V8_API_ENABLED=1
export NVIDIA_TF32_OVERRIDE=1
export CUDA_CACHE_DISABLE=0

# 設置 FFmpeg 硬體編碼器
export FFMPEG_HWACCEL=nvdec
export FFMPEG_VIDEO_CODEC=h264_nvenc
export FFMPEG_AUDIO_CODEC=aac

# 設置 NVIDIA 編碼器參數
export NVENC_PRESET=p7
export NVENC_TUNE=hq
export NVENC_RC=vbr

echo "環境變數設置完成"

# 檢查模型文件
echo "檢查模型文件..."
if [[ -f "../models/wav2lip.pth" ]]; then
    echo "Wav2Lip 模型文件存在"
else
    echo "警告: 未找到 Wav2Lip 模型文件"
fi

# 檢查 avatar 文件
if [[ -d "data/avatars" ]]; then
    echo "Avatar 目錄存在"
    ls -la data/avatars/
else
    echo "警告: 未找到 avatar 目錄"
fi

# 啟動 GPU 監控（可選）
if [[ "$1" == "--monitor" ]]; then
    echo "啟動 GPU 監控..."
    python3 gpu_monitor.py &
    MONITOR_PID=$!
    echo "GPU 監控進程 ID: $MONITOR_PID"
fi

# 啟動主應用
echo "啟動 LiveTalking 應用..."
echo "使用 GPU 優化模式"
echo "按 Ctrl+C 停止應用"

# 設置啟動參數
ARGS=(
    "--model" "wav2lip"
    "--transport" "webrtc"
    "--fps" "50"
    "--batch_size" "16"
    "--W" "450"
    "--H" "450"
    "--avatar_id" "avator_1"
    "--tts" "edgetts"
    "--listenport" "8010"
    "--max_session" "1"
)

echo "啟動參數: ${ARGS[*]}"

# 啟動應用
python3 app.py "${ARGS[@]}"

# 清理
if [[ -n "$MONITOR_PID" ]]; then
    echo "停止 GPU 監控..."
    kill $MONITOR_PID 2>/dev/null || true
fi

echo "LiveTalking 已停止"
