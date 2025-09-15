FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 系統相依套件（包含編譯工具和 PostgreSQL 開發套件）
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安裝 uv（預設安裝到 /root/.local/bin）
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
# 將 uv 加入 PATH（供後續步驟與執行時使用）
ENV PATH="/root/.local/bin:${PATH}"

# 先安裝 fast-agent-mcp 及其依賴（需要 protobuf>=5.0）
RUN uv pip install --system "protobuf>=5.0.0,<6.0.0"
RUN uv pip install --system "fast-agent-mcp>=0.2.49"

# 再安裝主系統依賴
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案原始碼
COPY . .

EXPOSE 8001

# 預設使用 uv run 執行 gunicorn（Uvicorn workers）
CMD ["bash", "-lc", "uv run gunicorn -k uvicorn.workers.UvicornWorker -w 1 backend.fastapi_app:app -b 0.0.0.0:8001 --timeout 120"]


