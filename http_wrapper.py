#!/usr/bin/env python3
"""
簡單的 HTTP 包裝器，讓瀏覽器可以直接使用 MCP 工具
整合 tools 模組
"""

import json
import logging
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 導入 tools 模組
try:
    from tools.answer_analyzer import answer_analyzer
    from tools.interactive_interview import InteractiveInterview
    from tools.question_manager import question_manager

    logger.info("✅ Tools 模組導入成功")
except ImportError as e:
    logger.error(f"❌ Tools 模組導入失敗: {e}")
    sys.exit(1)

# 導入你的 MCP 伺服器工具
try:
    from server import (
        analyze_user_answer,
        conduct_interview,
        get_analysis_history,
        get_question_by_category,
        get_question_by_difficulty,
        get_question_history,
        get_random_question,
        get_standard_answer,
        provide_answer_with_context,
    )

    # 標記 MCP 工具可用
    MCP_TOOLS_AVAILABLE = True
    logger.info("✅ MCP 工具導入成功")
except ImportError as e:
    logger.warning(f"⚠️ MCP 工具導入失敗: {e}")
    MCP_TOOLS_AVAILABLE = False


class MCPHTTPHandler(BaseHTTPRequestHandler):
    """MCP HTTP 處理器"""

    # 類變數，用於存儲面試狀態
    current_interview = None
    interview_sessions = {}

    def __init__(self, *args, **kwargs):
        # 初始化面試工具
        self.interviewer = InteractiveInterview()

        # 調用父類的 __init__
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """處理 GET 請求"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # 讀取並返回 chat_interface.html
            try:
                with open("chat_interface.html", "r", encoding="utf-8") as f:
                    html_content = f.read()
                self.wfile.write(html_content.encode("utf-8"))
            except FileNotFoundError:
                self.wfile.write(b"chat_interface.html not found")
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        """處理 POST 請求"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == "/api/chat":
            # 讀取請求內容
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)

            try:
                data = json.loads(post_data.decode("utf-8"))
                message = data.get("message", "")

                # 處理聊天訊息
                result = self.process_chat_message(message)

                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

            except Exception as e:
                logger.error(f"聊天處理錯誤: {e}")
                self.send_response(500)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
                )
        else:
            self.send_response(404)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                json.dumps({"error": "端點不存在"}, ensure_ascii=False).encode("utf-8")
            )

    def do_OPTIONS(self):
        """處理 CORS 預檢請求"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def process_chat_message(self, message):
        """處理聊天訊息 - 優先使用你的 MCP 工具"""
        logger.info(f"處理訊息: {message}")

        # 優先使用你的 MCP 工具
        if MCP_TOOLS_AVAILABLE:
            try:
                # 檢查是否在面試狀態中
                session_id = "default_session"
                current_interview = MCPHTTPHandler.interview_sessions.get(session_id)

                # 如果當前有面試問題，且用戶的回答不是面試相關關鍵字，則分析答案
                if current_interview and not any(
                    word in message.lower()
                    for word in [
                        "面試",
                        "問題",
                        "開始面試",
                        "你好",
                        "hello",
                        "hi",
                        "新問題",
                        "下一個",
                        "標準答案",
                        "conduct",
                        "conduct_interview",
                    ]
                ):
                    logger.info(f"🎯 使用 MCP 工具分析面試答案: {message}")
                    try:
                        # 使用你的 MCP 工具分析答案
                        analysis_result = analyze_user_answer(
                            user_answer=message,
                            question=current_interview.get("question", ""),
                            standard_answer=current_interview.get(
                                "standard_answer", ""
                            ),
                        )

                        # 清除當前面試會話，準備下一個問題
                        MCPHTTPHandler.interview_sessions[session_id] = None
                        logger.info(f"✅ 已清除面試會話: {session_id}")

                        if analysis_result.get("status") == "success":
                            return {
                                "response": f"""📊 MCP 工具分析結果：

問題：{current_interview.get('question', '')}
您的答案：{message}

評分：{analysis_result.get('score', 'N/A')}/100
相似度：{analysis_result.get('similarity', 'N/A')}
反饋：{analysis_result.get('feedback', '無反饋')}

