import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import time
from swisper_core import get_logger


class FSMStateMonitor:
    """High-performance logging-only monitoring for FSM state corruption detection"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.transition_counts = defaultdict(int)
        self.failure_counts = defaultdict(int)
        self.recent_transitions = defaultdict(lambda: deque(maxlen=5))
        self.session_metrics = defaultdict(dict)
        self.start_time = time.time()
    
    def track_state_transition(self, session_id: str, from_state: str, to_state: str, success: bool):
        """High-performance state transition tracking with logging only"""
        timestamp = datetime.now()
        transition_key = f"{from_state}→{to_state}"
        
        transition_record = {
            "from": from_state,
            "to": to_state,
            "timestamp": timestamp,
            "success": success
        }
        
        self.recent_transitions[session_id].append(transition_record)
        
        if success:
            self.transition_counts[transition_key] += 1
            self.logger.debug(f"FSM transition success: {session_id} {transition_key}")
        else:
            self.failure_counts[transition_key] += 1
            self.logger.error(f"FSM transition failure: {session_id} {transition_key}")
        
        if self.detect_infinite_loop(session_id):
            self.log_state_corruption(session_id, "infinite_loop", {
                "transition": transition_key,
                "recent_transitions": [
                    f"{t['from']}→{t['to']}" for t in list(self.recent_transitions[session_id])[-3:]
                ]
            })
    
    def detect_infinite_loop(self, session_id: str) -> bool:
        """Fast infinite loop detection using recent transition history"""
        recent = list(self.recent_transitions[session_id])
        
        if len(recent) < 3:
            return False
        
        last_transition = f"{recent[-1]['from']}→{recent[-1]['to']}"
        
        same_transition_count = sum(
            1 for t in recent 
            if f"{t['from']}→{t['to']}" == last_transition and
            t['timestamp'] > datetime.now() - timedelta(minutes=5)
        )
        
        return same_transition_count >= 3
    
    def log_state_corruption(self, session_id: str, corruption_type: str, details: Dict):
        """Log state corruption events (no external alerting)"""
        corruption_message = f"FSM State Corruption Detected - {corruption_type} in session {session_id}"
        
        if corruption_type == "infinite_loop":
            self.logger.critical(f"🚨 INFINITE LOOP DETECTED: Session {session_id} - {details}")
            recent_history = list(self.recent_transitions[session_id])
            transition_list = [f"{t['from']}→{t['to']}" for t in recent_history]
            self.logger.critical(f"Recent transition history: {transition_list}")
        else:
            self.logger.error(f"🚨 {corruption_message}: {details}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Lightweight performance metrics for health checks"""
        total_transitions = sum(self.transition_counts.values())
        total_failures = sum(self.failure_counts.values())
        uptime_hours = (time.time() - self.start_time) / 3600
        
        return {
            "uptime_hours": round(uptime_hours, 2),
            "total_transitions": total_transitions,
            "total_failures": total_failures,
            "success_rate": (total_transitions - total_failures) / max(total_transitions, 1),
            "transitions_per_hour": total_transitions / max(uptime_hours, 0.01),
            "top_failing_transitions": sorted(
                self.failure_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5],
            "active_sessions": len(self.recent_transitions),
            "most_active_transitions": sorted(
                self.transition_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
    
    def log_health_summary(self):
        """Log periodic health summary for monitoring"""
        metrics = self.get_performance_metrics()
        
        self.logger.info(f"FSM Health Summary: "
                        f"{metrics['total_transitions']} transitions, "
                        f"{metrics['success_rate']:.1%} success rate, "
                        f"{metrics['active_sessions']} active sessions")
        
        if metrics['total_failures'] > 0:
            self.logger.warning(f"FSM Failures: {metrics['total_failures']} total, "
                               f"Top failing: {metrics['top_failing_transitions'][:3]}")

fsm_monitor = FSMStateMonitor()
