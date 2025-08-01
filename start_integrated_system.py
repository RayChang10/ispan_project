#!/usr/bin/env python3
"""
整合智能面試系統啟動腳本
同時啟動 Fast Agent、virtual_interviewer 和 HTTP 包裝器
"""

import asyncio
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def start_fast_agent_background():
    """在背景啟動 Fast Agent"""
    try:
        logger.info("🤖 在背景啟動 Fast Agent...")

        def run_fast_agent():
            try:
                # 導入並運行 Fast Agent
                from fast_agent_interview import main as fast_agent_main

                asyncio.run(fast_agent_main())
            except Exception as e:
                logger.error(f"❌ 背景 Fast Agent 執行失敗: {e}")

        fast_agent_thread = threading.Thread(target=run_fast_agent, daemon=True)
        fast_agent_thread.start()
        logger.info("✅ Fast Agent 已在背景啟動")

    except Exception as e:
        logger.error(f"❌ Fast Agent 背景啟動失敗: {e}")


def start_virtual_interviewer_background():
    """在背景啟動虛擬面試系統"""
    try:
        logger.info("🎭 在背景啟動虛擬面試系統...")

        def run_virtual_interviewer():
            try:
                # 切換到 virtual_interviewer 目錄
                interviewer_path = Path("virtual_interviewer")
                if interviewer_path.exists():
                    os.chdir(interviewer_path)
                    if Path("run.py").exists():
                        subprocess.run([sys.executable, "run.py"], check=True)
                    else:
                        logger.error("❌ virtual_interviewer/run.py 不存在")
                else:
                    logger.error("❌ virtual_interviewer 目錄不存在")
            except Exception as e:
                logger.error(f"❌ 背景虛擬面試系統執行失敗: {e}")

        interviewer_thread = threading.Thread(
            target=run_virtual_interviewer, daemon=True
        )
        interviewer_thread.start()
        logger.info("✅ 虛擬面試系統已在背景啟動")

    except Exception as e:
        logger.error(f"❌ 虛擬面試系統背景啟動失敗: {e}")


def start_http_wrapper():
    """啟動 HTTP 包裝器"""
    try:
        from http_wrapper import main as http_main

        logger.info("🌐 啟動 HTTP 包裝器...")
        http_main()
    except Exception as e:
        logger.error(f"❌ HTTP 包裝器啟動失敗: {e}")


def test_tools_modules():
    """測試 tools 模組"""
    try:
        from tools.answer_analyzer import answer_analyzer
        from tools.question_manager import question_manager

        logger.info("🧪 測試 tools 模組...")

        # 測試問題管理器
        question = question_manager.get_random_question()
        logger.info(f"✅ 問題管理器測試成功: {question.get('question', 'N/A')}")

        # 測試答案分析器
        analysis = answer_analyzer.analyze_answer("測試回答", "標準答案")
        logger.info(f"✅ 答案分析器測試成功: 評分 {analysis.get('score', 0)}")

        logger.info("✅ 所有 tools 模組測試通過")

    except Exception as e:
        logger.error(f"❌ tools 模組測試失敗: {e}")


