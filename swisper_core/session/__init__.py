"""
Session management utilities for Swisper Core
"""

from typing import Dict, Any, Optional
from .stores import UnifiedSessionStore, PipelineSessionManager

try:
    from contract_engine.session_persistence import (
        session_manager as _original_session_manager, 
        save_pipeline_execution as _original_save_pipeline_execution, 
        get_cached_pipeline_result as _original_get_cached_pipeline_result,
        save_session_context as _original_save_session_context, 
        load_session_context as _original_load_session_context, 
        get_session_performance_metrics as _original_get_session_performance_metrics,
        cleanup_old_sessions as _original_cleanup_old_sessions
    )
    
    session_manager = _original_session_manager
    save_pipeline_execution = _original_save_pipeline_execution
    get_cached_pipeline_result = _original_get_cached_pipeline_result
    save_session_context = _original_save_session_context
    load_session_context = _original_load_session_context
    get_session_performance_metrics = _original_get_session_performance_metrics
    cleanup_old_sessions = _original_cleanup_old_sessions
    
except ImportError:
    class MockSessionManager:
        def __init__(self):
            self.pipeline_cache = {}
            self.context_cache = {}
            self.session_metrics = {}
        
        def save_pipeline_state(self, session_id: str, pipeline_name: str, result: Dict[str, Any], execution_time: Optional[float] = None):
            if session_id not in self.pipeline_cache:
                self.pipeline_cache[session_id] = {}
            
            pipeline_state = {
                "result": result,
                "timestamp": "2025-06-05T05:21:11.000000",
                "execution_time": execution_time,
                "status": result.get("status", "unknown"),
                "operation_mode": "full"
            }
            
            if pipeline_name not in self.pipeline_cache[session_id]:
                self.pipeline_cache[session_id][pipeline_name] = []
            
            self.pipeline_cache[session_id][pipeline_name].append(pipeline_state)
        
        def get_pipeline_state(self, session_id: str, pipeline_name: str):
            if session_id in self.pipeline_cache and pipeline_name in self.pipeline_cache[session_id]:
                pipeline_states = self.pipeline_cache[session_id][pipeline_name]
                if pipeline_states:
                    return pipeline_states[-1]
            return None
        
        def save_enhanced_context(self, session_id: str, context, pipeline_metadata: Optional[Dict[str, Any]] = None):
            self.context_cache[session_id] = {
                "context": context.to_dict(),
                "saved_at": "2025-06-05T05:21:11.000000",
                "pipeline_metadata": pipeline_metadata or {}
            }
        
        def load_enhanced_context(self, session_id: str):
            if session_id in self.context_cache:
                from swisper_core.types import SwisperContext
                context_data = self.context_cache[session_id]["context"]
                return SwisperContext.from_dict(context_data)
            return None
        
        def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
            total_executions = 0
            total_time = 0.0
            
            if session_id in self.pipeline_cache:
                for pipeline_states in self.pipeline_cache[session_id].values():
                    if isinstance(pipeline_states, list):
                        for state in pipeline_states:
                            total_executions += 1
                            if state.get("execution_time"):
                                total_time += state["execution_time"]
                    else:
                        total_executions += 1
                        if pipeline_states.get("execution_time"):
                            total_time += pipeline_states["execution_time"]
            
            avg_time = total_time / total_executions if total_executions > 0 else 0.0
            
            pipeline_executions = {}
            if session_id in self.pipeline_cache:
                for pipeline_name, pipeline_states in self.pipeline_cache[session_id].items():
                    if isinstance(pipeline_states, list):
                        pipeline_executions[pipeline_name] = len(pipeline_states)
                    else:
                        pipeline_executions[pipeline_name] = 1
            
            return {
                "total_pipeline_executions": total_executions,
                "total_execution_time": total_time,
                "average_execution_time": avg_time,
                "pipeline_success_rate": 1.0 if total_executions > 0 else 0.0,
                "pipeline_executions": pipeline_executions,
                "last_activity": None
            }
        
        def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
            return 0
    
    session_manager = MockSessionManager()
    
    def save_pipeline_execution(session_id: str, pipeline_name: str, result: Dict[str, Any], execution_time: Optional[float] = None) -> None:
        """Convenience function to save pipeline execution state"""
        session_manager.save_pipeline_state(session_id, pipeline_name, result, execution_time)

    def get_cached_pipeline_result(session_id: str, pipeline_name: str) -> Optional[Dict[str, Any]]:
        """Convenience function to get cached pipeline result"""
        state = session_manager.get_pipeline_state(session_id, pipeline_name)
        return state.get("result") if state else None

    def save_session_context(session_id: str, context, pipeline_metadata: Optional[Dict[str, Any]] = None) -> None:
        """Convenience function to save enhanced session context"""
        session_manager.save_enhanced_context(session_id, context, pipeline_metadata)

    def load_session_context(session_id: str):
        """Convenience function to load enhanced session context"""
        return session_manager.load_enhanced_context(session_id)

    def get_session_performance_metrics(session_id: str) -> Dict[str, Any]:
        """Convenience function to get session performance metrics"""
        return session_manager.get_session_metrics(session_id)

    def cleanup_old_sessions(max_age_hours: int = 24) -> int:
        """Convenience function to clean up old session data"""
        return session_manager.cleanup_expired_sessions(max_age_hours)

__all__ = [
    'UnifiedSessionStore', 'PipelineSessionManager', 'session_manager',
    'save_pipeline_execution', 'get_cached_pipeline_result', 'save_session_context',
    'load_session_context', 'get_session_performance_metrics', 'cleanup_old_sessions'
]
