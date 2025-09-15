#!/usr/bin/env python3
"""
統一配置檔案 - 解決網址設定重複問題
"""

import os
from typing import Any, Dict


class Config:
    """統一配置類別"""

    # 服務埠號配置
    PORTS = {
        "virtual_interviewer": 5000,  # 虛擬面試系統
        "http_wrapper": 8080,  # HTTP API 包裝器
        "mcp_server": 8000,  # MCP 伺服器
        "fast_agent": 3000,  # Fast Agent (預留)
        "websocket_fay": 8080,  # FAY WebSocket
        "websocket_speech": 5000,  # 語音 WebSocket
    }

    # 主機配置
    HOST = "localhost"

    # MongoDB 配置（允許環境變數覆蓋）
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")

    # 服務 URL 配置
    @classmethod
    def get_service_urls(cls) -> Dict[str, str]:
        """獲取所有服務的 URL"""
        return {
            "virtual_interviewer": f"http://{cls.HOST}:{cls.PORTS['virtual_interviewer']}",
            "http_wrapper": f"http://{cls.HOST}:{cls.PORTS['http_wrapper']}",
            "mcp_server": f"http://{cls.HOST}:{cls.PORTS['mcp_server']}",
            "fast_agent": f"http://{cls.HOST}:{cls.PORTS['fast_agent']}",
        }

    @classmethod
    def get_api_endpoints(cls) -> Dict[str, str]:
        """獲取所有 API 端點"""
        return {
            "virtual_interviewer": f"http://{cls.HOST}:{cls.PORTS['virtual_interviewer']}/api/interview",
            "http_wrapper": f"http://{cls.HOST}:{cls.PORTS['http_wrapper']}/api/chat",
            "mcp_server": f"http://{cls.HOST}:{cls.PORTS['mcp_server']}/api/chat",
        }

    @classmethod
    def get_websocket_urls(cls) -> Dict[str, str]:
        """獲取所有 WebSocket URL"""
        return {
            "fay": f"ws://{cls.HOST}:{cls.PORTS['websocket_fay']}/fay",
            "speech": f"ws://{cls.HOST}:{cls.PORTS['websocket_speech']}/speech-realtime",
        }

    @classmethod
    def get_port(cls, service_name: str) -> int:
        """獲取指定服務的埠號"""
        return cls.PORTS.get(service_name, 8000)

    @classmethod
    def get_url(cls, service_name: str) -> str:
        """獲取指定服務的 URL"""
        return f"http://{cls.HOST}:{cls.PORTS.get(service_name, 8000)}"

    @classmethod
    def get_api_url(cls, service_name: str) -> str:
        """獲取指定服務的 API URL"""
        if service_name == "virtual_interviewer":
            return (
                f"http://{cls.HOST}:{cls.PORTS.get(service_name, 5000)}/api/interview"
            )
        elif service_name == "http_wrapper":
            return f"http://{cls.HOST}:{cls.PORTS.get(service_name, 8080)}/api/chat"
        else:
            return f"http://{cls.HOST}:{cls.PORTS.get(service_name, 8000)}/api/chat"


# 創建全域配置實例
config = Config()

# 導出常用配置
__all__ = ["Config", "config"]
