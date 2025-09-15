#!/usr/bin/env python3
"""
MCP Events 實作
提供面試事件和系統事件的 MCP 介面
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import redis
import os

# 設定日誌
logger = logging.getLogger(__name__)

# Redis 連接
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

class MCPEventManager:
    """MCP 事件管理器"""
    
    def __init__(self):
        try:
            self.redis_client = redis.from_url(REDIS_URL)
            # 測試連接
            self.redis_client.ping()
            logger.info("✅ Redis 連接成功，用於事件管理")
        except Exception as e:
            logger.warning(f"⚠️ Redis 連接失敗: {e}")
            self.redis_client = None
    
    def emit_interview_event(self, event_type: str, session_id: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        發出面試事件
        
        Args:
            event_type: 事件類型 ("start", "answer", "end")
            session_id: 會話 ID
            data: 事件資料
        
        Returns:
            事件發送結果
        """
        try:
            if not self.redis_client:
                return {
                    "status": "error",
                    "message": "Redis 不可用，無法發送事件"
                }
            
            # 構建事件資料
            event_data = {
                "event_type": f"interview/{event_type}",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "data": data or {}
            }
            
            # 發送到 Redis
            event_key = f"mcp:events:interview:{session_id}:{event_type}"
            self.redis_client.setex(
                event_key, 
                3600,  # 1小時過期
                json.dumps(event_data, ensure_ascii=False)
            )
            
            # 添加到事件列表
            events_list_key = f"mcp:events:interview:{session_id}"
            self.redis_client.lpush(events_list_key, json.dumps(event_data, ensure_ascii=False))
            self.redis_client.expire(events_list_key, 3600)
            
            # 添加到全域事件流
            global_events_key = "mcp:events:global"
            self.redis_client.lpush(global_events_key, json.dumps(event_data, ensure_ascii=False))
            self.redis_client.ltrim(global_events_key, 0, 999)  # 保留最近1000個事件
            
            logger.info(f"✅ 發出面試事件: {event_type} for session {session_id}")
            
            return {
                "status": "success",
                "event": event_data,
                "message": f"成功發出面試事件: {event_type}"
            }
            
        except Exception as e:
            logger.error(f"發出面試事件失敗: {e}")
            return {
                "status": "error",
                "message": f"發出面試事件失敗: {str(e)}"
            }
    
    def get_interview_events(self, session_id: str, event_type: str = None) -> Dict[str, Any]:
        """
        獲取面試事件
        
        Args:
            session_id: 會話 ID
            event_type: 事件類型（可選）
        
        Returns:
            事件列表
        """
        try:
            if not self.redis_client:
                return {
                    "status": "error",
                    "message": "Redis 不可用，無法獲取事件"
                }
            
            if event_type:
                # 獲取特定類型的事件
                events_list_key = f"mcp:events:interview:{session_id}"
                raw_events = self.redis_client.lrange(events_list_key, 0, -1)
                
                events = []
                for raw_event in raw_events:
                    try:
                        event = json.loads(raw_event)
                        if event.get("event_type") == f"interview/{event_type}":
                            events.append(event)
                    except json.JSONDecodeError:
                        continue
                
                return {
                    "status": "success",
                    "session_id": session_id,
                    "event_type": event_type,
                    "events": events,
                    "count": len(events),
                    "message": f"找到 {len(events)} 個 {event_type} 事件"
                }
            else:
                # 獲取所有事件
                events_list_key = f"mcp:events:interview:{session_id}"
                raw_events = self.redis_client.lrange(events_list_key, 0, -1)
                
                events = []
                for raw_event in raw_events:
                    try:
                        event = json.loads(raw_event)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue
                
                return {
                    "status": "success",
                    "session_id": session_id,
                    "events": events,
                    "count": len(events),
                    "message": f"找到 {len(events)} 個事件"
                }
                
        except Exception as e:
            logger.error(f"獲取面試事件失敗: {e}")
            return {
                "status": "error",
                "message": f"獲取面試事件失敗: {str(e)}"
            }
    
    def emit_system_event(self, event_type: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        發出系統事件
        
        Args:
            event_type: 事件類型
            data: 事件資料
        
        Returns:
            事件發送結果
        """
        try:
            if not self.redis_client:
                return {
                    "status": "error",
                    "message": "Redis 不可用，無法發送事件"
                }
            
            # 構建事件資料
            event_data = {
                "event_type": f"system/{event_type}",
                "timestamp": datetime.now().isoformat(),
                "data": data or {}
            }
            
            # 發送到全域事件流
            global_events_key = "mcp:events:global"
            self.redis_client.lpush(global_events_key, json.dumps(event_data, ensure_ascii=False))
            self.redis_client.ltrim(global_events_key, 0, 999)  # 保留最近1000個事件
            
            logger.info(f"✅ 發出系統事件: {event_type}")
            
            return {
                "status": "success",
                "event": event_data,
                "message": f"成功發出系統事件: {event_type}"
            }
            
        except Exception as e:
            logger.error(f"發出系統事件失敗: {e}")
            return {
                "status": "error",
                "message": f"發出系統事件失敗: {str(e)}"
            }
    
    def get_global_events(self, limit: int = 50) -> Dict[str, Any]:
        """
        獲取全域事件
        
        Args:
            limit: 事件數量限制
        
        Returns:
            全域事件列表
        """
        try:
            if not self.redis_client:
                return {
                    "status": "error",
                    "message": "Redis 不可用，無法獲取事件"
                }
            
            global_events_key = "mcp:events:global"
            raw_events = self.redis_client.lrange(global_events_key, 0, limit - 1)
            
            events = []
            for raw_event in raw_events:
                try:
                    event = json.loads(raw_event)
                    events.append(event)
                except json.JSONDecodeError:
                    continue
            
            return {
                "status": "success",
                "events": events,
                "count": len(events),
                "limit": limit,
                "message": f"找到 {len(events)} 個全域事件"
            }
            
        except Exception as e:
            logger.error(f"獲取全域事件失敗: {e}")
            return {
                "status": "error",
                "message": f"獲取全域事件失敗: {str(e)}"
            }

# 創建全域實例
event_manager = MCPEventManager()

# MCP Event 函數
def emit_interview_start_event(session_id: str, interview_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """MCP Event: 發出面試開始事件"""
    return event_manager.emit_interview_event("start", session_id, interview_data)

def emit_interview_answer_event(session_id: str, answer_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """MCP Event: 發出面試回答事件"""
    return event_manager.emit_interview_event("answer", session_id, answer_data)

def emit_interview_end_event(session_id: str, end_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """MCP Event: 發出面試結束事件"""
    return event_manager.emit_interview_event("end", session_id, end_data)

def get_interview_events(session_id: str, event_type: str = None) -> Dict[str, Any]:
    """MCP Event: 獲取面試事件"""
    return event_manager.get_interview_events(session_id, event_type)

def emit_system_event(event_type: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """MCP Event: 發出系統事件"""
    return event_manager.emit_system_event(event_type, data)

def get_global_events(limit: int = 50) -> Dict[str, Any]:
    """MCP Event: 獲取全域事件"""
    return event_manager.get_global_events(limit)