標準答案：{current_interview.get('standard_answer', '')}""",
                                "tool_used": "mcp_analyze_user_answer",
                                "confidence": 0.95,
                                "reason": "MCP 工具分析",
                            }
                        else:
                            return {
                                "response": f"分析失敗：{analysis_result.get('message', '未知錯誤')}",
                                "tool_used": "mcp_analyze_user_answer",
                                "confidence": 0.0,
                                "reason": "MCP 工具分析失敗",
                            }
                    except Exception as e:
                        logger.error(f"❌ MCP 工具分析失敗: {e}")
                        return {
                            "response": f"抱歉，MCP 工具分析時發生錯誤：{str(e)}",
                            "tool_used": "mcp_analyze_user_answer",
                            "confidence": 0.0,
                            "reason": "MCP 工具分析錯誤",
                        }

                # 自然語言處理
                lower_message = message.lower()
                logger.info(f"🔍 分析訊息: '{message}' -> '{lower_message}'")

                # 面試問題相關 - 優先處理
                interview_keywords = ["面試", "問題", "開始面試", "新問題", "下一個"]
                if any(word in lower_message for word in interview_keywords):
                    logger.info(f"🎯 使用 MCP 工具獲取面試問題: {lower_message}")
                    try:
                        # 使用你的 MCP 工具獲取問題
                        result = get_random_question()
                        logger.info(f"📝 MCP 工具獲取到的面試問題: {result}")

                        if result.get("status") == "success":
                            question = result.get("question", "無法獲取面試問題")
                            source = result.get("source", "未知來源")
                            category = result.get("category", "一般問題")
                            difficulty = result.get("difficulty", "中等")
                            standard_answer = result.get(
                                "standard_answer", "標準答案未提供"
                            )

                            response = f"""🎯 MCP 工具面試問題：

問題：{question}
類別：{category}
難度：{difficulty}
來源：{source}

請在下方輸入您的回答："""

                            # 保存面試問題到會話
                            MCPHTTPHandler.interview_sessions[session_id] = {
                                "question": question,
                                "source": source,
                                "standard_answer": standard_answer,
                                "timestamp": time.time(),
                            }
                            logger.info(f"✅ 已保存 MCP 面試會話: {session_id}")

                            return {
                                "response": response,
                                "tool_used": "mcp_get_random_question",
                                "confidence": 0.95,
                                "reason": "MCP 工具面試問題",
                            }
                        else:
                            return {
                                "response": f"獲取問題失敗：{result.get('message', '未知錯誤')}",
                                "tool_used": "mcp_get_random_question",
                                "confidence": 0.0,
                                "reason": "MCP 工具獲取問題失敗",
                            }
                    except Exception as e:
                        logger.error(f"❌ MCP 工具獲取問題失敗: {e}")
                        return {
                            "response": f"抱歉，MCP 工具獲取問題時發生錯誤：{str(e)}",
                            "tool_used": "mcp_get_random_question",
                            "confidence": 0.0,
                            "reason": "MCP 工具獲取問題錯誤",
                        }

                # 標準答案相關
                if any(
                    word in lower_message for word in ["標準答案", "正確答案", "答案"]
                ):
                    logger.info(f"🎯 使用 MCP 工具獲取標準答案: {lower_message}")
                    try:
                        if current_interview:
                            question = current_interview.get("question", "")
                            result = get_standard_answer(question=question)
                        else:
                            result = get_standard_answer()

                        if result.get("status") == "success":
                            return {
                                "response": f"""✅ MCP 工具標準答案：

問題：{result.get('question', '')}
標準答案：{result.get('standard_answer', '')}
來源：{result.get('source', '')}""",
                                "tool_used": "mcp_get_standard_answer",
                                "confidence": 0.95,
                                "reason": "MCP 工具標準答案",
                            }
                        else:
                            return {
                                "response": f"獲取標準答案失敗：{result.get('message', '未知錯誤')}",
                                "tool_used": "mcp_get_standard_answer",
                                "confidence": 0.0,
                                "reason": "MCP 工具標準答案失敗",
                            }
                    except Exception as e:
                        logger.error(f"❌ MCP 工具獲取標準答案失敗: {e}")
                        return {
                            "response": f"抱歉，MCP 工具獲取標準答案時發生錯誤：{str(e)}",
                            "tool_used": "mcp_get_standard_answer",
                            "confidence": 0.0,
                            "reason": "MCP 工具標準答案錯誤",
                        }

                # 進行面試相關
                if any(
                    word in lower_message
                    for word in ["conduct", "conduct_interview", "進行面試"]
                ):
                    logger.info(f"🎯 使用 MCP 工具進行面試: {lower_message}")
                    try:
                        result = conduct_interview()
                        if result.get("status") == "success":
                            return {
                                "response": f"""🤖 MCP 工具面試系統：

