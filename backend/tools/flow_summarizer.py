#!/usr/bin/env python3
"""
流程總結生成器
使用 OpenAI 生成面試流程總結
"""

import json
import logging
import os
from typing import Any, Dict, List

# 可選導入 dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    # 如果沒有 dotenv，直接從環境變數讀取
    pass


try:
    from openai import OpenAI
except ImportError as e:
    OpenAI = None  # 延後在執行時再報錯，避免導入期間中止


class FlowSummarizer:
    """封裝與 OpenAI 的互動以生成會話總結。"""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("尚未設定 OPENAI_API_KEY，請在 .env 中配置後再試。")
        if OpenAI is None:
            raise ImportError("找不到 openai 套件，請先安裝: pip install openai")

        self.client = OpenAI(api_key=api_key)

    # 對外主要介面 -----------------------------------------------------------
    def generate_user_summary(self, session_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        依據會話摘要生成「使用者可讀」的最終建議。

        回傳結構包含：
        - text: 直接可顯示的卡片文案
        - insights: 結構化建議（overview/strengths/weaknesses/...）
        """

        conversation_compact = self._compact_history(
            session_summary.get("session_history", [])
        )
        prompt = self._build_prompt(session_summary, conversation_compact)

        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一位面試教練。請根據輸入的面試會話歷史，"
                        "輸出精煉、可執行、用詞禮貌且具體的建議。"
                        "只回傳 JSON，不要任何額外文字。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=1200,
        )

        raw = completion.choices[0].message.content or "{}"
        insights = self._safe_json(raw)
        text = self._format_user_text(session_summary, insights)

        return {"text": text, "insights": insights, "raw": raw}

    # Prompt 與格式 ---------------------------------------------------------
    def _build_prompt(
        self, session_summary: Dict[str, Any], compact_history: List[Dict[str, Any]]
    ) -> str:
        total_questions = session_summary.get("total_questions", 0)
        average_score = session_summary.get("average_score", 0)

        payload = {
            "meta": {
                "total_questions": total_questions,
                "average_score": average_score,
            },
            "history": compact_history,
            "requirements": {
                "format": {
                    "overview": "string",
                    "grade": "string",
                    "top_categories": ["string"],
                    "weak_categories": ["string"],
                    "self_intro": {
                        "opening": {"status": "ok|miss", "tip": "string"},
                        "background": {"status": "ok|miss", "tip": "string"},
                        "skills": {"status": "ok|miss", "tip": "string"},
                        "achievements": {"status": "ok|miss", "tip": "string"},
                        "role_match": {"status": "ok|miss", "tip": "string"},
                        "closing": {"status": "ok|miss", "tip": "string"},
                    },
                    "highlights": ["string"],
                    "gaps": ["string"],
                    "practice_checklist": ["string"],
                    "resources": ["string"],
                    "cta": "string",
                },
                "principles": [
                    "以台灣繁體中文回答",
                    "每條建議務必具體且可行",
                    "保持禮貌、鼓勵式語氣，但避免空話",
                    "若資訊不足，合理推斷但要保守",
                ],
            },
        }

        return (
            "以下是一次面試會話的精簡歷史與表現分數，請生成結構化總結：\n\n"
            + json.dumps(payload, ensure_ascii=False)
        )

    def _compact_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compact: List[Dict[str, Any]] = []
        for item in history:
            if item.get("type") == "question":
                compact.append(
                    {
                        "type": "q",
                        "q": str(item.get("data", {}).get("question", "")),
                        "src": str(item.get("data", {}).get("source", "")),
                    }
                )
            elif item.get("type") == "answer":
                analysis = item.get("analysis", {}) or {}
                compact.append(
                    {
                        "type": "a",
                        "user_answer": str(item.get("user_answer", "")),
                        "score": int(analysis.get("score", 0)),
                        "grade": str(analysis.get("grade", "")),
                        "similarity": float(analysis.get("similarity", 0.0)),
                        "differences": analysis.get("differences", []) or [],
                    }
                )
        return compact

    def _format_user_text(
        self, session_summary: Dict[str, Any], insights: Dict[str, Any]
    ) -> str:
        total_questions = session_summary.get("total_questions", 0)
        average_score = session_summary.get("average_score", 0)

        def join_list(values: List[str]) -> str:
            return "、".join([v for v in values if v]) or "—"

        self_intro = (
            insights.get("self_intro", {}) if isinstance(insights, dict) else {}
        )

        lines: List[str] = []
        lines.append("✅ 面試已完成｜你的本次表現分析與建議")
        lines.append(
            f"概況：完成題數 {total_questions}｜平均分 {average_score}/100｜等級 {insights.get('grade', '—')}"
        )
        lines.append(f"強項類別：{join_list(insights.get('top_categories', []))}")
        lines.append(f"待加強類別：{join_list(insights.get('weak_categories', []))}")
        lines.append("")
        lines.append("自我介紹檢視（六構面）")
        for key, title in [
            ("opening", "開場簡介"),
            ("background", "學經歷概述"),
            ("skills", "核心技能"),
            ("achievements", "代表成果"),
            ("role_match", "與職缺連結"),
            ("closing", "結語與期待"),
        ]:
            block = self_intro.get(key, {})
            status = block.get("status", "—")
            tip = block.get("tip", "")
            lines.append(f"- {title}：{status}；建議：{tip}")
        lines.append("")
        if insights.get("highlights"):
            lines.append("高分亮點：")
            for h in insights["highlights"][:3]:
                lines.append(f"- {h}")
        if insights.get("gaps"):
            lines.append("常見缺口：")
            for g in insights["gaps"][:3]:
                lines.append(f"- {g}")
        if insights.get("practice_checklist"):
            lines.append("立即練習清單：")
            for p in insights["practice_checklist"][:5]:
                lines.append(f"- {p}")
        if insights.get("resources"):
            lines.append("建議資源：")
            for r in insights["resources"][:5]:
                lines.append(f"- {r}")
        if insights.get("cta"):
            lines.append("")
            lines.append(insights["cta"])

        # 永遠附上結語，確保有收尾
        lines.append("")
        lines.append(
            "結語：恭喜完成本輪練習！建議以 1 分鐘自我介紹作為開場，答題採 STAR/SCQA 結構，收尾補充風險控管與後續計畫。輸入『重新開始』即可再練一輪。"
        )

        return "\n".join(lines)

    # 工具 -------------------------------------------------------------------
    def _safe_json(self, content: str) -> Dict[str, Any]:
        try:
            # 有時模型會包多餘文字，嘗試抓取第一個 JSON 區塊
            import re

            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                return json.loads(match.group(0))
            return json.loads(content)
        except Exception:
            # 回退為最小可用結構
            return {
                "overview": "",
                "grade": "",
                "top_categories": [],
                "weak_categories": [],
                "self_intro": {},
                "highlights": [],
                "gaps": [],
                "practice_checklist": [],
                "resources": [],
                "cta": "輸入『重新開始』立即再練一輪。",
            }


# 模組級單例，方便其他模組直接使用
flow_summarizer = None


def _get_summarizer_singleton() -> FlowSummarizer:
    global flow_summarizer
    if flow_summarizer is None:
        flow_summarizer = FlowSummarizer()
    return flow_summarizer


def generate_flow_summary(session_summary: Dict[str, Any]) -> Dict[str, Any]:
    """對外函式：生成會話總結與文本。"""
    summarizer = _get_summarizer_singleton()
    return summarizer.generate_user_summary(session_summary)