def create_chat_interface():
    """創建聊天介面 HTML 檔案"""
    html_content = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智能面試系統</title>
    <style>
        body {
            font-family: 'Microsoft JhengHei', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .chat-container {
            height: 400px;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px 15px;
            border-radius: 10px;
            max-width: 80%;
        }
        .user-message {
            background: #007bff;
            color: white;
            margin-left: auto;
        }
        .bot-message {
            background: #e9ecef;
            color: #333;
        }
        .input-container {
            padding: 20px;
            background: white;
            border-top: 1px solid #dee2e6;
        }
        .input-group {
            display: flex;
            gap: 10px;
        }
        #messageInput {
            flex: 1;
            padding: 12px;
            border: 2px solid #dee2e6;
            border-radius: 25px;
            font-size: 16px;
            outline: none;
        }
        #messageInput:focus {
            border-color: #667eea;
        }
        #sendButton {
            padding: 12px 25px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            transition: transform 0.2s;
        }
        #sendButton:hover {
            transform: translateY(-2px);
        }
        .status {
            text-align: center;
            padding: 10px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            font-size: 14px;
            color: #6c757d;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 10px;
            color: #6c757d;
        }
        .system-links {
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-top: 1px solid #dee2e6;
        }
        .system-links a {
            display: inline-block;
            margin: 0 10px;
            padding: 8px 16px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 20px;
            font-size: 14px;
            transition: background 0.3s;
        }
        .system-links a:hover {
            background: #5a6fd8;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 智能面試系統</h1>
            <p>支援面試問題、答案分析、標準答案等功能</p>
        </div>
        <div class="status" id="status">連接中...</div>
        <div class="chat-container" id="chatContainer">
            <div class="message bot-message">
                你好！我是智能面試助手，可以幫您：<br>
                1. 獲取面試問題<br>
                2. 分析您的回答<br>
                3. 提供標準答案<br><br>
                請告訴我您需要什麼幫助？
            </div>
        </div>
        <div class="loading" id="loading">正在處理中...</div>
        <div class="input-container">
            <div class="input-group">
                <input type="text" id="messageInput" placeholder="輸入您的問題..." />
                <button id="sendButton">發送</button>
            </div>
        </div>
        <div class="system-links">
            <a href="http://localhost:5000" target="_blank">🎭 虛擬面試系統</a>
            <a href="http://localhost:8080" target="_blank">🌐 HTTP API</a>
            <a href="http://localhost:3000" target="_blank">🤖 Fast Agent</a>
        </div>
    </div>

    <script>
        const chatContainer = document.getElementById('chatContainer');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const status = document.getElementById('status');
        const loading = document.getElementById('loading');

        function addMessage(message, isUser = false) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
            messageDiv.innerHTML = message.replace(/\\n/g, '<br>');
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function setStatus(text) {
            status.textContent = text;
        }

        function showLoading(show) {
            loading.style.display = show ? 'block' : 'none';
        }

        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;

            addMessage(message, true);
            messageInput.value = '';
            showLoading(true);

            try {
                // 嘗試多個 API 端點
                const endpoints = [
                    'http://localhost:5000/api/interview',
                    'http://localhost:8080/api/chat',
                    'http://localhost:3000/api/chat'
                ];

                let response = null;
                let data = null;

                for (const endpoint of endpoints) {
                    try {
                        const res = await fetch(endpoint, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ message: message })
                        });

                        if (res.ok) {
                            data = await res.json();
                            response = res;
                            setStatus(`使用服務: ${endpoint}`);
                            break;
                        }
                    } catch (error) {
                        console.log(`端點 ${endpoint} 不可用:`, error);
                        continue;
                    }
                }

                if (data) {
                    if (data.error) {
                        addMessage(`錯誤: ${data.error}`);
                    } else {
                        addMessage(data.response || data.message || '收到回應');
                        if (data.tool_used) {
                            setStatus(`使用工具: ${data.tool_used} (信心度: ${(data.confidence || 0.8) * 100}%)`);
                        }
                    }
                } else {
                    addMessage('所有服務都無法連接，請檢查系統狀態');
                    setStatus('連接失敗');
                }
            } catch (error) {
                addMessage(`連接錯誤: ${error.message}`);
                setStatus('連接失敗');
            } finally {
                showLoading(false);
            }
        }

        sendButton.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });

        // 檢查連接狀態
        async function checkConnection() {
            const endpoints = [
                'http://localhost:5000/api/interview',
                'http://localhost:8080/api/chat',
                'http://localhost:3000/api/chat'
            ];

            let connected = false;
            for (const endpoint of endpoints) {
                try {
                    const response = await fetch(endpoint, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: 'ping' })
                    });
                    if (response.ok) {
                        setStatus(`已連接: ${endpoint}`);
                        connected = true;
                        break;
                    }
                } catch (error) {
                    continue;
                }
            }
            
            if (!connected) {
                setStatus('未連接');
            }
        }

        // 定期檢查連接狀態
        setInterval(checkConnection, 5000);
        checkConnection();
    </script>
</body>
</html>"""

    try:
        with open("chat_interface.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info("✅ 聊天介面 HTML 檔案已創建")
    except Exception as e:
        logger.error(f"❌ 創建聊天介面失敗: {e}")


def main():
    """主函數"""
    logger.info("🚀 啟動整合智能面試系統...")

    # 創建聊天介面
    create_chat_interface()

    # 測試 tools 模組
    test_tools_modules()

    # 在背景啟動 Fast Agent
    start_fast_agent_background()

    # 在背景啟動虛擬面試系統
    start_virtual_interviewer_background()

    # 等待一下讓背景服務啟動
    logger.info("⏳ 等待背景服務啟動...")
    time.sleep(5)

    # 啟動 HTTP 包裝器作為主要介面
    logger.info("🌐 啟動 HTTP 包裝器作為主要介面...")
    start_http_wrapper()


if __name__ == "__main__":
    main()