{result.get('message', '面試已開始')}""",
                                "tool_used": "mcp_conduct_interview",
                                "confidence": 0.95,
                                "reason": "MCP 工具面試系統",
                            }
                        else:
                            return {
                                "response": f"面試失敗：{result.get('message', '未知錯誤')}",
                                "tool_used": "mcp_conduct_interview",
                                "confidence": 0.0,
                                "reason": "MCP 工具面試失敗",
                            }
                    except Exception as e:
                        logger.error(f"❌ MCP 工具面試失敗: {e}")
                        return {
                            "response": f"抱歉，MCP 工具面試時發生錯誤：{str(e)}",
                            "tool_used": "mcp_conduct_interview",
                            "confidence": 0.0,
                            "reason": "MCP 工具面試錯誤",
                        }
            except Exception as e:
                logger.error(f"❌ MCP 工具處理失敗: {e}")
                # 如果 MCP 工具失敗，回退到原始邏輯
                pass

        # 回退到原始邏輯（如果 MCP 工具不可用或失敗）
        logger.info("📝 回退到原始邏輯")
        session_id = "default_session"
        current_interview = MCPHTTPHandler.interview_sessions.get(session_id)

        # 問候相關
        if any(word in lower_message for word in ["你好", "hello", "hi"]):
            name = self.extract_name(message)
            greeting = f"你好，{name or '朋友'}！歡迎使用智能面試系統！\n\n我可以幫您：\n1. 獲取面試問題\n2. 分析您的回答\n\n請輸入「面試」或「問題」開始面試！"
            return {
                "response": greeting,
                "tool_used": "greet_user",
                "confidence": 0.9,
                "reason": "問候功能",
            }

        # 計算相關
        if any(word in lower_message for word in ["計算", "加", "+"]):
            numbers = self.extract_numbers(message)
            if len(numbers) >= 2:
                result = numbers[0] + numbers[1]
                return {
                    "response": f"計算結果：{numbers[0]} + {numbers[1]} = {result}",
                    "tool_used": "add_numbers",
                    "confidence": 0.9,
                    "reason": "計算功能",
                }

        # 預設回應
        logger.info("📝 沒有匹配到特定功能，使用預設回應")
        return {
            "response": "您好！我是智能面試助手。\n\n請輸入：\n• 「面試」或「問題」- 開始面試\n• 回答問題 - 我會分析您的任何回答\n• 「標準答案」- 查看正確答案\n\n開始您的面試之旅吧！",
            "tool_used": "default_response",
            "confidence": 0.7,
            "reason": "預設回應",
        }

    def analyze_interview_answer(self, user_answer, interview_data):
        """分析面試答案"""
        try:
            # 使用 tools 模組的答案分析器
            standard_answer = interview_data.get("standard_answer", "標準答案未提供")
            question = interview_data.get("question", "未知問題")

            logger.info(f"分析答案 - 問題: {question}")
            logger.info(f"分析答案 - 用戶回答: {user_answer}")
            logger.info(f"分析答案 - 標準答案: {standard_answer}")

            analysis = answer_analyzer.analyze_answer(user_answer, standard_answer)

            score = analysis.get("score", 0)
            grade = analysis.get("grade", "未知")
            similarity = analysis.get("similarity", 0)
            feedback = analysis.get("feedback", "無反饋")

            return f"""📝 面試答案分析：

問題：{question}
您的答案：{user_answer}

評分：{score}/100 ({grade})
相似度：{similarity:.1%}
反饋：{feedback}

標準答案：{standard_answer}

建議：請繼續努力，多練習相關技術概念！"""

        except Exception as e:
            logger.error(f"❌ 分析面試答案時發生錯誤: {e}")
            return f"抱歉，分析答案時發生錯誤。錯誤詳情：{str(e)}"

    def extract_name(self, message):
        """提取姓名"""
        import re

        name_match = re.search(r"我叫(.+?)(?:\s|$)", message) or re.search(
            r"我是(.+?)(?:\s|$)", message
        )
        return name_match.group(1).strip() if name_match else ""

    def extract_numbers(self, message):
        """提取數字"""
        import re

        numbers = re.findall(r"\d+", message)
        return [int(n) for n in numbers]

    def log_message(self, format, *args):
        """自定義日誌格式"""
        logger.info(f"HTTP {format % args}")


def main():
    """主函數"""
    port = 8080

    try:
        server = HTTPServer(("localhost", port), MCPHTTPHandler)
        logger.info(f"🚀 啟動 MCP HTTP 包裝器 - http://localhost:{port}")
        logger.info("按 Ctrl+C 停止伺服器")
        server.serve_forever()

    except KeyboardInterrupt:
        logger.info("伺服器被用戶中斷")
    except Exception as e:
        logger.error(f"伺服器啟動失敗: {e}")
    finally:
        logger.info("伺服器關閉")


if __name__ == "__main__":
    main()
