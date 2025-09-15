#!/usr/bin/env python3
"""
LiveTalking GPU 應用程式
支援 GPU 加速的即時語音合成
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# 設定日誌
# 確保 logs 目錄存在
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/livetalking.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_gpu():
    """檢查 GPU 可用性"""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"GPU 可用: {gpu_name} (共 {gpu_count} 個)")
            return True
        else:
            logger.warning("GPU 不可用，將使用 CPU")
            return False
    except ImportError:
        logger.error("PyTorch 未安裝")
        return False

def main():
    parser = argparse.ArgumentParser(description='LiveTalking GPU 應用程式')
    parser.add_argument('--host', default='0.0.0.0', help='主機地址')
    parser.add_argument('--port', type=int, default=8010, help='端口號')
    parser.add_argument('--debug', action='store_true', help='除錯模式')
    
    args = parser.parse_args()
    
    # 檢查 GPU
    gpu_available = check_gpu()
    
    # 創建必要的目錄
    Path('models').mkdir(exist_ok=True)
    Path('outputs').mkdir(exist_ok=True)
    Path('logs').mkdir(exist_ok=True)
    
    logger.info(f"LiveTalking 啟動中...")
    logger.info(f"主機: {args.host}:{args.port}")
    logger.info(f"GPU 支援: {'是' if gpu_available else '否'}")
    
    # 這裡可以添加您的 LiveTalking 應用程式邏輯
    # 例如啟動 FastAPI 或 Gradio 服務
    
    try:
        # 模擬應用程式運行
        import time
        while True:
            logger.info("LiveTalking 服務運行中...")
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("LiveTalking 服務已停止")

if __name__ == '__main__':
    main()