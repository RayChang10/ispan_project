# LiveTalking GPU Docker Compose 配置

## 功能說明
- 使用 NVIDIA CUDA 11.8 基礎映像
- 支援 GPU 加速運算
- 自動安裝 Python 依賴
- 包含 Redis 快取服務

## 使用方法

### 1. 啟動服務
```bash
docker compose up -d
```

### 2. 查看日誌
```bash
docker compose logs -f livetalking
```

### 3. 停止服務
```bash
docker compose down
```

### 4. 重新構建
```bash
docker compose up --build
```

## 目錄結構
```
FastMCP-FastAgent2/
├── docker-compose.yml
├── livetalking/          # LiveTalking 應用程式碼
├── models/              # 模型檔案
├── outputs/             # 輸出檔案
└── logs/                # 日誌檔案
```

## GPU 支援
- 需要安裝 NVIDIA Container Toolkit
- 需要支援 CUDA 的 GPU
- 在 WSL2 中需要額外設定

## 端口說明
- 8000: LiveTalking API 服務
- 7860: Gradio Web 介面
- 6379: Redis 快取服務