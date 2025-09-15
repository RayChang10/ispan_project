#!/usr/bin/env python3
"""
簡化的 HTTP 代理包裝器
只負責將請求轉發到 FastAPI 主服務
"""

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SimpleHTTPProxy(BaseHTTPRequestHandler):
    """簡化的 HTTP 代理 - 只負責轉發"""

    def do_GET(self):
        """處理 GET 請求 - 重定向到主服務"""
        if self.path == "/":
            # 重定向到 FastAPI 主服務
            self.send_response(302)
            self.send_header("Location", "http://localhost:5000")
            self.end_headers()
        else:
            # 轉發其他 GET 請求
            self.forward_request("GET")

    def do_POST(self):
        """處理 POST 請求 - 轉發到主服務"""
        self.forward_request("POST")

    def do_OPTIONS(self):
        """處理 CORS 預檢請求"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def forward_request(self, method: str):
        """轉發請求到 FastAPI 主服務或 LiveTalking 服務"""
        try:
            # 檢查是否為 LiveTalking 請求
            if self.path.startswith("/ltapi/"):
                # 代理到 LiveTalking 服務
                livetalking_url = os.getenv("LIVETALKING_URL", "http://fastmcp-livetalking-simple:8010")
                target_url = f"{livetalking_url}{self.path[6:]}"  # 移除 /ltapi 前綴
                logger.info(f"代理 LiveTalking 請求: {self.path} -> {target_url}")
            else:
                # 轉發到 FastAPI 主服務
                fastapi_url = os.getenv("FASTAPI_URL", "http://127.0.0.1:5000")
                target_url = f"{fastapi_url}{self.path}"
            
            headers = {}
            data = None
            
            if method == "POST":
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length > 0:
                    data = self.rfile.read(content_length)
                    headers["Content-Type"] = self.headers.get("Content-Type", "application/json")
            
            # 轉發請求
            if method == "GET":
                response = requests.get(target_url, headers=headers, timeout=120)
            else:
                response = requests.post(target_url, data=data, headers=headers, timeout=120)
            
            # 返回回應
            self.send_response(response.status_code)
            
            # 複製回應標頭
            for key, value in response.headers.items():
                if key.lower() not in ['transfer-encoding', 'connection']:
                    self.send_header(key, value)
            
            # 添加 CORS 標頭
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            # 發送回應內容
            self.wfile.write(response.content)
            
        except requests.exceptions.ConnectionError:
            logger.error(f"無法連接到主服務: {fastapi_url}")
            self.send_error_response(502, "主服務不可用")
        except requests.exceptions.Timeout:
            logger.error("請求超時")
            self.send_error_response(504, "請求超時")
        except Exception as e:
            logger.error(f"轉發請求失敗: {e}")
            self.send_error_response(500, f"代理錯誤: {str(e)}")

    def send_error_response(self, status_code: int, message: str):
        """發送錯誤回應"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        error_response = {
            "success": False,
            "error": message,
            "status_code": status_code
        }
        self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        """自定義日誌格式"""
        logger.info(f"{self.address_string()} - {format % args}")


def main():
    """主函數"""
    port = int(os.getenv("HTTP_PROXY_PORT", "8080"))
    fastapi_url = os.getenv("FASTAPI_URL", "http://127.0.0.1:5000")
    
    try:
        server = HTTPServer(("0.0.0.0", port), SimpleHTTPProxy)
        logger.info(f"🚀 啟動 HTTP 代理服務 - http://0.0.0.0:{port}")
        logger.info(f"📍 轉發目標：{fastapi_url}")
        logger.info("按 Ctrl+C 停止服務")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("服務被用戶中斷")
    except Exception as e:
        logger.error(f"服務啟動失敗: {e}")
    finally:
        logger.info("代理服務關閉")


if __name__ == "__main__":
    main()