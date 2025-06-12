import logging
import json
import asyncio
from collections import deque
from typing import Dict, List, Any, Optional, Set, Union
from datetime import datetime
import threading

class LogBuffer:
    def __init__(self, max_size: int = 1000):
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.Lock()
        self.subscribers: Set = set()
    
    def add_log(self, record: logging.LogRecord):
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        
        extra_data = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename', 
                          'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated', 
                          'thread', 'threadName', 'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info']:
                try:
                    extra_data[key] = str(value) if value is not None else None
                except Exception:
                    extra_data[key] = f"<{type(value).__name__}>"
        
        if extra_data:
            log_entry["extra"] = extra_data
        
        with self.lock:
            self.buffer.append(log_entry)
        
        if self.subscribers:
            asyncio.create_task(self._notify_subscribers(log_entry))
    
    async def _notify_subscribers(self, log_entry: Dict[str, Any]):
        if not self.subscribers:
            return
            
        message = json.dumps(log_entry)
        disconnected = set()
        
        for websocket in self.subscribers.copy():
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.add(websocket)
        
        self.subscribers -= disconnected
    
    def get_logs(self, level: str = "INFO", limit: int = 100) -> List[Dict[str, Any]]:
        level_priority = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
        min_level = level_priority.get(level.upper(), 20)
        
        with self.lock:
            filtered_logs = [
                log for log in self.buffer 
                if level_priority.get(log["level"], 20) >= min_level
            ]
            return list(filtered_logs)[-limit:]
    
    def add_subscriber(self, websocket):
        self.subscribers.add(websocket)
    
    def remove_subscriber(self, websocket):
        self.subscribers.discard(websocket)

class WebSocketLogHandler(logging.Handler):
    def __init__(self, log_buffer: LogBuffer):
        super().__init__()
        self.log_buffer = log_buffer
    
    def emit(self, record: logging.LogRecord):
        try:
            self.log_buffer.add_log(record)
        except Exception:
            self.handleError(record)

log_buffer = LogBuffer()
