FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 升級 pip
RUN pip install --upgrade pip

# 先安裝 PyTorch (CUDA 版本)
RUN pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118

# 安裝其他依賴
COPY requirements.txt .
RUN pip install -r requirements.txt

# 複製應用程式碼
COPY . .

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/docs || exit 1

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]


