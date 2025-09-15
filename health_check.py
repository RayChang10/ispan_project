#!/usr/bin/env python3
"""
FastMCP-FastAgent2 健康檢查腳本
檢查所有服務的運行狀況
"""

import requests
import subprocess
import json
import time
from datetime import datetime

def check_port(port, service_name):
    """檢查端口是否在監聽"""
    try:
        result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
        if str(port) in result.stdout:
            return True, f"✅ {service_name} (端口 {port}) 正常監聽"
        else:
            return False, f"❌ {service_name} (端口 {port}) 未監聽"
    except Exception as e:
        return False, f"❌ 檢查 {service_name} 時出錯: {e}"

def check_http_endpoint(url, service_name):
    """檢查 HTTP 端點是否回應"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return True, f"✅ {service_name} ({url}) 正常回應 (HTTP {response.status_code})"
        else:
            return False, f"⚠️ {service_name} ({url}) 回應異常 (HTTP {response.status_code})"
    except requests.exceptions.RequestException as e:
        return False, f"❌ {service_name} ({url}) 無法連接: {e}"

def check_docker_container(container_name):
    """檢查 Docker 容器狀態"""
    try:
        result = subprocess.run(['docker', 'inspect', container_name], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            # 解析 JSON 輸出
            container_info = json.loads(result.stdout)[0]
            state = container_info['State']['Status']
            if state == 'running':
                return True, f"✅ {container_name} 容器正在運行"
            else:
                return False, f"⚠️ {container_name} 容器狀態: {state}"
        else:
            return False, f"❌ {container_name} 容器不存在或無法檢查"
    except Exception as e:
        return False, f"❌ 檢查 {container_name} 容器時出錯: {e}"

def main():
    """主函數"""
    print("🔍 FastMCP-FastAgent2 健康檢查")
    print("=" * 50)
    print(f"檢查時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 檢查 Docker 容器
    print("🐳 Docker 容器狀態:")
    containers = [
        'fastmcp-main',
        'fastmcp-postgres', 
        'fastmcp-mongo',
        'fastmcp-redis',
        'fastmcp-milvus',
        'fastmcp-minio',
        'fastmcp-livetalking'
    ]
    
    for container in containers:
        success, message = check_docker_container(container)
        print(f"  {message}")
    
    print()
    
    # 檢查端口監聽
    print("🔌 端口監聽狀態:")
    ports = [
        (5000, "主 API 服務"),
        (8080, "前端服務"),
        (8010, "LiveTalking 服務"),
        (9000, "MinIO S3 API"),
        (9001, "MinIO Web Console"),
        (6379, "Redis"),
        (27017, "MongoDB"),
        (19530, "Milvus")
    ]
    
    for port, service in ports:
        success, message = check_port(port, service)
        print(f"  {message}")
    
    print()
    
    # 檢查 HTTP 端點
    print("🌐 HTTP 端點檢查:")
    endpoints = [
        ("http://localhost:5000/health", "主服務健康檢查"),
        ("http://localhost:8080/", "前端服務"),
        ("http://localhost:8010/webrtcapi.html", "LiveTalking WebRTC API"),
        ("http://localhost:9001/", "MinIO Console")
    ]
    
    for url, service in endpoints:
        success, message = check_http_endpoint(url, service)
        print(f"  {message}")
    
    print()
    print("=" * 50)
    print("✅ 健康檢查完成！")

if __name__ == "__main__":
    main()
