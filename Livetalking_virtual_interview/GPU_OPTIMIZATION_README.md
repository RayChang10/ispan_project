# LiveTalking GPU 優化指南

## 概述

本指南說明如何將 LiveTalking 虛擬面試系統優化為使用 GPU 運行，以提升性能和響應速度。

## 系統要求

### 硬體要求
- **NVIDIA GPU**: 支援 CUDA 的 GPU（建議 RTX 2060 或更高）
- **記憶體**: 至少 6GB GPU 記憶體
- **系統記憶體**: 至少 16GB RAM

### 軟體要求
- **作業系統**: Linux (Ubuntu 18.04+) 或 WSL2
- **CUDA**: 11.8 或更高版本
- **cuDNN**: 8.6 或更高版本
- **Python**: 3.8 或更高版本
- **PyTorch**: 2.0 或更高版本（CUDA 版本）
- **Docker**: 20.10+ 和 Docker Compose 2.0+
- **NVIDIA Container Toolkit**: 最新版本

## 安裝步驟

### 1. 安裝 NVIDIA 驅動和 CUDA

#### Ubuntu/Debian:
```bash
# 更新系統
sudo apt update && sudo apt upgrade

# 安裝 NVIDIA 驅動
sudo apt install nvidia-driver-535

# 安裝 CUDA Toolkit
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin
sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600
sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub
sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/ /"
sudo apt update
sudo apt install cuda-toolkit-12-2

# 設置環境變數
echo 'export PATH=/usr/local/cuda-12.2/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.2/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

#### WSL2:
```bash
# 在 Windows 上安裝 NVIDIA 驅動
# 下載並安裝: https://developer.nvidia.com/cuda/wsl

# 在 WSL2 中安裝 CUDA
sudo apt update
sudo apt install nvidia-cuda-toolkit
```

### 2. 安裝 Docker 和 NVIDIA Container Toolkit

```bash
# 安裝 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安裝 NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# 驗證安裝
sudo docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi
```

### 3. 驗證安裝

```bash
# 檢查 CUDA
nvidia-smi

# 檢查 Docker
docker --version
docker-compose --version

# 檢查 NVIDIA Container Toolkit
sudo docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi
```

## 使用方法

### 1. 使用 Docker Compose 啟動（推薦）

#### 啟動 GPU 版本：
```bash
# 在專案根目錄執行
docker-compose --profile gpu up -d

# 查看服務狀態
docker-compose ps

# 查看日誌
docker-compose logs -f livetalking
```

#### 啟動 CPU 版本：
```bash
# 啟動簡化版（無需 GPU）
docker-compose --profile cpu up -d

# 查看服務狀態
docker-compose ps
```

#### 啟動完整版（包含所有服務）：
```bash
# 啟動所有服務，包括 GPU 版本
docker-compose --profile full up -d
```

### 2. 服務配置說明

#### GPU 版本 (`livetalking`):
- **端口**: 8010 (host 網路模式)
- **模型**: wav2lip
- **編碼器**: NVIDIA NVENC
- **批次大小**: 自動優化
- **網路**: host 模式（解決 WebRTC ICE 連接問題）

#### CPU 版本 (`livetalking-simple`):
- **端口**: 8010
- **模型**: simple
- **編碼器**: 軟體編碼
- **批次大小**: 較小
- **網路**: bridge 模式

### 3. 環境變數配置

GPU 版本的主要環境變數：
```bash
# GPU 設置
NVIDIA_VISIBLE_DEVICES=all
LIVETALKING_MODE=webrtc
LIVETALKING_MODEL=wav2lip

# FFmpeg 硬體編碼器
FFMPEG_HWACCEL=nvdec
FFMPEG_VIDEO_CODEC=h264_nvenc
FFMPEG_AUDIO_CODEC=aac

# WebRTC 編碼器
AIORTC_VIDEO_CODEC=h264_nvenc
AIORTC_AUDIO_CODEC=aac
```

### 4. 常用 Docker 命令

```bash
# 啟動服務
docker-compose --profile gpu up -d

# 停止服務
docker-compose down

# 重啟服務
docker-compose restart

# 查看日誌
docker-compose logs -f livetalking

# 進入容器
docker exec -it fastmcp-livetalking bash

# 查看 GPU 使用情況
docker exec fastmcp-livetalking nvidia-smi

