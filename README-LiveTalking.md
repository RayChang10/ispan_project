# LiveTalking 虛擬人整合指南

本專案已整合 [LiveTalking](https://github.com/lipku/LiveTalking) 實時互動流式數字人系統，實現音視頻同步對話功能。

## 🚀 快速開始

### 1. 準備模型檔案

在啟動前，您需要下載必要的模型檔案：

#### 下載連結
- **夸克雲盤**: https://pan.quark.cn/s/83a750323ef0
- **Google Drive**: https://drive.google.com/drive/folders/1FOC_MD6wdogyyX_7V1d4NDIO7P9NlSAJ

#### 檔案配置
1. 下載 `wav2lip256.pth`，放置到 `models/` 目錄並重命名為 `wav2lip.pth`
2. 下載 `wav2lip256_avatar1.tar.gz`，解壓後將整個 `wav2lip256_avatar1` 資料夾放到 `data/avatars/` 目錄

```bash
# 創建目錄結構
mkdir -p models data/avatars

# 模型檔案結構範例
models/
└── wav2lip.pth

data/avatars/
└── wav2lip256_avatar1/
    ├── avatar_info.json
    ├── face.jpg
    └── ...
```

### 2. 系統要求

#### 硬體需求
- **GPU**: NVIDIA RTX 3060 或以上 (推薦 3080Ti/4090)
- **記憶體**: 至少 8GB RAM
- **儲存**: 至少 5GB 可用空間

#### 軟體需求
- Docker >= 20.10
- Docker Compose >= 2.0
- NVIDIA Container Toolkit (用於 GPU 支援)

### 3. Docker 啟動

#### 方式一：完整系統啟動 (推薦)
```bash
# 啟動包含 LiveTalking 的完整系統
docker-compose up -d livetalking

# 查看日誌
docker-compose logs -f livetalking
```

#### 方式二：僅啟動 LiveTalking 服務
```bash
# 僅構建 LiveTalking 映像
docker build -f Dockerfile.livetalking -t fastmcp-livetalking .

# 啟動 LiveTalking 容器
docker run --gpus all -it --rm \
  -p 8010:8010 \
  -p 1985:1985 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/data:/app/data \
  -e LIVETALKING_MODEL=wav2lip \
  -e LIVETALKING_AVATAR_ID=wav2lip256_avatar1 \
  fastmcp-livetalking
```

### 4. 訪問服務

啟動成功後，您可以通過以下方式訪問：

#### 面試系統 (整合版)
- **URL**: http://localhost:8080
- **功能**: 完整面試系統 + 虛擬人功能

#### LiveTalking Dashboard (原始版)
- **URL**: http://localhost:8010/dashboard.html
- **功能**: 純虛擬人互動介面

#### API 端點
- **WebRTC API**: http://localhost:8010/webrtcapi.html
- **HTTP API**: http://localhost:8010/human (POST)

## 🎮 使用方式

### 1. 面試系統中使用虛擬人

1. 打開面試系統：http://localhost:8080
2. 在虛擬人區域點擊「開始連接」
3. 等待虛擬人載入完成
4. 開始面試，虛擬人會自動朗讀面試官的問題

### 2. 直接與虛擬人互動

1. 打開 LiveTalking Dashboard：http://localhost:8010/dashboard.html
2. 點擊「開始連接」
3. 在文字框輸入想要虛擬人說的話
4. 點擊「發送」，虛擬人會播報該文字

### 3. API 整合

```bash
# 讓虛擬人說話
curl -X POST http://localhost:8010/human \
  -H "Content-Type: application/json" \
  -d '{
    "text": "您好，歡迎參加面試！",
    "type": "echo",
    "interrupt": true,
    "sessionid": 0
  }'
```

## ⚙️ 配置選項

### 環境變數

```bash
# LiveTalking 模式 (webrtc/rtmp)
LIVETALKING_MODE=webrtc

# 使用的模型 (wav2lip/musetalk/ernerf)
LIVETALKING_MODEL=wav2lip

# Avatar ID
LIVETALKING_AVATAR_ID=wav2lip256_avatar1

# 服務端口
LIVETALKING_PORT=8010

# HuggingFace 鏡像 (中國用戶)
HF_ENDPOINT=https://hf-mirror.com
```

### 支援的模型

| 模型 | GPU 需求 | FPS 性能 | 特色 |
|------|----------|----------|------|
| wav2lip | RTX 3060+ | 60-120 | 高品質唇形同步 |
| musetalk | RTX 3080Ti+ | 42-72 | 更自然的頭部動作 |
| ernerf | RTX 3080+ | 25-45 | 神經輻射場技術 |

## 🔧 故障排除

### 常見問題

#### 1. GPU 記憶體不足
```bash
# 檢查 GPU 使用情況
nvidia-smi

# 降低批次大小或切換到較小的模型
docker-compose stop livetalking
# 修改 LIVETALKING_MODEL 環境變數
docker-compose up -d livetalking
```

#### 2. 模型載入失敗
```bash
# 檢查模型檔案是否存在
docker-compose exec livetalking ls -la /app/models/
docker-compose exec livetalking ls -la /app/data/avatars/

# 重新下載模型檔案
```

#### 3. WebRTC 連接失敗
```bash
# 檢查防火牆設定
# 確保以下端口開放：
# TCP: 8010 (LiveTalking)
# TCP: 1985 (SRS)
# UDP: 1-65536 (WebRTC)

# 檢查服務狀態
docker-compose logs livetalking
```

#### 4. 虛擬人不說話
```bash
# 檢查音訊設定
# 確保瀏覽器允許自動播放音訊

# 檢查 API 響應
curl -v http://localhost:8010/human \
  -H "Content-Type: application/json" \
  -d '{"text": "測試", "type": "echo"}'
```

### 性能優化

#### 1. GPU 優化
```bash
# 設定 GPU 記憶體增長
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

#### 2. 網路優化
```bash
# 如果在中國地區，使用鏡像加速
export HF_ENDPOINT=https://hf-mirror.com
export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
```

## 🌟 進階功能

### 1. 自定義 Avatar

您可以訓練自己的 Avatar：

1. 準備訓練資料（影片或圖片）
2. 使用 LiveTalking 的訓練腳本
3. 將訓練好的模型放到 `data/avatars/` 目錄
4. 更新 `LIVETALKING_AVATAR_ID` 環境變數

### 2. 多併發支援

LiveTalking 支援多個用戶同時使用：

```bash
# 啟動多個實例
docker-compose up -d --scale livetalking=3
```

### 3. 聲音克隆

支援自定義音色：

1. 準備音訊樣本
2. 使用支援的 TTS 引擎
3. 配置音色參數

## 📚 相關資源

- **LiveTalking 官方文檔**: https://livetalking-doc.readthedocs.io/
- **GitHub 專案**: https://github.com/lipku/LiveTalking
- **模型下載**: https://pan.quark.cn/s/83a750323ef0
- **技術交流**: LiveTalking 微信公眾號

## 🆘 支援

如果遇到問題，請：

1. 檢查本文檔的故障排除部分
2. 查看容器日誌：`docker-compose logs livetalking`
3. 訪問 LiveTalking 官方文檔
4. 在 GitHub Issues 中回報問題

---

**注意**: 本專案整合的是 LiveTalking 開源版本。商業版本提供更多進階功能，詳情請參考官方文檔。
