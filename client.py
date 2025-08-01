import asyncio
import json
import logging
import sys
from typing import Any, Dict

# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class MCPStdioClient:
    def __init__(self, proc: asyncio.subprocess.Process):
        self.proc = proc
        self.lock = asyncio.Lock()
        self.request_id = 1

    async def send_jsonrpc_request(
        self, method: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """發送 JSON-RPC 2.0 請求"""
        async with self.lock:
            message = {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": method,
                "params": params,
            }
            self.request_id += 1

            if self.proc.stdin is None:
                raise Exception("stdin 不可用")
            self.proc.stdin.write((json.dumps(message) + "\n").encode())
            await self.proc.stdin.drain()

            logger.info(f"📨 發送訊息: {message}")

            try:
                if self.proc.stdout is None:
                    raise Exception("stdout 不可用")
                response_line = await asyncio.wait_for(
                    self.proc.stdout.readline(), timeout=10
                )

                if response_line:
                    response = json.loads(response_line.decode())
                    logger.info(f"📩 收到回應: {response}")
                    return response
                else:
                    if self.proc.stderr is None:
                        raise Exception("stderr 不可用")
                    stderr_output = await self.proc.stderr.read()
                    logger.error(f"⚠️ 沒有收到回應，stderr: {stderr_output.decode()}")
                    raise Exception("沒有收到回應")

            except asyncio.TimeoutError:
                if self.proc.stderr is None:
                    raise Exception("stderr 不可用")
                stderr_output = await self.proc.stderr.read()
                logger.error(f"❌ 請求逾時! stderr: {stderr_output.decode()}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON 解析錯誤: {e}")
                raise

    async def send_notification(
        self, method: str, params: Dict[str, Any] | None = None
    ):
        """發送 JSON-RPC 2.0 通知（無需回應）"""
        async with self.lock:
            message: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
            if params:
                message["params"] = params

            if self.proc.stdin is None:
                raise Exception("stdin 不可用")
            self.proc.stdin.write((json.dumps(message) + "\n").encode())
            await self.proc.stdin.drain()
            logger.info(f"📨 發送通知: {message}")

    async def initialize(self):
        """初始化 MCP 連接"""
        logger.info("🔧 開始初始化 MCP 連接...")

        # Step 1: 發送初始化請求
        init_response = await self.send_jsonrpc_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "multi-agent-client", "version": "1.0.0"},
            },
        )

        if "error" in init_response:
            raise Exception(f"初始化失敗: {init_response['error']}")

        logger.info("✅ 初始化成功")

        # Step 2: 發送初始化完成通知
        await self.send_notification("notifications/initialized")
        logger.info("✅ 初始化完成通知已發送")

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """呼叫工具"""
        response = await self.send_jsonrpc_request(
            "tools/call", {"name": tool_name, "arguments": arguments}
        )

        if "error" in response:
            raise Exception(f"工具呼叫失敗: {response['error']}")

        return response.get("result", {})


async def main():
    proc = await asyncio.create_subprocess_exec(
        "python",
        "server.py",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    client = MCPStdioClient(proc)

    try:
        # 初始化連接
        await client.initialize()

        # Step 1：履歷分析
        print("\n📤 分析履歷中...")
        resume_text = "I have 3 years experience in Python and data analysis. I also know JavaScript and machine learning."

        skills_response = await client.call_tool(
            "resume_analysis", {"resume_text": resume_text}
        )

        print("✅ 擷取技能:", skills_response)
        extracted_skills = skills_response.get("skills", [])

        # Step 2：根據技能推薦職缺
        print("\n📤 推薦職缺中...")

        jobs_response = await client.call_tool(
            "job_recommendation", {"skills": extracted_skills}
        )

        print("🎯 推薦職缺:", jobs_response)

        # 額外測試其他工具
        print("\n📤 測試其他工具...")

        # 測試問候功能
        greet_response = await client.call_tool("greet_user", {"name": "測試用戶"})
        print("👋 問候回應:", greet_response)

        # 測試計算功能
        calc_response = await client.call_tool("add_numbers", {"a": 10, "b": 15})
        print("🧮 計算結果:", calc_response)

    except Exception as e:
        logger.error(f"❌ 發生錯誤: {e}")
    finally:
        # 結束通訊
        if proc.stdin is not None:
            proc.stdin.close()
        await proc.wait()
        logger.info("🔚 客戶端結束")


if __name__ == "__main__":
    asyncio.run(main())