# 清理
docker-compose down --rmi all --volumes
```

## 優化特性

### 1. Docker 容器優化
- **NVIDIA Container Toolkit**: 完整的 GPU 支援
- **CUDA 11.8**: 穩定的 CUDA 版本
- **Host 網路模式**: 解決 WebRTC 連接問題
- **GPU 資源預留**: 確保 GPU 可用性

### 2. FFmpeg 硬體編碼器
- **NVIDIA NVENC**: 硬體視訊編碼
- **NVIDIA NVDEC**: 硬體視訊解碼
- **高品質預設**: 使用最高品質編碼參數

### 3. WebRTC 優化
- **H.264 硬體編碼器**: 優先使用硬體編碼
- **ICE 連接優化**: 使用 host 網路模式
- **編碼器自動選擇**: 根據硬體能力選擇最佳編碼器

## 性能調優

### 1. 批次大小調整

根據 GPU 記憶體調整批次大小：

```bash
# 在 docker-compose.yml 中修改環境變數
environment:
  - LIVETALKING_BATCH_SIZE=32  # 高記憶體 GPU
  - LIVETALKING_BATCH_SIZE=16  # 中等記憶體 GPU
  - LIVETALKING_BATCH_SIZE=8   # 低記憶體 GPU
```

### 2. 記憶體優化

```bash
# 在 docker-compose.yml 中添加記憶體限制
deploy:
  resources:
    limits:
      memory: 8G
    reservations:
      memory: 4G
      devices:
        - capabilities: [ gpu ]
```

### 3. 網路優化

```bash
# 使用 host 網路模式（已在配置中啟用）
network_mode: host

# 或者使用自定義網路
networks:
  - livetalking-network
```

## 故障排除

### 1. Docker 相關錯誤

**錯誤**: `nvidia-docker not found`
```bash
# 解決方案：安裝 NVIDIA Container Toolkit
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

**錯誤**: `CUDA driver version is insufficient`
```bash
# 解決方案：更新 NVIDIA 驅動
sudo apt update
sudo apt install nvidia-driver-535
```

### 2. WebRTC 連接問題

**問題**: WebRTC 無法建立連接
```bash
# 解決方案：使用 host 網路模式
network_mode: host

# 或者檢查防火牆設置
sudo ufw allow 8010
```

### 3. 性能問題

**問題**: GPU 使用率低
```bash
# 檢查容器內的 GPU 狀態
docker exec fastmcp-livetalking nvidia-smi

# 檢查模型是否在 GPU 上
docker exec fastmcp-livetalking python3 -c "
import torch
print(f'CUDA 可用: {torch.cuda.is_available()}')
print(f'GPU 數量: {torch.cuda.device_count()}')
"
```

## 性能基準

### 測試環境
- **GPU**: NVIDIA RTX 3080 (10GB)
- **CPU**: AMD Ryzen 7 5800X
- **記憶體**: 32GB DDR4
- **Docker**: 24.0.5
- **NVIDIA Container Toolkit**: 1.14.0

### 性能結果
- **CPU 模式**: ~15 FPS
- **GPU 模式**: ~45 FPS
- **性能提升**: 3x

### 記憶體使用
- **GPU 記憶體**: 4-6 GB
- **容器記憶體**: 6-8 GB

## 進階配置

### 1. 多 GPU 支援

```yaml
# 在 docker-compose.yml 中
deploy:
  resources:
    reservations:
      devices:
        - capabilities: [ gpu ]
          count: 2  # 使用 2 個 GPU
```

### 2. 自定義編碼器參數

```yaml
# 在環境變數中添加
environment:
  - NVENC_PRESET=p7
  - NVENC_TUNE=hq
  - NVENC_RC=vbr
  - NVENC_BITRATE=5000
```

### 3. 監控和日誌

```bash
# 實時監控 GPU 使用情況
watch -n 1 docker exec fastmcp-livetalking nvidia-smi

# 查看詳細日誌
docker-compose logs -f livetalking

# 查看容器資源使用
docker stats fastmcp-livetalking
```

## 支援和回饋

如果遇到問題或有改進建議，請：

1. 檢查本指南的故障排除部分
2. 查看 Docker 容器日誌
3. 確認 NVIDIA Container Toolkit 配置
4. 提交新的 Issue 或 Pull Request

## 更新日誌

- **v1.0.0**: 初始 GPU 優化版本
- **v1.1.0**: 添加 Docker 容器化支援
- **v1.2.0**: 改進 FFmpeg 硬體編碼器支援
- **v1.3.0**: 添加 Docker Compose 配置
- **v1.4.0**: 整合到主專案 Docker 配置
